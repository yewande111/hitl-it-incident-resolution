"""Builds Chapter Four - Results.docx from the result files, using Chapter Three as the formatting template."""
import copy
import json
import re
from pathlib import Path

import docx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches

PROJECT = Path("/Users/user/Downloads/Project")
RES = PROJECT / "code" / "results"
TEMPLATE = PROJECT / "Chapter Three - Research Design and Methodology.docx"
OUT = PROJECT / "Chapter Four - Results.docx"

exp = json.load(open(RES / "experiment_results.json"))
ex = json.load(open(RES / "chapter4_extra_results.json"))
cv = json.load(open(RES / "transformer_cv_results.json"))
N = exp["tickets"]
SEL, SEC, FULL, AI = "Selective review", "Selective review + security rule", "Full review", "AI only"
CONDS = [AI, SEL, SEC, FULL]
SHORT = {AI: "AI only", SEL: "Selective", SEC: "Selective + security", FULL: "Full"}
RATES = [0, 5, 10, 20]
SETTINGS = [(o, m) for o in RATES for m in RATES]


def k(x):
    x = float(x)
    return int(round(x * 100)) if x <= 1 and x != 0 else int(round(x))


# overturn/miss may be stored as fractions or percents
scale = 100 if max(r["overturn_pct"] for r in exp["results"]) <= 1 else 1
R = {(int(round(r["overturn_pct"] * scale)), int(round(r["miss_pct"] * scale)), r["condition"]): r
     for r in exp["results"]}
MC = {(int(round(r["overturn_pct"] * scale)), int(round(r["miss_pct"] * scale)), r["a"], r["b"]): r
      for r in exp["mcnemar"]}
assert len(R) == 64, len(R)


def v(o, m, c, key):
    return R[(o, m, c)][key]


def lab(o, m):
    return f"{o}/{m}"


def f1(x):
    return f"{x:.1f}"


def f2(x):
    return f"{x:.2f}"


def num(x):
    return f"{int(round(x)):,}"


def pval(p):
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


# ---------------------------------------------------------------- facts computed from the test predictions
df = pd.read_csv(RES / "test_predictions.csv")
classes = np.array([c[2:] for c in df.columns if c.startswith("p_")])
proba = df[[f"p_{c}" for c in classes]].to_numpy()
true = np.searchsorted(classes, df["true_category"].to_numpy())
pred, conf = proba.argmax(1), proba.max(1)
right = pred == true
rules = exp["rules"]
adm = np.searchsorted(classes, rules["sensitive_categories"])
pred_s, true_s = np.isin(pred, adm), np.isin(true, adm)
general = conf < rules["general_threshold"]
strict = pred_s & (conf < rules["sensitive_threshold"]) & ~general
watch = ~pred_s & (proba[:, adm].max(1) >= rules["watch_threshold"]) & ~general
secmask = general | strict | watch
masks = {AI: np.zeros(N, bool), SEL: general, SEC: secmask, FULL: np.ones(N, bool)}
sr = ex["security_rule"]
assert secmask.sum() == sr["total_reviewed"] and general.sum() == sr["general_only"]
n_wrong = int((~right).sum())
n_right = int(right.sum())
ai_acc = v(0, 0, AI, "accuracy_mean")

# ---------------------------------------------------------------- derived results used in the text
best_acc = {s: max([SEL, SEC, FULL], key=lambda c: v(*s, c, "accuracy_mean")) for s in SETTINGS}
best_f1 = {s: max([SEL, SEC, FULL], key=lambda c: v(*s, c, "macro_f1_mean")) for s in SETTINGS}
for name, b in [("accuracy", best_acc), ("macro F1", best_f1)]:
    print(f"best by {name}:", {SHORT[c]: [lab(*s) for s in SETTINGS if b[s] == c] for c in [SEL, SEC, FULL]})
extra = {s: (v(*s, SEC, "accuracy_mean") - v(*s, SEL, "accuracy_mean")) / 100 * N for s in SETTINGS}
n_extra = sr["total_reviewed"] - sr["general_only"]
sd_max = max(v(*s, c, "accuracy_sd") for s in SETTINGS for c in [SEL, SEC, FULL])
sel_gap = [v(*s, SEL, "accuracy_mean") - ai_acc for s in SETTINGS]
full_vs_ai_20 = [v(20, m, FULL, "accuracy_mean") - ai_acc for m in RATES]
print("selective minus AI:", f2(min(sel_gap)), f2(max(sel_gap)), "| full minus AI at 20:", [f2(x) for x in full_vs_ai_20])
print("max sd", sd_max)
grants_best = [s for s in SETTINGS if v(*s, SEC, "wrong_sensitive_grants_mean")
               <= min(v(*s, c, "wrong_sensitive_grants_mean") for c in [SEL, FULL]) + 1e-9]
print("security rule fewest wrong grants in", len(grants_best), "settings")
sec_fewer_err = [lab(*s) for s in SETTINGS if v(*s, SEC, "sensitive_errors_mean") < v(*s, SEL, "sensitive_errors_mean")]
print("security fewer admin errors than selective:", sec_fewer_err)
PAIRS = [(AI, SEL), (SEL, SEC), (SEC, FULL), (AI, FULL)]
for a, b in PAIRS:
    print(SHORT[a], "vs", SHORT[b], "not always significant:",
          [(lab(*s), MC[(*s, a, b)]["share_of_runs_significant"], round(MC[(*s, a, b)]["first_run_p"], 4))
           for s in SETTINGS if MC[(*s, a, b)]["share_of_runs_significant"] < 1])
for s in SETTINGS:
    if s[0] == 20:
        for a, b in [(SEC, FULL), (AI, FULL)]:
            r = MC[(*s, a, b)]
            print("direction", lab(*s), SHORT[a], SHORT[b], r["first_run_only_a_correct"], r["first_run_only_b_correct"])

# ---------------------------------------------------------------- template
doc = docx.Document(TEMPLATE)
tp = doc.paragraphs
T = {"h1": tp[0], "h2": tp[1], "body": tp[2], "figure": tp[7], "figcap": tp[8], "tabcap": tp[17],
     "after_table": tp[18], "refhead": [p for p in tp if p.text == "REFERENCES"][0],
     "ref": [p for p in tp if p.text.startswith("Silva Filho")][0]}
assert T["tabcap"].text.startswith("Table 3.1") and T["figcap"].text.startswith("Figure 3.1")
TPL = {}
for name, p in T.items():
    ppr = p._p.pPr
    rpr = next((r._r.rPr for r in p.runs if r.text), None)
    TPL[name] = (copy.deepcopy(ppr) if ppr is not None else None, copy.deepcopy(rpr) if rpr is not None else None)
ttbl = doc.tables[0]._tbl
TBL_PR = copy.deepcopy(ttbl.tblPr)
CELL_PPR = copy.deepcopy(doc.tables[0].rows[0].cells[0].paragraphs[0]._p.pPr)

