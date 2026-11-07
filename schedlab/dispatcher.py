"""
dispatcher.py - the CPU "dispatcher": it builds the timeline and handles context switches.
Owner: Member 3 (Mohammad Al-Dalain) - Context switch.   Function F11

All five algorithms use this same class, so they all draw the timeline the same way
and they all pay the same context-switch cost.

What is a context switch?
    When the CPU stops running process A and starts running process B, the OS must
    SAVE A's state (registers, program counter ... in its PCB) and LOAD B's state.
    During that time no process does useful work. That lost time is the
    "dispatcher latency" = switch_cost.
"""

from .models import IDLE, SWITCH, ScheduleResult, Segment, SchedulerOptions


class Dispatcher:
    def __init__(self, switch_cost: int = 0):
        self.switch_cost = switch_cost
        self.timeline: list[Segment] = []
        self.switches = 0          # number of context switches that happened
        self._last_pid = None      # the last process that was on the CPU

    # ------------------------------------------------------------------ #
    def dispatch(self, pid: str, now: int) -> int:
        """Give the CPU to `pid` at time `now`.

        If a DIFFERENT process was on the CPU before, this is a context switch:
        we count it and (if switch_cost > 0) add a "CS" block to the timeline.
        Returns the time at which `pid` can really start running.
        """
        if self._last_pid is not None and pid != self._last_pid:
            self.switches += 1
            if self.switch_cost > 0:
                self._add(SWITCH, now, now + self.switch_cost)
                now += self.switch_cost
        self._last_pid = pid
        return now

    def run(self, pid: str, start: int, end: int) -> None:
        """Record that `pid` used the CPU from `start` to `end`."""
        self._add(pid, start, end)

    def idle(self, start: int, end: int) -> None:
        """Record that the CPU was idle (no process ready) from `start` to `end`."""
        if end > start:
            self._add(IDLE, start, end)

    def result(self, algorithm, processes, options=None) -> ScheduleResult:
        """Package everything into the common ScheduleResult."""
        return ScheduleResult(
            algorithm=algorithm,
            timeline=self.timeline,
            processes=list(processes),
            context_switches=self.switches,
            options=options or SchedulerOptions(),
        )

    # ------------------------------------------------------------------ #
    def _add(self, pid: str, start: int, end: int) -> None:
        # If the same process simply continues, make the last bar longer
        # instead of drawing many small bars (P1 0-1, P1 1-2 -> P1 0-2).
        last = self.timeline[-1] if self.timeline else None
        if last and last.pid == pid and last.end == start:
            last.end = end
        else:
            self.timeline.append(Segment(pid, start, end))
