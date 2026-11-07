"""The five scheduling algorithms. Every file offers the same function:

    schedule(processes, options) -> ScheduleResult
"""

from . import fcfs, priority, round_robin, sjf, srtf

__all__ = ["fcfs", "sjf", "srtf", "round_robin", "priority"]
