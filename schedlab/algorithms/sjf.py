"""
sjf.py - Shortest Job First (non-preemptive).
Owner: Member 2 (Sami Al-Maaytah).   Function F4   OS concept: optimal (minimum) average waiting time

Rule: every time the CPU becomes free, look at the processes that have
ALREADY ARRIVED and pick the one with the SHORTEST burst.
Once it starts, it runs to the end (non-preemptive).

Example:  P1(0,5)  P2(1,3)  P3(2,1)
    At t=0 only P1 has arrived -> P1 runs 0..5
    At t=5 P2(3) and P3(1) are waiting -> P3 is shorter -> P3 runs 5..6, then P2 6..9
    | P1 ............ | P3 | P2 ...... |
    0                 5    6           9          average waiting = 2.67
"""

from ..dispatcher import Dispatcher
from ..models import SchedulerOptions


def schedule(processes, options=None):
    options = options or SchedulerOptions()
    cpu = Dispatcher(options.switch_cost)
    time = 0
    waiting = list(processes)          # processes that have not run yet

    while waiting:
        # 1) Which processes are in the ready queue right now?
        ready = [p for p in waiting if p.arrival <= time]

        # 2) Nobody ready -> CPU idle until the next arrival.
        if not ready:
            next_arrival = min(p.arrival for p in waiting)
            cpu.idle(time, next_arrival)
            time = next_arrival
            continue

        # 3) Pick the SHORTEST burst. If two are equal -> the one that arrived first.
        p = min(ready, key=lambda p: (p.burst, p.arrival))

        # 4) Run it completely (non-preemptive).
        time = cpu.dispatch(p.pid, time)
        cpu.run(p.pid, time, time + p.burst)
        time += p.burst
        waiting.remove(p)

    return cpu.result("SJF", processes, options)
