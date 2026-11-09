"""Step 2. Main model: DistilBERT, a transformer-based encoder model, fine-tuned to classify the tickets.
Run this on Kaggle (free GPU T4) - see README.txt. It does not need a paid service.

Uses 5-fold cross validation on the 80 percent training portion only (same split and folds as step 1, so the results
can be compared with the baselines). In each fold:
  - 10 percent of the fold's training tickets are kept aside as a calibration set,
  - DistilBERT is fine-tuned on the rest,
  - temperature scaling is fitted on the calibration set so the confidence scores match how often the model is right,
  - the held-out fold is predicted.
It then checks confidence reliability, the review thresholds, and the stricter rule for security-sensitive
(Administrative rights) tickets, and finds real examples of high, medium and low confidence with the words that
drove each prediction. The 20 percent test portion is never used here.

Outputs (in /kaggle/working on Kaggle, otherwise code/results):
  transformer_cv_results.json     all figures used in Chapter Three
  transformer_cv_predictions.csv  held-out (out-of-fold) prediction and probabilities for every training ticket

Set the environment variable QUICK_TEST=1 to run a tiny version on a laptop CPU just to check the code works.
"""
import os
import glob
import json
import time
import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader
from scipy.special import softmax, log_softmax
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.metrics import accuracy_score, f1_score
from transformers import AutoTokenizer, AutoModelForSequenceClassification, get_linear_schedule_with_warmup

QUICK_TEST = os.environ.get("QUICK_TEST") == "1"

# Model settings. Standard fine-tuning values for DistilBERT, fixed in advance and not tuned.
MODEL_NAME = "distilbert-base-uncased"
MAX_LEN = 64 if QUICK_TEST else 256       # word pieces; only 1.4% of training tickets are longer than this
BATCH_SIZE = 32
EPOCHS = 1 if QUICK_TEST else 3
LEARNING_RATE = 5e-5
WEIGHT_DECAY = 0.01
WARMUP_SHARE = 0.1                         # learning rate warms up over the first 10% of steps
CALIBRATION_SHARE = 0.1                    # share of each fold's training tickets kept for temperature scaling
SEED = 42

# Security-sensitive categories get a stricter review rule. Same settings as 01_model_selection_cross_validation.py.
SENSITIVE = ["Administrative rights"]
GENERAL_THRESHOLD = 0.70
SENSITIVE_THRESHOLDS = [0.70, 0.80, 0.90, 0.95, 0.99]
WATCH_THRESHOLDS = [None, 0.01, 0.02, 0.05, 0.10, 0.20]
TARGET_MAX_UNCHECKED_PCT = 1.0             # at most 1% of Administrative rights tickets wrong and not reviewed
TARGET_MIN_ACCEPTED_CORRECT_PCT = 98.0     # tickets auto-accepted as Administrative rights at least 98% correct

DATA_NAME = "all_tickets_processed_improved_v3.csv"
HERE = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()


def find_data():
    for pattern in [f"/kaggle/input/**/{DATA_NAME}", f"/content/**/{DATA_NAME}",
                    str(HERE.parent / "dataset" / DATA_NAME), str(HERE / DATA_NAME)]:
        hits = glob.glob(pattern, recursive=True)
        if hits:
            return hits[0]
    raise FileNotFoundError(f"Cannot find {DATA_NAME}. On Kaggle, add the dataset 'IT Service Ticket Classification "
                            "Dataset' with '+ Add Input'. On Colab, upload the csv file first.")


OUT = Path("/kaggle/working") if Path("/kaggle/working").exists() else HERE / "results"
OUT.mkdir(exist_ok=True)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
USE_AMP = DEVICE.type == "cuda"
if DEVICE.type != "cuda" and not QUICK_TEST and os.environ.get("ALLOW_CPU") != "1":
    raise SystemExit("No GPU found. On Kaggle open Settings > Accelerator and choose GPU T4 x2 (or P100), then run again. "
                     "Training on a laptop CPU would take days.")
