"""
gantt.py - the SIMPLE Gantt chart (Phase 2 version, works without the GUI).
Owner: Member 5 (Sara Almajali).   Function F8   OS concept: CPU TIMELINE

text_gantt()  -> prints the chart with characters, e.g.
    |   P1   | P2 | P3 |
    0        5    8    9
plot_gantt()  -> the same chart as a Matplotlib picture.
The animated chart of the full GUI is in gui.py (GanttCanvas).
"""

from .models import IDLE, SWITCH

# One fixed colour per process index, also used by the GUI.
PALETTE = ["#2f6db5", "#13a19a", "#ef8a3c", "#7a5af8", "#d6455d",
           "#3aa655", "#c27c0e", "#1c8cc4", "#b3489b", "#6b7a8f"]
IDLE_COLOR = "#e5e9f0"
SWITCH_COLOR = "#9aa5b1"


def color_for(pid, pids):
    if pid == IDLE:
        return IDLE_COLOR
    if pid == SWITCH:
        return SWITCH_COLOR
    return PALETTE[pids.index(pid) % len(PALETTE)] if pid in pids else PALETTE[0]


def text_gantt(timeline, scale=2) -> str:
    """Return a two-line text Gantt chart. `scale` = characters per time unit."""
    bar, axis = "|", "0"
    for s in timeline:
        label = "--" if s.pid == IDLE else s.pid
        width = max(len(label) + 2, s.duration * scale)
        bar += label.center(width) + "|"
        axis += str(s.end).rjust(width + 1)
    return bar + "\n" + axis


def plot_gantt(result, ax=None):
    """Draw the timeline with Matplotlib (horizontal bars on one row)."""
    import matplotlib.pyplot as plt

    if ax is None:
        _, ax = plt.subplots(figsize=(10, 2))
    pids = [p.pid for p in result.processes]
    for s in result.timeline:
        ax.broken_barh([(s.start, s.duration)], (0, 1), facecolors=color_for(s.pid, pids),
                       edgecolor="white")
        ax.text(s.start + s.duration / 2, 0.5, "" if s.pid == IDLE else s.pid,
                ha="center", va="center", color="white", fontweight="bold")
    ax.set_xticks(sorted({0} | {s.end for s in result.timeline}))
    ax.set_yticks([])
    ax.set_title(result.algorithm)
    return ax
