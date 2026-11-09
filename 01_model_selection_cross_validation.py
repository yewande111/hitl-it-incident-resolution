"""Step 1. Baseline models. Compares Naive Bayes, Logistic Regression and a calibrated linear SVM with 5-fold cross validation on the 80 percent training portion only (the 20 percent test portion is never used). Also measures how reliable the Logistic Regression confidence scores are, the effect of different review thresholds, and how safe a single 70 percent threshold is for security-sensitive (Administrative rights) tickets. Output: results/cv_results.json"""
from pathlib import Path
HERE = Path(__file__).resolve().parent
DATA_FILE = HERE.parent / "dataset" / "all_tickets_processed_improved_v3.csv"
RESULTS = HERE / "results"
RESULTS.mkdir(exist_ok=True)
import json
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, f1_score

# Security-sensitive categories get a stricter review rule. Same settings as 02_transformer_cross_validation.py.
SENSITIVE = ["Administrative rights"]
GENERAL_THRESHOLD = 0.70
SENSITIVE_THRESHOLDS = [0.70, 0.80, 0.90, 0.95, 0.99]
WATCH_THRESHOLDS = [None, 0.01, 0.02, 0.05, 0.10, 0.20]
TARGET_MAX_UNCHECKED_PCT = 1.0
TARGET_MIN_ACCEPTED_CORRECT_PCT = 98.0

df = pd.read_csv(DATA_FILE).dropna()

# Same 80/20 split as before; only the 80% training portion is used here.
X_train, X_test, y_train, y_test = train_test_split(
    df["Document"], df["Topic_group"], test_size=0.2, random_state=42, stratify=df["Topic_group"]
)
X_train = X_train.reset_index(drop=True)
y_train = y_train.reset_index(drop=True)
print("training tickets used for model selection:", len(X_train))

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)


def run_fold(tr_idx, va_idx):
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    Xtr = vec.fit_transform(X_train.iloc[tr_idx])
    Xva = vec.transform(X_train.iloc[va_idx])
    ytr, yva = y_train.iloc[tr_idx], y_train.iloc[va_idx]
    models = {
        "Naive Bayes": MultinomialNB(alpha=0.3),
        "Logistic Regression": LogisticRegression(max_iter=2000, C=10),
        "Linear SVM (calibrated)": CalibratedClassifierCV(LinearSVC(C=1.0), cv=3),
    }
    out = {}
    for name, m in models.items():
        m.fit(Xtr, ytr)
        proba = m.predict_proba(Xva)
        pred = m.classes_[proba.argmax(axis=1)]
        out[name] = {
            "acc": accuracy_score(yva, pred),
            "f1": f1_score(yva, pred, average="macro"),
            "proba": proba if name == "Logistic Regression" else None,
            "classes": m.classes_,
        }
    out["va_idx"] = va_idx
    return out

folds = list(skf.split(X_train, y_train))
results = Parallel(n_jobs=5)(delayed(run_fold)(a, b) for a, b in folds)

summary = {}
for name in ["Naive Bayes", "Logistic Regression", "Linear SVM (calibrated)"]:
    accs = [r[name]["acc"] for r in results]
    f1s = [r[name]["f1"] for r in results]
    summary[name] = {
        "acc_mean": float(np.mean(accs)), "acc_sd": float(np.std(accs)),
        "f1_mean": float(np.mean(f1s)), "f1_sd": float(np.std(f1s)),
    }
    print(f"{name}: accuracy {np.mean(accs):.4f} (sd {np.std(accs):.4f}) | macro F1 {np.mean(f1s):.4f} (sd {np.std(f1s):.4f})")

# Out-of-fold Logistic Regression probabilities for every training ticket.
classes = results[0]["Logistic Regression"]["classes"]
proba = np.zeros((len(X_train), len(classes)))
for r in results:
    proba[r["va_idx"]] = r["Logistic Regression"]["proba"]
y_true = y_train.values
pred = classes[proba.argmax(axis=1)]
conf = proba.max(axis=1)
correct = pred == y_true

print("\nLogistic Regression, out-of-fold confidence reliability")
bins = [0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0001]
labels = ["<0.5", "0.5-0.6", "0.6-0.7", "0.7-0.8", "0.8-0.9", ">=0.9"]
cb = pd.cut(conf, bins=bins, labels=labels, right=False)
tab = pd.DataFrame({"bin": cb, "correct": correct}).groupby("bin", observed=True)["correct"].agg(["count", "mean"])
print(tab.round(3).to_string())

print("\nThreshold trade-off (out-of-fold, validation data only)")
thr_rows = []
for thr in [0.5, 0.6, 0.7, 0.8, 0.9]:
    low = conf < thr
    row = {
        "threshold": thr,
        "flagged_pct": float(low.mean() * 100),
        "acc_kept": float(correct[~low].mean()),
        "acc_flagged": float(correct[low].mean()),
    }
    thr_rows.append(row)
    print(f"{thr}: flagged {row['flagged_pct']:.1f}% | accuracy kept {row['acc_kept']:.3f} | accuracy flagged {row['acc_flagged']:.3f}")