print("device:", DEVICE, "| quick test" if QUICK_TEST else "")


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


# ---------------------------------------------------------------- data (same split and folds as step 1)
df = pd.read_csv(find_data()).dropna()
X_train, X_test, y_train, y_test = train_test_split(
    df["Document"], df["Topic_group"], test_size=0.2, random_state=42, stratify=df["Topic_group"]
)
X_train = X_train.reset_index(drop=True)
y_train = y_train.reset_index(drop=True)
if QUICK_TEST:
    keep, _ = train_test_split(np.arange(len(X_train)), train_size=1000, random_state=SEED, stratify=y_train)
    X_train, y_train = X_train.iloc[keep].reset_index(drop=True), y_train.iloc[keep].reset_index(drop=True)
print("training tickets used:", len(X_train))

CLASSES = np.array(sorted(y_train.unique()))        # same order as scikit-learn uses
y = np.searchsorted(CLASSES, y_train.values)
texts = X_train.tolist()

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
ENC = tokenizer(texts, truncation=True, max_length=MAX_LEN)["input_ids"]
print("tickets cut short at", MAX_LEN, "word pieces:", f"{np.mean([len(e) >= MAX_LEN for e in ENC]):.1%}")


def collate(batch):
    """Pads each batch only to its longest ticket, which keeps training fast."""
    n = max(len(ids) for ids, _ in batch)
    input_ids = torch.full((len(batch), n), tokenizer.pad_token_id, dtype=torch.long)
    mask = torch.zeros((len(batch), n), dtype=torch.long)
    for i, (ids, _) in enumerate(batch):
        input_ids[i, :len(ids)] = torch.tensor(ids)
        mask[i, :len(ids)] = 1
    labels = torch.tensor([lab for _, lab in batch], dtype=torch.long)
    return {"input_ids": input_ids, "attention_mask": mask, "labels": labels}


def make_loader(encoded, labels, shuffle, batch_size=BATCH_SIZE, seed=SEED):
    g = torch.Generator()
    g.manual_seed(seed)
    return DataLoader(list(zip(encoded, labels)), batch_size=batch_size, shuffle=shuffle,
                      collate_fn=collate, generator=g)


# ---------------------------------------------------------------- training and prediction
def train_model(idx, seed):
    set_seed(seed)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=len(CLASSES)).to(DEVICE)
    loader = make_loader([ENC[i] for i in idx], y[idx], shuffle=True, seed=seed)
    optimiser = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    total = len(loader) * EPOCHS
    scheduler = get_linear_schedule_with_warmup(optimiser, int(WARMUP_SHARE * total), total)
    scaler = (torch.amp.GradScaler("cuda", enabled=USE_AMP) if hasattr(torch, "amp") and hasattr(torch.amp, "GradScaler")
              else torch.cuda.amp.GradScaler(enabled=USE_AMP))
    model.train()
    for epoch in range(EPOCHS):
        start, running = time.time(), 0.0
        for step, batch in enumerate(loader, 1):
            batch = {k: v.to(DEVICE) for k, v in batch.items()}
            with torch.autocast(device_type=DEVICE.type, dtype=torch.float16, enabled=USE_AMP):
                loss = model(**batch).loss
            optimiser.zero_grad()
            scaler.scale(loss).backward()
            scaler.unscale_(optimiser)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optimiser)
            scaler.update()
            scheduler.step()
            running += loss.item()
            if step % 200 == 0:
                print(f"    epoch {epoch + 1} step {step}/{len(loader)} loss {running / step:.4f}")
        print(f"    epoch {epoch + 1} done, loss {running / len(loader):.4f}, {(time.time() - start) / 60:.1f} min")
    model.eval()
    return model


