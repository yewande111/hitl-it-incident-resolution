"""Step 17: fill the survey placeholders in Chapter Four (Section 4.12, Tables 4.11 to 4.14, 4.13 summary).

Numbers come from results/survey_results.json (step 16). The themes in the open answers were coded
by hand from the export, so their counts are approximate ("about") and are typed below, with short
anonymous quotes copied word for word.
Fills "Chapter Four - Results.docx" and the Chapters 1-4 file, and removes the yellow highlight.
Back up both files first. Then rebuild with steps 11, 13, 14, 12 and 15.

Run from the Project folder:
    python3 code/17_fill_survey_results.py
"""
import json
from pathlib import Path

import docx

ROOT = Path(__file__).resolve().parent.parent
RES = json.loads((ROOT / "results" / "survey_results.json").read_text())
FILES = ["Chapter Four - Results.docx",
         "Chapters 1-4 - Introduction, Literature Review, Research Design and Results.docx"]

S = {s["no"]: s for s in RES["statements"]}
P = RES["preference"]
R, E = RES["role"], RES["experience"]
SEC, EVERY, SEL = (P["Human reviews only uncertain cases, with stricter checks for security-sensitive requests"],
                   P["Human reviews every case"], P["Human reviews only uncertain cases"])
n = RES["used"]
WORDS = "zero one two three four five six seven eight nine ten".split()
four_plus = E["4 to 7 years"][0] + E["More than 7 years"][0]


def p(x):                      # 58.7 -> "58.7 percent"
    return f"{x:.1f} percent"


# Every sentence below was checked against results/survey_results.json and the export on 2026-11-07.
TEXT = {
    "[[The survey was open from (date) to (date).]]":
        f"The survey was open from 30 October to 7 November 2026, and the median time taken to "
        f"complete it was about {WORDS[round(RES['minutes_median'])]} minutes.",
    "[[Number]]":
        f"In total, {RES['responses_received']} responses were received. One was empty and was removed, "
        f"leaving {n} respondents. All {n} agreed to take part and confirmed they were aged 18 or over. "
        f"Microsoft Forms only records submitted responses, so the number of people who opened the survey "
        f"without finishing it is not known. Table 4.12 shows their roles and experience.",
    "[[Describe the respondents":
        f"Most respondents were IT professionals ({R['IT professional'][0]}, {p(R['IT professional'][1])}), "
        f"followed by technical students ({R['Technical student'][0]}, {p(R['Technical student'][1])}). "
        f"Nearly all had at least one year of experience with IT support or service desk tools, and "
        f"{four_plus} ({p(four_plus / n * 100)}) had four years or more.",
    "[[Describe the main pattern in Table 4.13":
        f"Agreement was highest for statement 8: {p(S[8]['agree_pct'])} wanted a human to check the AI’s "
        f"decision on security-sensitive requests. Statements 3 and 5 followed, at {p(S[3]['agree_pct'])} each. "
        f"Agreement was lowest for statement 4: only {p(S[4]['agree_pct'])} would be comfortable relying on AI "
        f"with no human review, and {p(S[4]['disagree_pct'])} disagreed. General trust in AI based IT support "
        f"tools was moderate. About half agreed with statement 1 ({p(S[1]['agree_pct'])}) and fewer with "
        f"statement 2 ({p(S[2]['agree_pct'])}), and many gave a neutral answer ({p(S[1]['neutral_pct'])} and "
        f"{p(S[2]['neutral_pct'])}). Across statements 4 to 7, comfort was highest for full review "
        f"(mean {S[5]['mean']:.2f}), then selective review ({S[6]['mean']:.2f}), then selective review with the "
        f"security rule ({S[7]['mean']:.2f}), and lowest for AI only ({S[4]['mean']:.2f}).",
    "[[Describe Table 4.14":
        f"Nearly two thirds of respondents ({SEC[0]}, {p(SEC[1])}) chose selective review with stricter checks "
        f"for security-sensitive requests, and about a third ({EVERY[0]}, {p(EVERY[1])}) chose full review. "
        f"{'One respondent' if SEL[0] == 1 else SEL[0]} chose selective review without the stricter checks, "
        f"and no one chose AI only or Unsure. IT professionals and the other respondents answered in a similar "
        f"way: 18 of the 27 IT professionals and 12 of the other 19 respondents chose selective review with "
        f"stricter checks.",
    "[[For each open question":
        "For the first question, on what makes people trust an IT support tool more or less (32 answers), "
        "the most common theme was accuracy and a good track record (about 14 respondents). About 8 said that "
        "wrong answers lower their trust, about 8 wanted the tool to explain its reasoning or show its sources, "
        "and about 6 wanted evidence that it had been tested. Fewer mentioned human involvement (about 4) or "
        "security and data protection (about 3). One respondent wrote: “I trust a tool more when it explains "
        "how it reached an answer and has a good track record. I trust it less when it gives confident wrong "
        "answers or makes changes without asking.” For the second question, whether human review of AI "
        "decisions is worth the extra time and effort (40 answers), 35 respondents said yes, most often "
        "because AI makes mistakes (about 16), for example: “It is worth it, because AI decisions tend to "
        "hallucinate”. Smaller groups said that review matters most when the risk is high (about 5), or "
        "mentioned accountability (about 4). Three said it depends on the risk, for example: “For simple tasks "
        "like password resets, occasional spot checks are enough.” Two said it is not needed for every "
        "decision, one writing that “having a human review every decision would be counter productive”. "
        "For the third question, on anything else about AI based IT support tools (23 answers), the most "
        "common theme was that these tools are not reliable on their own for complex or unusual problems "
        "(about 14), although about 7 found them useful for quick, routine tasks. About 5 said the tools "
        "should support people rather than replace them, for example: “it’s still a tool regardless and it "
        "needs a guiding hand”.",
    "[[Judge H4 here":
        f"The first part is supported. Most respondents ({p(S[3]['agree_pct'])}) agreed that having a human "
        f"review AI decisions makes them trust the system more (statement 3), and only {p(S[4]['agree_pct'])} "
        f"would be comfortable relying on AI with no human review (statement 4). The second part has mixed "
        f"support. When asked to choose one approach, most respondents ({p(SEC[1])}) chose selective review "
        f"with stricter checks for security-sensitive requests. This is in line with Part A, where selective "
        f"review was more accurate than AI only at every setting and the security rule left far fewer wrong "
        f"Administrative rights tickets without a human check. However, when rating each approach on its own, "
        f"respondents were most comfortable with full review (mean {S[5]['mean']:.2f}) and least comfortable, "
        f"of the three review options, with selective review with the security rule (mean "
        f"{S[7]['mean']:.2f}), and about a third ({p(EVERY[1])}) chose full review. In Part A, full review was "
        f"the most accurate only when the reviewer overturned 5 percent or fewer of correct answers. So "
        f"respondents’ comfort did not fully follow how well each approach performed. Statement 7 was also much "
        f"longer than the other statements, which may have lowered its rating. H4 is therefore judged as "
        f"partly supported.",
    "[[Add one or two sentences summarising the survey results":
        f"In the survey, {p(S[3]['agree_pct'])} of the {n} respondents agreed that human review makes them "
        f"trust an AI system more, and only {p(S[4]['agree_pct'])} would be comfortable with AI alone. Most "
        f"({p(SEC[1])}) preferred selective review with stricter checks for security-sensitive requests, in "
        f"line with Part A, but full review had the highest comfort rating, so H4 was partly supported.",
}
H4_ROW = ("Partly supported",
          f"{S[3]['agree_pct']:.1f}% agreed that human review makes them trust the system more (statement 3). "
          f"{SEC[1]:.1f}% chose selective review with the security rule, in line with Part A, but comfort "
          f"ratings were highest for full review (mean {S[5]['mean']:.2f}), which in Part A was the most "
          f"accurate only at an overturn rate of 5% or less.")