def review_flags(proba, classes, general, sensitive=None, watch=None):
    """True where a ticket goes to the reviewer. 'sensitive' is the stricter threshold for tickets predicted as a
    sensitive category; 'watch' sends any other ticket whose sensitive-category probability is at least this value."""
    sens_idx = [list(classes).index(c) for c in SENSITIVE]
    pred_idx = proba.argmax(axis=1)
    conf = proba.max(axis=1)
    pred_sens = np.isin(pred_idx, sens_idx)
    flag = conf < general
    if sensitive is not None:
        flag |= pred_sens & (conf < sensitive)
    if watch is not None:
        flag |= ~pred_sens & (proba[:, sens_idx].max(axis=1) >= watch)
    return flag


def security_stats(proba, classes, y_true, flag):
    pred = classes[proba.argmax(axis=1)]
    wrong = pred != y_true
    true_s = np.isin(y_true, SENSITIVE)
    pred_s = np.isin(pred, SENSITIVE)
    accepted_s = pred_s & ~flag
    unchecked = int((true_s & wrong & ~flag).sum())
    return {
        "reviewed_pct": float(flag.mean() * 100),
        "sensitive_tickets": int(true_s.sum()),
        "sensitive_reviewed_pct": float(flag[true_s].mean() * 100),
        "sensitive_unchecked_errors": unchecked,
        "sensitive_unchecked_error_pct": float(unchecked / true_s.sum() * 100),
        "accepted_as_sensitive": int(accepted_s.sum()),
        "accepted_as_sensitive_correct_pct": float((~wrong[accepted_s]).mean() * 100) if accepted_s.any() else float("nan"),
        "wrongly_accepted_as_sensitive": int((accepted_s & wrong).sum()),
    }


def security_grid(proba, classes, y_true):
    rows = []
    for s in SENSITIVE_THRESHOLDS:
        for w in WATCH_THRESHOLDS:
            flag = review_flags(proba, classes, GENERAL_THRESHOLD, s, w)
            rows.append({"sensitive_threshold": s, "watch_threshold": w, **security_stats(proba, classes, y_true, flag)})
    ok = [r for r in rows if r["sensitive_unchecked_error_pct"] <= TARGET_MAX_UNCHECKED_PCT
          and r["accepted_as_sensitive_correct_pct"] >= TARGET_MIN_ACCEPTED_CORRECT_PCT]
    if ok:
        chosen = min(ok, key=lambda r: r["reviewed_pct"])
    else:
        chosen = [r for r in rows if r["sensitive_threshold"] == max(SENSITIVE_THRESHOLDS)
                  and r["watch_threshold"] == min(w for w in WATCH_THRESHOLDS if w is not None)][0]
    return rows, chosen, bool(ok)


print(f"\nSecurity-sensitive tickets ({', '.join(SENSITIVE)}) with one {GENERAL_THRESHOLD:.0%} threshold for everything")
single = security_stats(proba, classes, y_true, review_flags(proba, classes, GENERAL_THRESHOLD))
for k, v in single.items():
    print(f"  {k}: {v:.1f}" if isinstance(v, float) else f"  {k}: {v}")

grid, chosen, met = security_grid(proba, classes, y_true)
print(f"\nSecurity rule grid (general threshold stays at {GENERAL_THRESHOLD:.0%})")
print(pd.DataFrame(grid)[["sensitive_threshold", "watch_threshold", "reviewed_pct", "sensitive_reviewed_pct",
                          "sensitive_unchecked_errors", "accepted_as_sensitive_correct_pct"]].round(
    {"reviewed_pct": 1, "sensitive_reviewed_pct": 1, "accepted_as_sensitive_correct_pct": 1}).to_string(index=False))
print("chosen rule:", {k: chosen[k] for k in ["sensitive_threshold", "watch_threshold", "reviewed_pct"]},
      "| targets met" if met else "| targets NOT met, strictest rule used")

per_category = {}
for c in classes:
    m = y_true == c
    per_category[c] = {"tickets": int(m.sum()), "recall": float(correct[m].mean()),
                       "mean_confidence": float(conf[m].mean())}

json.dump({"summary": summary, "thresholds": thr_rows,
           "bins": {k: {"count": int(v["count"]), "acc": float(v["mean"])} for k, v in tab.iterrows()},
           "per_category": per_category,
           "security": {"sensitive_categories": SENSITIVE, "general_threshold": GENERAL_THRESHOLD,
                        "single_threshold": single, "grid": grid, "chosen": chosen, "targets_met": met,
                        "targets": {"max_unchecked_pct": TARGET_MAX_UNCHECKED_PCT,
                                    "min_accepted_correct_pct": TARGET_MIN_ACCEPTED_CORRECT_PCT}}},
          open(RESULTS / "cv_results.json", "w"), indent=2)
pred_df = pd.DataFrame(proba, columns=[f"p_{c}" for c in classes])
pred_df.insert(0, "confidence", conf)
pred_df.insert(0, "predicted_category", pred)
pred_df.insert(0, "true_category", y_true)
pred_df.to_csv(RESULTS / "lr_cv_predictions.csv", index=False)
print("saved", RESULTS / "cv_results.json", "and lr_cv_predictions.csv")
