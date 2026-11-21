"""Step 12: build the full dissertation draft, with front matter, A4 pages, page numbers and appendices.

Reads "Chapters 1-6 - Introduction to Conclusion.docx" (it is not changed) and writes
"Dissertation - Full Draft.docx". The front matter follows the order of the Fergal Connolly
template thesis: title page, declaration, acknowledgements, acronyms, list of figures, list of
tables, contents and abstract. All headings are black, as in the template. Front matter pages are numbered i, ii, iii (the title page shows no number)
and Chapter One starts again at page 1.

The Contents, List of Figures and List of Tables are Word fields. This script cannot work out
page numbers, so Word fills them in when the file is opened: click Yes when Word asks to update
the fields, or right-click a list and choose Update Field > Update entire table.

Run from the Project folder:  python3 code/12_make_full_draft.py
"""
import copy
import json
import re
from pathlib import Path
from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Inches, Twips

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "Chapters 1-6 - Introduction to Conclusion.docx"
SURVEY = ROOT / "3. Survey Instrument (version 2).docx"
PIS = ROOT / "untitled folder" / "1. Participant Information Sheet.docx"
CONSENT = ROOT / "untitled folder" / "2. Participant Consent Form.docx"
OUT = ROOT / "Dissertation - Full Draft.docx"
LOGO = ROOT / "images" / "TU Dublin logo.png"      # taken from the title page of the template theses

TITLE = "Evaluating the Effectiveness of Human in the Loop Feedback on the Accuracy of AI Driven IT Ticket Classification"
A4_W, A4_H = 11906, 16838          # twips
CAPTION = re.compile(r"^(Figure|Table) \d+\.\d+:")

DECLARATION = ("I hereby certify that the material, which I now submit for assessment on the programmes of study "
    "leading to the award of a Master of Science, is entirely my own personal work. The work of others has not been "
    "taken except to the extent that it has been cited and acknowledged within the text of my own. No portion of the "
    "work contained within this dissertation has been submitted in support of an application for another degree or "
    "qualification to this or any other institution.")

ACKNOWLEDGEMENTS = ("I would like to thank my supervisor, Mr. Kevin Bayliss, for the guidance, advice and patience "
    "given throughout this project. I am deeply grateful to my parents for their love and constant support, "
    "and for always believing in me. I also thank my classmates, who encouraged me not to give up when we started "
    "this programme. Their support made a real difference, and I could not have completed this work without it.")

ABSTRACT = [
    "Many IT service desks use artificial intelligence (AI) to categorise incoming tickets. Having a person "
    "check the AI's decisions is a common safeguard, but research shows that this does not always improve "
    "accuracy. This study asked whether targeted human in the loop feedback improves the accuracy of AI "
    "driven IT incident resolution, and how human involvement affects user trust. As the study is a simulation, "
    "accuracy was measured as correct ticket categorisation, the first step in resolving an incident, not as full "
    "resolution.",
    "A DistilBERT model was fine-tuned on a public dataset of 47,837 IT support tickets and calibrated with "
    "temperature scaling. Four conditions were compared on 9,568 test tickets: AI only, selective review of tickets "
    "below 70 percent confidence, selective review with a stricter rule for Administrative rights requests, and full "
    "review, with modelled reviewer error rates from 0 to 20 percent. An anonymous survey asked 46 IT professionals, "
    "technical students and other IT support users about their trust in AI tools.",
    "The model alone categorised 88.5 percent of tickets correctly. Selective review checked 10.7 percent of tickets "
    "and raised accuracy to between 91.7 and 93.9 percent at every reviewer error setting. Full review was the most "
    "accurate only when the reviewer rarely changed correct answers, and fell below AI only when the reviewer "
    "overturned 20 percent of them. The security rule cut unchecked wrong Administrative rights tickets from 35 to 5, "
    "but needed 85 percent more reviews. In the survey, 82.6 percent said human review raises their trust, and most "
    "preferred selective review with stricter security checks, but they rated full review highest for comfort.",
    "Service desks should aim human review at tickets the AI is unsure about, and measure how often reviewers change "
    "answers that were already correct. Measuring full resolution is left for future research.",
]

