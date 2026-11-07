"""
fcfs.py - First Come, First Served.
Owner: Member 1 (Mohammad Al-Makawi).   Function F3   OS concept: NON-preemptive scheduling

Rule: the process that ARRIVES first runs first, and it keeps the CPU
until it finishes. Nobody can interrupt it.

Example (from our proposal):  P1(0,5)  P2(1,3)  P3(2,1)
    | P1 | P1 | P1 | P1 | P1 | P2 | P2 | P2 | P3 |
    0                        5              8    9      average waiting = 3.33
"""

from ..dispatcher import Dispatcher
from ..models import SchedulerOptions


def schedule(processes, options=None):
    options = options or SchedulerOptions()
    cpu = Dispatcher(options.switch_cost)
    time = 0

    # 1) Put the processes in order of arrival (the ready queue is a FIFO queue).
    #    sorted() is stable: if two arrive together, the one entered first goes first.
    queue = sorted(processes, key=lambda p: p.arrival)

    for p in queue:
        # 2) If the CPU is free but this process has not arrived yet -> CPU is idle.
        if time < p.arrival:
            cpu.idle(time, p.arrival)
            time = p.arrival

        # 3) Give it the CPU and let it run its WHOLE burst (non-preemptive).
        time = cpu.dispatch(p.pid, time)
        cpu.run(p.pid, time, time + p.burst)
        time += p.burst

    return cpu.result("FCFS", processes, options)
