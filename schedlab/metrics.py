"""
metrics.py - performance metrics (scheduling criteria).
Owner: Member 4 (Aroob Alamro).   Function F9   OS concept: SCHEDULING CRITERIA

From the timeline we read, for every process:
    completion time = when its LAST block ends
    first run       = when its FIRST block starts

and then apply the textbook formulas:
    Turnaround time = completion - arrival
    Waiting time    = turnaround - burst        (time spent in the ready queue)
    Response time   = first run  - arrival      (how long until it FIRST got the CPU)

For the whole run:
    CPU utilization = time the CPU did useful work / total time  x 100 %
    Throughput      = number of processes / total time            (processes per time unit)
"""

from dataclasses import dataclass

from .models import IDLE, SWITCH, ScheduleResult


@dataclass
class ProcessMetrics:
    pid: str
    arrival: int
    burst: int
    priority: int
    completion: int
    turnaround: int
    waiting: int
    response: int


@dataclass
class Summary:
    algorithm: str
    avg_waiting: float
    avg_turnaround: float
    avg_response: float
    cpu_utilization: float     # percent
    throughput: float          # processes per time unit
    total_time: int
    context_switches: int


def compute(result: ScheduleResult) -> tuple[list[ProcessMetrics], Summary]:
    """Calculate the metrics of one scheduling result."""
    rows = []
    for p in result.processes:
        blocks = [s for s in result.timeline if s.pid == p.pid]
        completion = blocks[-1].end
        first_run = blocks[0].start

        turnaround = completion - p.arrival
        waiting = turnaround - p.burst
        response = first_run - p.arrival
        rows.append(ProcessMetrics(p.pid, p.arrival, p.burst, p.priority,
                                   completion, turnaround, waiting, response))

    n = len(rows)
    total_time = result.end_time
    busy = sum(s.duration for s in result.timeline if s.pid not in (IDLE, SWITCH))

    summary = Summary(
        algorithm=result.algorithm,
        avg_waiting=sum(r.waiting for r in rows) / n,
        avg_turnaround=sum(r.turnaround for r in rows) / n,
        avg_response=sum(r.response for r in rows) / n,
        cpu_utilization=100 * busy / total_time if total_time else 0.0,
        throughput=n / total_time if total_time else 0.0,
        total_time=total_time,
        context_switches=result.context_switches,
    )
    return rows, summary