ABBREVIATIONS = [
    ("AI", "Artificial intelligence"),
    ("AIOps", "Artificial intelligence for IT operations"),
    ("BERT", "Bidirectional Encoder Representations from Transformers"),
    ("DistilBERT", "A smaller, distilled version of BERT"),
    ("GDPR", "General Data Protection Regulation"),
    ("GPU", "Graphics processing unit"),
    ("H1 to H4", "Hypotheses one to four"),
    ("HITL", "Human in the loop"),
    ("IT", "Information technology"),
    ("MSc", "Master of Science"),
    ("REIC", "Research Ethics and Integrity Committee"),
    ("RQ1, RQ2", "Research questions one and two"),
    ("SVM", "Support vector machine"),
    ("TF-IDF", "Term frequency-inverse document frequency"),
    ("TU Dublin", "Technological University Dublin"),
]

SURVEY_RESULTS = json.loads((ROOT / "results" / "survey_results.json").read_text())     # from step 16

RESULTS_INTRO = ("This appendix gives the full counts for the survey in Appendix A. In total, 47 responses were "
    "received between 30 October and 5 November 2026 (the survey closed on 7 November). One was empty and was removed, leaving 46. All 46 respondents "
    "agreed to take part, confirmed they were aged 18 or over, and answered every closed question. Their roles and "
    "experience are in Table 4.12, the mean and agreement for each rating statement in Table 4.13, and the approach "
    "they would feel most comfortable relying on in Table 4.14. Table C.1 gives the number of respondents who chose "
    "each answer for the nine rating statements, whose wording is in Table 4.13. The counts were produced from the "
    "Microsoft Forms export by script 16 (Appendix D).")
RESULTS_OPEN = ("The three open questions were optional. Table C.2 gives the number who answered each one and the "
    "main themes, with the approximate number of respondents who raised each theme. Some answers had no content "
    "(for example “no” or “none”) and are not counted. One answer can raise more than one theme. The open "
    "answers are summarised as themes, not given in full, so that no respondent can be identified.")
OPEN_THEMES = [     # in question order; the questions themselves come from the export
    "Accuracy and a good track record (about 14); wrong answers lower trust (about 8); explaining its reasoning or "
    "showing its sources (about 8); evidence that it has been tested (about 6); human involvement (about 4); "
    "security and data protection (about 3).",
    "Yes (35), mostly because AI makes mistakes (about 16), because the risk or impact is high (about 5), for "
    "accountability (about 4) or to help the AI improve (about 3); it depends on the risk (3); not for every "
    "decision (2).",
    "Not reliable on their own for complex or unusual problems (about 14); useful for quick, routine tasks "
    "(about 7); should support people rather than replace them (about 5); control, security and audit (2); "
    "expected to improve (2); concern about jobs (1).",
]