body = doc.element.body
sectPr = body.sectPr
for el in list(body):
    if el is not sectPr:
        body.remove(el)

PH = re.compile(r"(\[\[.*?\]\])")


def runs_into(p, text, rpr=None, bold=False):
    for piece in PH.split(text):
        if not piece:
            continue
        r = p.add_run(piece)
        if rpr is not None:
            r._r.insert(0, copy.deepcopy(rpr))
        if bold:
            r.bold = True
        if PH.fullmatch(piece):
            r.font.highlight_color = WD_COLOR_INDEX.YELLOW


def para(kind, text=""):
    p = doc.add_paragraph()
    ppr, rpr = TPL[kind]
    if ppr is not None:
        p._p.insert(0, copy.deepcopy(ppr))
    if text:
        runs_into(p, text, rpr)
    return p


def h1(t): para("h1", t)
def h2(t): para("h2", t)
def body_p(t): para("body", t)
def caption(t): para("tabcap", t)


def table(headers, rows, widths, bold_cells=(), group_header=None, merged_rows=()):
    """headers: list of str. rows: list of lists. widths: twips per column (sum about 8640).
    bold_cells: set of (row, col) in rows to put in bold. group_header: list of (text, span) for a first header row.
    merged_rows: indexes of rows whose first cell spans the whole table (sub-headings)."""
    extra_rows = 1 if group_header else 0
    t = doc.add_table(rows=len(rows) + 1 + extra_rows, cols=len(headers))
    tbl = t._tbl
    tbl.remove(tbl.tblPr)
    tbl.insert(0, copy.deepcopy(TBL_PR))
    grid = tbl.tblGrid
    for gc, w in zip(grid.findall(qn("w:gridCol")), widths):
        gc.set(qn("w:w"), str(w))

    def fill(cell, text, bold, w):
        tcpr = cell._tc.get_or_add_tcPr()
        tcw = tcpr.find(qn("w:tcW"))
        if tcw is None:
            tcw = OxmlElement("w:tcW")
            tcpr.append(tcw)
        tcw.set(qn("w:type"), "dxa")
        tcw.set(qn("w:w"), str(w))
        p = cell.paragraphs[0]
        if p._p.pPr is not None:
            p._p.remove(p._p.pPr)
        p._p.insert(0, copy.deepcopy(CELL_PPR))
        rpr = OxmlElement("w:rPr")
        if bold:
            rpr.append(OxmlElement("w:b"))
        sz = OxmlElement("w:sz")
        sz.set(qn("w:val"), "21")
        rpr.append(sz)
        runs_into(p, str(text), rpr)

    r0 = 0
    if group_header:
        col = 0
        for text, span in group_header:
            c = t.rows[0].cells[col]
            if span > 1:
                c = c.merge(t.rows[0].cells[col + span - 1])
            fill(c, text, True, sum(widths[col:col + span]))
            col += span
        r0 = 1
    for j, h in enumerate(headers):
        fill(t.rows[r0].cells[j], h, True, widths[j])
    for i, row in enumerate(rows):
        cells = t.rows[r0 + 1 + i].cells
        if i in merged_rows:
            c = cells[0].merge(cells[-1])
            fill(c, row[0], True, sum(widths))
            continue
        for j, val in enumerate(row):
            fill(cells[j], val, (i, j) in bold_cells, widths[j])
    para("after_table")
    return t


def even(first, n_other, total=8640):
    rest = (total - first) // n_other
    return [first] + [rest] * n_other


# ================================================================ CHAPTER FOUR
h1("CHAPTER FOUR: RESULTS")

h2("4.1 Introduction")
body_p("This chapter reports the results of the study. Sections 4.2 to 4.11 report Part A, the simulation experiment, "
       "which answers RQ1, “Does targeted human in the loop feedback improve the accuracy of AI driven IT incident "
       "resolution compared with an AI only approach?”, and tests hypotheses H1 to H3. Section 4.12 reports Part B, "
       "the survey, which answers RQ2, “How does human involvement affect user trust in AI based IT support "
       "systems?”, and tests H4. The results are given here with only brief comment. What they mean, and how they "
       "compare with the studies reviewed in Chapter Two, is discussed in Chapter Five.")
body_p(f"All Part A results come from the test portion of {N:,} tickets, which was set aside at the start "
       "(Section 3.5). It was not used to train the model, to set the temperature or to choose the thresholds, so the "
       "results show how the method works on tickets it has not seen before. As in Chapter Three, resolution accuracy "
       "means the share of tickets that were finally given the correct category. The reviewer is modelled and is not "
       "a real person, so every result that involves review is an estimated effect of human review under the "
       "assumptions set out in Section 3.9. It is not a measurement of how real service desk staff behave.")
body_p("Reviewer error settings are written as two numbers: the overturn rate followed by the miss rate. The overturn "
       "rate is the share of correct answers that the modelled reviewer wrongly changes, and the miss rate is the share "
       "of wrong answers that the reviewer fails to correct. For example, 10/5 means that the reviewer overturns 10 "
       "percent of correct answers and misses 5 percent of wrong ones. Where the reviewer can make mistakes, each "
       "figure is the average of 100 runs. A perfect reviewer, 0/0, gives the same result in every run.")

# ---------------------------------------------------------------- 4.2
h2("4.2 How the Model Performed on Its Own")
s = cv["summary"]
body_p(f"Working alone, the model gave the correct category to {f2(ai_acc)} percent of the {N:,} test tickets, so "
       f"{f2(v(0, 0, AI, 'misclassification_mean'))} percent ({n_wrong:,} tickets) were misclassified. Its macro "
       f"precision was {f1(v(0, 0, AI, 'macro_precision_mean'))} percent, its macro recall "
       f"{f1(v(0, 0, AI, 'macro_recall_mean'))} percent and its macro F1 {f1(v(0, 0, AI, 'macro_f1_mean'))} percent. "
       f"These are very close to the five fold cross validation results on the training portion, an accuracy of "
       f"{f1(s['acc_mean'] * 100)} percent and a macro F1 of {f1(s['f1_mean'] * 100)} percent (Section 3.6), so the "
       "model did as well on new tickets as it had during development. Table 4.1 shows the results for each category.")
caption("Table 4.1: AI only results for each category on the test portion")
pc = ex["per_category"]
rows = [[c["category"], f"{c['tickets']:,}", f"{c['precision']:.1f}%", f"{c['recall']:.1f}%", f"{c['f1']:.1f}%",
         f"{c['low_confidence_pct']:.1f}%"] for c in pc]
rows.append(["All categories (macro average)", f"{N:,}", f"{v(0, 0, AI, 'macro_precision_mean'):.1f}%",
             f"{v(0, 0, AI, 'macro_recall_mean'):.1f}%", f"{v(0, 0, AI, 'macro_f1_mean'):.1f}%",
             f"{general.mean() * 100:.1f}%"])
