"""Step 09: draw the extra figures for Chapters Three and Four.

Every number comes from the saved results files in code/results. Nothing is typed in by hand,
except the rule values in the routing diagram (70, 95 and 1 percent), which are set in Chapter Three.

Outputs (in code/results):
    figure_routing_rules.png        Figure 3.2  how a ticket is routed in each condition
    figure_calibration.png          Figure 4.1  confidence against actual accuracy on the test tickets
    figure_accuracy_by_error.png    Figure 4.2  accuracy of the four conditions as reviewer error rises
    figure_security_errors.png      Figure 4.3  security-sensitive errors as reviewer error rises
    figure_threshold_tradeoff.png   Figure 4.4  review threshold against accuracy and unchecked admin errors
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon

RES = Path(__file__).resolve().parent / "results"
exp = json.load(open(RES / "experiment_results.json"))
ex = json.load(open(RES / "chapter4_extra_results.json"))

AI, SEL, SEC, FULL = "AI only", "Selective review", "Selective review + security rule", "Full review"
CONDS = [AI, SEL, SEC, FULL]
RATES = [0, 5, 10, 20]
DIAG = [(r, r) for r in RATES]

scale = 100 if max(r["overturn_pct"] for r in exp["results"]) <= 1 else 1
R = {(int(round(r["overturn_pct"] * scale)), int(round(r["miss_pct"] * scale)), r["condition"]): r
     for r in exp["results"]}


def v(o, m, c, key):
    return R[(o, m, c)][key]


# Colours: validated categorical slots 1-4 (fixed order, one per condition), a one-hue blue ramp
# for the ordered reviewer error settings, and dark ink for all text.
COND_COL = {AI: "#2a78d6", SEL: "#eb6834", SEC: "#1baf7a", FULL: "#eda100"}
COND_MK = {AI: "o", SEL: "s", SEC: "^", FULL: "D"}
RAMP = {(0, 0): "#86b6ef", (10, 10): "#2a78d6", (20, 20): "#104281"}
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
NAVY, GOLD, LIGHT = "#123C54", "#E8A33D", "#EAF3F6"

plt.rcParams.update({"font.family": "Arial", "font.size": 9.5, "text.color": INK,
                     "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.edgecolor": "#b9b8b2", "axes.linewidth": 0.8})


def tidy(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def save(fig, name):
    fig.savefig(RES / name, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------- Figure 3.2 routing rules
def routing():
    fig, ax = plt.subplots(figsize=(9, 4.9))
    ax.set_xlim(0, 104)
    ax.set_ylim(-5, 52)
    ax.axis("off")

    def box(x, y, w, h, text, fill=LIGHT, color=INK, bold=False, size=9.5):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=0.8",
                                    linewidth=1.6, edgecolor=NAVY, facecolor=fill))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size, color=color,
                fontweight="bold" if bold else "normal", linespacing=1.2)

    def diamond(cx, cy, w, h, text):
        ax.add_patch(Polygon([(cx - w / 2, cy), (cx, cy + h / 2), (cx + w / 2, cy), (cx, cy - h / 2)],
                             closed=True, linewidth=1.6, edgecolor=NAVY, facecolor="white"))
        ax.text(cx, cy, text, ha="center", va="center", fontsize=8.6, linespacing=1.15)

    def arrow(x1, y1, x2, y2, label=None, lx=0, ly=0):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color=NAVY, lw=1.6, mutation_scale=12))
        if label:
            ax.text((x1 + x2) / 2 + lx, (y1 + y2) / 2 + ly, label, fontsize=8.5, color=INK2,
                    fontweight="bold", ha="center", va="center")

    yc = 34
    box(0.5, yc - 6, 12, 12, "New ticket\n\nDistilBERT\ngives a\ncategory and\nconfidence", fill=NAVY,
        color="white", bold=True, size=8.4)
    diamond(24, yc, 19, 16, "Confidence\nbelow\n70 percent?")
    diamond(51, yc, 21, 16, "Placed in\nAdministrative\nrights, below\n95 percent?")
    diamond(77, yc, 20, 16, "Administrative\nrights given\n1 percent\nor more?")
    box(93, yc - 5, 10, 10, "Accepted\nwithout\nreview", fill=GOLD, color=NAVY, bold=True, size=8.8)
    box(14, 2, 74, 7.5, "Sent to the modelled reviewer", fill=GOLD, color=NAVY, bold=True)

    arrow(12.9, yc, 14.4, yc)
    arrow(33.5, yc, 40.4, yc, "No", lx=-2.4, ly=1.6)
    arrow(61.5, yc, 66.9, yc, "No", ly=1.6)
    arrow(87, yc, 92.7, yc, "No", lx=-1.6, ly=1.6)
    for cx in (24, 51, 77):
        arrow(cx, yc - 8, cx, 9.9, "Yes", lx=2.6)

    # dashed frame around the two security checks
    ax.add_patch(FancyBboxPatch((38, 22.5), 52, 25, boxstyle="round,pad=0.2,rounding_size=1",
                                linewidth=1.2, edgecolor=INK2, facecolor="none", linestyle=(0, (4, 3))))
    ax.text(64, 49.6, "Security rule: third condition only", ha="center", fontsize=8.8,
            color=INK2, style="italic")
    ax.text(52, -3, "AI only: every ticket is accepted without review.     Selective review: the first "
                    "check only.     Full review: every ticket is sent to the reviewer.",
            fontsize=8.4, color=INK, ha="center", va="center")
    save(fig, "figure_routing_rules.png")


# ---------------------------------------------------------------- Figure 4.1 calibration
def calibration():
    bins = ex["bins"]
    conf = [b["mean_conf"] for b in bins.values()]
    acc = [b["acc"] for b in bins.values()]
    share = [b["share_pct"] for b in bins.values()]
    labels = ["Below 50 percent", "50 to 60 percent", "60 to 70 percent", "70 to 80 percent",
              "80 to 90 percent", "90 percent and above"]

    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    ax.plot([35, 100], [35, 100], color=INK2, linewidth=1, linestyle=(0, (4, 3)))
    ax.text(36.5, 56, "Dashed line:\nconfidence equal\nto accuracy", fontsize=8.5, color=INK2, ha="left")
    ax.plot(conf, acc, color=COND_COL[AI], linewidth=2, marker="o", markersize=7,
            markeredgecolor="white", markeredgewidth=1.5, zorder=3)
    for c, a, s, lab in zip(conf, acc, share, labels):
        text = f"{lab}\n({s:.1f} percent of tickets)"
        if lab.startswith("90"):
            ax.annotate(text, (c, a), xytext=(62, 95), textcoords="data", fontsize=7.8, color=INK,
                        ha="left", va="center",
                        arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8, shrinkB=5))
        else:
            ax.annotate(text, (c, a), textcoords="offset points", xytext=(8, -14), fontsize=7.8,
                        color=INK, ha="left")
    gap = bins["0.8-0.9"]
    ax.annotate("", xy=(gap["mean_conf"], gap["acc"]), xytext=(gap["mean_conf"], gap["mean_conf"]),
                arrowprops=dict(arrowstyle="<->", color=INK2, lw=1))
    ax.text(gap["mean_conf"] - 1, (gap["acc"] + gap["mean_conf"]) / 2,
            f"gap of {gap['mean_conf'] - gap['acc']:.1f}\npoints", fontsize=8, color=INK2, ha="right", va="center",
            bbox=dict(facecolor="white", edgecolor="none", pad=1.5))
    ax.set_xlim(35, 100)
    ax.set_ylim(35, 100)
    ax.set_xlabel("Mean confidence of the band (percent)")
    ax.set_ylabel("Actual accuracy (percent)")
    tidy(ax)
    save(fig, "figure_calibration.png")


# ---------------------------------------------------------------- Figure 4.2 accuracy lines
def accuracy_lines():
    fig, ax = plt.subplots(figsize=(7, 4.2))
    x = range(4)
    for c in CONDS:
        ys = [v(*d, c, "accuracy_mean") for d in DIAG]
        ax.plot(x, ys, color=COND_COL[c], marker=COND_MK[c], markersize=8, linewidth=2,
                markeredgecolor="white", markeredgewidth=1.2, label=c)
        nudge = {SEL: 0.45, SEC: -0.45}.get(c, 0)
        ax.text(3.12, ys[-1] + nudge, c, fontsize=8.3, color=INK, va="center")
    ax.set_xticks(list(x))
    ax.set_xticklabels([f"{o}/{m}" for o, m in DIAG])
    ax.set_xlim(-0.2, 4.4)
    ax.spines["bottom"].set_bounds(0, 3)
    ax.set_xlabel("Reviewer error (overturn rate / miss rate, percent)")
    ax.set_ylabel("Resolution accuracy (percent)")
    ax.legend(frameon=False, fontsize=8.5, loc="lower left")
    tidy(ax)
    save(fig, "figure_accuracy_by_error.png")


# ---------------------------------------------------------------- Figure 4.3 security errors
def security_errors():
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.8))
    panels = [("sensitive_errors_mean", "(a) Administrative rights tickets\nleft with a wrong category"),
              ("wrong_sensitive_grants_mean", "(b) Tickets wrongly given the\nAdministrative rights category")]
    for ax, (key, title) in zip(axes, panels):
        for c in CONDS:
            ax.plot(range(4), [v(*d, c, key) for d in DIAG], color=COND_COL[c], marker=COND_MK[c],
                    markersize=7, linewidth=2, markeredgecolor="white", markeredgewidth=1.2, label=c)
        ax.set_xticks(range(4))
        ax.set_xticklabels([f"{o}/{m}" for o, m in DIAG])
        ax.set_title(title, fontsize=9.5, loc="left", color=INK)
        ax.set_xlabel("Reviewer error (overturn / miss, percent)")
        ax.set_ylim(bottom=0)
        tidy(ax)
    axes[0].set_ylabel("Tickets (mean of 100 runs)")
    h, lab = axes[0].get_legend_handles_labels()
    fig.legend(h, lab, loc="lower center", ncol=4, frameon=False, fontsize=8.5, bbox_to_anchor=(0.5, -0.06))
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    save(fig, "figure_security_errors.png")


# ---------------------------------------------------------------- Figure 4.4 threshold trade-off
def threshold_tradeoff():
    th = ex["thresholds"]
    xs = [t["reviewed_pct"] for t in th]
    sec_x = v(0, 0, SEC, "reviewed_pct_mean")
    ai = v(0, 0, AI, "accuracy_mean")
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 4))

    ax = axes[0]
    ax.axhline(ai, color=INK2, linewidth=1, linestyle=(0, (4, 3)))
    ax.text(26.5, ai - 0.32, "AI only", fontsize=8.3, color=INK2, ha="right", va="center")
    for (o, m), col in RAMP.items():
        ys = [t[f"acc_{o}_{m}"] for t in th]
        ax.plot(xs, ys, color=col, linewidth=2, marker="o", markersize=6, markeredgecolor="white",
                markeredgewidth=1, label=f"Reviewer error {o}/{m}")
        ax.plot([sec_x], [v(o, m, SEC, "accuracy_mean")], marker="*", markersize=13, color=col,
                markeredgecolor=INK, markeredgewidth=0.8, linestyle="none")
    for t in th:
        ax.annotate(f"{t['threshold_pct']}", (t["reviewed_pct"], t["acc_0_0"]), textcoords="offset points",
                    xytext=(0, 7), fontsize=7.8, color=INK2, ha="center")
    ax.set_title("(a) Resolution accuracy", fontsize=9.5, loc="left", color=INK)
    ax.set_ylabel("Resolution accuracy (percent)")
    ax.plot([], [], marker="*", markersize=11, color="white", markeredgecolor=INK, markeredgewidth=0.8,
            linestyle="none", label=f"Security rule ({sec_x:.1f} percent reviewed)")
    ax.legend(frameon=False, fontsize=8, loc="lower right", bbox_to_anchor=(1, 0.07))
    ax.set_ylim(ai - 0.6, 98.6)

    ax = axes[1]
    ax.plot(xs, [t["admin_left_wrong_unreviewed"] for t in th], color=COND_COL[SEL], linewidth=2,
            marker="s", markersize=6, markeredgecolor="white", markeredgewidth=1,
            label="Selective review, one threshold")
    sr = ex["security_rule"]
    left = sr["admin_wrong_ai"] - sr["admin_wrong_caught_security"]
    ax.plot([sec_x], [left], marker="*", markersize=13, color=COND_COL[SEC], markeredgecolor=INK,
            markeredgewidth=0.8, linestyle="none", label="Selective review + security rule")
    for t in th:
        ax.annotate(f"{t['threshold_pct']}", (t["reviewed_pct"], t["admin_left_wrong_unreviewed"]),
                    textcoords="offset points", xytext=(0, 7), fontsize=7.8, color=INK2, ha="center")
    ax.set_ylim(0, 62)
    ax.set_title("(b) Wrong Administrative rights tickets\nleft without a human check", fontsize=9.5,
                 loc="left", color=INK)
    ax.set_ylabel("Tickets")
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    for ax in axes:
        ax.set_xlabel("Share of tickets sent for review (percent)")
        ax.set_xlim(0, 27)
        tidy(ax)
    fig.tight_layout()
    save(fig, "figure_threshold_tradeoff.png")


if __name__ == "__main__":
    routing()
    calibration()
    accuracy_lines()
    security_errors()
    threshold_tradeoff()
    print("figures saved in", RES)
