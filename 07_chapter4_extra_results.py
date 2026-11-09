"""Step 7. Extra results for Chapter Four that step 5 does not produce. Runs on a laptop in under a minute.

  1. AI only results for each category on the test portion (precision, recall, F1)
  2. How well the calibrated confidence matched the actual accuracy on the test portion (bins and ECE)
  3. The threshold check promised in Section 3.7: general thresholds from 50 to 90 percent, applied to the test
     portion, with the share of tickets reviewed, the accuracy of kept and reviewed tickets, and the final accuracy
     with a perfect reviewer and with a reviewer who overturns 10 percent and misses 10 percent (100 runs each,
     the same modelled reviewer and random draws as step 5)
  4. Which part of the security rule sent each extra ticket to review

The threshold of 70 percent and the security rule were fixed on the training portion. The check in part 3 only shows
how sensitive the results are to that choice; it is not used to pick a new threshold.

Inputs:  results/test_predictions.csv, results/transformer_cv_results.json
Output:  results/chapter4_extra_results.json
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
RUNS = 100

df = pd.read_csv(RESULTS / "test_predictions.csv")
security = json.load(open(RESULTS / "transformer_cv_results.json"))["security"]
SENSITIVE = security["sensitive_categories"]
GENERAL = security["general_threshold"]
S_THR = security["chosen"]["sensitive_threshold"]
W_THR = security["chosen"]["watch_threshold"]

classes = np.array([c[2:] for c in df.columns if c.startswith("p_")])
proba = df[[f"p_{c}" for c in classes]].to_numpy()
n_cls = len(classes)
true = np.searchsorted(classes, df["true_category"].to_numpy())
pred = proba.argmax(axis=1)
conf = proba.max(axis=1)
right = pred == true
sens_idx = np.searchsorted(classes, SENSITIVE)
pred_sens = np.isin(pred, sens_idx)
true_sens = np.isin(true, sens_idx)
out = {"tickets": len(df)}

# ---------------------------------------------------------------- 1. per category, AI only
rows = []
for k, c in enumerate(classes):
    tp = int(((pred == k) & (true == k)).sum())
    n_pred, n_true = int((pred == k).sum()), int((true == k).sum())
    p = tp / n_pred if n_pred else 0.0
    r = tp / n_true if n_true else 0.0
    rows.append({"category": c, "tickets": n_true, "precision": p * 100, "recall": r * 100,
                 "f1": (2 * p * r / (p + r) * 100) if p + r else 0.0,
                 "low_confidence_pct": float((conf[true == k] < GENERAL).mean() * 100)})
out["per_category"] = rows

# where the Administrative rights tickets went when the model was wrong
k = sens_idx[0]
wrong_sens = true_sens & ~right
out["admin_rights_wrong_predicted_as"] = {classes[j]: int(((pred == j) & wrong_sens).sum())
                                          for j in range(n_cls) if ((pred == j) & wrong_sens).any()}
wrong_grant = pred_sens & ~right
out["admin_rights_wrong_grants_true_category"] = {classes[j]: int(((true == j) & wrong_grant).sum())
                                                  for j in range(n_cls) if ((true == j) & wrong_grant).any()}

# ---------------------------------------------------------------- 2. calibration on the test portion
edges = [0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0001]
labels = ["<0.5", "0.5-0.6", "0.6-0.7", "0.7-0.8", "0.8-0.9", ">=0.9"]
bins = {}
for lo, hi, lab in zip(edges[:-1], edges[1:], labels):
    m = (conf >= lo) & (conf < hi)
    bins[lab] = {"count": int(m.sum()), "share_pct": float(m.mean() * 100),
                 "mean_conf": float(conf[m].mean() * 100) if m.any() else None,
                 "acc": float(right[m].mean() * 100) if m.any() else None}
out["bins"] = bins
ece_edges = np.linspace(0, 1, 16)                  # 15 equal-width bins, the usual choice
ece = 0.0
for lo, hi in zip(ece_edges[:-1], ece_edges[1:]):
    m = (conf > lo) & (conf <= hi)
    if m.any():
        ece += m.mean() * abs(conf[m].mean() - right[m].mean())
out["ece_pct"] = float(ece * 100)
out["mean_confidence_pct"] = float(conf.mean() * 100)
out["ai_accuracy_pct"] = float(right.mean() * 100)


# ---------------------------------------------------------------- 3. threshold check
def reviewer_answers(run, overturn, miss):
    rng = np.random.default_rng(run)                # same draws as step 5
    u_overturn = rng.random(len(df))
    u_miss = rng.random(len(df))
    other = (true + rng.integers(1, n_cls, len(df))) % n_cls
    return np.where(right, np.where(u_overturn < overturn, other, true), np.where(u_miss < miss, pred, true))


def final_accuracy(reviewed, overturn, miss):
    accs = []
    for run in range(RUNS):
        final = np.where(reviewed, reviewer_answers(run, overturn, miss), pred)
        accs.append((final == true).mean() * 100)
    return float(np.mean(accs)), float(np.std(accs, ddof=1))


thr_rows = []
for t in [0.5, 0.6, 0.7, 0.8, 0.9]:
    reviewed = conf < t
    row = {"threshold_pct": int(t * 100), "reviewed_pct": float(reviewed.mean() * 100),
           "reviewed_tickets": int(reviewed.sum()),
           "acc_kept": float(right[~reviewed].mean() * 100),
           "acc_sent": float(right[reviewed].mean() * 100) if reviewed.any() else None,
           "admin_left_wrong_unreviewed": int((true_sens & ~right & ~reviewed).sum())}
    for o, m in [(0, 0), (0.10, 0.10), (0.20, 0.20)]:
        mean, sd = final_accuracy(reviewed, o, m)
        key = f"{int(o * 100)}_{int(m * 100)}"
        row[f"acc_{key}"] = mean
        row[f"acc_{key}_sd"] = sd
        row[f"gain_per_100_{key}"] = (mean - out["ai_accuracy_pct"]) / 100 * len(df) / reviewed.sum() * 100
    thr_rows.append(row)
out["thresholds"] = thr_rows

# ---------------------------------------------------------------- 4. what the security rule added
general = conf < GENERAL
strict = pred_sens & (conf < S_THR) & ~general
watch = (~pred_sens & (proba[:, sens_idx].max(axis=1) >= W_THR) & ~general) if W_THR is not None \
    else np.zeros(len(df), dtype=bool)
sec = general | strict | watch
out["security_rule"] = {
    "general_only": int(general.sum()),
    "added_by_strict_threshold": int(strict.sum()),
    "added_by_watch_value": int(watch.sum()),
    "total_reviewed": int(sec.sum()),
    "admin_tickets": int(true_sens.sum()),
    "admin_tickets_reviewed_selective": int((true_sens & general).sum()),
    "admin_tickets_reviewed_security": int((true_sens & sec).sum()),
    "admin_wrong_ai": int((true_sens & ~right).sum()),
    "admin_wrong_caught_selective": int((true_sens & ~right & general).sum()),
    "admin_wrong_caught_security": int((true_sens & ~right & sec).sum()),
    "extra_reviewed_ai_was_right": int((sec & ~general & right).sum()),
    "extra_reviewed_ai_was_wrong": int((sec & ~general & ~right).sum()),
}

json.dump(out, open(RESULTS / "chapter4_extra_results.json", "w"), indent=2)

pd.set_option("display.width", 200)
print(f"AI only accuracy on the test portion: {out['ai_accuracy_pct']:.2f}%  |  ECE {out['ece_pct']:.2f}%")
print("\nPer category (AI only)\n", pd.DataFrame(rows).round(1).to_string(index=False))
print("\nAdministrative rights tickets the model got wrong, by predicted category:",
      out["admin_rights_wrong_predicted_as"])
print("Tickets wrongly placed in Administrative rights, by true category:",
      out["admin_rights_wrong_grants_true_category"])
print("\nConfidence bins (test)\n", pd.DataFrame(bins).T.round(1).to_string())
print("\nThreshold check (test)\n", pd.DataFrame(thr_rows).round(2).to_string(index=False))
print("\nSecurity rule\n", json.dumps(out["security_rule"], indent=1))
print("\nsaved", RESULTS / "chapter4_extra_results.json")