CODE_INTRO = [
    "The code for Part A is a set of numbered Python scripts that are run in order. Scripts 02 and 04, which train "
    "DistilBERT, were run on the free GPU service provided by Kaggle. The other steps run on an ordinary laptop. The "
    "data is the public IT Service Ticket Classification Dataset (Goh, 2024). The code, result files and figures are "
    "available at https://github.com/yewande111/hitl-it-incident-resolution. The fine-tuned DistilBERT model (about "
    "270 MB) is too large for GitHub, but scripts 02 and 04 recreate it on Kaggle.",
]
CODE_STEPS = [
    "01_model_selection_cross_validation.py compares Naive Bayes, logistic regression and a linear support vector "
    "machine with five fold cross validation on the training portion.",
    "02_transformer_cross_validation.py runs DistilBERT on the same five folds, fits temperature scaling and checks "
    "the confidence bands, review thresholds and security rule (Tables 3.2 to 3.6).",
    "03_make_diagram.py draws Figure 3.1.",
    "04_final_model_and_test_predictions.py fine-tunes DistilBERT on the whole training portion and records its "
    "predictions for the test portion.",
    "05_review_conditions_experiment.py runs the four conditions with the modelled reviewer and the McNemar tests.",
    "06_fill_chapter_values.py fills the results into Chapter 3.",
    "07_chapter4_extra_results.py works out the extra results used in Chapter 4.",
    "09_make_extra_figures.py draws Figure 3.2 and Figures 4.1 to 4.4.",
    "16_survey_analysis.py counts the survey answers (Part B) from the Microsoft Forms export, for Section 4.12 "
    "and Appendix C.",
    "Scripts 08, 10 to 15, 17 and 18 build the Word files, format them or tighten their wording, and do not change "
    "any results.",
]
CODE_SETTINGS = ("Main settings: an 80 percent training and 20 percent test split, stratified by category, with random "
    "seed 42; five fold cross validation on the training portion only, with seed 42; DistilBERT "
    "(distilbert-base-uncased) with up to 256 word pieces per ticket, learning rate 5e-5, 3 epochs and batch size 32, "
    "not tuned; a temperature chosen between 0.50 and 5.00 on 10 percent of each fold's training tickets; a general "
    "review threshold of 70 percent; a security rule threshold of 95 percent with a 1 percent watch value; and "
    "modelled reviewer overturn and miss rates of 0, 5, 10 and 20 percent, with 100 runs each. Full details are in "
    "the README file that comes with the code.")


# ---------- small helpers ----------

def curly(text, prev=" "):
    """Straight quotes to curly ones. prev is the character before text, to tell opening from closing."""
    out = []
    for i, ch in enumerate(text):
        if ch == "'":           # an apostrophe before a year, as in CHI '21, is not an opening quote
            ch = "‘" if prev in " (“" and not text[i + 1:i + 2].isdigit() else "’"
        elif ch == '"':
            ch = "“" if prev in " (‘" else "”"
        out.append(ch)
        prev = ch
    return "".join(out)


def curl_document(doc):
    """Curly quotes everywhere, including text copied from the appendix documents. Works on the w:t
    elements directly, so field codes such as the table of contents are left alone."""
    for p in doc.element.body.iter(qn("w:p")):
        prev = " "
        for t in p.iter(qn("w:t")):
            if t.text:
                t.text = curly(t.text, prev)
                prev = t.text[-1]


def add_text(p, text, bold=None, italic=None, size=None):
    """Add text to a paragraph, highlighting [[placeholders]] in yellow."""
    for piece in re.split(r"(\[\[.*?\]\])", curly(text)):
        if not piece:
            continue
        r = p.add_run(piece)
        r.bold, r.italic = bold, italic
        if size:
            r.font.size = Pt(size)
        if piece.startswith("[["):
            r.font.highlight_color = WD_COLOR_INDEX.YELLOW
    return p


def new_par(doc, text="", style="Normal", align=None, bold=None, italic=None, size=None,
            before=None, after=None, indent=None, hanging=None, keep_next=False):
    """Make a paragraph and detach it, so it can be placed anywhere in the body."""
    p = doc.add_paragraph(style=style)
    add_text(p, text, bold, italic, size)
    f = p.paragraph_format
    if align is not None:
        f.alignment = align
    if before is not None:
        f.space_before = Pt(before)
    if after is not None:
        f.space_after = Pt(after)
    if indent is not None:
        f.left_indent = Inches(indent)
    if hanging is not None:
        f.first_line_indent = Inches(-hanging)
    if keep_next:
        f.keep_with_next = True
    if style == "Front Heading":
        f.page_break_before = True      # also set directly, as on the REFERENCES heading
    doc.element.body.remove(p._p)
    return p


def body_par(doc, text):
    return new_par(doc, text, align=WD_ALIGN_PARAGRAPH.JUSTIFY)


def field_start(p, instr):
    for kind, val in (("begin", None), (None, instr), ("separate", None)):
        r = OxmlElement("w:r")
        if kind:
            fc = OxmlElement("w:fldChar")
            fc.set(qn("w:fldCharType"), kind)
            r.append(fc)
        else:
            it = OxmlElement("w:instrText")
            it.set(qn("xml:space"), "preserve")
            it.text = val
            r.append(it)
        p._p.append(r)