table(["Category", "Test tickets", "Precision", "Recall", "F1", "Confidence below 70%"], rows, even(2340, 5),
      bold_cells={(len(rows) - 1, j) for j in range(6)})
pcd = {c["category"]: c for c in pc}
top2 = sorted(pc, key=lambda c: -c["f1"])[:2]
a_c = pcd["Administrative rights"]
wrong_as = ex["admin_rights_wrong_predicted_as"]
grant_true = ex["admin_rights_wrong_grants_true_category"]
assert max(pc, key=lambda c: c["low_confidence_pct"])["category"] == "Administrative rights"
assert min(pc, key=lambda c: c["f1"])["category"] == "Administrative rights"
body_p(f"{top2[0]['category']} and {top2[1]['category']} had the highest F1, at {f1(top2[0]['f1'])} and "
       f"{f1(top2[1]['f1'])} percent. Administrative rights, the security-sensitive category, had the lowest F1 at "
       f"{f1(a_c['f1'])} percent, and it also had the highest share of tickets with a confidence below 70 percent "
       f"({f1(a_c['low_confidence_pct'])} percent). The model got {sr['admin_wrong_ai']} of the {sr['admin_tickets']} "
       f"Administrative rights tickets wrong ({f1(sr['admin_wrong_ai'] / sr['admin_tickets'] * 100)} percent), and "
       f"{wrong_as['Hardware']} of these {sr['admin_wrong_ai']} were placed in Hardware. In the other direction, "
       f"{v(0, 0, AI, 'wrong_sensitive_grants_mean'):.0f} tickets were wrongly given the Administrative rights "
       f"category, and {grant_true['Hardware']} of them were really Hardware tickets. For this category, the main "
       "confusion is therefore with Hardware. Of the two kinds of error, the tickets wrongly given the Administrative "
       "rights category matter more on a service desk, because these are the tickets that could lead to access being "
       "granted when it should not be.")

# ---------------------------------------------------------------- 4.3
h2("4.3 Confidence on the Test Tickets")
body_p("Selective review relies on the model’s confidence being a fair guide to whether its answer is right. "
       "Table 4.2 compares the confidence the model gave with the actual accuracy on the test tickets, using the same "
       "confidence bands as Table 3.3.")
caption("Table 4.2: Confidence compared with actual accuracy on the test portion")
names = {"<0.5": "Below 50%", "0.5-0.6": "50% to 60%", "0.6-0.7": "60% to 70%", "0.7-0.8": "70% to 80%",
         "0.8-0.9": "80% to 90%", ">=0.9": "90% and above"}
bins = ex["bins"]
rows = [[names[b], f"{d['count']:,}", f"{d['share_pct']:.1f}%", f"{d['mean_conf']:.1f}%", f"{d['acc']:.1f}%"]
        for b, d in bins.items()]
table(["Model confidence", "Tickets", "Share of tickets", "Mean confidence", "Actual accuracy"], rows,
      even(2240, 4))
gaps = {b: d["mean_conf"] - d["acc"] for b, d in bins.items()}
worst = max(gaps, key=gaps.get)
acc_sent = (~right[general]).mean()
body_p(f"Accuracy rose steadily with confidence, from {f1(bins['<0.5']['acc'])} percent for tickets below 50 percent "
       f"confidence to {f1(bins['>=0.9']['acc'])} percent for tickets at 90 percent or above, and "
       f"{f1(bins['>=0.9']['share_pct'])} percent of all tickets were in this top band. The {general.sum():,} tickets "
       f"below the 70 percent threshold were correct only {f1(right[general].mean() * 100)} percent of the time, "
       f"against {f1(right[~general].mean() * 100)} percent for the tickets the model kept, so the threshold did "
       "separate the less reliable answers from the more reliable ones.")
body_p(f"The expected calibration error, which is the average gap between the stated confidence and the actual "
       f"accuracy (Silva Filho et al., 2023), was {f1(ex['ece_pct'])} percent on the test tickets, against "
       f"{f1(cv['calibration']['ece_after'] * 100)} percent in cross validation. Overall, the confidence was close to "
       "the accuracy, but in the middle bands the model was more confident than it should have been. The largest gap "
       f"was in the {names[worst].replace('%', ' percent').replace(' percent to ', ' to ')} band, where the mean "
       f"confidence was {f1(bins[worst]['mean_conf'])} percent and the accuracy was {f1(bins[worst]['acc'])} percent. "
       "In practice, this means that tickets just above the 70 percent threshold were somewhat less reliable than "
       "their confidence suggested.")

# ---------------------------------------------------------------- 4.4
h2("4.4 Tickets Sent for Review")
body_p("Table 4.3 shows how many tickets each condition sent to the modelled reviewer. These numbers depend only on "
       "the model’s confidence, so they are the same at every reviewer error setting.")
caption("Table 4.3: Tickets sent to the modelled reviewer in each condition")
rows = []
for c in CONDS:
    m = masks[c]
    wr = int((m & ~right).sum())
    rows.append([c, f"{int(m.sum()):,}", f"{m.mean() * 100:.1f}%",
                 "-" if not m.any() else f"{wr:,} ({wr / m.sum() * 100:.1f}%)",
                 f"{int((m & true_s).sum())} of {int(true_s.sum())}",
                 f"{int((m & true_s & ~right).sum())} of {sr['admin_wrong_ai']}",
                 f"{int((~m & true_s & ~right).sum())}"])
table(["Condition", "Tickets reviewed", "Share of all tickets", "Model wrong among reviewed tickets",
       "Administrative rights tickets reviewed", "Wrong Administrative rights tickets reviewed",
       "Wrong Administrative rights tickets not reviewed"], rows, even(1800, 6))
assert sr["added_by_strict_threshold"] + sr["added_by_watch_value"] == n_extra
sel_wrong = int((general & ~right).sum())
body_p(f"Selective review sent {general.sum():,} tickets ({f1(general.mean() * 100)} percent) to the reviewer, and the "
       f"model was wrong on {sel_wrong} of them, about half. Adding the security rule sent {n_extra} more tickets, "
       f"for {sr['total_reviewed']:,} in total ({f1(secmask.mean() * 100)} percent). Of the {n_extra} extra tickets, "
       f"{sr['added_by_strict_threshold']} were sent because the model placed them in Administrative rights with a "
       f"confidence below {rules['sensitive_threshold'] * 100:.0f} percent, and {sr['added_by_watch_value']} because "
       f"the model gave Administrative rights a probability of at least {rules['watch_threshold'] * 100:.0f} percent "
       f"without choosing it. The model was right on {sr['extra_reviewed_ai_was_right']} of the {n_extra} extra "
       f"tickets and wrong on {sr['extra_reviewed_ai_was_wrong']}.")