def set_cell(cell, text):
    runs = [r for par in cell.paragraphs for r in par.runs]
    runs[0].text = text
    runs[0].font.highlight_color = None
    for r in runs[1:]:
        r.text = ""
        r.font.highlight_color = None


def fill(path):
    d = docx.Document(path)
    done = set()
    for par in d.paragraphs:
        runs = par.runs
        for i, r in enumerate(runs):
            key = next((k for k in TEXT if r.text.startswith(k)), None)
            if not key:
                continue
            closed = "]]" in r.text
            r.text = TEXT[key]
            r.font.highlight_color = None
            done.add(key)
            if key == "[[Number]]":          # the rest of this paragraph is replaced by the new sentences
                for x in runs[i + 1:]:
                    x.text = ""
                break
            for x in runs[i + 1:]:           # Word sometimes splits a placeholder over several runs
                if closed:
                    break
                closed = "]]" in x.text
                x.text = ""
                x.font.highlight_color = None
    missing = set(TEXT) - done
    assert not missing, f"not found in {path.name}: {missing}"

    by_header = {tuple(c.text for c in t.rows[0].cells): t for t in d.tables}
    hyp = by_header[("Hypothesis", "Result", "Main evidence")]
    row = next(r for r in hyp.rows if r.cells[0].text == "H4")
    set_cell(row.cells[1], H4_ROW[0])
    set_cell(row.cells[2], H4_ROW[1])

    t412 = by_header[("Question", "Answer", "Respondents", "Share")]
    for r in t412.rows[1:]:
        c, pc = (R | E)[r.cells[1].text]
        set_cell(r.cells[2], str(c))
        set_cell(r.cells[3], f"{pc:.1f}%")

    t413 = next(t for h, t in by_header.items() if h[:2] == ("No.", "Statement"))
    for r in t413.rows[1:]:
        s = S[int(r.cells[0].text)]
        same = r.cells[1].text.replace("’", "'").startswith(s["text"].strip()[:150])   # Forms cuts long headings
        assert same, (r.cells[1].text, s["text"])
        for cell, val in zip(r.cells[2:], (str(s["responses"]), f"{s['mean']:.2f}",
                                           f"{s['agree_pct']:.1f}%", f"{s['disagree_pct']:.1f}%")):
            set_cell(cell, val)

    t414 = by_header[("Approach", "Respondents", "Share")]
    for r in t414.rows[1:]:
        c, pc = P[r.cells[0].text]
        set_cell(r.cells[1], str(c))
        set_cell(r.cells[2], f"{pc:.1f}%")

    d.save(path)
    left = [x.text[:60] for x in d.paragraphs if "[[" in x.text]
    left += [c.text for t in d.tables for row in t.rows for c in row.cells if "[[" in c.text]
    print(f"filled {path.name}; placeholders left: {left or 'none'}")


if __name__ == "__main__":
    for f in FILES:
        fill(ROOT / f)
    for k, v in TEXT.items():
        print(f"\n{k[:40]}...\n  {v}")