def field_end(p):
    r = OxmlElement("w:r")
    fc = OxmlElement("w:fldChar")
    fc.set(qn("w:fldCharType"), "end")
    r.append(fc)
    p._p.append(r)


def ensure_style(doc, name, base, configure=None):
    try:
        return doc.styles[name]
    except KeyError:
        s = doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        s.base_style = doc.styles[base]
        s.quick_style = False
        if configure:
            configure(s)
        return s


# ---------- steps ----------

def setup_styles(doc, text_w):
    def front(s):
        s.paragraph_format.page_break_before = True
        s.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT      # supervisor feedback, 2026-11-21
        lvl = OxmlElement("w:outlineLvl")       # body text level, so these headings stay out of Contents
        lvl.set(qn("w:val"), "9")
        s.element.get_or_add_pPr().append(lvl)

    def toc(level):
        def conf(s):
            f = s.paragraph_format
            f.alignment = WD_ALIGN_PARAGRAPH.LEFT
            f.line_spacing = 1.15
            f.space_before = Pt(0)
            f.space_after = Pt(6 if level == 1 else 3)
            f.left_indent = Inches(0.3 * (level - 1))
            f.tab_stops.add_tab_stop(Twips(text_w), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        return conf

    # Word's built-in heading styles (and the character styles linked to them) are blue;
    # the template theses use black headings
    names = ["Heading %d" % i for i in range(1, 10)] + ["Title", "Subtitle", "Caption"]
    for name in names + [n + " Char" for n in names]:
        try:
            s = doc.styles[name]
        except KeyError:
            continue
        for c in s.element.xpath("./w:rPr/w:color"):
            for a in ("themeColor", "themeShade", "themeTint"):
                c.attrib.pop(qn("w:" + a), None)
            c.set(qn("w:val"), "000000")

    ensure_style(doc, "Front Heading", "Heading 1", front)
    for kind in ("Figure", "Table"):
        ensure_style(doc, f"{kind} Caption", "Normal").font.bold = True
    for level in (1, 2):
        s = ensure_style(doc, f"toc {level}", "Normal", toc(level))
        s.element.set(qn("w:styleId"), f"TOC{level}")     # the ID Word itself uses for these styles


def fit_to_page(doc, text_w):
    """A4 is narrower than US Letter, so shrink images and tables that are wider than the text area."""
    max_emu = text_w * 635
    body = doc.element.body
    for inline in body.iter(qn("wp:inline")):
        ext = inline.find(qn("wp:extent"))
        cx, cy = int(ext.get("cx")), int(ext.get("cy"))
        if cx > max_emu:
            ncy = int(cy * max_emu / cx)
            ext.set("cx", str(max_emu)); ext.set("cy", str(ncy))
            for a in inline.iter(qn("a:ext")):
                a.set("cx", str(max_emu)); a.set("cy", str(ncy))
    for t in doc.tables:
        cols = t._tbl.tblGrid.findall(qn("w:gridCol"))
        total = sum(int(c.get(qn("w:w"))) for c in cols)
        if total <= text_w:
            continue
        k = text_w / total
        for c in cols:
            c.set(qn("w:w"), str(int(int(c.get(qn("w:w"))) * k)))
        for tcw in t._tbl.iter(qn("w:tcW")):
            if tcw.get(qn("w:type")) == "dxa":
                tcw.set(qn("w:w"), str(int(int(tcw.get(qn("w:w"))) * k)))


NUMBERS = {"ONE": "1", "TWO": "2", "THREE": "3", "FOUR": "4", "FIVE": "5", "SIX": "6"}


def chapter_digits(doc):
    """CHAPTER ONE -> CHAPTER 1, and Chapter Two / Chapters Two to Four -> Chapter 2 / Chapters 2 to 4
    (supervisor feedback, 2026-11-21)."""
    word = r"(One|Two|Three|Four|Five|Six|ONE|TWO|THREE|FOUR|FIVE|SIX)"
    pat = re.compile(r"\b(CHAPTER|Chapters?) " + word + r"\b(?:( to | and )" + word + r"\b)?")

    def sub(m):
        out = m.group(1) + " " + NUMBERS[m.group(2).upper()]
        if m.group(3):
            out += m.group(3) + NUMBERS[m.group(4).upper()]
        return out
    for t in doc.element.body.iter(qn("w:t")):
        if t.text:
            t.text = pat.sub(sub, t.text)
    left = [p.text[:60] for p in doc.paragraphs if re.search(r"\b(CHAPTER|Chapters?) " + word + r"\b", p.text)]
    assert not left, left


def spell_out_chapter4(doc):
    """In Chapter 4, write RQ1 as Research Question 1 and H1 as Hypothesis 1 (supervisor feedback, 2026-11-21)."""
    body = list(doc.element.body.iterchildren())
    heads = [i for i, el in enumerate(body)
             if el.tag == qn("w:p") and "".join(t.text or "" for t in el.iter(qn("w:t"))).startswith(("CHAPTER 4", "CHAPTER 5"))]
    assert len(heads) == 2, heads
    steps = [(r"\b[Hh]ypotheses H(\d) to H(\d)\b", r"Hypotheses \1 to \2"),
             (r"\bH(\d) to H(\d)\b", r"Hypotheses \1 to \2"),
             (r"\bRQ(\d)\b", r"Research Question \1"),
             (r"\bH(\d)\b", r"Hypothesis \1")]
    for el in body[heads[0]:heads[1]]:
        for t in el.iter(qn("w:t")):
            if t.text:
                for a, b in steps:
                    t.text = re.sub(a, b, t.text)


def mark_captions(doc):
    figs, tabs = [], []
    for p in doc.paragraphs:
        m = CAPTION.match(p.text)
        if m:
            kind = m.group(1)
            p.style = doc.styles[f"{kind} Caption"]
            for r in p.runs:            # Word copies direct formatting into the lists of figures and tables
                r.bold = None
                r.italic = None
            (figs if kind == "Figure" else tabs).append(p.text)
    return figs, tabs


def highlight_placeholders(doc):
    """Chapter Five's [[placeholders]] were not yellow; split those runs so only the placeholder is highlighted."""
    for p in doc.paragraphs:
        for r in list(p.runs):
            if "[[" not in r.text or r.font.highlight_color:
                continue
            pieces = [x for x in re.split(r"(\[\[.*?\]\])", r.text) if x]
            for piece in pieces:
                nr = copy.deepcopy(r._r)
                r._r.addprevious(nr)
                for t in nr.findall(qn("w:t")):
                    nr.remove(t)
                t = OxmlElement("w:t")
                t.set(qn("xml:space"), "preserve")
                t.text = piece
                nr.append(t)
                if piece.startswith("[["):
                    rpr = nr.get_or_add_rPr()
                    h = OxmlElement("w:highlight")
                    h.set(qn("w:val"), "yellow")
                    rpr.append(h)
            r._r.getparent().remove(r._r)


def _h1(doc, text):
    p = new_par(doc, text, style="Heading 1", align=WD_ALIGN_PARAGRAPH.CENTER)
    p.paragraph_format.page_break_before = True
    return p


def sub_heading(doc, text):
    return new_par(doc, text, bold=True, before=12, after=4, keep_next=True)


def copy_support_doc(doc, path, skip=(), replace=None, number_from=1):
    """Copy a supporting document's text: Heading 2 becomes a bold line, lists become numbered or bulleted lines."""
    out, n = [], number_from
    for i, p in enumerate(Document(path).paragraphs):
        text = p.text.strip()
        if i == 0 or i in skip or not text:
            continue
        if replace and i in replace:
            text = replace[i]
        style = p.style.name
        if style.startswith("Heading"):
            out.append(sub_heading(doc, text))
        elif style == "List Number":
            out.append(new_par(doc, f"{n}.\t{text}", indent=0.35, hanging=0.35, after=4))
            n += 1
        elif style == "List Bullet":
            out.append(new_par(doc, f"•\t{text}", indent=0.35, hanging=0.35, after=4))
        else:
            out.append(body_par(doc, text))
    return out


def build_appendices(doc):
    els = [_h1(doc, "APPENDIX A: SURVEY INSTRUMENT")]
    els += copy_support_doc(doc, SURVEY, skip={3}, replace={
        2: "Survey platform: Microsoft Forms (online, anonymous responses). Estimated completion time: 5 to 10 minutes.",
        5: "The survey opens with the Participant Information Sheet and consent statement in Appendix B. Respondents "
           "must select I Agree to proceed to the questions below. Respondents must also confirm that they are aged "
           "18 or over. Anyone who selects No is taken straight to the end of the survey and no answers are recorded.",
    })
    els.append(_h1(doc, "APPENDIX B: PARTICIPANT INFORMATION SHEET AND CONSENT FORM"))
    els.append(sub_heading(doc, "Participant Information Sheet"))
    els += copy_support_doc(doc, PIS, replace={
        22: "This study has been reviewed and approved by the Research Ethics and Integrity Committee (REIC) in line "
            "with Technological University Dublin ethical guidelines. No recruitment, survey distribution, or "
            "collection of participant responses took place until written ethics approval had been received.",
    })
    els.append(sub_heading(doc, "Participant Consent Form"))
    els += copy_support_doc(doc, CONSENT, skip={1})
    els.append(_h1(doc, "APPENDIX C: SURVEY RESULTS"))
    els += survey_results_appendix(doc)
    els.append(_h1(doc, "APPENDIX D: CODE AND REPRODUCIBILITY"))
    els += [body_par(doc, t) for t in CODE_INTRO]
    els += [new_par(doc, f"•\t{t}", indent=0.35, hanging=0.35, after=4) for t in CODE_STEPS[:-1]]
    els.append(body_par(doc, CODE_STEPS[-1]))
    els.append(body_par(doc, CODE_SETTINGS))
    sect = doc.element.body[-1]
    for p in els:
        sect.addprevious(p._element)      # paragraphs and tables


def appendix_table(doc, caption, header, rows, widths):
    """A captioned table with the same borders as the chapter tables (copied from the first one)."""
    t = doc.add_table(rows=0, cols=len(header))
    t._tbl.remove(t._tbl.tblPr)
    t._tbl.insert(0, copy.deepcopy(doc.tables[0]._tbl.tblPr))
    for i, values in enumerate([header] + rows):
        cells = t.add_row().cells
        for cell, text, w in zip(cells, values, widths):
            cell.width = Inches(w)
            add_text(cell.paragraphs[0], str(text), bold=True if i == 0 else None, size=10.5)
    for col, w in zip(t._tbl.tblGrid.findall(qn("w:gridCol")), widths):
        col.set(qn("w:w"), str(int(w * 1440)))
    doc.element.body.remove(t._tbl)
    return [new_par(doc, caption, bold=True, before=6, keep_next=True), t, new_par(doc)]


def survey_results_appendix(doc):
    names = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]
    rows = [[s["no"]] + [s["counts"][k] for k in names] + [s["responses"], f"{s['median']:g}"]
            for s in SURVEY_RESULTS["statements"]]
    els = [body_par(doc, RESULTS_INTRO)]
    els += appendix_table(doc, "Table C.1: Number of respondents choosing each answer to the rating statements",
                          ["No.", "Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree", "Total",
                           "Median"], rows, [0.45, 0.85, 0.8, 0.75, 0.65, 0.85, 0.6, 0.7])
    els.append(body_par(doc, RESULTS_OPEN))
    answered = SURVEY_RESULTS["open_answered"]
    assert len(answered) == len(OPEN_THEMES)
    rows = [[q, a["with_content"], themes] for (q, a), themes in zip(answered.items(), OPEN_THEMES)]
    els += appendix_table(doc, "Table C.2: Answers to the open questions and their main themes",
                          ["Open question", "Answers", "Main themes (approximate number of respondents)"],
                          rows, [1.9, 0.8, 3.3])
    return els