body_p(f"The security rule raised the number of Administrative rights tickets checked by the reviewer from "
       f"{sr['admin_tickets_reviewed_selective']} to {sr['admin_tickets_reviewed_security']}, and the number of wrong "
       f"Administrative rights tickets that reached the reviewer from {sr['admin_wrong_caught_selective']} to "
       f"{sr['admin_wrong_caught_security']} of {sr['admin_wrong_ai']}. Only "
       f"{sr['admin_wrong_ai'] - sr['admin_wrong_caught_security']} wrong Administrative rights tickets were left "
       f"without a human check, against {sr['admin_wrong_ai'] - sr['admin_wrong_caught_selective']} with selective "
       f"review alone. Full review sent every ticket, including the {n_right:,} tickets that the model had already "
       "got right.")

# ---------------------------------------------------------------- 4.5
h2("4.5 Results with a Perfect Reviewer")
body_p("Table 4.4 gives every measure from Section 3.10 for the four conditions when the reviewer makes no mistakes. "
       "This is the best case for human review, so it shows the most that each condition could gain.")
caption("Table 4.4: Results of the four conditions with a perfect reviewer (0/0)")


def measure_rows(o, m, with_effort=True):
    out = [["Resolution accuracy"] + [f"{v(o, m, c, 'accuracy_mean'):.2f}%" for c in CONDS],
           ["Misclassification rate"] + [f"{v(o, m, c, 'misclassification_mean'):.2f}%" for c in CONDS],
           ["Macro precision"] + [f"{v(o, m, c, 'macro_precision_mean'):.2f}%" for c in CONDS],
           ["Macro recall"] + [f"{v(o, m, c, 'macro_recall_mean'):.2f}%" for c in CONDS],
           ["Macro F1"] + [f"{v(o, m, c, 'macro_f1_mean'):.2f}%" for c in CONDS]]
    if with_effort:
        out += [["Tickets reviewed"] + [f"{v(o, m, c, 'reviewed_tickets_mean'):,.0f}" for c in CONDS],
                ["Share of tickets reviewed"] + [f"{v(o, m, c, 'reviewed_pct_mean'):.1f}%" for c in CONDS],
                ["Extra correct tickets per 100 reviewed"] + ["-"] + [f"{v(o, m, c, 'gain_per_100_reviewed'):.1f}"
                                                                     for c in CONDS[1:]]]
    dec = 0 if o == 0 and m == 0 else 1
    out += [["Administrative rights tickets wrong in the final result"] +
            [f"{v(o, m, c, 'sensitive_errors_mean'):.{dec}f} ({v(o, m, c, 'sensitive_error_pct_mean'):.1f}%)"
             for c in CONDS],
            ["Tickets wrongly given the Administrative rights category"] +
            [f"{v(o, m, c, 'wrong_sensitive_grants_mean'):.{dec}f}" for c in CONDS]]
    return out


table(["Measure", "AI only", "Selective review", "Selective review + security rule", "Full review"],
      measure_rows(0, 0), even(2640, 4))
g = {c: v(0, 0, c, "gain_per_100_reviewed") for c in CONDS[1:]}
body_p("With a perfect reviewer, review can only correct errors, so accuracy rises with the number of tickets "
       f"checked. Selective review raised accuracy from {f1(ai_acc)} to {f1(v(0, 0, SEL, 'accuracy_mean'))} percent "
       f"by checking {f1(general.mean() * 100)} percent of the tickets, and the security rule raised it further to "
       f"{f1(v(0, 0, SEC, 'accuracy_mean'))} percent. Full review reached 100 percent, as it must when a reviewer who "
       "never makes mistakes checks every ticket. Macro precision, recall and F1 moved in the same way as accuracy.")
body_p(f"The cost of these gains was very different. Selective review corrected about {g[SEL]:.0f} tickets for every "
       f"100 it checked, the security rule about {g[SEC]:.0f} and full review about {g[FULL]:.0f}, because most of the "
       "tickets that full review checks were already right. For Administrative rights, the number of tickets left "
       f"wrong fell from {v(0, 0, AI, 'sensitive_errors_mean'):.0f} with AI only to "
       f"{v(0, 0, SEL, 'sensitive_errors_mean'):.0f} with selective review, {v(0, 0, SEC, 'sensitive_errors_mean'):.0f} "
       "with the security rule and none with full review. The number of tickets wrongly given the Administrative "
       f"rights category fell from {v(0, 0, AI, 'wrong_sensitive_grants_mean'):.0f} to "
       f"{v(0, 0, SEL, 'wrong_sensitive_grants_mean'):.0f} with selective review, and to none with either the "
       "security rule or full review.")

# ---------------------------------------------------------------- 4.6
h2("4.6 Results When the Reviewer Makes Mistakes")
body_p(f"Table 4.5 shows the resolution accuracy of each condition at all 16 reviewer error settings, and Figure 4.1 "
       "shows the four settings where the two error rates are equal. AI only does not use a reviewer, so its accuracy "
       f"is {f2(ai_acc)} percent at every setting. The most accurate condition at each setting is shown in bold.")
caption("Table 4.5: Resolution accuracy at each reviewer error setting (mean of 100 runs)")
rows, bold = [], set()
for i, s_ in enumerate(SETTINGS):
    vals = [v(*s_, c, "accuracy_mean") for c in CONDS]
    rows.append([lab(*s_)] + [f"{x:.2f}%" for x in vals])
    bold.add((i, CONDS.index(max(CONDS, key=lambda c: v(*s_, c, "accuracy_mean")))))
table(["Reviewer error (overturn/miss)", "AI only", "Selective review", "Selective review + security rule",
       "Full review"], rows, even(2240, 4), bold_cells={(i, j + 1) for i, j in bold})

# figure 4.1
fig, ax = plt.subplots(figsize=(7, 4))
diag = [(r, r) for r in RATES]
for c, mk in zip(CONDS, ["o", "s", "^", "D"]):
    ax.plot(range(4), [v(*d, c, "accuracy_mean") for d in diag], marker=mk, label=c, linewidth=2)
ax.set_xticks(range(4))
ax.set_xticklabels([lab(*d) for d in diag])
ax.set_xlabel("Reviewer error (overturn rate / miss rate, percent)")
ax.set_ylabel("Resolution accuracy (percent)")
ax.grid(alpha=0.3)
ax.legend(frameon=False, fontsize=9)
fig.tight_layout()
fig_path = Path("/tmp/figure_4_1.png")
fig.savefig(fig_path, dpi=200)
fp = para("figure")
fp.add_run().add_picture(str(fig_path), width=Inches(6))
para("figcap", "Figure 4.1: Resolution accuracy of the four conditions as reviewer error rises (overturn and miss "
               "rates equal, mean of 100 runs)")

