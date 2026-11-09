"""Step 10: put the figures from step 09 into the chapter documents.

Paragraphs are found by their text, so the script works on the separate chapter files and on the
combined file. It is meant to be run once on each file (it stops if a figure is already there).
"""
import copy
import sys
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.shared import Inches
from PIL import Image

RES = Path(__file__).resolve().parent / "results"
WIDTH = Inches(6.0)


def find(doc, prefix, start=0):
    for i, p in enumerate(doc.paragraphs[start:], start):
        if p.text.strip().startswith(prefix):
            return i, p
    raise KeyError(prefix)


def has_image(p):
    return "graphicData" in p._p.xml


def template(doc):
    """Return the image paragraph and caption paragraph of an existing figure, to copy their layout."""
    for i, p in enumerate(doc.paragraphs):
        if p.text.startswith("Figure ") and ":" in p.text[:12] and i > 0 and has_image(doc.paragraphs[i - 1]):
            return doc.paragraphs[i - 1], p
    raise RuntimeError("no figure to copy")


def append_text(p, text):
    p.runs[-1].text = p.runs[-1].text.rstrip() + " " + text


def set_text(p, text):
    for r in p.runs[1:]:
        r._r.getparent().remove(r._r)
    p.runs[0].text = text


def insert_figure(doc, after, png, caption):
    img_t, cap_t = template(doc)
    # image paragraph: same paragraph settings as the template, new picture run
    new_img = copy.deepcopy(img_t._p)
    for r in list(new_img):
        if r.tag.endswith("}r"):
            new_img.remove(r)
    after._p.addnext(new_img)
    from docx.text.paragraph import Paragraph
    pi = Paragraph(new_img, after._parent)
    pi.add_run().add_picture(str(png), width=WIDTH)
    new_cap = copy.deepcopy(cap_t._p)
    new_img.addnext(new_cap)
    set_text(Paragraph(new_cap, after._parent), caption)


def replace_image(doc, p, png):
    """Swap the picture inside paragraph p for png, keeping the width and fixing the height."""
    blip = p._p.xpath(".//a:blip")[0]
    rid = blip.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
    part = doc.part.related_parts[rid]
    data = png.read_bytes()
    part._blob = data
    w, h = Image.open(BytesIO(data)).size
    for ext in p._p.xpath(".//wp:extent") + p._p.xpath(".//a:ext"):
        cx = int(ext.get("cx"))
        ext.set("cy", str(int(cx * h / w)))


def chapter3(doc):
    if any(p.text.startswith("Figure 3.2:") for p in doc.paragraphs):
        print("  Figure 3.2 already present"); return
    _, p = find(doc, "For DistilBERT, the combination that met both targets")
    append_text(p, "Figure 3.2 shows how a ticket is routed in each of the four conditions once this rule "
                   "is in place.")
    insert_figure(doc, p, RES / "figure_routing_rules.png",
                  "Figure 3.2: How a ticket is routed in each condition (the security rule applies to the "
                  "third condition only)")


def chapter4(doc):
    if any(p.text.startswith("Figure 4.4:") for p in doc.paragraphs):
        print("  Chapter Four figures already present"); return
    start, _ = find(doc, "4.3 Confidence on the Test Tickets")
    # old Figure 4.1 becomes Figure 4.2, with the new colours
    i, p = find(doc, "Table 4.5 shows the resolution accuracy", start)
    for r in p.runs:
        r.text = r.text.replace("Figure 4.1", "Figure 4.2")
    i, cap = find(doc, "Figure 4.1: Resolution accuracy", start)
    for r in cap.runs:
        r.text = r.text.replace("Figure 4.1", "Figure 4.2")
    replace_image(doc, doc.paragraphs[i - 1], RES / "figure_accuracy_by_error.png")

    _, p = find(doc, "The expected calibration error, which is", start)
    append_text(p, "Figure 4.1 shows this. Points below the dashed line are bands where the model was more "
                   "confident than it was accurate.")
    insert_figure(doc, p, RES / "figure_calibration.png",
                  "Figure 4.1: Confidence compared with actual accuracy on the test portion, by confidence band")

    _, p = find(doc, "Table 4.8 shows the two security-sensitive measures", start)
    append_text(p, "Figure 4.3 shows both measures at the four settings where the two error rates are equal.")
    _, p = find(doc, "The security rule gave the fewest tickets wrongly placed", start)
    insert_figure(doc, p, RES / "figure_security_errors.png",
                  "Figure 4.3: Security-sensitive errors as reviewer error rises (overturn and miss rates equal, "
                  "mean of 100 runs)")

    _, p = find(doc, "The check also shows what the security rule adds", start)
    append_text(p, "Figure 4.4 shows this trade-off.")
    insert_figure(doc, p, RES / "figure_threshold_tradeoff.png",
                  "Figure 4.4: Share of tickets reviewed against (a) resolution accuracy and (b) wrong "
                  "Administrative rights tickets left without a human check, for general thresholds of 50 to "
                  "90 percent and for the security rule")


if __name__ == "__main__":
    for f in sys.argv[1:]:
        print(f)
        doc = Document(f)
        heads = [p.text for p in doc.paragraphs if p.style.name == "Heading 1"]
        if any("CHAPTER THREE" in h for h in heads):
            chapter3(doc)
        if any("CHAPTER FOUR" in h for h in heads):
            chapter4(doc)
        doc.save(f)
