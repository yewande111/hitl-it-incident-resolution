"""Step 6. Puts the DistilBERT results into Chapter Three. Runs on a laptop in a few seconds.

Chapter Three (and the combined Chapters 1-3 file) contains yellow placeholders such as [[bert_acc]] wherever a figure
depends on the Kaggle run. This script reads results/transformer_cv_results.json (step 2) and results/cv_results.json
(step 1), replaces every placeholder with its value or sentence, and removes the yellow highlight.

Before anything is changed, the chapter files are copied to
  untitled folder/previous versions/Before filling results (<date>)/
Read the filled sentences afterwards: they are generated from the numbers and may need small edits in your own words.

Usage:  python3 06_fill_chapter_values.py
"""
import os
import re
import json
import math
import shutil
import datetime
from pathlib import Path

import docx
from docx.enum.text import WD_COLOR_INDEX

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
CHAPTERS_DIR = Path(os.environ.get("CHAPTERS_DIR", HERE.parent))
BACKUP_ROOT = HERE.parent / "untitled folder" / "previous versions"
PH = re.compile(r"\[\[(\w+)\]\]")

bert = json.load(open(RESULTS / "transformer_cv_results.json"))
lr = json.load(open(RESULTS / "cv_results.json"))["summary"]["Logistic Regression"]
if bert.get("quick_test") and os.environ.get("ALLOW_QUICK_TEST") != "1":
    raise SystemExit("transformer_cv_results.json comes from a quick test, not the full Kaggle run. "
                     "Run step 2 on Kaggle and download the results first.")


def missing(x):
    return x is None or (isinstance(x, float) and math.isnan(x))


def pct(x, digits=1):            # x is a fraction (0.853 -> "85.3%")
    return "-" if missing(x) else f"{x * 100:.{digits}f}%"


def pct_text(x, digits=1):       # x is a fraction (0.853 -> "85.3 percent")
    return "-" if missing(x) else f"{x * 100:.{digits}f} percent"


def num(n):
    return f"{int(n):,}"


V = {}

# ---------------------------------------------------------------- Table 3.2 and the comparison with LR
s = bert["summary"]
V["bert_acc"], V["bert_acc_sd"] = pct(s["acc_mean"]), f"{s['acc_sd'] * 100:.1f}"
V["bert_f1"], V["bert_f1_sd"] = pct(s["f1_mean"]), f"{s['f1_sd'] * 100:.1f}"
gain = (s["acc_mean"] - lr["acc_mean"]) * 100
if gain >= 0.5:
    V["bert_vs_lr_sentence"] = (
        f"Fine-tuned DistilBERT was the most accurate model, at {pct_text(s['acc_mean'])} against "
        f"{pct_text(lr['acc_mean'])} for logistic regression, a gain of {gain:.1f} percentage points, and its macro F1 "
        f"was {pct_text(s['f1_mean'])} against {pct_text(lr['f1_mean'])}.")
elif gain > 0:
    V["bert_vs_lr_sentence"] = (
        f"DistilBERT was only slightly more accurate than logistic regression, at {pct_text(s['acc_mean'])} against "
        f"{pct_text(lr['acc_mean'])}, a gain of {gain:.1f} percentage points, and its macro F1 was {pct_text(s['f1_mean'])} "
        f"against {pct_text(lr['f1_mean'])}.")
else:
    V["bert_vs_lr_sentence"] = (
        f"DistilBERT was not more accurate than logistic regression, at {pct_text(s['acc_mean'])} against "
        f"{pct_text(lr['acc_mean'])}, and its macro F1 was {pct_text(s['f1_mean'])} against {pct_text(lr['f1_mean'])}. It is still "
        f"used as the main model for the reasons given below, and this result is discussed in Chapter Five.")

# ---------------------------------------------------------------- Table 3.3 (confidence bins)
BIN_KEYS = {"<0.5": "lt50", "0.5-0.6": "50_60", "0.6-0.7": "60_70", "0.7-0.8": "70_80", "0.8-0.9": "80_90",
            ">=0.9": "ge90"}
for label, key in BIN_KEYS.items():
    b = bert["bins"][label]
    V[f"bert_bin_{key}_n"] = num(b["count"])
    V[f"bert_bin_{key}_acc"] = pct(b["acc"])
    V[f"bert_bin_{key}_acc_text"] = pct_text(b["acc"])

# ---------------------------------------------------------------- calibration
cal = bert["calibration"]
temps = cal["temperatures"]
V["temp_min"], V["temp_max"] = f"{min(temps):.2f}", f"{max(temps):.2f}"
if min(temps) > 1:
    V["temp_direction_sentence"] = ("Every value was above 1, which means that before calibration the model was more "
                                    "confident than it should have been, so its confidence scores were softened.")
elif max(temps) < 1:
    V["temp_direction_sentence"] = ("Every value was below 1, which means that before calibration the model was less "
                                    "confident than it should have been, so its confidence scores were sharpened.")