sel_acc = [v(*s_, SEL, "accuracy_mean") for s_ in SETTINGS]
sec_acc = [v(*s_, SEC, "accuracy_mean") for s_ in SETTINGS]
full_acc = [v(*s_, FULL, "accuracy_mean") for s_ in SETTINGS]
cnt = {c: sum(best_acc[s_] == c for s_ in SETTINGS) for c in [SEL, SEC, FULL]}
assert [s_ for s_ in SETTINGS if best_acc[s_] == FULL] == [(0, 0), (0, 5), (0, 10), (0, 20), (5, 0), (5, 5), (5, 10)]
assert all(best_acc[(20, m)] in (SEL, SEC) for m in RATES) and all(best_acc[s_] == SEL for s_ in [(20, 5), (20, 10), (20, 20)])
assert all(v(10, m, FULL, "accuracy_mean") < min(v(10, m, SEL, "accuracy_mean"), v(10, m, SEC, "accuracy_mean"))
           for m in RATES)
body_p(f"The two selective conditions changed little as the reviewer got worse. Selective review stayed between "
       f"{f2(min(sel_acc))} and {f2(max(sel_acc))} percent, and was always at least {f1(min(sel_gap))} percentage "
       f"points above AI only. With the security rule, accuracy stayed between {f2(min(sec_acc))} and "
       f"{f2(max(sec_acc))} percent. Full review changed far more, from {f2(max(full_acc))} percent down to "
       f"{f2(min(full_acc))} percent. For full review, the overturn rate mattered much more than the miss rate. This "
       f"is because full review sends all {n_right:,} tickets that the model got right to the reviewer, so each extra "
       f"percentage point of overturns turns about {n_right / 100:.0f} correct answers into wrong ones. The selective "
       "conditions send far fewer correct tickets to the reviewer, so they are much less exposed to this kind of "
       "mistake.")
body_p(f"Full review was the most accurate condition in {cnt[FULL]} of the 16 settings: the four settings with no "
       "overturns, and the settings with a 5 percent overturn rate and a miss rate of 10 percent or less. Selective "
       f"review with the security rule was the most accurate in {cnt[SEC]} settings: 5/20, all four settings with a "
       f"10 percent overturn rate, and 20/0. Selective review was the most accurate in the other {cnt[SEL]} settings "
       "with a 20 percent overturn rate. At a 10 percent overturn rate, full review was less accurate "
       "than both selective conditions in every setting, and at a 20 percent overturn rate it was less accurate than "
       f"AI only, by between {f1(-max(full_vs_ai_20))} and {f1(-min(full_vs_ai_20))} percentage points. The spread "
       f"across the 100 runs was small. The largest standard deviation at any setting was {f2(sd_max)} percentage "
       "points, for full review at 20/20, so the averages in Table 4.5 are stable.")
body_p("Table 4.6 gives every measure at two settings where the reviewer makes mistakes, 10/10 and 20/20.")
caption("Table 4.6: Results of the four conditions at reviewer error settings 10/10 and 20/20 (mean of 100 runs)")
rows = [["Reviewer error 10/10"]] + measure_rows(10, 10, False) + [["Reviewer error 20/20"]] + \
       measure_rows(20, 20, False)
table(["Measure", "AI only", "Selective review", "Selective review + security rule", "Full review"], rows,
      even(2640, 4), merged_rows={0, 8})
nf1 = sum(best_f1[s_] == FULL for s_ in SETTINGS)
assert [s_ for s_ in SETTINGS if best_f1[s_] == FULL] == [(0, m) for m in RATES]
body_p("The other measures followed the same pattern as accuracy, with one difference. At 10/10, full review was "
       f"still more accurate than AI only ({f2(v(10, 10, FULL, 'accuracy_mean'))} against {f2(ai_acc)} percent), but "
       f"its macro F1 was lower ({f2(v(10, 10, FULL, 'macro_f1_mean'))} against {f2(v(0, 0, AI, 'macro_f1_mean'))} "
       f"percent), and so was its macro precision ({f2(v(10, 10, FULL, 'macro_precision_mean'))} against "
       f"{f2(v(0, 0, AI, 'macro_precision_mean'))} percent). This is because the overturns move correct answers into "
       "all the other categories at random, including the small ones, and this lowers precision in those categories. "
       f"Judged by macro F1 instead of accuracy, full review was the best condition in only {nf1} settings, the ones "
       "with no overturns.")

# ---------------------------------------------------------------- 4.7
h2("4.7 Review Effort")
body_p(f"Table 4.7 shows the extra correct tickets for each 100 tickets reviewed, compared with AI only. The last two "
       f"columns show what the {n_extra} extra reviews added by the security rule achieved compared with selective "
       "review alone.")
caption("Table 4.7: Extra correct tickets for each 100 tickets reviewed, and the value of the security rule’s "
        "extra reviews")
rows = []
for s_ in SETTINGS:
    rows.append([lab(*s_)] + [f"{v(*s_, c, 'gain_per_100_reviewed'):.1f}" for c in [SEL, SEC, FULL]] +
                [f"{extra[s_]:+.1f}", f"{extra[s_] / n_extra * 100:+.1f}"])
table(["Reviewer error (overturn/miss)", "Selective review", "Selective review + security rule", "Full review",
       f"Extra correct tickets from the {n_extra} extra reviews", "Per 100 extra reviews"], rows, even(1840, 5))
gs = {c: [v(*s_, c, "gain_per_100_reviewed") for s_ in SETTINGS] for c in [SEL, SEC, FULL]}
assert all(v(*s_, SEL, "gain_per_100_reviewed") > max(v(*s_, SEC, "gain_per_100_reviewed"),
                                                     v(*s_, FULL, "gain_per_100_reviewed")) for s_ in SETTINGS)
neg = [s_ for s_ in SETTINGS if v(*s_, FULL, "gain_per_100_reviewed") < 0]
assert neg == [(20, m) for m in RATES]
body_p("Selective review gave the most benefit for each ticket reviewed in every setting, between "
       f"{f1(min(gs[SEL]))} and {f1(max(gs[SEL]))} extra correct tickets per 100 reviewed. The security rule gave "
       f"between {f1(min(gs[SEC]))} and {f1(max(gs[SEC]))}, and full review between {f1(max(gs[FULL]))} and minus "
       f"{f1(-min(gs[FULL]))}. A value below zero means that review made the result worse than leaving the model "
       "alone, and this happened for full review at every setting with a 20 percent overturn rate.")
body_p(f"The {n_extra} extra reviews added by the security rule were worth much less than the first "
       f"{general.sum():,}. With a perfect reviewer they corrected {extra[(0, 0)]:.0f} tickets, or "
       f"{f1(extra[(0, 0)] / n_extra * 100)} for every 100 extra reviews, against {f1(g[SEL])} for every 100 of the "
       f"first {general.sum():,}. At 10/10 they added about {extra[(10, 10)]:.0f} correct tickets "
       f"({f1(extra[(10, 10)] / n_extra * 100)} per 100), and at a 20 percent overturn rate they added very little or "
       f"made the result worse, from {f1(extra[(20, 0)])} tickets at 20/0 to minus {f1(-extra[(20, 20)])} at 20/20. "
       "This is because most of the extra tickets were ones the model had already got right, as shown in "
       "Section 4.4.")

