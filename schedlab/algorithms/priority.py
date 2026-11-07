"""
priority.py - Priority scheduling (non-preemptive OR preemptive) with optional AGING.
Owner: Member 4 (Aroob Alamro).   Function F7   OS concept: STARVATION & AGING

Rule: the ready process with the HIGHEST priority runs first.
      In this project (like the textbook) a SMALLER number = HIGHER priority.

    non-preemptive : once a process starts, it runs to the end.
    preemptive     : if a more important process arrives, it interrupts the running one.

Problem - STARVATION: a low-priority process may wait forever if important
processes keep arriving.
Solution - AGING: every `aging_interval` time units that a process waits,
its priority number goes down by 1 (it becomes more important), until it reaches 0.
So the longer a process waits, the more important it becomes - it cannot wait forever.

Textbook example (non-preemptive, all arrive at 0):
    P1(10, pr 3) P2(1, pr 1) P3(2, pr 4) P4(1, pr 5) P5(5, pr 2)
    | P2 | P5 ...... | P1 ............ | P3 .. | P4 |
    0    1           6                 16      18   19     average waiting = 8.2
"""

from ..dispatcher import Dispatcher
from ..models import SchedulerOptions


def schedule(processes, options=None):
    options = options or SchedulerOptions()
    cpu = Dispatcher(options.switch_cost)

    remaining = {p.pid: p.burst for p in processes}
    current_priority = {p.pid: p.priority for p in processes}   # changes with aging
    waited = {p.pid: 0 for p in processes}                      # waiting since last aging step
    time = 0
    running = None   # process that ran in the previous time unit

    while any(r > 0 for r in remaining.values()):
        ready = [p for p in processes if p.arrival <= time and remaining[p.pid] > 0]

        if not ready:                                            # CPU idle until next arrival
            next_arrival = min(p.arrival for p in processes if remaining[p.pid] > 0)
            cpu.idle(time, next_arrival)
            time = next_arrival
            continue

        # --- 1) choose the process -------------------------------------------------
        running_unfinished = running is not None and remaining[running] > 0
        if running_unfinished and not options.preemptive:
            # Non-preemptive: the running process keeps the CPU until it finishes.
            p = next(q for q in ready if q.pid == running)
        else:
            # Best (smallest) priority number. Tie -> keep the running one, then FCFS.
            p = min(ready, key=lambda q: (current_priority[q.pid], q.pid != running, q.arrival))

        # --- 2) run it for one time unit --------------------------------------------
        start = cpu.dispatch(p.pid, time)
        cpu.run(p.pid, start, start + 1)
        elapsed = start + 1 - time          # 1 time unit (+ switch cost if a switch happened)
        time = start + 1
        remaining[p.pid] -= 1
        running = p.pid

        waited[p.pid] = 0                   # it is running, so it is not waiting

        # --- 3) aging: everybody else who waited becomes a little more important ---
        if options.aging_interval > 0:
            for q in ready:
                if q.pid == p.pid:
                    continue
                waited[q.pid] += elapsed
                while waited[q.pid] >= options.aging_interval:
                    waited[q.pid] -= options.aging_interval
                    current_priority[q.pid] = max(0, current_priority[q.pid] - 1)

    mode = "preemptive" if options.preemptive else "non-preemptive"
    name = f"Priority ({mode}{', aging' if options.aging_interval else ''})"
    return cpu.result(name, processes, options)