def list_field(doc, heading, instr, entries):
    """A heading, then a TOC field pre-filled with the entries (without page numbers until Word updates it)."""
    els = [new_par(doc, heading, style="Front Heading")]
    if not entries:
        entries = [(1, "Right-click and choose Update Field")]
    for k, (level, text) in enumerate(entries):
        p = new_par(doc, style=f"toc {level}")
        if k == 0:
            field_start(p, instr)
        add_text(p, text)
        if k == len(entries) - 1:
            field_end(p)
        els.append(p)
    return els


def abbreviation_table(doc, text_w):
    """A two column table without borders, so the full forms line up in any viewer."""
    t = doc.add_table(rows=0, cols=2)
    widths = (Inches(1.4), Twips(text_w) - Inches(1.4))
    for short, full in ABBREVIATIONS:
        cells = t.add_row().cells
        for cell, text, w in zip(cells, (short, full), widths):
            cell.width = w
            par = cell.paragraphs[0]
            add_text(par, text)
            par.paragraph_format.space_after = Pt(4)
            par.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    tblPr = t._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        b = OxmlElement(f"w:{edge}")
        b.set(qn("w:val"), "nil")
        borders.append(b)
    later = [tblPr.find(qn(f"w:{tag}")) for tag in ("shd", "tblLayout", "tblCellMar", "tblLook")]
    later = [e for e in later if e is not None]
    if later:
        later[0].addprevious(borders)       # keep the order Word expects inside tblPr
    else:
        tblPr.append(borders)
    for old in tblPr.findall(qn("w:tblStyle")):
        tblPr.remove(old)
    doc.element.body.remove(t._tbl)
    return t