# ---------------------------------------------------------------- 4.8
h2("4.8 Security-Sensitive Tickets")
body_p("Table 4.8 shows the two security-sensitive measures from Section 3.10 at every setting: the number of "
       "Administrative rights tickets left with a wrong category in the final result, and the number of tickets "
       f"wrongly given the Administrative rights category. With AI only, these were "
       f"{v(0, 0, AI, 'sensitive_errors_mean'):.0f} and {v(0, 0, AI, 'wrong_sensitive_grants_mean'):.0f} at every "
       "setting.")
caption("Table 4.8: Security-sensitive errors at each reviewer error setting (mean of 100 runs)")
rows = []
for s_ in SETTINGS:
    d = 0 if s_ == (0, 0) else 1
    rows.append([lab(*s_)] + [f"{v(*s_, c, 'sensitive_errors_mean'):.{d}f}" for c in [SEL, SEC, FULL]] +
                [f"{v(*s_, c, 'wrong_sensitive_grants_mean'):.{d}f}" for c in [SEL, SEC, FULL]])
table(["Reviewer error (overturn/miss)", "Selective", "Selective + security", "Full", "Selective",
       "Selective + security", "Full"], rows, even(1800, 6),
      group_header=[("", 1), ("Administrative rights tickets wrong in the final result", 3),
                    ("Tickets wrongly given the Administrative rights category", 3)])
assert sec_fewer_err == [lab(*s_) for s_ in SETTINGS if s_[0] <= 10]
assert len(grants_best) == 16
body_p("Up to a 10 percent overturn rate, the security rule left fewer Administrative rights tickets wrong than "
       f"selective review in every setting, for example {f1(v(10, 10, SEC, 'sensitive_errors_mean'))} against "
       f"{f1(v(10, 10, SEL, 'sensitive_errors_mean'))} at 10/10. At a 20 percent overturn rate this was reversed, and "
       "the security rule left more of these tickets wrong than selective review, for example "
       f"{f1(v(20, 20, SEC, 'sensitive_errors_mean'))} against {f1(v(20, 20, SEL, 'sensitive_errors_mean'))} at 20/20. "
       f"This is because the rule sends many correct tickets to the reviewer ({sr['extra_reviewed_ai_was_right']} of "
       f"the {n_extra} extra tickets), and a reviewer who often overturns correct answers spoils some of them. Full "
       "review left the fewest Administrative rights tickets wrong when there were no overturns, was close to the "
       "security rule at a 5 percent overturn rate, and left the most at a 20 percent overturn rate, between "
       f"{f1(v(20, 0, FULL, 'sensitive_errors_mean'))} and {f1(v(20, 20, FULL, 'sensitive_errors_mean'))}.")
body_p("The security rule gave the fewest tickets wrongly placed in Administrative rights in every setting, tied with "
       "full review when there were no overturns. With full review, this kind of error rose sharply as the overturn "
       f"rate rose, to {v(20, 20, FULL, 'wrong_sensitive_grants_mean'):.0f} at 20/20, more than four times the "
       f"{v(0, 0, AI, 'wrong_sensitive_grants_mean'):.0f} for AI only. These errors come from correct answers that "
       "the reviewer changed at random and that happened to land on Administrative rights. As noted in Section 3.9, "
       "a real reviewer would normally check for a manager’s approval before granting access, so this figure is "
       "likely to overstate the risk from full review.")

# ---------------------------------------------------------------- 4.9
h2("4.9 Statistical Comparisons")
body_p("McNemar’s test was used to compare the four pairs of conditions set out in Section 3.11. The test looks "
       "only at the tickets on which the two conditions disagree, that is, the tickets that one condition got right "
       "and the other got wrong. Table 4.9 gives the results for the first run at four settings. It shows the number "
       "of tickets that only each condition got right, so that the size of the difference can be seen as well as the "
       "p value. The last column shows the share of the 100 runs in which the difference was significant at the 0.05 "
       "level.")
caption("Table 4.9: McNemar’s test for the four pairs of conditions at four reviewer error settings")
rows = []
for s_ in [(0, 0), (5, 5), (10, 10), (20, 20)]:
    for a, b in PAIRS:
        r = MC[(*s_, a, b)]
        rows.append([lab(*s_), f"{SHORT[a]} (A) against {SHORT[b]} (B)", f"{r['first_run_only_a_correct']:,}",
                     f"{r['first_run_only_b_correct']:,}", pval(r["first_run_p"]),
                     f"{r['share_of_runs_significant'] * 100:.0f}%"])
table(["Reviewer error (overturn/miss)", "Comparison", "Only A right", "Only B right", "p value (first run)",
       "Runs significant"], rows, [1500, 2940, 1000, 1000, 1200, 1000])


def share(s_, a, b):
    return MC[(*s_, a, b)]["share_of_runs_significant"] * 100


assert all(share(s_, AI, SEL) == 100 for s_ in SETTINGS)
assert all(MC[(*s_, AI, SEL)]["first_run_only_b_correct"] > MC[(*s_, AI, SEL)]["first_run_only_a_correct"]
           for s_ in SETTINGS)
assert [s_ for s_ in SETTINGS if share(s_, SEL, SEC) < 100] == [(10, 20), (20, 0), (20, 5), (20, 10), (20, 20)]
assert [s_ for s_ in SETTINGS if share(s_, SEC, FULL) < 100] == [(5, 0), (5, 5), (5, 10), (5, 20)]
assert [s_ for s_ in SETTINGS if share(s_, AI, FULL) < 100] == [(10, 10), (10, 20)]
s20 = [share((20, m), SEL, SEC) for m in RATES]
s5 = [share((5, m), SEC, FULL) for m in RATES]
r1010 = MC[(10, 10, AI, FULL)]
net = r1010["first_run_only_b_correct"] - r1010["first_run_only_a_correct"]
body_p("Across all 16 settings, AI only against selective review was significant in every run, always in favour of "
       "selective review. Selective review against the security rule was significant in every run at every setting "
       f"with an overturn rate of 10 percent or less, except 10/20, where it was significant in "
       f"{share((10, 20), SEL, SEC):.0f} of the 100 runs. At a 20 percent overturn rate, the two were rarely "
       f"significantly different, in between {min(s20):.0f} and {max(s20):.0f} percent of runs. The security rule "
       "against full review was significant in every run except at a 5 percent overturn rate, where the two conditions "
       f"were close and the share of significant runs fell from {s5[0]:.0f} percent at 5/0 to {s5[-1]:.0f} at 5/20. "
       "AI only against full review was significant in every run except at 10/10 "
       f"({share((10, 10), AI, FULL):.0f} percent of runs) and 10/20 ({share((10, 20), AI, FULL):.0f} percent of "
       "runs). At a 20 percent overturn rate, the significant differences between AI only and full review were in "
       "favour of AI only.")
