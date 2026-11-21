"""Step 13: build Chapter Six (Conclusion) as a Word file, using the styles of Chapter Four.

The text is typed below. Every number in it comes from Chapters Four and Five, and every source is
already in the reference list. The survey findings come from Section 4.12, which step 17 filled from the survey results.

Run from the Project folder:  python3 code/13_make_chapter6.py
"""
import re
import shutil
from pathlib import Path
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "Chapter Four - Results.docx"
OUT = ROOT / "Chapter Six - Conclusion.docx"

H1, H2 = "Heading 1", "Heading 2"
CH6 = [
(H1, "CHAPTER SIX: CONCLUSION"),
(H2, "6.1 Introduction"),
("", "This chapter concludes the dissertation. It gives a short overview of the research, answers the two research questions, states what the study adds, and notes its main limits and directions for future work."),

(H2, "6.2 Research Overview"),
("", "Many IT service desks now use AI to sort incoming tickets, often with a human check added on the assumption that it will improve the results. Chapter Two showed that this does not always hold (Vaccaro, Almaatouq and Malone, 2024), and that no study had separated the human contribution in IT incident resolution. This study set out to find whether, and under what conditions, human in the loop feedback improves the accuracy of AI driven IT incident resolution, and how human involvement affects user trust."),
("", "In Part A, a fine-tuned and calibrated DistilBERT model was used to compare four conditions on 9,568 test tickets from a public dataset (Goh, 2024): AI only, selective review of tickets below 70 percent confidence, selective review with a stricter rule for Administrative rights tickets, and full review. The reviewer was modelled, with overturn and miss rates from 0 to 20 percent. In Part B, 46 IT professionals, technical students and other users of IT support answered an anonymous survey about trust. All six objectives in Section 1.5 were met: the first four in Chapters Two to Four, the fifth in Section 4.12, and the sixth in Chapter Five and Section 6.6."),

(H2, "6.3 Answers to the Research Questions"),
("", "RQ1 asked: “Does targeted human in the loop feedback improve the accuracy of AI driven IT incident resolution compared with an AI only approach?” Under the assumptions of the simulation, and with accuracy measured as correct ticket categorisation, the answer is yes, as long as the review is aimed. Sending the 10.7 percent of tickets with a confidence below 70 percent to the reviewer raised accuracy from 88.5 percent to between 91.7 and 93.9 percent at all 16 reviewer error settings, a significant gain in every run. Full review reached 100 percent with a perfect reviewer, but it only beat AI only when the reviewer overturned fewer than about 10 to 13 percent of correct answers. Targeted feedback improves accuracy, but more human feedback is not always better."),
("", "RQ2 asked: “How does human involvement affect user trust in AI based IT support systems?” Human involvement raised the trust people said they would place in these systems. Of the 46 respondents, 82.6 percent agreed that human review makes them trust an AI system more, and only 6.5 percent would be comfortable relying on AI with no human review. Most (65.2 percent) preferred selective review with stricter checks for security-sensitive requests, the approach that Part A supports. However, they rated full review as the most comfortable, so their comfort did not fully follow how well each approach performed."),

(H2, "6.4 Summary of the Hypotheses"),
("", "H1 was supported. Selective review was more accurate than AI only at every reviewer error setting."),
("", "H2 was supported under the stated assumptions. Full review was the most accurate condition only when the reviewer rarely overturned correct answers, and at a 20 percent overturn rate it was less accurate than AI only."),
("", "H3 was partly supported. The security rule cut the wrong Administrative rights tickets left without a human check from 35 to 5, but it added 869 reviews, 85 percent more than selective review alone."),
("", "H4 was partly supported. Most respondents said human review raises their trust and chose the approach that Part A supports, but they felt most comfortable with full review."),

(H2, "6.5 Contribution of the Study"),
("", "The study makes four contributions. First, it gives evidence from IT support that human review can lower accuracy as well as raise it. This extends the finding of Vaccaro, Almaatouq and Malone (2024) to ticket classification and shows one reason for it: when the AI is usually right, most of a reviewer's work falls on answers that need no change, so even a small overturn rate can cancel out the errors the reviewer fixes."),
("", "Second, it offers a design that sits between laboratory experiments and uncontrolled real deployments. Real tickets and a real model are combined with a modelled reviewer, and the results are reported across a grid of overturn and miss rates on which another study can place its own reviewers. This is a small step towards the common frameworks that Lai et al. (2023) called for."),
("", "Third, it turns the question of whether to check every ticket into a figure an organisation can measure. On this dataset, full review only paid off if reviewers overturned fewer than about one in ten correct answers. Fourth, it shows the cost of extra protection for a security-sensitive category. Most of the cost of the stricter rule came from the 1 percent watch value, and compared with an 80 percent general threshold it needed about 16 extra reviews for each additional wrong ticket that reached a person. The study also used only free tools and a public dataset, so others can repeat it."),

(H2, "6.6 Recommendations for Practice"),
("", "Service desks that use AI to sort tickets should aim human review at the tickets the AI is unsure about rather than check everything. Before checking every ticket, they should measure how often their reviewers overturn correct answers. Security-sensitive categories can have their own stricter rule, but its cost should be counted and reviewer workload watched. Review thresholds should be checked against accuracy on the organisation's own tickets, and results reported by category (Section 5.8)."),
("", "In production, the same design could be introduced in stages. The model could first run alongside the existing process without changing any tickets, so that its accuracy and confidence can be checked on the organisation's own tickets before any threshold is set. Tickets below the threshold, and security-sensitive tickets that fail the stricter rule, would then go to a review queue in the service desk tool, while the rest are routed automatically. The categories that reviewers correct could be stored and used to retrain the model, which closes the human in the loop. Because ticket wording and categories change over time, accuracy and calibration should be monitored, and the temperature and threshold refitted at regular intervals. A sample of reviewed tickets should also be checked by a second person, so that the overturn rate of the reviewers is known. The security rule fits into existing access approval steps, so that an Administrative rights ticket is never acted on without a human check."),
("", "Review does not have to stop at the category. Where the cost of a mistake is high, for example for security-sensitive or high-impact tickets, reviewers could check the suggested resolution as well as, or instead of, the category, so that a person confirms the fix before it is applied. The confidence-based routing tested in this study could decide which tickets receive this closer check, although its effect on resolution would need to be measured in the future research described in Section 6.8."),

(H2, "6.7 Limitations"),
("", "The main limits were set out in Sections 3.18 and 5.9. Human review was modelled, not observed, and the modelled reviewer made random, independent errors, while real reviewers are likely to make errors that cluster on particular tickets. The results come from one dataset, one model and one security-sensitive category, and they measure correct categorisation, which is an early step in resolving an incident, not a completed fix. The survey sample was small and self-selected, and it records what people say they would trust, not how they act."),

(H2, "6.8 Future Work"),
("", "The most important next step is to repeat the four conditions with real service desk staff reviewing the same tickets. This would measure real overturn and miss rates and show whether errors cluster on hard tickets, as the finding of Sele and Chugunova (2024) suggests. Organisations could also measure their own overturn rates in daily work, which would show where real reviewers sit on the grid used here."),
("", "Second, a longer study could test whether reviewer error rises with workload. Tariq et al. (2025) describe alert fatigue among security analysts, and if a larger review load made reviewers less careful, the security rule would pay off less than this study suggests. Third, the design could be repeated with other datasets, categories and models. Large language models have been used to classify service desk tickets (Paket et al., 2024) and to suggest causes and fixes for cloud incidents (Ahmed et al., 2023), but their confidence would need to be checked and calibrated before it could be used to choose tickets for review."),
("", "Fourth, more flexible calibration methods, several of which are reviewed by Silva Filho et al. (2023), could be tried to close the gap in the 80 to 90 percent confidence band. Fifth, this study measured whether tickets were categorised correctly, not whether they were resolved. A separate research project could measure resolution itself on a live service desk, for example whether a ticket was fixed first time, how long it took and how often it was passed between teams, extending pilots such as that of Peralta et al. (2025) while keeping the human contribution separate. Finally, a follow-up survey could show people how accurate each approach actually was and see whether their preferences change, building on the work of Rechkemmer and Yin (2022) on how performance information shapes trust."),

(H2, "6.9 Final Remarks"),
("", "The main message of this study is simple: adding a human to an AI system is not automatically a safeguard. Human review helped most when it was aimed at the tickets the model was unsure about, where about half of the answers were wrong. Checking everything placed most of the reviewer's effort on answers that needed no change, and with an unreliable reviewer it did more harm than good. The question for service desks is not whether to keep a human in the loop, but where to place them and how reliable their checks are. The survey suggests that people value a human check, and that most would accept one aimed at uncertain and security-sensitive tickets, which is where Part A found it did the most good. In production, this means sending uncertain and security-sensitive tickets to people, checking the suggested fix as well as the category where the stakes are high, and keeping both the model's confidence and the reviewers' accuracy under regular review."),
]


