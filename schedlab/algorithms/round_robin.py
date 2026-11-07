"""
round_robin.py - Round Robin.
Owner: Member 3 (Mohammad Al-Dalain).   Function F6   OS concept: TIME SHARING

Rule: the ready queue is a circle (FIFO). Each process runs for at most
`quantum` time units. If it is not finished, it goes to the BACK of the
queue and waits for its next turn.

Textbook example (quantum = 4): P1(0,24) P2(0,3) P3(0,3)
    | P1 | P2 | P3 | P1 | P1 | P1 | P1 | P1 |
    0    4    7    10   14   18   22   26   30      average waiting = 5.67

Small quantum  -> fast response but MANY context switches.
Large quantum  -> behaves like FCFS.
"""

from collections import deque

from ..dispatcher import Dispatcher
from ..models import SchedulerOptions


def schedule(processes, options=None):
    options = options or SchedulerOptions()
    quantum = options.quantum
    cpu = Dispatcher(options.switch_cost)

    arrivals = sorted(processes, key=lambda p: p.arrival)   # processes not yet in the queue
    remaining = {p.pid: p.burst for p in processes}
    queue = deque()                                        # the ready queue
    time = 0

    def admit_arrivals(up_to):
        """Move every process that has arrived by time `up_to` into the ready queue."""
        while arrivals and arrivals[0].arrival <= up_to:
            queue.append(arrivals.pop(0))

    admit_arrivals(time)
    while queue or arrivals:
        if not queue:                                      # queue empty -> idle until next arrival
            cpu.idle(time, arrivals[0].arrival)
            time = arrivals[0].arrival
            admit_arrivals(time)
            continue

        p = queue.popleft()                                # take the process at the FRONT
        time = cpu.dispatch(p.pid, time)
        admit_arrivals(time)                               # some may arrive during the switch

        run_for = min(quantum, remaining[p.pid])           # one quantum, or less if it finishes
        cpu.run(p.pid, time, time + run_for)
        time += run_for
        remaining[p.pid] -= run_for

        # New arrivals enter the queue BEFORE the process that was just preempted.
        admit_arrivals(time)
        if remaining[p.pid] > 0:
            queue.append(p)                                # not finished -> back of the queue

    return cpu.result(f"Round Robin (q={quantum})", processes, options)