else:
    V["temp_direction_sentence"] = ("A value above 1 softens the confidence scores and a value below 1 sharpens them, "
                                    "and the folds differed in which was needed.")
before, after = cal["ece_before"] * 100, cal["ece_after"] * 100
ece = (f"The expected calibration error, which is the average gap between the stated confidence and the share of "
       f"tickets that were actually correct (Silva Filho et al., 2023), was {before:.1f} percent before calibration and "
       f"{after:.1f} percent after it")
if after < before - 0.1:
    V["ece_sentence"] = ece + ", so calibration brought the confidence scores closer to the actual accuracy."
elif after <= before + 0.1:
    V["ece_sentence"] = ece + ", so the model was already well calibrated and the change was small."
else:
    V["ece_sentence"] = (ece + ", so on these tickets calibration did not help. The temperature was fixed in advance "
                         "and is still used, and this is noted as a limitation.")

# ---------------------------------------------------------------- Table 3.5 (thresholds)
for t in bert["thresholds"]:
    k = int(round(t["threshold"] * 100))
    V[f"thr_{k}_flag"] = pct(t["flagged_pct"] / 100)
    V[f"thr_{k}_kept"] = pct(t["acc_kept"])
    V[f"thr_{k}_sent"] = pct(t["acc_flagged"])
    V[f"thr_{k}_flag_text"] = pct_text(t["flagged_pct"] / 100)
    V[f"thr_{k}_kept_text"] = pct_text(t["acc_kept"])
    V[f"thr_{k}_sent_text"] = pct_text(t["acc_flagged"])


# ---------------------------------------------------------------- Table 3.4 (examples)
def extract(text, key_words, size=18):
    """A short window of the ticket around its key words, so long tickets fit in the table."""
    words = text.split()
    if len(words) <= size + 4:
        return f"\"{text}\""
    hits = [i for i, w in enumerate(words) if w in key_words]
    best = max(range(len(words) - size + 1), key=lambda s: (sum(s <= h < s + size for h in hits), -s))
    piece = " ".join(words[best:best + size])
    return f"\"{'... ' if best > 0 else ''}{piece}{' ...' if best + size < len(words) else ''}\""


examples = {e["level"].lower(): e for e in bert["examples"]}
for lvl, e in examples.items():
    V[f"ex_{lvl}_extract"] = extract(e["text"], e["key_words"])
    V[f"ex_{lvl}_kw"] = ", ".join(e["key_words"])
    V[f"ex_{lvl}_pred"] = f"{e['predicted']} ({e['confidence'] * 100:.0f}%)"
    V[f"ex_{lvl}_true"] = e["true"]
low = examples.get("low")
if low:
    V["low_example_sentence"] = (
        f"In the low confidence example, the model was split between {low['predicted']} "
        f"({low['confidence'] * 100:.0f} percent) and {low['second']} ({low['second_confidence'] * 100:.0f} percent), "
        f"and the correct category was {low['true']}"
        + (", so its first choice was wrong." if low["predicted"] != low["true"] else
           ", so its first choice was right, but only just."))
wc = bert["word_counts"]
hi_w, lo_w = wc["mean_words_conf_90_plus"], wc["mean_words_conf_below_70"]
if not missing(hi_w) and not missing(lo_w):
    if lo_w > hi_w * 1.2:
        V["length_sentence"] = (f"Length also played a part. Tickets given a confidence of 90 percent or above had "
                                f"{hi_w:.0f} words on average, against {lo_w:.0f} words for tickets below 70 percent, "
                                f"because longer tickets often mix several topics.")
    else:
        V["length_sentence"] = (f"Length made little difference. Tickets given a confidence of 90 percent or above had "
                                f"{hi_w:.0f} words on average, against {lo_w:.0f} words for tickets below 70 percent.")

# ---------------------------------------------------------------- Table 3.6 (security rule)
sec = bert["security"]
one, ch = sec["single_threshold"], sec["chosen"]


def unchecked(r):
    return f"{num(r['sensitive_unchecked_errors'])} ({r['sensitive_unchecked_error_pct']:.1f}%)"


def rule_label(r):
    w = r["watch_threshold"]
    return f"{r['sensitive_threshold'] * 100:.0f}%, " + ("no watch rule" if w is None else f"watch {w * 100:.0f}%")


