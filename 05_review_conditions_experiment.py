"""Step 5. The experiment: compares four conditions on exactly the same test tickets. Runs on a laptop in a few minutes.

  1. AI only                              the model's category is final
  2. Selective review                     tickets below the 70 percent confidence threshold go to the reviewer
  3. Selective review + security rule     as 2, plus the stricter rule for Administrative rights tickets
  4. Full review                          every ticket goes to the reviewer

The reviewer is modelled, not a real person. When a ticket is reviewed:
  - if the model was right, the reviewer wrongly changes it to another category with probability OVERTURN
  - if the model was wrong, the reviewer fails to correct it with probability MISS
Each of OVERTURN and MISS takes the values 0, 5, 10 and 20 percent (16 settings), and each setting is run 100 times.
In each run the same random draws are used for every condition (common random numbers), so differences between
conditions come from which tickets are reviewed and not from luck.

Inputs:  results/test_predictions.csv (from step 4) and results/transformer_cv_results.json (from step 2, which holds
         the security rule chosen on the training portion)
Outputs: results/experiment_results.json and results/experiment_summary.csv

The input and output files can be changed with PREDICTIONS_FILE, RULES_FILE and OUT_PREFIX (used to check the code).
"""
import os
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
PREDICTIONS_FILE = Path(os.environ.get("PREDICTIONS_FILE", RESULTS / "test_predictions.csv"))
RULES_FILE = Path(os.environ.get("RULES_FILE", RESULTS / "transformer_cv_results.json"))
OUT_PREFIX = os.environ.get("OUT_PREFIX", str(RESULTS / "experiment"))

OVERTURN_RATES = [0.0, 0.05, 0.10, 0.20]
MISS_RATES = [0.0, 0.05, 0.10, 0.20]
RUNS = 100
COMPARISONS = [("AI only", "Selective review"),
               ("Selective review", "Selective review + security rule"),
               ("Selective review + security rule", "Full review"),
               ("AI only", "Full review")]

df = pd.read_csv(PREDICTIONS_FILE)
security = json.load(open(RULES_FILE))["security"]
SENSITIVE = security["sensitive_categories"]
GENERAL = security["general_threshold"]
S_THR = security["chosen"]["sensitive_threshold"]
W_THR = security["chosen"]["watch_threshold"]
print(f"{len(df)} tickets | general threshold {GENERAL:.0%} | security rule: Administrative rights predictions need "
      f"{S_THR:.0%}, other tickets reviewed if Administrative rights probability >= "
      f"{'none' if W_THR is None else f'{W_THR:.0%}'}")

classes = np.array([c[2:] for c in df.columns if c.startswith("p_")])
proba = df[[f"p_{c}" for c in classes]].to_numpy()
n_cls = len(classes)
true = np.searchsorted(classes, df["true_category"].to_numpy())
pred = proba.argmax(axis=1)
conf = proba.max(axis=1)
sens_idx = np.searchsorted(classes, SENSITIVE)
pred_sens = np.isin(pred, sens_idx)
true_sens = np.isin(true, sens_idx)

security_flag = conf < GENERAL
security_flag |= pred_sens & (conf < S_THR)
if W_THR is not None:
    security_flag |= ~pred_sens & (proba[:, sens_idx].max(axis=1) >= W_THR)
REVIEWED = {
    "AI only": np.zeros(len(df), dtype=bool),
    "Selective review": conf < GENERAL,
    "Selective review + security rule": security_flag,
    "Full review": np.ones(len(df), dtype=bool),
}


def measures(final, reviewed):
    cm = np.bincount(true * n_cls + final, minlength=n_cls * n_cls).reshape(n_cls, n_cls)
    tp = np.diag(cm).astype(float)
    precision = np.divide(tp, cm.sum(axis=0), out=np.zeros(n_cls), where=cm.sum(axis=0) > 0)
    recall = np.divide(tp, cm.sum(axis=1), out=np.zeros(n_cls), where=cm.sum(axis=1) > 0)
    f1 = np.divide(2 * precision * recall, precision + recall, out=np.zeros(n_cls), where=(precision + recall) > 0)
    wrong = final != true
    final_sens = np.isin(final, sens_idx)
    return {
        "accuracy": tp.sum() / len(true) * 100,
        "misclassification": wrong.mean() * 100,
        "macro_precision": precision.mean() * 100,
        "macro_recall": recall.mean() * 100,
        "macro_f1": f1.mean() * 100,
        "reviewed_pct": reviewed.mean() * 100,
        "reviewed_tickets": int(reviewed.sum()),
        "sensitive_errors": int((true_sens & wrong).sum()),              # Administrative rights tickets left wrong
        "sensitive_error_pct": (true_sens & wrong).sum() / true_sens.sum() * 100,
        "wrong_sensitive_grants": int((final_sens & wrong).sum()),       # tickets wrongly finalised as Admin rights
    }


