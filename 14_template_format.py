"""Step 14: format "Chapters 1-6 - Introduction to Conclusion.docx" like the template theses.

Two changes, to match Fergal Connolly's thesis: every heading is black (Word's built-in heading
styles are blue), and every chapter and the References start on a new page. No text is touched.
Script 12 does the same for the full draft.

Run from the Project folder:  python3 code/14_template_format.py
Other files can be given as arguments:  python3 code/14_template_format.py "Chapter Six - Conclusion.docx"
"""
import sys
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = ROOT / "Chapters 1-6 - Introduction to Conclusion.docx"


def make_black(doc):
    """Set heading, title and caption styles (and the character styles linked to them) to black."""
    names = ["Heading %d" % i for i in range(1, 10)] + ["Title", "Subtitle", "Caption"]
    changed = 0
    for name in names + [n + " Char" for n in names]:
        try:
            s = doc.styles[name]
        except KeyError:
            continue
        for c in s.element.xpath("./w:rPr/w:color"):
            for a in ("themeColor", "themeShade", "themeTint"):
                c.attrib.pop(qn("w:" + a), None)
            c.set(qn("w:val"), "000000")
            changed += 1
    return changed


def chapters_on_new_page(doc):
    """Start every chapter heading (Heading 1) on a new page, except one at the very top of the file."""
    first = doc.paragraphs[0]._p
    heads = [p for p in doc.paragraphs if p.style.name == "Heading 1"]
    for p in heads:
        p.paragraph_format.page_break_before = p._p is not first
    return len(heads)


if __name__ == "__main__":
    paths = [ROOT / p for p in sys.argv[1:]] or [DEFAULT]
    for path in paths:
        doc = Document(path)
        n = make_black(doc)
        h = chapters_on_new_page(doc)
        doc.save(path)
        print(f"{path.name}: {n} style colours set to black; {h} chapter headings start a new page")