@torch.no_grad()
def logits_for(model, encoded):
    out = []
    for batch in make_loader(encoded, np.zeros(len(encoded), dtype=int), shuffle=False, batch_size=128):
        batch = {k: v.to(DEVICE) for k, v in batch.items() if k != "labels"}
        with torch.autocast(device_type=DEVICE.type, dtype=torch.float16, enabled=USE_AMP):
            out.append(model(**batch).logits.float().cpu().numpy())
    return np.concatenate(out)


def proba_for_texts(model, temperature, text_list):
    enc = tokenizer(text_list, truncation=True, max_length=MAX_LEN)["input_ids"]
    return softmax(logits_for(model, enc) / temperature, axis=1)


# ---------------------------------------------------------------- calibration
def fit_temperature(logits, labels):
    """Temperature scaling (Guo et al., 2017): one number T that divides the scores before they become
    percentages. T is chosen to give the best log loss on the calibration tickets. It never changes the predicted
    category, only how confident the model says it is."""
    grid = np.round(np.arange(0.50, 5.001, 0.01), 2)
    nll = [-log_softmax(logits / t, axis=1)[np.arange(len(labels)), labels].mean() for t in grid]
    return float(grid[int(np.argmin(nll))])


def expected_calibration_error(proba, labels, n_bins=15):
    conf, correct = proba.max(axis=1), proba.argmax(axis=1) == labels
    edges = np.linspace(0, 1, n_bins + 1)
    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.any():
            total += m.mean() * abs(correct[m].mean() - conf[m].mean())
    return float(total)


# ---------------------------------------------------------------- examples for Table 3.4
def key_words(model, temperature, text, cls, top=3, max_words=200):
    """Removes each word in turn and measures how much the probability of the predicted category falls.
    The words whose removal lowers it most are the ones that drove the prediction."""
    words = text.split()[:max_words]
    base = proba_for_texts(model, temperature, [" ".join(words)])[0, cls]
    variants = [" ".join(words[:i] + words[i + 1:]) for i in range(len(words))]
    drops = base - proba_for_texts(model, temperature, variants)[:, cls]
    best = {}
    for w, d in zip(words, drops):
        best[w] = max(best.get(w, -1.0), float(d))
    return [w for w, d in sorted(best.items(), key=lambda kv: -kv[1])[:top] if d > 0]


def confidence_examples(model, temperature, idx, proba):
    conf, pred = proba.max(axis=1), proba.argmax(axis=1)
    correct = pred == y[idx]
    groups = {"High": (conf > 0.97) & correct,
              "Medium": (conf >= 0.60) & (conf < 0.70),
              "Low": (conf < 0.45) & ~correct}
    rng = np.random.default_rng(1)
    out = []
    for level, m in groups.items():
        if not m.any():
            continue
        j = int(rng.choice(np.flatnonzero(m)))
        order = np.argsort(-proba[j])
        text = texts[idx[j]]
        out.append({
            "level": level, "text": text, "words": len(text.split()),
            "key_words": key_words(model, temperature, text, int(order[0])),
            "predicted": CLASSES[order[0]], "confidence": float(proba[j, order[0]]),
            "second": CLASSES[order[1]], "second_confidence": float(proba[j, order[1]]),
            "true": CLASSES[y[idx[j]]],
        })
        print(f"  {level}: {out[-1]['predicted']} {out[-1]['confidence']:.0%} (true {out[-1]['true']}) "
              f"key words {out[-1]['key_words']}")
    return out


# ---------------------------------------------------------------- security rule (same as step 1)
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