def build_front_matter(doc, figs, tabs, contents, text_w):
    C = WD_ALIGN_PARAGRAPH.CENTER
    logo = new_par(doc, align=C, after=12)
    logo.add_run().add_picture(str(LOGO), width=Inches(2.6))
    els = [
        logo,
        new_par(doc, "Technological University Dublin, Tallaght Campus", align=C, size=14),
        new_par(doc, TITLE, align=C, bold=True, size=18, before=36, after=36),
        new_par(doc, "Omolara Ibikunle", align=C, bold=True, size=14, after=36),
        new_par(doc, "A dissertation submitted in partial fulfilment of the requirements for the award of the "
                     "Master of Science in DevOps", align=C, after=36),
        new_par(doc, "Supervised by Mr. Kevin Bayliss", align=C, after=36),
        new_par(doc, "School of Enterprise Computing and Digital Transformation", align=C, after=0),
        new_par(doc, "Technological University Dublin", align=C, after=36),
        new_par(doc, "Blessington Road, Tallaght, Dublin 24, D24 FKT9", align=C),
        new_par(doc, "DECLARATION", style="Front Heading"),
        body_par(doc, DECLARATION),
        new_par(doc, "Signed: ", before=36),
        new_par(doc, "Omolara Ibikunle"),
        new_par(doc, "Date: "),
        new_par(doc, "ACKNOWLEDGEMENTS", style="Front Heading"),
        body_par(doc, ACKNOWLEDGEMENTS),
        new_par(doc, "ACRONYMS", style="Front Heading"),
        abbreviation_table(doc, text_w),
    ]
    els += list_field(doc, "LIST OF FIGURES", ' TOC \\h \\z \\t "Figure Caption,1" ', [(1, t) for t in figs])
    els += list_field(doc, "LIST OF TABLES", ' TOC \\h \\z \\t "Table Caption,1" ', [(1, t) for t in tabs])
    els += list_field(doc, "CONTENTS", ' TOC \\o "1-2" \\h \\z ', contents)
    els.append(new_par(doc, "ABSTRACT", style="Front Heading"))
    els += [body_par(doc, t) for t in ABSTRACT]
    els.append(new_par(doc, after=0))       # the front matter section break is attached to this paragraph
    first = doc.element.body[0]
    for p in els:
        first.addprevious(p._p if hasattr(p, '_p') else p._tbl)
    return els[-1]