body_p("Because the test portion is large, quite small differences can be significant. For example, at 10/10 the "
       f"difference between AI only and full review was significant in the first run (p = {r1010['first_run_p']:.3f}), "
       f"but full review got only {net} more tickets right, or {f1(net / N * 100)} percentage points. For this reason, "
       "the size of each difference is given alongside the test result.")

# ---------------------------------------------------------------- 4.10
h2("4.10 Checking the Choice of Threshold")
body_p("The 70 percent threshold was chosen on the training portion (Section 3.7). To see how much the results depend "
       "on that choice, selective review was repeated on the test portion with general thresholds from 50 to 90 "
       "percent and no security rule, using the same modelled reviewer and the same 100 runs. This check was not used "
       "to choose a new threshold. Table 4.10 gives the results.")
caption("Table 4.10: Selective review with different general thresholds on the test portion")
rows = []
for t in ex["thresholds"]:
    rows.append([f"{t['threshold_pct']}%", f"{t['reviewed_tickets']:,} ({t['reviewed_pct']:.1f}%)",
                 f"{t['acc_kept']:.1f}%", f"{t['acc_sent']:.1f}%", f"{t['admin_left_wrong_unreviewed']}",
                 f"{t['acc_0_0']:.2f}%", f"{t['acc_10_10']:.2f}%", f"{t['acc_20_20']:.2f}%",
                 f"{t['gain_per_100_10_10']:.1f}"])
table(["Threshold", "Tickets reviewed", "Accuracy of kept tickets", "Accuracy of sent tickets",
       "Wrong Administrative rights tickets not reviewed", "Accuracy 0/0", "Accuracy 10/10", "Accuracy 20/20",
       "Extra correct per 100 reviewed (10/10)"], rows, [840, 1200, 900, 900, 1080, 900, 900, 900, 1020])
th = {t["threshold_pct"]: t for t in ex["thresholds"]}
cvt = {round(t["threshold"] * 100): t for t in cv["thresholds"]}
body_p("A higher threshold sends more tickets for review. The tickets the model keeps become more accurate, and so "
       "does the final result, but each review is worth less. With a perfect reviewer, final accuracy rose from "
       f"{f1(th[50]['acc_0_0'])} percent at a 50 percent threshold to {f1(th[90]['acc_0_0'])} percent at 90 percent, "
       f"while the extra correct tickets per 100 reviewed fell from {f1(th[50]['gain_per_100_0_0'])} to "
       f"{f1(th[90]['gain_per_100_0_0'])}. Even at 20/20, the 90 percent threshold gave the highest accuracy "
       f"({f2(th[90]['acc_20_20'])} percent), but it needed {th[90]['reviewed_tickets']:,} reviews, more than twice "
       f"the {th[70]['reviewed_tickets']:,} needed at 70 percent. At 70 percent, the accuracy of the kept and sent "
       f"tickets on the test portion ({f1(th[70]['acc_kept'])} and {f1(th[70]['acc_sent'])} percent) was close to "
       f"the cross validation results ({f1(cvt[70]['acc_kept'] * 100)} and {f1(cvt[70]['acc_flagged'] * 100)} "
       "percent).")
assert th[80]["reviewed_tickets"] < sr["total_reviewed"] and th[80]["acc_0_0"] > v(0, 0, SEC, "accuracy_mean")
body_p("The check also shows what the security rule adds. An 80 percent general threshold sends "
       f"{th[80]['reviewed_tickets']:,} tickets for review, fewer than the {sr['total_reviewed']:,} sent with the "
       "security rule, and it gives slightly higher overall accuracy: "
       f"{f2(th[80]['acc_0_0'])} against {f2(v(0, 0, SEC, 'accuracy_mean'))} percent with a perfect reviewer, and "
       f"{f2(th[80]['acc_10_10'])} against {f2(v(10, 10, SEC, 'accuracy_mean'))} percent at 10/10. However, it leaves "
       f"{th[80]['admin_left_wrong_unreviewed']} wrong Administrative rights tickets without a human check, against "
       f"{sr['admin_wrong_ai'] - sr['admin_wrong_caught_security']} with the security rule. The security rule "
       "therefore does not give the best overall accuracy for the number of tickets reviewed. Its benefit is that it "
       "aims the extra checks at the security-sensitive category.")

# ---------------------------------------------------------------- 4.11
h2("4.11 Hypotheses H1 to H3")
sec_cut = sr["admin_wrong_caught_security"] - sr["admin_wrong_caught_selective"]
left_sel = sr["admin_wrong_ai"] - sr["admin_wrong_caught_selective"]
left_sec = sr["admin_wrong_ai"] - sr["admin_wrong_caught_security"]
pct_fewer = (left_sel - left_sec) / left_sel * 100
pct_more = n_extra / general.sum() * 100
body_p("Table 4.11 sets the Part A results against hypotheses H1 to H3 from Chapter One. H4 is judged from the survey "
       "in Section 4.12.")
caption("Table 4.11: Summary of the results for each hypothesis")
rows = [["H1", "Supported",
         f"Selective review was more accurate than AI only at all 16 settings, by {f1(min(sel_gap))} to "
         f"{f1(max(sel_gap))} percentage points, and the difference was significant in every run."],
        ["H2", "Supported under the stated assumptions",
         f"Full review was the most accurate only when the reviewer overturned 5% of correct answers or fewer "
         f"({cnt[FULL]} of 16 settings). At a 10% overturn rate it was below both selective conditions, and at 20% it "
         f"was below AI only by {f1(-max(full_vs_ai_20))} to {f1(-min(full_vs_ai_20))} percentage points."],
        ["H3", "Partly supported",
         f"Wrong Administrative rights tickets left without a human check fell from {left_sel} to {left_sec} "
         f"({pct_fewer:.0f}% fewer), but the tickets reviewed rose from {general.sum():,} to "
         f"{sr['total_reviewed']:,} ({pct_more:.0f}% more). At a 20% overturn rate the rule did not reduce "
         "Administrative rights errors in the final result."],
        ["H4", "[[To be judged from the survey]]", "See Section 4.12."]]
table(["Hypothesis", "Result", "Main evidence"], rows, [1300, 1900, 5440])
body_p("H1 stated: “When a human only steps in on tickets that the AI is unsure about, overall accuracy will be "
       "higher than when the AI works alone.” Selective review was more accurate than AI only at every one of the "
       "16 reviewer error settings, even when the reviewer overturned 20 percent of correct answers and missed 20 "
       "percent of wrong ones, and McNemar’s test was significant in every run. H1 is supported.")