# ---------------------------------------------------------------- cross validation
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
oof = np.zeros((len(texts), len(CLASSES)))
oof_raw = np.zeros_like(oof)
fold_rows, examples = [], []
run_start = time.time()
for fold, (tr, va) in enumerate(skf.split(texts, y)):
    print(f"\nFold {fold + 1} of 5: {len(tr)} training tickets, {len(va)} held out")
    start = time.time()
    tr_fit, tr_cal = train_test_split(tr, test_size=CALIBRATION_SHARE, random_state=SEED, stratify=y[tr])
    model = train_model(tr_fit, SEED + fold)
    temperature = fit_temperature(logits_for(model, [ENC[i] for i in tr_cal]), y[tr_cal])
    va_logits = logits_for(model, [ENC[i] for i in va])
    oof_raw[va] = softmax(va_logits, axis=1)
    oof[va] = softmax(va_logits / temperature, axis=1)
    pred = oof[va].argmax(axis=1)
    row = {"fold": fold + 1, "accuracy": float(accuracy_score(y[va], pred)),
           "macro_f1": float(f1_score(y[va], pred, average="macro")), "temperature": temperature,
           "ece_before": expected_calibration_error(oof_raw[va], y[va]),
           "ece_after": expected_calibration_error(oof[va], y[va]),
           "minutes": (time.time() - start) / 60}
    fold_rows.append(row)
    print(f"  accuracy {row['accuracy']:.4f} | macro F1 {row['macro_f1']:.4f} | temperature {temperature:.2f} | "
          f"ECE {row['ece_before']:.4f} -> {row['ece_after']:.4f} | {row['minutes']:.1f} min")
    if fold == 0:
        print("  confidence examples from this fold's held-out tickets:")
        examples = confidence_examples(model, temperature, va, oof[va])
    del model
    if DEVICE.type == "cuda":
        torch.cuda.empty_cache()

# ---------------------------------------------------------------- results
accs = [r["accuracy"] for r in fold_rows]
f1s = [r["macro_f1"] for r in fold_rows]
summary = {"acc_mean": float(np.mean(accs)), "acc_sd": float(np.std(accs)),
           "f1_mean": float(np.mean(f1s)), "f1_sd": float(np.std(f1s))}
print(f"\nDistilBERT: accuracy {summary['acc_mean']:.4f} (sd {summary['acc_sd']:.4f}) | "
      f"macro F1 {summary['f1_mean']:.4f} (sd {summary['f1_sd']:.4f})")

y_true = CLASSES[y]
pred = oof.argmax(axis=1)
conf = oof.max(axis=1)
correct = pred == y
calibration = {"temperatures": [r["temperature"] for r in fold_rows],
               "ece_before": expected_calibration_error(oof_raw, y),
               "ece_after": expected_calibration_error(oof, y)}
print(f"calibration error (ECE) before {calibration['ece_before']:.4f}, after temperature scaling "
      f"{calibration['ece_after']:.4f}")

bins = [0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0001]
labels = ["<0.5", "0.5-0.6", "0.6-0.7", "0.7-0.8", "0.8-0.9", ">=0.9"]


def bin_table(proba):
    c = proba.max(axis=1)
    ok = proba.argmax(axis=1) == y
    cb = pd.cut(c, bins=bins, labels=labels, right=False)
    tab = pd.DataFrame({"bin": cb, "correct": ok, "conf": c}).groupby("bin", observed=False).agg(
        count=("correct", "size"), acc=("correct", "mean"), mean_conf=("conf", "mean"))
    return {k: {"count": int(v["count"]), "acc": float(v["acc"]) if v["count"] else None,
                "mean_conf": float(v["mean_conf"]) if v["count"] else None} for k, v in tab.iterrows()}


bins_cal, bins_raw = bin_table(oof), bin_table(oof_raw)
print("\nConfidence compared with accuracy (after temperature scaling)")
for k, v in bins_cal.items():
    print(f"  {k}: {v['count']} tickets, correct {v['acc'] if v['acc'] is None else round(v['acc'], 3)}")

