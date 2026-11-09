"""Step 16: summarise the survey (Part B) from the Microsoft Forms export.

Reads the Excel file exported from Microsoft Forms without changing it. By default it looks in the Project
folder; if the export is kept elsewhere (for example OneDrive), give its path as an argument.
Only responses where the person agreed to take part and confirmed they are 18 or over are used.
Rating answers are scored from Strongly Disagree (1) to Strongly Agree (5), as in Section 3.14.
Writes results/survey_results.json and prints the tables for Section 4.12.

Needs pandas and openpyxl. Run from the Project folder:
    python3 code/16_survey_analysis.py
    python3 code/16_survey_analysis.py "/path/to/the export.xlsx"
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
# The export can be passed as an argument if it is kept elsewhere, for example in OneDrive.
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else next(ROOT.glob("Human in the Loop*Participant Survey.xlsx"))
OUT = ROOT / "results" / "survey_results.json"

SCALE = {"Strongly Disagree": 1, "Disagree": 2, "Neutral": 3, "Agree": 4, "Strongly Agree": 5}
ROLES = ["IT professional", "Technical student", "Other technology user", "Prefer not to say"]
EXPS = ["Less than 1 year", "1 to 3 years", "4 to 7 years", "More than 7 years"]
OPTS = ["AI only, no human review", "Human reviews only uncertain cases",
        "Human reviews only uncertain cases, with stricter checks for security-sensitive requests",
        "Human reviews every case", "Unsure"]
NO_CONTENT = {"", ".", "no", "nil", "none", "n/a", "non at the moment"}       # answered, but nothing to code


def pct(n, total):
    return round(n / total * 100, 1)


if __name__ == "__main__":
    df = pd.read_excel(SRC)
    cols = list(df.columns)
    consent, age, role, exp = cols[5], cols[6], cols[7], cols[8]
    likert, pref, opens = cols[9:18], cols[18], cols[19:22]

    start, end = pd.to_datetime(df[cols[1]]), pd.to_datetime(df[cols[2]])
    ok = df[consent].astype(str).str.startswith("I Agree") & df[age].astype(str).str.startswith("Yes")
    v = df[ok]
    n = len(v)
    mins = ((end - start).dt.total_seconds() / 60)[ok]

    res = {"source": SRC.name, "responses_received": len(df),
           "excluded": {"empty or no consent/age": int((~ok).sum())},
           "used": n,
           "first_response": str(start.min().date()), "last_response": str(start.max().date()),
           "minutes_median": round(float(mins.median()), 1),
           "role": {r: [int((v[role] == r).sum()), pct((v[role] == r).sum(), n)] for r in ROLES},
           "experience": {e: [int((v[exp] == e).sum()), pct((v[exp] == e).sum(), n)] for e in EXPS},
           "statements": [], "preference": {}, "open_answered": {}}
    assert sum(c for c, _ in res["role"].values()) == n and sum(c for c, _ in res["experience"].values()) == n

    for i, c in enumerate(likert, 1):
        s = v[c].map(SCALE)
        assert s.notna().all() or s.isna().sum() == v[c].isna().sum()
        s = s.dropna()
        res["statements"].append({
            "no": i, "text": c, "responses": int(len(s)), "mean": round(float(s.mean()), 2),
            "median": float(s.median()),
            "counts": {k: int((s == x).sum()) for k, x in SCALE.items()},
            "agree_pct": pct((s >= 4).sum(), len(s)), "disagree_pct": pct((s <= 2).sum(), len(s)),
            "neutral_pct": pct((s == 3).sum(), len(s))})

    for o in OPTS:
        k = int((v[pref] == o).sum())
        res["preference"][o] = [k, pct(k, n)]
    other = set(v[pref].dropna()) - set(OPTS)
    assert not other, f"unexpected preference answers: {other}"

    for c in opens:
        t = v[c].fillna("").astype(str).str.strip()
        res["open_answered"][c] = {"any_answer": int((t != "").sum()),
                                   "with_content": int((~t.str.lower().isin(NO_CONTENT)).sum())}

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2, ensure_ascii=False))

    print(f"{res['responses_received']} received, {n} used; {res['first_response']} to {res['last_response']}; "
          f"median {res['minutes_median']} minutes")
    for k in ("role", "experience"):
        for a, (c, p) in res[k].items():
            print(f"  {a:<24}{c:>4}{p:>7}%")
    print("\nNo.  n  mean median agree neutral disagree")
    for s in res["statements"]:
        print(f"{s['no']:>3}{s['responses']:>4}{s['mean']:>6}{s['median']:>6}{s['agree_pct']:>7}%"
              f"{s['neutral_pct']:>7}%{s['disagree_pct']:>7}%  {s['text'][:60]}")
    print()
    for o, (c, p) in res["preference"].items():
        print(f"  {c:>3} {p:>5}%  {o}")
    print()
    for c, a in res["open_answered"].items():
        print(f"  {a['any_answer']} answered, {a['with_content']} with content: {c}")
    print("\nsaved", OUT)