body_p("H2 stated: “Having a human check every AI output will not always give better results, and may do worse "
       "than reviewing only the uncertain cases.” Full review gave the highest accuracy when the reviewer rarely "
       "or never overturned a correct answer. At an overturn rate of 10 percent or more, it did worse than both "
       "selective conditions in all 8 settings, and at 20 percent it did worse than no review at all. H2 is "
       "therefore supported, but only under the stated assumptions, because the result depends on the overturn rate, "
       "and there is no data on what this rate is for real service desk reviewers.")
body_p("H3 stated: “A stricter review rule for security-sensitive tickets, using Administrative rights requests "
       "as the example, will greatly reduce the number of these tickets that are left wrong without a human check, "
       "for a modest increase in review effort.” The first part is supported. The number of wrong Administrative "
       f"rights tickets left without a human check fell from {left_sel} to {left_sec}, which is {pct_fewer:.0f} "
       "percent fewer. The second part is not clearly supported. The rule added "
       f"{n_extra} reviews, {pct_more:.0f} percent more than selective review alone, and raised the share of tickets "
       f"reviewed from {f1(general.mean() * 100)} to {f1(secmask.mean() * 100)} percent. In addition, when the "
       "reviewer overturned 20 percent of correct answers, the rule led to more Administrative rights errors in the "
       "final result, not fewer. H3 is therefore judged as partly supported. Whether the extra effort is acceptable "
       "for a real service desk is discussed in Chapter Five.")

# ---------------------------------------------------------------- 4.12 survey (placeholders only)
h2("4.12 Survey Results")
body_p("This section reports Part B, the survey, which answers RQ2 and tests H4. The survey was run on Microsoft Forms "
       "after approval from the TU Dublin Research Ethics and Integrity Committee. [[The survey was open from (date) "
       "to (date).]]")
body_p("[[Number]] people opened the survey, [[number]] agreed to take part, and [[number]] "
       "completed it. Table 4.12 shows their roles and experience.")
caption("Table 4.12: Respondents by role and experience")
roles = ["IT professional", "Technical student", "Other technology user", "Prefer not to say"]
exps = ["Less than 1 year", "1 to 3 years", "4 to 7 years", "More than 7 years"]
rows = [["Role", r, "[[n]]", "[[pct]]"] for r in roles] + \
       [["Experience with IT support or service desk tools", e, "[[n]]", "[[pct]]"] for e in exps]
table(["Question", "Answer", "Respondents", "Share"], rows, [2640, 2800, 1600, 1600])
body_p("[[Describe the respondents in one or two sentences, for example the largest group by role and by "
       "experience.]]")
body_p("Table 4.13 shows the answers to the nine rating statements. Each statement used a five point scale from "
       "Strongly Disagree (1) to Strongly Agree (5). Statements 4 to 7 match the four conditions in Part A: AI only, "
       "full review, selective review, and selective review with the security rule.")
caption("Table 4.13: Answers to the rating statements")
stmts = ["I trust the recommendations made by AI based IT support tools.",
         "I believe AI based IT support tools are generally accurate.",
         "Having a human review AI decisions makes me trust the system more.",
         "I would be comfortable relying on a fully automated AI system with no human review.",
         "I would be comfortable relying on a system where a human reviews every AI decision.",
         "I would be comfortable relying on a system where a human only reviews uncertain AI decisions.",
         "I would be comfortable relying on a system where a human reviews uncertain AI decisions, and where "
         "security-sensitive requests, such as requests for administrative rights, need a much higher level of AI "
         "confidence before they are accepted without a human check.",
         "For security-sensitive requests, such as requests for administrative rights, I would want a human to check "
         "the AI’s decision.",
         "Knowing how accurate an AI support tool has been in practice would affect how much I trust it."]
rows = [[str(i + 1), st, "[[n]]", "[[mean]]", "[[pct]]", "[[pct]]"] for i, st in enumerate(stmts)]
table(["No.", "Statement", "Responses", "Mean (1 to 5)", "Agree or strongly agree", "Disagree or strongly disagree"],
      rows, [600, 4040, 1000, 1000, 1000, 1000])
body_p("[[Describe the main pattern in Table 4.13 in two or three sentences, for example which statements had the "
       "highest and lowest agreement, and how comfort differed across statements 4 to 7.]]")
body_p("Table 4.14 shows which approach the respondents said they would feel most comfortable relying on.")
caption("Table 4.14: The approach respondents would feel most comfortable relying on")
opts = ["AI only, no human review", "Human reviews only uncertain cases",
        "Human reviews only uncertain cases, with stricter checks for security-sensitive requests",
        "Human reviews every case", "Unsure"]
table(["Approach", "Respondents", "Share"], [[o, "[[n]]", "[[pct]]"] for o in opts], [5040, 1800, 1800])
body_p("[[Describe Table 4.14 in one or two sentences.]]")
body_p("The answers to the three open questions were grouped into themes using basic thematic analysis "
       "(Section 3.14). [[For each open question, name the main themes, say roughly how many respondents raised each "
       "one, and give a short anonymous quote. The questions were: what makes you trust an IT support tool more or "
       "less; whether human review of AI decisions is worth the extra time and effort; and anything else about AI "
       "based IT support tools.]]")
body_p("H4 stated: “People will say they trust AI support systems more when a human is involved, although this "
       "trust may not match how well the system actually performs.” [[Judge H4 here once the survey data is in. "
       "The first part is supported if most respondents agree with statement 3 in Table 4.13. For the second part, "
       "compare the approach respondents preferred in Table 4.14 with the Part A results. For example, if many "
       "preferred full review, this does not match Part A, where full review was not the most accurate once the "
       "reviewer overturned 10 percent or more of correct answers. Then state whether H4 is supported, partly "
       "supported or not supported.]]")

# ---------------------------------------------------------------- 4.13
h2("4.13 Chapter Summary")
body_p(f"On the {N:,} test tickets, the fine-tuned DistilBERT model gave the correct category to "
       f"{f1(ai_acc)} percent of tickets on its own, and its confidence was a fair guide to whether it was right. "
       f"Sending the {f1(general.mean() * 100)} percent of tickets with a confidence below 70 percent to a modelled "
       f"reviewer raised accuracy to between {f1(min(sel_acc))} and {f1(max(sel_acc))} percent across all 16 "
       "reviewer error settings, a significant gain in every case, so H1 was supported. Full review was the most "
       "accurate condition only when the reviewer rarely overturned correct answers, and with a 20 percent overturn "
       "rate it was less accurate than AI only, so H2 was supported under the stated assumptions. The security rule "
       f"cut the wrong Administrative rights tickets left without a human check from {left_sel} to {left_sec}, but it "
       f"needed {pct_more:.0f} percent more reviews and did not help when the reviewer overturned 20 percent of "
       "correct answers, so H3 was partly supported. [[Add one or two sentences summarising the survey results and "
       "the judgement on H4.]] Chapter Five discusses what these results mean and how they compare with earlier "
       "studies.")

# ---------------------------------------------------------------- references
para("refhead", "REFERENCES")
para("ref", T["ref"].text)

doc.save(OUT)
print("saved", OUT)