print("\nThreshold trade-off")
thr_rows = []
for thr in [0.5, 0.6, 0.7, 0.8, 0.9]:
    low = conf < thr
    row = {"threshold": thr, "flagged_pct": float(low.mean() * 100),
           "acc_kept": float(correct[~low].mean()) if (~low).any() else None,
           "acc_flagged": float(correct[low].mean()) if low.any() else None}
    thr_rows.append(row)
    print(f"  {thr}: flagged {row['flagged_pct']:.1f}% | correct kept {row['acc_kept']} | correct flagged {row['acc_flagged']}")

print(f"\nSecurity-sensitive tickets ({', '.join(SENSITIVE)}) with one {GENERAL_THRESHOLD:.0%} threshold for everything")
single = security_stats(oof, CLASSES, y_true, review_flags(oof, CLASSES, GENERAL_THRESHOLD))
for k, v in single.items():
    print(f"  {k}: {v:.1f}" if isinstance(v, float) else f"  {k}: {v}")
grid, chosen, met = security_grid(oof, CLASSES, y_true)
print(f"\nSecurity rule grid (general threshold stays at {GENERAL_THRESHOLD:.0%})")
print(pd.DataFrame(grid)[["sensitive_threshold", "watch_threshold", "reviewed_pct", "sensitive_reviewed_pct",
                          "sensitive_unchecked_errors", "accepted_as_sensitive_correct_pct"]].round(
    {"reviewed_pct": 1, "sensitive_reviewed_pct": 1, "accepted_as_sensitive_correct_pct": 1}).to_string(index=False))
print("chosen rule:", {k: chosen[k] for k in ["sensitive_threshold", "watch_threshold", "reviewed_pct"]},
      "| targets met" if met else "| targets NOT met, strictest rule used")

per_category = {c: {"tickets": int((y_true == c).sum()), "recall": float(correct[y_true == c].mean()),
                    "mean_confidence": float(conf[y_true == c].mean())} for c in CLASSES}
words = np.array([len(t.split()) for t in texts])
word_counts = {"mean_words_conf_90_plus": float(words[conf >= 0.9].mean()) if (conf >= 0.9).any() else None,
               "mean_words_conf_below_70": float(words[conf < 0.7].mean()) if (conf < 0.7).any() else None}

results = {
    "model": MODEL_NAME, "quick_test": QUICK_TEST,
    "settings": {"max_len": MAX_LEN, "batch_size": BATCH_SIZE, "epochs": EPOCHS, "learning_rate": LEARNING_RATE,
                 "weight_decay": WEIGHT_DECAY, "warmup_share": WARMUP_SHARE, "calibration_share": CALIBRATION_SHARE,
                 "seed": SEED, "device": str(torch.cuda.get_device_name(0) if USE_AMP else DEVICE),
                 "minutes_total": (time.time() - run_start) / 60},
    "folds": fold_rows, "summary": summary, "calibration": calibration,
    "bins": bins_cal, "bins_uncalibrated": bins_raw, "thresholds": thr_rows,
    "security": {"sensitive_categories": SENSITIVE, "general_threshold": GENERAL_THRESHOLD,
                 "single_threshold": single, "grid": grid, "chosen": chosen, "targets_met": met,
                 "targets": {"max_unchecked_pct": TARGET_MAX_UNCHECKED_PCT,
                             "min_accepted_correct_pct": TARGET_MIN_ACCEPTED_CORRECT_PCT}},
    "per_category": per_category, "examples": examples, "word_counts": word_counts,
}
json.dump(results, open(OUT / "transformer_cv_results.json", "w"), indent=2)

pred_df = pd.DataFrame(oof, columns=[f"p_{c}" for c in CLASSES])
pred_df.insert(0, "confidence", conf)
pred_df.insert(0, "predicted_category", CLASSES[pred])
pred_df.insert(0, "true_category", y_true)
pred_df.to_csv(OUT / "transformer_cv_predictions.csv", index=False)
print(f"\nsaved {OUT / 'transformer_cv_results.json'} and transformer_cv_predictions.csv "
      f"({(time.time() - run_start) / 60:.0f} minutes in total)")
