"""
Correctness tests: every algorithm is checked against examples solved by hand
(our proposal page 3 and the textbook, Silberschatz ch. 5/6).

Run with:   python -m unittest -v
"""

import os
import tempfile
import unittest

from schedlab import compare, core, metrics, storage
from schedlab.models import IDLE, SWITCH, Process, SchedulerOptions
from schedlab.workload import example_workload, parse_process, random_workload


def avg_wait(algorithm, processes, **options):
    result = core.run(algorithm, processes, SchedulerOptions(**options))
    return round(metrics.compute(result)[1].avg_waiting, 2)


def order(algorithm, processes, **options):
    """The Gantt chart as a list of (pid, start, end)."""
    result = core.run(algorithm, processes, SchedulerOptions(**options))
    return [(s.pid, s.start, s.end) for s in result.timeline]


TEXTBOOK_PRIORITY = [Process("P1", 0, 10, 3), Process("P2", 0, 1, 1), Process("P3", 0, 2, 4),
                     Process("P4", 0, 1, 5), Process("P5", 0, 5, 2)]
TEXTBOOK_RR = [Process("P1", 0, 24), Process("P2", 0, 3), Process("P3", 0, 3)]
TEXTBOOK_SRTF = [Process("P1", 0, 8), Process("P2", 1, 4), Process("P3", 2, 9), Process("P4", 3, 5)]


class ProposalExample(unittest.TestCase):
    """The exact numbers printed on page 3 of our proposal."""

    def test_fcfs(self):
        self.assertEqual(order("FCFS", example_workload()),
                         [("P1", 0, 5), ("P2", 5, 8), ("P3", 8, 9)])
        self.assertEqual(avg_wait("FCFS", example_workload()), 3.33)

    def test_sjf(self):
        self.assertEqual(order("SJF", example_workload()),
                         [("P1", 0, 5), ("P3", 5, 6), ("P2", 6, 9)])
        self.assertEqual(avg_wait("SJF", example_workload()), 2.67)

    def test_srtf(self):
        self.assertEqual(order("SRTF", example_workload()),
                         [("P1", 0, 1), ("P2", 1, 2), ("P3", 2, 3), ("P2", 3, 5), ("P1", 5, 9)])
        self.assertEqual(avg_wait("SRTF", example_workload()), 1.67)


class TextbookExamples(unittest.TestCase):
    def test_srtf_textbook(self):          # Silberschatz: average waiting = 6.5
        self.assertEqual(avg_wait("SRTF", TEXTBOOK_SRTF), 6.5)

    def test_round_robin_textbook(self):   # quantum 4: average waiting = 5.67
        self.assertEqual(order("Round Robin", TEXTBOOK_RR, quantum=4),
                         [("P1", 0, 4), ("P2", 4, 7), ("P3", 7, 10), ("P1", 10, 30)])
        self.assertEqual(avg_wait("Round Robin", TEXTBOOK_RR, quantum=4), 5.67)

    def test_priority_textbook(self):      # average waiting = 8.2
        self.assertEqual([s[0] for s in order("Priority", TEXTBOOK_PRIORITY)],
                         ["P2", "P5", "P1", "P3", "P4"])
        self.assertEqual(avg_wait("Priority", TEXTBOOK_PRIORITY), 8.2)

    def test_priority_preemptive(self):
        procs = [Process("P1", 0, 5, 3), Process("P2", 2, 2, 1)]
        self.assertEqual(order("Priority", procs, preemptive=True),
                         [("P1", 0, 2), ("P2", 2, 4), ("P1", 4, 7)])
        self.assertEqual(order("Priority", procs, preemptive=False),
                         [("P1", 0, 5), ("P2", 5, 7)])


class Behaviour(unittest.TestCase):
    def test_idle_gap(self):
        procs = [Process("P1", 0, 2), Process("P2", 5, 1)]
        for name in core.ALGORITHMS:
            self.assertIn((IDLE, 2, 5), order(name, procs), name)

    def test_aging_prevents_starvation(self):
        procs = storage.load_workload(os.path.join(os.path.dirname(__file__), "..",
                                                   "samples", "starvation.csv"))
        def p3_finish(**opt):
            rows, _ = metrics.compute(core.run("Priority", procs, SchedulerOptions(**opt)))
            return next(r.completion for r in rows if r.pid == "P3")
        self.assertEqual(p3_finish(), 23)                       # starves until the very end
        self.assertLess(p3_finish(aging_interval=2), 23)        # aging lets it run earlier

    def test_context_switch_cost(self):
        no_cost = core.run("Round Robin", TEXTBOOK_RR, SchedulerOptions(quantum=4))
        cost = core.run("Round Robin", TEXTBOOK_RR, SchedulerOptions(quantum=4, switch_cost=1))
        self.assertEqual(no_cost.context_switches, 3)
        self.assertEqual(cost.end_time, 30 + 3)                 # 3 switches x 1 unit
        self.assertEqual(sum(s.duration for s in cost.timeline if s.pid == SWITCH), 3)
        self.assertLess(metrics.compute(cost)[1].cpu_utilization, 100)

    def test_every_process_gets_exactly_its_burst(self):
        procs = random_workload(30, seed=7)
        for name in core.ALGORITHMS:
            for opt in (SchedulerOptions(), SchedulerOptions(quantum=3, preemptive=True,
                                                             aging_interval=2, switch_cost=1)):
                result = core.run(name, procs, opt)
                for p in procs:
                    used = sum(s.duration for s in result.timeline if s.pid == p.pid)
                    self.assertEqual(used, p.burst, f"{name} {p.pid}")
                    first = min(s.start for s in result.timeline if s.pid == p.pid)
                    self.assertGreaterEqual(first, p.arrival)
                # timeline has no gaps or overlaps
                for a, b in zip(result.timeline, result.timeline[1:]):
                    self.assertEqual(a.end, b.start)

    def test_user_data_not_changed(self):
        procs = example_workload()
        core.run("SRTF", procs)
        self.assertEqual(procs, example_workload())

    def test_compare(self):
        summaries = compare.compare_all(example_workload())
        self.assertEqual(len(summaries), 5)
        self.assertEqual(compare.best(summaries).algorithm, "SRTF")


class InputValidation(unittest.TestCase):
    def test_bad_values(self):
        for args in (("P1", "-1", "3"), ("P1", "0", "0"), ("P1", "", "3"), ("P1", "a", "3"),
                     ("", "0", "3")):
            with self.assertRaises(ValueError):
                parse_process(*args)

    def test_duplicates_and_empty(self):
        with self.assertRaises(ValueError):
            core.run("FCFS", [])
        with self.assertRaises(ValueError):
            core.run("FCFS", [Process("P1", 0, 1), Process("P1", 1, 1)])
        with self.assertRaises(ValueError):
            SchedulerOptions(quantum=0)


class Storage(unittest.TestCase):
    def test_save_load_export(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "w.csv")
            storage.save_workload(path, example_workload())
            self.assertEqual(storage.load_workload(path), example_workload())
            result = core.run("FCFS", example_workload())
            rows, summary = metrics.compute(result)
            out = os.path.join(d, "r.csv")
            storage.export_results(out, result, rows, summary)
            with open(out, encoding="utf-8") as f:
                self.assertIn("Average waiting,3.33", f.read())


if __name__ == "__main__":
    unittest.main()
