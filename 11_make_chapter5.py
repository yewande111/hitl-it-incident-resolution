"""Step 11: build Chapter Five (Discussion) as a Word file, using the styles of Chapter Four.

The text is typed below. Every number in it comes from Chapter Four, or from simple arithmetic on the
counts reported there (for example, the overturn rate at which full review stops beating AI only).
The survey findings come from Section 4.12, which step 17 filled from the survey results.

Run from the Project folder:  python3 code/11_make_chapter5.py
"""
import shutil
from pathlib import Path
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "Chapter Four - Results.docx"
OUT = ROOT / "Chapter Five - Discussion.docx"

H1, H2 = "Heading 1", "Heading 2"
CH5 = [
(H1, "CHAPTER FIVE: DISCUSSION"),
(H2, "5.1 Introduction"),
("", "This chapter discusses what the results in Chapter Four mean. It takes the hypotheses in turn, then considers the model's confidence and trust, compares the findings with the studies reviewed in Chapter Two, and draws out what they mean for service desks. As before, every result that involves review is an estimated effect under the assumptions of the simulation, not a measurement of real reviewers."),

(H2, "5.2 Selective Review Improves Accuracy (RQ1 and H1)"),
("", "Selective review was more accurate than AI only at all 16 reviewer error settings, and even its weakest result, 91.72 percent, was 3.2 percentage points above AI only. The answer to RQ1 is therefore yes: under the assumptions of the simulation, targeted human feedback improved the accuracy of AI driven ticket categorisation."),
("", "The gain held up because the model's confidence did what selective review needs. The tickets the model kept were correct 93.1 percent of the time, and the tickets it sent for review only 49.6 percent of the time. The reviewer therefore saw about as many wrong answers as correct ones (518 against 510), so there was much to fix and little to spoil. Even at 20/20, the modelled reviewer fixed about 414 wrong answers and spoiled about 102 correct ones. Working from these counts, with a 20 percent miss rate, selective review would only fall below AI only if the reviewer overturned more than about four in five of the correct answers they saw. This is the logic of active learning, in which the system asks a person for help only with the cases it is unsure about (Mosqueira-Rey et al., 2023)."),

(H2, "5.3 Full Review Depends on the Reviewer (H2)"),
("", "Full review behaved very differently. With a reviewer who never overturned a correct answer it reached 100 percent, but at a 20 percent overturn rate it fell between 6.2 and 8.5 percentage points below AI only. Full review sends the reviewer all 8,465 tickets the model already got right and only 1,103 that it got wrong. Working from these counts, full review only beats AI only when the reviewer overturns fewer than about 10 to 13 percent of correct answers, depending on the miss rate. This matches Table 4.9: at 10/20, the difference between full review and AI only was significant in only 6 percent of runs. Whether checking everything helps therefore depends mainly on the overturn rate, and there is no published figure for that rate on a service desk."),
("", "Accuracy alone also flattered full review. At 10/10 it was 1.5 percentage points more accurate than AI only, but its macro F1 and macro precision were lower, because overturned answers were scattered across all categories, including the small ones. At 20/20 it also placed 243 tickets in Administrative rights by mistake, more than four times as many as AI only. This probably overstates the risk, because a real reviewer would normally check for a manager's approval (Section 3.9), but it shows that a reviewer who changes many answers can create security errors as well as fix them."),
("", "These results support H2 under the stated assumptions. They echo, in an IT support setting, the finding of Vaccaro, Almaatouq and Malone (2024) that a person and an AI working together did worse than the better of the two in decision tasks, especially when the AI alone was more accurate. Sorting tickets is a decision task, and the model was right on 88.5 percent of tickets before any review, so almost all of the reviewer's work fell on answers that needed no change."),

(H2, "5.4 The Security Rule: Coverage at a Cost (H3)"),
("", "The security rule did what it was designed to do. It cut the wrong Administrative rights tickets left without a human check from 35 to 5, and with a reliable reviewer it removed every ticket wrongly given that category. This is the kind of protection that the principle of least privilege calls for (Joint Task Force, 2025), and it follows the idea of holding back a prediction when a mistake would be costly (Hendrickx et al., 2024)."),
("", "The cost was larger than H3 expected. The rule added 85 percent more reviews than selective review alone, and 720 of the 869 extra tickets were already correct. Most of them (686) came from the 1 percent watch value, not from the 95 percent threshold, so the watch value is the main source of the cost. An 80 percent general threshold (Section 4.10) reviewed 326 fewer tickets than the security rule and gave slightly higher accuracy, but it left 26 wrong Administrative rights tickets unchecked, against 5. Compared with that threshold, the security rule spends about 16 extra reviews for each additional wrong Administrative rights ticket that reaches a person. It buys security coverage, not accuracy."),
("", "Whether this effort is acceptable depends on two things. The first is the cost of a wrongly granted access right compared with the cost of a review, which differs between organisations and was not measured here. The second is the reliability of the reviewer. At a 20 percent overturn rate the extra reviews made the result worse, and the rule left more Administrative rights tickets wrong than selective review alone. Tariq et al. (2025) describe alert fatigue among analysts who face very large numbers of alerts. If the extra reviews made reviewers less careful, error rates would rise, which is exactly where the rule stops paying off. The extra effort is defensible where access requests carry real risk and reviewers have time to check them with care, but it is not a free gain. H3 is partly supported."),

(H2, "5.5 Confidence and Calibration"),
("", "Selective review is only as good as the confidence behind it. Temperature scaling worked well in general. The fitted temperatures were above 1, which confirms that the model was overconfident before calibration, as Chen et al. (2023) found for pre-trained language models, and the expected calibration error on the test tickets was 2.9 percent."),
("", "The middle bands were less well behaved. In the 80 to 90 percent band the mean confidence was 85.6 percent but the accuracy only 75.3 percent. Temperature scaling uses one number for every ticket, so it can soften confidence as a whole but cannot fix a gap in one band. This helps explain why a 90 percent threshold still found many wrong answers and gave the highest accuracy even at 20/20. A threshold should therefore be checked against accuracy on an organisation's own tickets, as Silva Filho et al. (2023) argue where mistakes differ in cost, and not taken from the model's stated confidence alone."),
("", "DistilBERT was 2.1 percentage points more accurate than logistic regression in cross validation, in line with Paket et al. (2024), where BERT-based models did well on service desk tickets. The gap was small, which supports the view of Fuchs, Drieschner and Wittges (2022) that simpler models remain strong for tickets. For selective review, the quality of the confidence scores mattered as much as the accuracy."),

(H2, "5.6 Trust and Human Involvement (RQ2 and H4)"),
("", "The literature pointed both ways. Kern et al. (2022) found that a person making the final call made decisions seem fairer, and Kahr et al. (2023) and Rechkemmer and Yin (2022) found that trust follows the accuracy people observe. On the other hand, Alon-Barkat and Busuioc (2023) found that people followed algorithmic advice selectively, and Buçinca, Malaya and Gajos (2021) found that the designs that made people rely on AI more carefully were the ones they liked least."),
("", "The survey supports the first of these views. Of the 46 respondents, 82.6 percent agreed that human review makes them trust a system more, only 6.5 percent would be comfortable with AI alone, and no one chose AI only as their preferred approach. In the open answers, trust was linked mainly to accuracy and a good track record, and nearly everyone who answered the second question said human review was worth the extra time, most often because AI makes mistakes."),
("", "These preferences only partly match Part A. Most respondents (65.2 percent) chose selective review with stricter checks for security-sensitive requests, the approach that Part A supports. Yet when rating each approach on its own, they were most comfortable with full review (mean 4.20 out of 5), although in Part A it was the most accurate only when the reviewer overturned 5 percent or fewer of correct answers. Of the three review options, they were least comfortable with selective review with the security rule (mean 3.46), possibly because that statement was much longer. Considered on its own, more checking seems to feel safer, even though Part A shows that checking everything can lower accuracy. This fits Kern et al. (2022) and echoes Buçinca, Malaya and Gajos (2021), where the designs that worked best were not the ones people liked most. The answer to RQ2 is therefore that human involvement raises the trust people say they would place in AI based IT support systems. Most prefer review aimed at uncertain and security-sensitive tickets, but many still feel most comfortable when every case is checked. H4 is partly supported."),

(H2, "5.7 Position Relative to Earlier Studies"),
("", "Chapter Two found that earlier work ran from abstract experiments to real deployments with no control over what caused the results. This study sits between the two. Unlike Peralta et al. (2025), whose pilot reported the combined effect of several changes, the simulation separates the effect of human review and shows that its size, and even its direction, depend on how review is aimed and how reliable the reviewer is. Unlike the AIOps studies (Notaro, Cardoso and Gerndt, 2021; Ahmed et al., 2023; Zangari et al., 2023), it measures what happens when people review some outputs and not others."),
("", "The study also puts numbers on findings from general experiments. Sele and Chugunova (2024) and Klingbeil, Grützner and Schreck (2024) showed that people often fail to correct AI advice when they should, which corresponds to the miss rate here, and Bansal et al. (2021) found that explanations made people more likely to accept the AI's answer whether it was right or wrong. In this simulation, however, a reviewer who accepted too readily did limited harm, while one who changed too many correct answers did the most damage to full review, so this second kind of error deserves more attention. Reporting results across a grid of overturn and miss rates is also one simple answer to the call of Lai et al. (2023) for common frameworks, because another study can place its own reviewers on the same grid."),

(H2, "5.8 Implications for Service Desks"),
("", "Four practical points follow, subject to the limits in Section 5.9. First, review should be aimed, not applied to everything: sending about one ticket in ten to a person gave most of the available gain and stayed ahead of AI only even with a poor reviewer. Second, an organisation that wants to check every ticket should first measure how often its reviewers overturn correct answers, for example by having a second person check a sample of reviewed tickets. Above about one in ten, full review may do more harm than good. Third, security-sensitive categories can have their own stricter rule, but its review cost should be counted, it should be tuned on the organisation's own tickets, and reviewer workload should be watched. Fourth, results should be reported by category and with macro F1 as well as accuracy, because a single accuracy figure can hide errors in small but important categories."),

(H2, "5.9 Limitations of the Findings"),
("", "The limits of the design were set out in Section 3.18, and three matter most here. First, the modelled reviewer makes random, independent errors, whereas Sele and Chugunova (2024) found that people were least likely to step in when a recommendation was least accurate, so real errors may cluster on particular tickets or categories. Second, because overturned answers go to a random category, the simulation probably overstates the tickets wrongly placed in Administrative rights by full review. Third, the results come from one dataset, one model and one security-sensitive category, and they measure correct categorisation, not a completed fix. The general pattern, in which aimed review holds up and full review depends on the overturn rate, follows from the counts of right and wrong tickets and is likely to hold more widely, but the exact numbers will not. The survey, too, had only 46 respondents, recruited by convenience and snowball sampling, and it records what people say they would trust, not how they act with a real system."),

(H2, "5.10 Chapter Summary"),
("", "Selective review improved accuracy at every reviewer error setting, because the model's confidence sent roughly equal numbers of wrong and correct answers to the reviewer. Full review was better only when the reviewer overturned fewer than about one in ten correct answers. The security rule greatly reduced unchecked security-sensitive errors, but at a high review cost that is only worth paying with a reliable reviewer. Most survey respondents said human review raises their trust and preferred aimed review, but full review felt the most comfortable. Chapter Six draws these findings together."),
]


def build_paragraphs(doc):
    """Return a list of new paragraph elements built from CH5, using the doc's styles."""
    body = doc.element.body
    elems = []
    for style, text in CH5:
        p = doc.add_paragraph(text.replace("'", "\u2019"), style=style or "Normal")
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
    words = sum(len(t.split()) for s, t in CH5 if not t.startswith("[["))
    print(f"saved {OUT.name}: {words} words (not counting placeholders)")


def insert_into_combined(path):
    doc = Document(path)
    if any(p.text.startswith("CHAPTER FIVE") for p in doc.paragraphs):
        print("combined file already has Chapter Five; skipped")
        return
    ref = [p for p in doc.paragraphs if p.text.strip() == "REFERENCES"][0]
    for el in build_paragraphs(doc):
        ref._p.addprevious(el)
    doc.save(path)
    print("inserted Chapter Five into", Path(path).name)


if __name__ == "__main__":
    make_chapter()
    old = ROOT / "Chapters 1-4 - Introduction, Literature Review, Research Design and Results.docx"
    new = ROOT / "Chapters 1-5 - Introduction to Discussion.docx"
    if not new.exists():
        shutil.copy(old, new)
    insert_into_combined(new)
