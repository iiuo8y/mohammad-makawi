"""
core.py - the scheduler core: connects the GUI to the algorithms.
Owner: Member 1 (Mohammad Al-Makawi) - Core engine & integration.

The GUI never calls an algorithm directly. It calls `run("SJF", processes, options)`
and the core:
    1) checks the input,
    2) finds the algorithm in the ALGORITHMS table,
    3) gives it a COPY of the processes (so no algorithm can damage the user's data),
    4) returns the ScheduleResult.

Adding a new algorithm = write a file with schedule(processes, options) + one line here.
"""

import copy

from .algorithms import fcfs, priority, round_robin, sjf, srtf
from .models import SchedulerOptions
from .workload import validate_workload

# name shown in the GUI  ->  the schedule() function in that algorithm's file
ALGORITHMS = {
    "FCFS": fcfs.schedule,
    "SJF": sjf.schedule,
    "SRTF": srtf.schedule,
    "Round Robin": round_robin.schedule,
    "Priority": priority.schedule,
}


def run(algorithm: str, processes, options: SchedulerOptions | None = None):
    validate_workload(processes)
    if algorithm not in ALGORITHMS:
        raise ValueError(f"Unknown algorithm '{algorithm}'. Choose one of: {', '.join(ALGORITHMS)}")
    schedule = ALGORITHMS[algorithm]
    return schedule(copy.deepcopy(processes), options or SchedulerOptions())