def page_numbers(sectPr, fmt, title_page=False):
    for old in sectPr.findall(qn("w:pgNumType")):
        sectPr.remove(old)
    pg = OxmlElement("w:pgNumType")
    pg.set(qn("w:fmt"), fmt)
    pg.set(qn("w:start"), "1")
    cols = sectPr.find(qn("w:cols"))
    if cols is not None:
        cols.addprevious(pg)
    else:
        sectPr.find(qn("w:pgMar")).addnext(pg)


def setup_sections(doc, last_front_par):
    body_sect = doc.element.body[-1]
    front_sect = copy.deepcopy(body_sect)
    for ref in front_sect.findall(qn("w:footerReference")) + front_sect.findall(qn("w:headerReference")):
        front_sect.remove(ref)
    last_front_par._p.get_or_add_pPr().append(front_sect)
    page_numbers(front_sect, "lowerRoman")
    page_numbers(body_sect, "decimal")
    front, main = doc.sections[0], doc.sections[1]
    for s in (front, main):
        s.page_width, s.page_height = Twips(A4_W), Twips(A4_H)
    front.different_first_page_header_footer = True     # no number on the title page
    front.first_page_footer.is_linked_to_previous = False
    front.footer.is_linked_to_previous = False
    fp = front.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    field_start(fp, " PAGE ")
    fp.add_run("i")
    field_end(fp)
    # main.footer stays linked, so it shows the same PAGE field, numbered 1, 2, 3 from Chapter One