V["bert_single_reviewed"] = pct(one["reviewed_pct"] / 100)
V["bert_single_sens_reviewed"] = pct(one["sensitive_reviewed_pct"] / 100)
V["bert_single_sens_reviewed_text"] = pct_text(one["sensitive_reviewed_pct"] / 100)
V["bert_single_unchecked"] = unchecked(one)
V["bert_single_unchecked_n"] = num(one["sensitive_unchecked_errors"])
V["bert_single_unchecked_pct_text"] = pct_text(one["sensitive_unchecked_error_pct"] / 100)
V["bert_single_accepted_correct"] = pct(one["accepted_as_sensitive_correct_pct"] / 100)
V["bert_single_wrong_grants"] = num(one["wrongly_accepted_as_sensitive"])
V["bert_rule_label"] = rule_label(ch)
V["bert_sec_reviewed"] = pct(ch["reviewed_pct"] / 100)
V["bert_sec_sens_reviewed"] = pct(ch["sensitive_reviewed_pct"] / 100)
V["bert_sec_unchecked"] = unchecked(ch)
V["bert_sec_accepted_correct"] = pct(ch["accepted_as_sensitive_correct_pct"] / 100)

watch = ("no watch rule" if ch["watch_threshold"] is None
         else f"a watch value of {ch['watch_threshold'] * 100:.0f} percent")
effect = (f"With it, {num(ch['sensitive_unchecked_errors'])} Administrative rights tickets "
          f"({ch['sensitive_unchecked_error_pct']:.1f} percent) were left wrong without review, against "
          f"{num(one['sensitive_unchecked_errors'])} with one 70 percent threshold, and "
          + ("no tickets were accepted without review as Administrative rights. "
             if missing(ch["accepted_as_sensitive_correct_pct"]) else
             f"{ch['accepted_as_sensitive_correct_pct']:.1f} percent of the tickets accepted without review as "
             f"Administrative rights were correct. ")
          + f"The cost is that {ch['reviewed_pct']:.1f} percent of all tickets are sent for review, against "
            f"{one['reviewed_pct']:.1f} percent with one 70 percent threshold.")
if sec["targets_met"]:
    V["security_rule_sentence"] = (
        f"For DistilBERT, the combination that met both targets with the fewest reviews was a stricter threshold of "
        f"{ch['sensitive_threshold'] * 100:.0f} percent for tickets placed in Administrative rights, with {watch}. "
        + effect)
else:
    V["security_rule_sentence"] = (
        f"For DistilBERT, no combination tested met both targets, so the strictest rule was used: a threshold of "
        f"{ch['sensitive_threshold'] * 100:.0f} percent for tickets placed in Administrative rights, with {watch}. "
        + effect + " The targets were not fully met, and this is reported as a limitation.")


# ---------------------------------------------------------------- fill the documents
def fill_paragraph(p, unknown):
    """Replaces placeholders even when Word has split one across several runs."""
    while True:
        runs = p.runs
        text = "".join(r.text for r in runs)
        m = next((m for m in PH.finditer(text) if m.group(1) in V), None)
        for u in PH.finditer(text):
            if u.group(1) not in V:
                unknown.add(u.group(1))
        if m is None:
            return
        starts, pos = [], 0
        for r in runs:
            starts.append(pos)
            pos += len(r.text)
        i = max(k for k, st in enumerate(starts) if st <= m.start() and len(runs[k].text) > 0)
        j = max(k for k, st in enumerate(starts) if st < m.end() and len(runs[k].text) > 0)
        prefix = runs[i].text[:m.start() - starts[i]]
        suffix = runs[j].text[m.end() - starts[j]:]
        if i == j:
            runs[i].text = prefix + V[m.group(1)] + suffix
        else:
            runs[i].text = prefix + V[m.group(1)]
            for k in range(i + 1, j):
                runs[k].text = ""
            runs[j].text = suffix
        if runs[i].font.highlight_color == WD_COLOR_INDEX.YELLOW:
            runs[i].font.highlight_color = None


def all_paragraphs(doc):
    yield from doc.paragraphs
    for t in doc.tables:
        for row in t.rows:
            for cell in row.cells:
                yield from cell.paragraphs


files = sorted(f for f in CHAPTERS_DIR.glob("Chapter*.docx") if not f.name.startswith("~$"))
targets = [f for f in files if PH.search("\n".join(p.text for p in all_paragraphs(docx.Document(f))))]
if not targets:
    raise SystemExit("No placeholders found in the chapter files, so there is nothing to fill.")

backup = BACKUP_ROOT / f"Before filling results ({datetime.date.today().isoformat()})"
backup.mkdir(parents=True, exist_ok=True)
for f in targets:
    shutil.copy2(f, backup / f.name)
print("backed up", len(targets), "files to", backup)

for f in targets:
    doc = docx.Document(f)
    unknown = set()
    for p in all_paragraphs(doc):
        fill_paragraph(p, unknown)
    doc.save(f)
    left = sorted(unknown)
    print(f"{f.name}: filled" + (f", NOT filled (no value in the results): {', '.join(left)}" if left else ""))

print("\nGenerated sentences - please read them in the chapter and reword if you wish:")
for k in ["bert_vs_lr_sentence", "temp_direction_sentence", "ece_sentence", "low_example_sentence",
          "length_sentence", "security_rule_sentence"]:
    print(f"\n[{k}]\n{V.get(k, '(not available)')}")
