"""
workload.py - creating and checking a set of processes ("workload").
Owner: Member 1 (Mohammad Al-Makawi).   Functions F1 (process input) and F2 (random workload)
OS concept: process creation.
"""

import random

from .models import Process


def parse_process(pid, arrival, burst, priority="0") -> Process:
    """Turn text typed by the user into a Process, with a clear message if it is wrong."""
    pid = str(pid).strip()
    values = {}
    for name, text in (("Arrival", arrival), ("Burst", burst), ("Priority", priority)):
        text = str(text).strip()
        if text == "":
            raise ValueError(f"{name} time is empty." if name != "Priority" else "Priority is empty.")
        try:
            values[name] = int(text)
        except ValueError:
            raise ValueError(f"{name} must be a whole number (you typed '{text}').") from None
    return Process(pid, values["Arrival"], values["Burst"], values["Priority"])


def validate_workload(processes) -> None:
    """Check the whole list before scheduling it."""
    if not processes:
        raise ValueError("Add at least one process first.")
    ids = [p.pid for p in processes]
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        raise ValueError(f"Process ids must be unique: {', '.join(sorted(duplicates))}")


def random_workload(count=5, max_arrival=10, max_burst=10, max_priority=5, seed=None):
    """Generate `count` random processes P1..Pn (F2). Use `seed` to get the same set again."""
    if not 1 <= count <= 50:
        raise ValueError("Number of processes must be between 1 and 50.")
    rng = random.Random(seed)
    procs = [
        Process(f"P{i}", rng.randint(0, max_arrival), rng.randint(1, max_burst),
                rng.randint(0, max_priority))
        for i in range(1, count + 1)
    ]
    return procs


def example_workload():
    """The 3-process example from our proposal (page 3)."""
    return [Process("P1", 0, 5, 2), Process("P2", 1, 3, 1), Process("P3", 2, 1, 3)]