rows, mcnemar = [], []
for overturn in OVERTURN_RATES:
    for miss in MISS_RATES:
        per_run = {c: [] for c in REVIEWED}
        p_values = {pair: [] for pair in COMPARISONS}
        for run in range(RUNS):
            rng = np.random.default_rng(run)                     # same draws for every condition and setting
            u_overturn = rng.random(len(df))
            u_miss = rng.random(len(df))
            other = (true + rng.integers(1, n_cls, len(df))) % n_cls   # a random wrong category
            reviewer = np.where(pred == true,
                                np.where(u_overturn < overturn, other, true),
                                np.where(u_miss < miss, pred, true))
            correct = {}
            for cond, reviewed in REVIEWED.items():
                final = np.where(reviewed, reviewer, pred)
                m = measures(final, reviewed)
                correct[cond] = final == true
                per_run[cond].append(m)
            for a, b in COMPARISONS:
                only_a = int((correct[a] & ~correct[b]).sum())
                only_b = int((~correct[a] & correct[b]).sum())
                p = binomtest(min(only_a, only_b), only_a + only_b, 0.5).pvalue if only_a + only_b else 1.0
                p_values[(a, b)].append((p, only_a, only_b))
        ai_correct = np.mean([m["accuracy"] for m in per_run["AI only"]])
        for cond, runs in per_run.items():
            run_df = pd.DataFrame(runs)
            row = {"overturn_pct": overturn * 100, "miss_pct": miss * 100, "condition": cond}
            for k in run_df.columns:
                row[f"{k}_mean"] = float(run_df[k].mean())
                row[f"{k}_sd"] = float(run_df[k].std(ddof=1))
            reviewed = run_df["reviewed_tickets"].mean()
            row["gain_per_100_reviewed"] = float((row["accuracy_mean"] - ai_correct) / 100 * len(df) / reviewed * 100) \
                if reviewed else None
            rows.append(row)
        for (a, b), vals in p_values.items():
            mcnemar.append({"overturn_pct": overturn * 100, "miss_pct": miss * 100, "a": a, "b": b,
                            "first_run_p": float(vals[0][0]), "first_run_only_a_correct": vals[0][1],
                            "first_run_only_b_correct": vals[0][2],
                            "share_of_runs_significant": float(np.mean([v[0] < 0.05 for v in vals]))})

summary = pd.DataFrame(rows)
summary.to_csv(OUT_PREFIX + "_summary.csv", index=False)
json.dump({"tickets": len(df), "sensitive_tickets": int(true_sens.sum()), "runs": RUNS,
           "rules": {"general_threshold": GENERAL, "sensitive_threshold": S_THR, "watch_threshold": W_THR,
                     "sensitive_categories": SENSITIVE},
           "results": rows, "mcnemar": mcnemar}, open(OUT_PREFIX + "_results.json", "w"), indent=2)

show = ["condition", "accuracy_mean", "accuracy_sd", "macro_f1_mean", "reviewed_pct_mean", "sensitive_errors_mean",
        "wrong_sensitive_grants_mean", "gain_per_100_reviewed"]
for o, m in [(0, 0), (10, 10), (20, 20)]:
    print(f"\nReviewer overturns {o}% of correct answers and misses {m}% of wrong ones (mean of {RUNS} runs)")
    print(summary[(summary.overturn_pct == o) & (summary.miss_pct == m)][show].round(2).to_string(index=False))
    mc = pd.DataFrame(mcnemar)
    print(mc[(mc.overturn_pct == o) & (mc.miss_pct == m)][["a", "b", "first_run_p", "share_of_runs_significant"]]
          .to_string(index=False))
print("\nsaved", OUT_PREFIX + "_results.json", "and", OUT_PREFIX + "_summary.csv")
