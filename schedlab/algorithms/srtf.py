"""
srtf.py - Shortest Remaining Time First (= preemptive SJF).
Owner: Member 2 (Sami Al-Maaytah).   Function F5   OS concept: PREEMPTION

Rule: at EVERY time unit, run the ready process with the smallest REMAINING time.
If a new process arrives that needs less time than what the running process
still needs, it interrupts (preempts) the running process.

Example:  P1(0,5)  P2(1,3)  P3(2,1)
    t=0 P1 runs (rem 5)
    t=1 P2 arrives, needs 3 < P1's remaining 4  -> P2 preempts P1
    t=2 P3 arrives, needs 1 < P2's remaining 2  -> P3 preempts P2
    t=3 P3 done; P2 (rem 2) < P1 (rem 4)        -> P2 runs until 5, then P1 until 9
    | P1 | P2 | P3 | P2 ... | P1 ............ |
    0    1    2    3        5                 9      average waiting = 1.67 (the best)
"""

from ..dispatcher import Dispatcher
from ..models import SchedulerOptions


def schedule(processes, options=None):
    options = options or SchedulerOptions()
    cpu = Dispatcher(options.switch_cost)
    remaining = {p.pid: p.burst for p in processes}   # CPU time each process still needs
    time = 0
    running = None                                     # pid on the CPU in the last time unit

    while any(r > 0 for r in remaining.values()):
        ready = [p for p in processes if p.arrival <= time and remaining[p.pid] > 0]

        if not ready:                                  # nothing to run -> idle until next arrival
            next_arrival = min(p.arrival for p in processes if remaining[p.pid] > 0)
            cpu.idle(time, next_arrival)
            time = next_arrival
            continue

        # Smallest remaining time wins. On a tie, keep the running process
        # (avoids a useless context switch), then the earlier arrival.
        p = min(ready, key=lambda p: (remaining[p.pid], p.pid != running, p.arrival))

        # Run it for ONE time unit only, then decide again (that is what makes it preemptive).
        time = cpu.dispatch(p.pid, time)
        cpu.run(p.pid, time, time + 1)
        time += 1
        remaining[p.pid] -= 1
        running = p.pid

    return cpu.result("SRTF", processes, options)
