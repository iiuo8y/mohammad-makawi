"""
storage.py - save / load workloads and export results as CSV.
Owner: Member 5 (Sara Almajali).   Function F12   OS concept: FILE-SYSTEM OPERATIONS

CSV = a plain text table that Excel can open. A saved workload looks like:

    pid,arrival,burst,priority
    P1,0,5,2
    P2,1,3,1
"""

import csv

from .workload import parse_process

WORKLOAD_HEADER = ["pid", "arrival", "burst", "priority"]


def save_workload(path, processes) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(WORKLOAD_HEADER)
        for p in processes:
            writer.writerow([p.pid, p.arrival, p.burst, p.priority])


def load_workload(path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [c for c in WORKLOAD_HEADER[:3] if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"The file is missing the column(s): {', '.join(missing)}")
        processes = []
        for line_no, row in enumerate(reader, start=2):
            try:
                processes.append(parse_process(row["pid"], row["arrival"], row["burst"],
                                               row.get("priority") or "0"))
            except ValueError as e:
                raise ValueError(f"Line {line_no}: {e}") from None
    return processes


def export_results(path, result, rows, summary) -> None:
    """Write the Gantt timeline, the per-process table and the averages to one CSV file."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Algorithm", result.algorithm])
        w.writerow([])
        w.writerow(["Gantt chart"])
        w.writerow(["pid", "start", "end"])
        for s in result.timeline:
            w.writerow([s.pid, s.start, s.end])
        w.writerow([])
        w.writerow(["pid", "arrival", "burst", "priority", "completion",
                    "turnaround", "waiting", "response"])
        for r in rows:
            w.writerow([r.pid, r.arrival, r.burst, r.priority, r.completion,
                        r.turnaround, r.waiting, r.response])
        w.writerow([])
        w.writerow(["Average waiting", f"{summary.avg_waiting:.2f}"])
        w.writerow(["Average turnaround", f"{summary.avg_turnaround:.2f}"])
        w.writerow(["Average response", f"{summary.avg_response:.2f}"])
        w.writerow(["CPU utilization %", f"{summary.cpu_utilization:.2f}"])
        w.writerow(["Throughput", f"{summary.throughput:.3f}"])
        w.writerow(["Context switches", summary.context_switches])


def export_comparison(path, summaries) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["algorithm", "avg_waiting", "avg_turnaround", "avg_response",
                    "cpu_utilization_%", "throughput", "context_switches"])
        for s in summaries:
            w.writerow([s.algorithm, f"{s.avg_waiting:.2f}", f"{s.avg_turnaround:.2f}",
                        f"{s.avg_response:.2f}", f"{s.cpu_utilization:.2f}",
                        f"{s.throughput:.3f}", s.context_switches])