def build_paragraphs(doc):
    """Return a list of new paragraph elements built from CH6, using the doc's styles."""
    body = doc.element.body
    elems = []
    for style, text in CH6:
        p = doc.add_paragraph(style=style or "Normal")
        for part in re.split(r"(\[\[.*?\]\])", text.replace("'", "’")):
            if part:
                r = p.add_run(part)
                if part.startswith("[["):
                    r.font.highlight_color = WD_COLOR_INDEX.YELLOW
        if not style:
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        elif style == H1:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elems.append(p._p)
        body.remove(p._p)
    return elems


def make_chapter():
    doc = Document(SRC)
    body = doc.element.body
    for el in list(body):
        if not el.tag.endswith("sectPr"):
            body.remove(el)
    sect = body[-1]
    for el in build_paragraphs(doc):
        sect.addprevious(el)
    doc.save(OUT)
    words = sum(len(re.sub(r"\[\[.*?\]\]", "", t).split()) for s, t in CH6)
    print(f"saved {OUT.name}: {words} words (not counting placeholders)")


def insert_into_combined(path):
    doc = Document(path)
    if any(p.text.startswith("CHAPTER SIX") for p in doc.paragraphs):
        print("combined file already has Chapter Six; skipped")
        return
    ref = [p for p in doc.paragraphs if p.text.strip() == "REFERENCES"][0]
    for el in build_paragraphs(doc):
        ref._p.addprevious(el)
    doc.save(path)
    print("inserted Chapter Six into", Path(path).name)


if __name__ == "__main__":
    make_chapter()
    old = ROOT / "Chapters 1-5 - Introduction to Discussion.docx"
    new = ROOT / "Chapters 1-6 - Introduction to Conclusion.docx"
    if not new.exists():
        shutil.copy(old, new)
    insert_into_combined(new)
