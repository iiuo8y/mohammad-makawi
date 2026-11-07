"""
compare.py - run EVERY algorithm on the same workload and compare them.
Owner: Member 3 (Mohammad Al-Dalain).   Function F10   OS concept: ALGORITHM EVALUATION

This is "deterministic modeling" from the textbook: take one fixed workload,
compute the performance of each algorithm on it, and compare the numbers.
"""

from . import core, metrics
from .models import SchedulerOptions


def compare_all(processes, options: SchedulerOptions | None = None):
    """Return one metrics.Summary per algorithm, in the order of core.ALGORITHMS."""
    options = options or SchedulerOptions()
    summaries = []
    for name in core.ALGORITHMS:
        result = core.run(name, processes, options)
        _, summary = metrics.compute(result)
        summaries.append(summary)
    return summaries


def best(summaries, key="avg_waiting"):
    """The algorithm with the smallest value of `key` (e.g. lowest average waiting time)."""
    return min(summaries, key=lambda s: getattr(s, key))


def plot_comparison(summaries, figure):
    """Draw grouped bar charts (waiting / turnaround / response) on a Matplotlib figure."""
    figure.clear()
    names = [s.algorithm.replace(" (", "\n(") for s in summaries]
    charts = [
        ("Average waiting time", [s.avg_waiting for s in summaries]),
        ("Average turnaround time", [s.avg_turnaround for s in summaries]),
        ("Average response time", [s.avg_response for s in summaries]),
        ("Context switches", [s.context_switches for s in summaries]),
    ]
    colors = ["#2f6db5", "#13a19a", "#ef8a3c", "#7a5af8", "#d6455d"]
    for i, (title, values) in enumerate(charts, start=1):
        ax = figure.add_subplot(2, 2, i)
        bars = ax.bar(range(len(values)), values, color=colors[: len(values)])
        ax.set_title(title, fontsize=10, fontweight="bold")
        ax.set_xticks(range(len(values)))
        ax.set_xticklabels(names, fontsize=7)
        ax.spines[["top", "right"]].set_visible(False)
        winner = values.index(min(values))
        bars[winner].set_edgecolor("black")
        bars[winner].set_linewidth(2)
        for bar, v in zip(bars, values):
            ax.annotate(f"{v:.2f}" if isinstance(v, float) else str(v),
                        (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                        ha="center", va="bottom", fontsize=7)
    figure.suptitle("Algorithm comparison (lower is better, best one outlined)", fontsize=11)
    figure.tight_layout()