def update_fields_on_open(doc):
    settings = doc.settings.element
    if settings.find(qn("w:updateFields")) is not None:
        return
    u = OxmlElement("w:updateFields")
    u.set(qn("w:val"), "true")
    later = {"hdrShapeDefaults", "footnotePr", "endnotePr", "compat", "docVars", "rsids", "mathPr",
             "attachedSchema", "themeFontLang", "clrSchemeMapping", "doNotIncludeSubdocsInStats",
             "doNotAutoCompressPictures", "forceUpgrade", "captions", "readModeInkLockDown", "smartTagType",
             "schemaLibrary", "shapeDefaults", "doNotEmbedSmartTags", "decimalSymbol", "listSeparator"}
    for child in settings:
        if child.tag.split("}")[1] in later:
            child.addprevious(u)
            return
    settings.append(u)


def main():
    doc = Document(SRC)
    sect = doc.sections[0]
    text_w = A4_W - sect.left_margin.twips - sect.right_margin.twips
    setup_styles(doc, text_w)
    fit_to_page(doc, text_w)
    chapter_digits(doc)
    spell_out_chapter4(doc)
    figs, tabs = mark_captions(doc)
    highlight_placeholders(doc)
    ch1 = doc.paragraphs[0]
    assert ch1.text.startswith("CHAPTER 1"), ch1.text
    for p in doc.paragraphs:            # every chapter starts on a new page, as in the template
        if p.style.name == "Heading 1":
            p.paragraph_format.page_break_before = True
    ch1.paragraph_format.page_break_before = False      # the section break already starts a new page
    words = 0
    for p in doc.paragraphs:
        if p.text.strip() == "REFERENCES":
            break
        if not p.style.name.startswith("Heading") and not CAPTION.match(p.text):
            words += len(re.sub(r"\[\[.*?\]\]", "", p.text).split())
    build_appendices(doc)
    contents = [(1 if p.style.name == "Heading 1" else 2, p.text) for p in doc.paragraphs
                if p.style.name in ("Heading 1", "Heading 2")]
    last = build_front_matter(doc, figs, tabs, contents, text_w)
    setup_sections(doc, last)
    update_fields_on_open(doc)
    curl_document(doc)
    doc.save(OUT)
    print(f"saved {OUT.name}")
    print(f"  {len(figs)} figures, {len(tabs)} tables, {len(contents)} contents entries")
    print(f"  Chapters One to Six: about {words:,} words (paragraph text, not tables, captions or placeholders)")
    abstract_words = sum(len(re.sub(r"\[\[.*?\]\]", "", t).split()) for t in ABSTRACT)
    print(f"  abstract: {abstract_words} words")


if __name__ == "__main__":
    main()
