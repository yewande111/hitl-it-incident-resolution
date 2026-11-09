"""Step 3. Draws the research design diagram (Figure 3.1 in Chapter Three). Output: results/research_design_diagram.png"""
from pathlib import Path
HERE = Path(__file__).resolve().parent
DATA_FILE = HERE.parent / "dataset" / "all_tickets_processed_improved_v3.csv"
RESULTS = HERE / "results"
RESULTS.mkdir(exist_ok=True)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

NAVY = '#123C54'
GOLD = '#E8A33D'
LIGHT = '#EAF3F6'
DARK = '#222222'

fig, ax = plt.subplots(figsize=(12, 4.9), dpi=300)
ax.set_xlim(0, 12)
ax.set_ylim(1.5, 6.2)
ax.axis('off')


def box(x, y, w, h, text, fill=LIGHT, edge=NAVY, color=DARK, size=10.5, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.08,rounding_size=0.08',
                                linewidth=1.8, edgecolor=edge, facecolor=fill))
    ax.text(x + w / 2, y + h / 2, text, ha='center', va='center', fontsize=size,
            color=color, fontweight='bold' if bold else 'normal', linespacing=1.15)


def arrow(x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle='-|>', mutation_scale=15,
                                 linewidth=1.8, color=NAVY, shrinkA=0, shrinkB=0))

ax.text(6, 5.85, 'Research Design Architecture', ha='center', va='center',
        fontsize=19, fontweight='bold', color=NAVY)

xs = [0.35, 2.9, 5.45, 8.2]
ws = [2.1, 2.1, 2.45, 1.7]
h = 0.85

# Row A
ax.text(0.35, 5.2, 'A. Simulation experiment', ha='left', va='center',
        fontsize=13, fontweight='bold', color=NAVY)
yA = 4.1
box(xs[0], yA, ws[0], h, 'IT ticket dataset\n47,837 tickets\n80% train, 20% test', fill=NAVY, color='white', bold=True)
box(xs[1], yA, ws[1], h, 'DistilBERT\npredicts category\nand confidence')
box(xs[2], yA, ws[2], h, 'Four conditions\nAI only | Selective review\nSelective + security rule\nFull review', size=9.5)
box(xs[3], yA, ws[3], h, 'Accuracy, safety\nand human effort', fill=GOLD, color=NAVY, bold=True)
for i in range(3):
    arrow(xs[i] + ws[i] + 0.04, yA + h / 2, xs[i + 1] - 0.04, yA + h / 2)
ax.text(0.35, 3.72, 'The model, its confidence calibration and the review rules are set using cross-validation on the training\ndata only. The test data is used once, for the four conditions.',
        ha='left', va='center', fontsize=9, style='italic', color=DARK)

# Row B
ax.text(0.35, 3.15, 'B. Survey of user trust and perception', ha='left', va='center',
        fontsize=13, fontweight='bold', color=NAVY)
yB = 1.95
box(xs[0], yB, ws[0], h, 'Participants\nIT professionals and\ntechnical users')
box(xs[1], yB, ws[1], h, 'Ethics approval,\nconsent, and\nMicrosoft Forms')
box(xs[2], yB, ws[2], h, 'Trust ratings and\nopen responses')
box(xs[3], yB, ws[3], h, 'User trust\nresults', fill=GOLD, color=NAVY, bold=True)
for i in range(3):
    arrow(xs[i] + ws[i] + 0.04, yB + h / 2, xs[i + 1] - 0.04, yB + h / 2)

# Combined findings box on the right, fed by both rows
box(10.4, 2.15, 1.45, 2.6, 'Combined\nfindings for\nChapter Four:\naccuracy,\nhuman effort,\nand user trust', fill=NAVY, color='white', size=10, bold=True)
arrow(xs[3] + ws[3] + 0.04, yA + h / 2, 10.36, yA + h / 2)
arrow(xs[3] + ws[3] + 0.04, yB + h / 2, 10.36, yB + h / 2)

plt.tight_layout()
plt.savefig(RESULTS / 'research_design_diagram.png', dpi=300, bbox_inches='tight', facecolor='white')
print('saved', RESULTS / 'research_design_diagram.png')
