"""
CPU SchedLab - start here.

    python main.py          -> opens the window (GUI)
    python main.py --cli    -> prints every algorithm on the example in the terminal
    python main.py --cli --file samples/textbook_priority.csv --quantum 4
"""

import argparse

from schedlab import compare, core, metrics, storage
from schedlab.gantt import text_gantt
from schedlab.models import SchedulerOptions
from schedlab.workload import example_workload


def run_cli(args):
    processes = storage.load_workload(args.file) if args.file else example_workload()
    options = SchedulerOptions(quantum=args.quantum, preemptive=args.preemptive,
                               aging_interval=args.aging, switch_cost=args.switch)

    print("Processes:", ", ".join(f"{p.pid}(arr={p.arrival}, burst={p.burst}, pr={p.priority})"
                                  for p in processes))
    for name in core.ALGORITHMS:
        result = core.run(name, processes, options)
        rows, s = metrics.compute(result)
        print("\n" + "=" * 70 + f"\n{result.algorithm}\n" + "=" * 70)
        print(text_gantt(result.timeline))
        print(f"{'PID':<5}{'Arr':>5}{'Burst':>7}{'Done':>6}{'TAT':>6}{'WT':>6}{'RT':>6}")
        for r in rows:
            print(f"{r.pid:<5}{r.arrival:>5}{r.burst:>7}{r.completion:>6}"
                  f"{r.turnaround:>6}{r.waiting:>6}{r.response:>6}")
        print(f"avg WT = {s.avg_waiting:.2f}   avg TAT = {s.avg_turnaround:.2f}   "
              f"avg RT = {s.avg_response:.2f}   CPU = {s.cpu_utilization:.1f}%   "
              f"switches = {s.context_switches}")

    win = compare.best(compare.compare_all(processes, options))
    print(f"\nLowest average waiting time: {win.algorithm} ({win.avg_waiting:.2f})")


def main():
    parser = argparse.ArgumentParser(description="CPU SchedLab - CPU scheduling simulator")
    parser.add_argument("--cli", action="store_true", help="text mode instead of the window")
    parser.add_argument("--file", help="CSV workload to load (pid,arrival,burst,priority)")
    parser.add_argument("--quantum", type=int, default=2, help="Round Robin time quantum")
    parser.add_argument("--preemptive", action="store_true", help="preemptive Priority")
    parser.add_argument("--aging", type=int, default=0, help="Priority aging interval (0 = off)")
    parser.add_argument("--switch", type=int, default=0, help="context-switch cost")
    args = parser.parse_args()

    if args.cli:
        run_cli(args)
    else:
        from schedlab.gui import main as gui_main
        gui_main()


if __name__ == "__main__":
    main()
