"""
models.py - the data the whole program shares.
Owner: Member 1 (Mohammad Al-Makawi) - Core engine.   Function F1 (Process & PCB)

Every other file imports from here, so these classes are the "common language"
of the project:

    Process          -> one process, like a small PCB (Process Control Block)
    Segment          -> one bar in the Gantt chart: "who used the CPU from start to end"
    SchedulerOptions -> the settings the user picks (quantum, preemptive, aging, switch cost)
    ScheduleResult   -> what every algorithm returns: the timeline + the processes

Time is measured in whole "time units" (ms in the textbook).
"""

from dataclasses import dataclass, field

# Special names used in the timeline instead of a process id.
IDLE = "IDLE"   # the CPU has nothing to do (no process has arrived yet)
SWITCH = "CS"   # the dispatcher is doing a context switch


@dataclass
class Process:
    """A process as the scheduler sees it - a simplified PCB.

    pid      : name of the process, e.g. "P1"
    arrival  : time the process enters the ready queue
    burst    : how much CPU time it needs
    priority : smaller number = MORE important (same rule as the textbook)
    """

    pid: str
    arrival: int
    burst: int
    priority: int = 0

    def __post_init__(self):
        # Reject wrong data as early as possible (non-functional "Reliable").
        if not str(self.pid).strip():
            raise ValueError("Process id cannot be empty.")
        if self.arrival < 0:
            raise ValueError(f"{self.pid}: arrival time cannot be negative.")
        if self.burst <= 0:
            raise ValueError(f"{self.pid}: burst time must be greater than 0.")
        if self.priority < 0:
            raise ValueError(f"{self.pid}: priority cannot be negative.")


@dataclass
class Segment:
    """One block of the Gantt chart: `pid` used the CPU from `start` to `end`."""

    pid: str
    start: int
    end: int

    @property
    def duration(self) -> int:
        return self.end - self.start


@dataclass
class SchedulerOptions:
    """Options chosen by the user. Each algorithm only reads what it needs."""

    quantum: int = 2          # Round Robin time slice
    preemptive: bool = False  # Priority: may a more important process interrupt?
    aging_interval: int = 0   # Priority: every N units of waiting -> priority improves by 1 (0 = off)
    switch_cost: int = 0      # time lost on every context switch (dispatcher latency)

    def __post_init__(self):
        if self.quantum <= 0:
            raise ValueError("Time quantum must be greater than 0.")
        if self.aging_interval < 0:
            raise ValueError("Aging interval cannot be negative.")
        if self.switch_cost < 0:
            raise ValueError("Context-switch cost cannot be negative.")


@dataclass
class ScheduleResult:
    """What every algorithm returns.

    timeline         : list of Segments in time order (this IS the Gantt chart)
    processes        : the processes that were scheduled
    context_switches : how many times the CPU changed from one process to another
    """

    algorithm: str
    timeline: list[Segment]
    processes: list[Process]
    context_switches: int = 0
    options: SchedulerOptions = field(default_factory=SchedulerOptions)

    @property
    def end_time(self) -> int:
        return self.timeline[-1].end if self.timeline else 0
