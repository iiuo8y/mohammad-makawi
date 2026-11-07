"""
CPU SchedLab - Interactive CPU Scheduling Simulator & Visualizer
Kernel Crew · Operating Systems 2211431 · Mutah University · Dr. Wafa Altarawneh

How to run (Python 3.12):
    pip install matplotlib
    python CPU_SchedLab.py

The file is divided into 5 parts, one for every team member:
    PART 1  Mohammad Al-Makawi   Process (PCB), input, random workload, FCFS, scheduler core
    PART 2  Sami Al-Maaytah      SJF, SRTF
    PART 3  Mohammad Al-Dalain   Round Robin, context switch, comparison
    PART 4  Aroob Alamro         Priority + aging, performance metrics
    PART 5  Sara Almajali        Gantt chart, GUI, save / load / export
"""

import copy
import csv
import random
import tkinter as tk
from collections import deque
from dataclasses import dataclass
from tkinter import filedialog, messagebox, ttk

IDLE = "IDLE"   # name used in the timeline when the CPU has nothing to do
SWITCH = "CS"   # name used in the timeline while the OS does a context switch


# ============================================================================
#  PART 1 — Mohammad Al-Makawi (team leader)
#  Process (PCB) · process input · random workload · FCFS · scheduler core
# ============================================================================

@dataclass
class Process:
    """One process, like a small PCB. Smaller priority number = more important."""
    pid: str
    arrival: int
    burst: int
    priority: int = 0

    def __post_init__(self):
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


@dataclass
class Options:
    """What the user chose. Each algorithm reads only what it needs."""
    quantum: int = 2          # Round Robin time slice
    preemptive: bool = False  # Priority: can a more important process interrupt?
    aging: int = 0            # Priority: every N units of waiting -> priority + 1 (0 = off)
    switch_cost: int = 0      # time lost in every context switch


@dataclass
class Result:
    """What every algorithm returns: the timeline (= the Gantt chart)."""
    algorithm: str
    timeline: list
    processes: list
    switches: int = 0

    @property
    def end_time(self):
        return self.timeline[-1].end if self.timeline else 0


def make_process(pid, arrival, burst, priority="0"):
    """Turn the text typed by the user into a Process, with a clear error message."""
    numbers = []
    for name, text in (("Arrival", arrival), ("Burst", burst), ("Priority", priority)):
        text = str(text).strip()
        if not text.lstrip("-").isdigit():
            raise ValueError(f"{name} must be a whole number (you typed '{text}').")
        numbers.append(int(text))
    return Process(str(pid).strip(), *numbers)


def random_workload(count=6, max_arrival=10, max_burst=10, max_priority=5):
    """F2: generate `count` random processes P1..Pn for quick testing."""
    if not 1 <= count <= 50:
        raise ValueError("Number of processes must be between 1 and 50.")
    return [Process(f"P{i}", random.randint(0, max_arrival), random.randint(1, max_burst),
                    random.randint(0, max_priority)) for i in range(1, count + 1)]


def fcfs_schedule(processes, options):
    """F3 FCFS: the first to ARRIVE runs first, until it finishes (non-preemptive)."""
    cpu = Dispatcher(options.switch_cost)
    time = 0
    for p in sorted(processes, key=lambda p: p.arrival):   # ready queue = FIFO by arrival
        if time < p.arrival:                                # nobody here yet -> CPU idle
            cpu.idle(time, p.arrival)
            time = p.arrival
        time = cpu.dispatch(p.pid, time)                    # give it the CPU
        cpu.run(p.pid, time, time + p.burst)                # it runs its WHOLE burst
        time += p.burst
    return cpu.result("FCFS", processes)


# ============================================================================
#  PART 2 — Sami Al-Maaytah
#  SJF (non-preemptive) · SRTF (preemptive SJF)
# ============================================================================

def sjf_schedule(processes, options):
    """F4 SJF: when the CPU is free, run the ARRIVED process with the SHORTEST burst."""
    cpu = Dispatcher(options.switch_cost)
    time = 0
    not_started = list(processes)
    while not_started:
        ready = [p for p in not_started if p.arrival <= time]
        if not ready:                                       # nobody ready -> idle
            next_arrival = min(p.arrival for p in not_started)
            cpu.idle(time, next_arrival)
            time = next_arrival
            continue
        p = min(ready, key=lambda p: (p.burst, p.arrival))  # shortest burst wins
        time = cpu.dispatch(p.pid, time)
        cpu.run(p.pid, time, time + p.burst)                # runs to the end
        time += p.burst
        not_started.remove(p)
    return cpu.result("SJF", processes)


def srtf_schedule(processes, options):
    """F5 SRTF: every time unit, run the process with the smallest REMAINING time."""
    cpu = Dispatcher(options.switch_cost)
    remaining = {p.pid: p.burst for p in processes}
    time, running = 0, None
    while any(remaining.values()):
        ready = [p for p in processes if p.arrival <= time and remaining[p.pid] > 0]
        if not ready:
            next_arrival = min(p.arrival for p in processes if remaining[p.pid] > 0)
            cpu.idle(time, next_arrival)
            time = next_arrival
            continue
        # smallest remaining time; on a tie keep the running one (no useless switch)
        p = min(ready, key=lambda p: (remaining[p.pid], p.pid != running, p.arrival))
        time = cpu.dispatch(p.pid, time)
        cpu.run(p.pid, time, time + 1)                      # ONE unit, then decide again
        time += 1
        remaining[p.pid] -= 1
        running = p.pid
    return cpu.result("SRTF", processes)


# ============================================================================
#  PART 3 — Mohammad Al-Dalain
#  Round Robin · context switch (Dispatcher) · comparison of all algorithms
# ============================================================================

def round_robin_schedule(processes, options):
    """F6 Round Robin: each process runs at most `quantum`, then goes to the back."""
    cpu = Dispatcher(options.switch_cost)
    arrivals = sorted(processes, key=lambda p: p.arrival)
    remaining = {p.pid: p.burst for p in processes}
    queue = deque()                                         # the ready queue (FIFO)
    time = 0

    def admit(up_to):                                       # arrived processes join the queue
        while arrivals and arrivals[0].arrival <= up_to:
            queue.append(arrivals.pop(0))

    admit(time)
    while queue or arrivals:
        if not queue:                                       # queue empty -> idle
            cpu.idle(time, arrivals[0].arrival)
            time = arrivals[0].arrival
            admit(time)
            continue
        p = queue.popleft()                                 # take the FRONT process
        time = cpu.dispatch(p.pid, time)
        admit(time)
        run_for = min(options.quantum, remaining[p.pid])    # one quantum (or less)
        cpu.run(p.pid, time, time + run_for)
        time += run_for
        remaining[p.pid] -= run_for
        admit(time)                                         # new arrivals enter first
        if remaining[p.pid] > 0:
            queue.append(p)                                 # not finished -> back of queue
    return cpu.result(f"Round Robin (q={options.quantum})", processes)


class Dispatcher:
    """F11 Builds the timeline for EVERY algorithm and handles context switches."""

    def __init__(self, switch_cost=0):
        self.switch_cost = switch_cost
        self.timeline = []
        self.switches = 0
        self.last_pid = None

    def dispatch(self, pid, now):
        """Give the CPU to `pid`. A different process than before = context switch."""
        if self.last_pid is not None and pid != self.last_pid:
            self.switches += 1                              # save old PCB, load new PCB
            if self.switch_cost > 0:
                self.add(SWITCH, now, now + self.switch_cost)
                now += self.switch_cost                     # time lost (dispatcher latency)
        self.last_pid = pid
        return now                                          # when the process really starts

    def run(self, pid, start, end):
        self.add(pid, start, end)

    def idle(self, start, end):
        if end > start:
            self.add(IDLE, start, end)

    def add(self, pid, start, end):
        last = self.timeline[-1] if self.timeline else None
        if last and last.pid == pid and last.end == start:  # same process continues
            last.end = end                                  # -> make the bar longer
        else:
            self.timeline.append(Segment(pid, start, end))

    def result(self, name, processes):
        return Result(name, self.timeline, list(processes), self.switches)


def compare_all(processes, options):
    """F10 Run EVERY algorithm on the SAME processes and collect the averages."""
    summaries = []
    for name in ALGORITHMS:
        _, summary = compute_metrics(run(name, processes, options))
        summaries.append(summary)
    return summaries


def plot_comparison(summaries, figure):
    """Bar charts of the comparison (lower is better, the best bar is outlined)."""
    names = [s["algorithm"].replace(" (", "\n(") for s in summaries]
    charts = [("Average waiting time", "avg_waiting"), ("Average turnaround time", "avg_turnaround"),
              ("Average response time", "avg_response"), ("Context switches", "switches")]
    for i, (title, key) in enumerate(charts, start=1):
        values = [s[key] for s in summaries]
        ax = figure.add_subplot(2, 2, i)
        bars = ax.bar(range(len(values)), values, color=PALETTE[:len(values)])
        best = values.index(min(values))
        bars[best].set_edgecolor("black")
        bars[best].set_linewidth(2)
        ax.set_title(title, fontsize=10, fontweight="bold")
        ax.set_xticks(range(len(values)))
        ax.set_xticklabels(names, fontsize=7)
        ax.spines[["top", "right"]].set_visible(False)
        for bar, v in zip(bars, values):
            ax.annotate(f"{v:.2f}" if isinstance(v, float) else str(v),
                        (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                        ha="center", va="bottom", fontsize=7)
    figure.suptitle("Algorithm comparison (lower is better, best one outlined)", fontsize=11)
    figure.tight_layout()


# ============================================================================
#  PART 4 — Aroob Alamro
#  Priority scheduling (non-preemptive / preemptive + aging) · performance metrics
# ============================================================================

def priority_schedule(processes, options):
    """F7 Priority: smallest priority number runs first. Aging prevents starvation."""
    cpu = Dispatcher(options.switch_cost)
    remaining = {p.pid: p.burst for p in processes}
    current = {p.pid: p.priority for p in processes}       # priority after aging
    waited = {p.pid: 0 for p in processes}
    time, running = 0, None
    while any(remaining.values()):
        ready = [p for p in processes if p.arrival <= time and remaining[p.pid] > 0]
        if not ready:
            next_arrival = min(p.arrival for p in processes if remaining[p.pid] > 0)
            cpu.idle(time, next_arrival)
            time = next_arrival
            continue
        if running and remaining[running] > 0 and not options.preemptive:
            p = next(q for q in ready if q.pid == running)  # non-preemptive: keep it
        else:                                               # best priority wins
            p = min(ready, key=lambda q: (current[q.pid], q.pid != running, q.arrival))
        start = cpu.dispatch(p.pid, time)
        cpu.run(p.pid, start, start + 1)
        elapsed, time = start + 1 - time, start + 1
        remaining[p.pid] -= 1
        running = p.pid
        waited[p.pid] = 0
        if options.aging > 0:                               # AGING
            for q in ready:
                if q.pid != p.pid:
                    waited[q.pid] += elapsed
                    while waited[q.pid] >= options.aging:   # waited long enough ->
                        waited[q.pid] -= options.aging
                        current[q.pid] = max(0, current[q.pid] - 1)   # more important
    mode = "preemptive" if options.preemptive else "non-preemptive"
    return cpu.result(f"Priority ({mode}{', aging' if options.aging else ''})", processes)


def compute_metrics(result):
    """F9 Waiting, turnaround and response time per process + averages."""
    rows = []
    for p in result.processes:
        blocks = [s for s in result.timeline if s.pid == p.pid]
        completion = blocks[-1].end                         # end of its LAST block
        first_run = blocks[0].start                         # start of its FIRST block
        turnaround = completion - p.arrival
        waiting = turnaround - p.burst
        response = first_run - p.arrival
        rows.append(dict(pid=p.pid, arrival=p.arrival, burst=p.burst, priority=p.priority,
                         completion=completion, turnaround=turnaround,
                         waiting=waiting, response=response))
    n, total = len(rows), result.end_time
    busy = sum(s.end - s.start for s in result.timeline if s.pid not in (IDLE, SWITCH))
    summary = dict(
        algorithm=result.algorithm,
        avg_waiting=sum(r["waiting"] for r in rows) / n,
        avg_turnaround=sum(r["turnaround"] for r in rows) / n,
        avg_response=sum(r["response"] for r in rows) / n,
        cpu_utilization=100 * busy / total,                 # % of time doing useful work
        throughput=n / total,                               # processes per time unit
        switches=result.switches,
    )
    return rows, summary


# ============================================================================
#  PART 1 (continued) — Mohammad Al-Makawi: the SCHEDULER CORE
#  The GUI never calls an algorithm directly; it calls run().
# ============================================================================

ALGORITHMS = {
    "FCFS": fcfs_schedule,
    "SJF": sjf_schedule,
    "SRTF": srtf_schedule,
    "Round Robin": round_robin_schedule,
    "Priority": priority_schedule,
}


def run(algorithm, processes, options):
    """Check the input, pick the algorithm, run it on a COPY of the processes."""
    if not processes:
        raise ValueError("Add at least one process first.")
    ids = [p.pid for p in processes]
    if len(ids) != len(set(ids)):
        raise ValueError("Process ids must be unique.")
    if options.quantum <= 0 or options.aging < 0 or options.switch_cost < 0:
        raise ValueError("Quantum must be > 0; aging and switch cost cannot be negative.")
    return ALGORITHMS[algorithm](copy.deepcopy(processes), options)


# ============================================================================
#  PART 5 — Sara Almajali
#  Gantt chart (simple + animated) · full GUI · save / load / export (CSV)
# ============================================================================

PALETTE = ["#2f6db5", "#13a19a", "#ef8a3c", "#7a5af8", "#d6455d",
           "#3aa655", "#c27c0e", "#1c8cc4", "#b3489b", "#6b7a8f"]
IDLE_COLOR, SWITCH_COLOR = "#e5e9f0", "#9aa5b1"
NAVY, TEAL, BG = "#14284b", "#13a19a", "#f4f7fb"
SPEEDS = {"Slow": 7.0, "Normal": 3.5, "Fast": 1.5, "Instant": 0.0}


def text_gantt(timeline):
    """F8 (Phase 2) the SIMPLE Gantt chart as text:  | P1 | P2 |  then the times."""
    bar, axis = "|", "0"
    for s in timeline:
        width = max(len(s.pid) + 2, (s.end - s.start) * 2)
        bar += ("--" if s.pid == IDLE else s.pid).center(width) + "|"
        axis += str(s.end).rjust(width + 1)
    return bar + "\n" + axis


def color_for(pid, pids):
    if pid == IDLE:
        return IDLE_COLOR
    if pid == SWITCH:
        return SWITCH_COLOR
    return PALETTE[pids.index(pid) % len(PALETTE)]


class GanttCanvas(tk.Canvas):
    """F8 (Phase 3) the ANIMATED Gantt chart."""

    def __init__(self, master):
        super().__init__(master, height=170, bg="white", highlightthickness=0)
        self.result, self.now, self.job = None, 0.0, None
        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<Button-1>", lambda e: self.play(self.result, 0) if self.result else None)

    def play(self, result, seconds):
        """Draw the chart little by little: 40 frames per second, `seconds` long."""
        if self.job:
            self.after_cancel(self.job)
        self.result, end = result, result.end_time
        self.now = 0.0 if seconds > 0 else end
        step = end / max(1, seconds * 40)

        def tick():
            self.now = min(end, self.now + step)
            self.redraw()
            if self.now < end:
                self.job = self.after(25, tick)              # next frame (window stays free)
        tick()

    def redraw(self):
        self.delete("all")
        w = self.winfo_width()
        if not self.result:
            self.create_text(w / 2, 85, fill="#8a96a8", font=("Segoe UI", 11),
                             text="Add processes, choose an algorithm and press  Run  ▶")
            return
        r, pad, y0, y1 = self.result, 30, 46, 100
        scale = (w - 2 * pad) / (r.end_time or 1)
        x = lambda t: pad + t * scale
        pids = [p.pid for p in r.processes]
        self.create_text(pad, 18, anchor="w", text=r.algorithm, fill=NAVY,
                         font=("Segoe UI", 12, "bold"))
        self.create_rectangle(x(0), y0, x(r.end_time), y1, fill="#f0f3f8", outline="")
        on_cpu, last_label = "-", -100
        for s in r.timeline:
            if s.start >= self.now:                          # not reached yet
                break
            end = min(s.end, self.now)                       # only the part before "now"
            self.create_rectangle(x(s.start), y0, x(end), y1, fill=color_for(s.pid, pids),
                                  outline="white", width=2,
                                  stipple="gray50" if s.pid == SWITCH else "")
            if s.pid != IDLE and (end - s.start) * scale > 22:
                self.create_text((x(s.start) + x(end)) / 2, (y0 + y1) / 2, text=s.pid,
                                 fill="white" if s.pid != SWITCH else NAVY,
                                 font=("Segoe UI", 10, "bold"))
            for t in ((s.start, end) if end == s.end else (s.start,)):
                if x(t) - last_label >= 20 or t == 0:
                    self.create_text(x(t), y1 + 15, text=str(t), fill="#4a5568",
                                     font=("Segoe UI", 9))
                    last_label = x(t)
            if s.start <= self.now < s.end:
                on_cpu = {IDLE: "idle", SWITCH: "context switch"}.get(s.pid, s.pid)
        if self.now < r.end_time:                            # the red "now" line
            self.create_line(x(self.now), y0 - 8, x(self.now), y1 + 8, fill="#d6455d", width=2)
            status = f"t = {self.now:.1f}    CPU → {on_cpu}"
        else:
            status = f"Finished at t = {r.end_time}    ·    context switches: {r.switches}"
        self.create_text(w - pad, 18, anchor="e", text=status, fill="#4a5568",
                         font=("Segoe UI", 10))
        lx = pad                                             # legend
        for name, col in [(p, color_for(p, pids)) for p in pids[:10]] + \
                         [("Idle", IDLE_COLOR), ("Switch", SWITCH_COLOR)]:
            self.create_rectangle(lx, 142, lx + 12, 154, fill=col, outline="")
            self.create_text(lx + 16, 148, anchor="w", text=name, fill="#4a5568",
                             font=("Segoe UI", 8))
            lx += 22 + 7 * len(name)


def save_workload(path, processes):
    """F12 Save the processes in a CSV file (opens in Excel)."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["pid", "arrival", "burst", "priority"])
        for p in processes:
            writer.writerow([p.pid, p.arrival, p.burst, p.priority])


def load_workload(path):
    """F12 Read processes back from a CSV file."""
    with open(path, newline="", encoding="utf-8") as f:
        return [make_process(r["pid"], r["arrival"], r["burst"], r.get("priority") or "0")
                for r in csv.DictReader(f)]


def export_results(path, result, rows, summary):
    """F12 Export the Gantt timeline, the results table and the averages as CSV."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Algorithm", result.algorithm])
        w.writerow(["pid", "start", "end"])
        w.writerows([s.pid, s.start, s.end] for s in result.timeline)
        w.writerow(list(rows[0].keys()))
        w.writerows(list(r.values()) for r in rows)
        w.writerows([k, round(v, 3) if isinstance(v, float) else v] for k, v in summary.items())


EXAMPLES = {   # ready workloads: (pid, arrival, burst, priority)
    "Proposal example": [("P1", 0, 5, 2), ("P2", 1, 3, 1), ("P3", 2, 1, 3)],
    "Textbook Round Robin": [("P1", 0, 24, 0), ("P2", 0, 3, 0), ("P3", 0, 3, 0)],
    "Textbook Priority": [("P1", 0, 10, 3), ("P2", 0, 1, 1), ("P3", 0, 2, 4),
                          ("P4", 0, 1, 5), ("P5", 0, 5, 2)],
    "Starvation (try aging)": [("P1", 0, 4, 1), ("P2", 1, 4, 1), ("P3", 2, 3, 5),
                               ("P4", 4, 4, 1), ("P5", 8, 4, 1), ("P6", 12, 4, 1)],
}


class SchedLabApp(tk.Tk):
    """The main window: 1 Processes · 2 Options · 3 Gantt chart · 4 Results."""

    def __init__(self):
        super().__init__()
        self.title("CPU SchedLab — Kernel Crew")
        self.geometry("1280x760")
        self.minsize(1100, 700)
        self.configure(bg=BG)
        self.processes, self.last = [], None
        self.build_style()
        self.build_menu()
        head = tk.Frame(self, bg=NAVY)
        head.pack(fill="x", pady=(0, 12))
        tk.Label(head, text="CPU SchedLab", bg=NAVY, fg="white",
                 font=("Segoe UI", 18, "bold")).pack(side="left", padx=16, pady=10)
        tk.Label(head, text="see how the operating system decides which process runs next",
                 bg=NAVY, fg="#7fe0d6", font=("Segoe UI", 11)).pack(side="left")
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        left, right = tk.Frame(body, bg=BG), tk.Frame(body, bg=BG)
        left.pack(side="left", fill="y")
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))
        self.build_processes(left)
        self.build_options(left)
        self.build_results(right)
        self.show_example("Proposal example")

    # ---------- building the window ----------
    def build_style(self):
        s = ttk.Style(self)
        if "clam" in s.theme_names():
            s.theme_use("clam")
        s.configure("TLabelframe", background=BG)
        s.configure("TLabelframe.Label", background=BG, foreground=NAVY,
                    font=("Segoe UI", 11, "bold"))
        s.configure("TLabel", background=BG)
        s.configure("TCheckbutton", background=BG)
        s.configure("Treeview", rowheight=24, font=("Segoe UI", 10))
        s.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        for name, color, active in (("Accent", TEAL, "#0e837d"), ("Navy", NAVY, "#22406f")):
            s.configure(f"{name}.TButton", background=color, foreground="white",
                        font=("Segoe UI", 11, "bold"), padding=6)
            s.map(f"{name}.TButton", background=[("active", active)])

    def build_menu(self):
        bar = tk.Menu(self)
        f = tk.Menu(bar, tearoff=False)
        f.add_command(label="Load workload…", command=self.on_load)
        f.add_command(label="Save workload…", command=self.on_save)
        f.add_command(label="Export results (CSV)…", command=self.on_export)
        f.add_separator()
        f.add_command(label="Exit", command=self.destroy)
        bar.add_cascade(label="File", menu=f)
        e = tk.Menu(bar, tearoff=False)
        for name in EXAMPLES:
            e.add_command(label=name, command=lambda n=name: self.show_example(n))
        bar.add_cascade(label="Examples", menu=e)
        self.config(menu=bar)

    def build_processes(self, parent):
        box = ttk.LabelFrame(parent, text="1 · Processes", padding=10)
        box.pack(fill="both", expand=True)
        self.ptable = self.make_table(box, ("PID", "Arrival", "Burst", "Priority"), 85, 7)
        self.ptable.bind("<<TreeviewSelect>>", self.on_select)
        form = tk.Frame(box, bg=BG)
        form.pack(fill="x", pady=(8, 0))
        self.entries = {}
        for i, name in enumerate(("PID", "Arrival", "Burst", "Priority")):
            ttk.Label(form, text=name).grid(row=0, column=i, sticky="w")
            self.entries[name] = ttk.Entry(form, width=9)
            self.entries[name].grid(row=1, column=i, padx=(0, 6))
        self.entries["Priority"].insert(0, "0")
        row = tk.Frame(box, bg=BG)
        row.pack(fill="x", pady=(8, 0))
        for text, cmd in (("Add", self.on_add), ("Update", self.on_update),
                          ("Delete", self.on_delete), ("Clear all", lambda: self.set_processes([]))):
            ttk.Button(row, text=text, command=cmd).pack(side="left", padx=(0, 6))
        row = tk.Frame(box, bg=BG)
        row.pack(fill="x", pady=(8, 0))
        ttk.Label(row, text="Random:").pack(side="left")
        self.random_count = tk.IntVar(value=6)
        ttk.Spinbox(row, from_=1, to=50, width=4, textvariable=self.random_count).pack(
            side="left", padx=4)
        ttk.Label(row, text="processes").pack(side="left")
        ttk.Button(row, text="Generate", command=self.on_random).pack(side="left", padx=6)

    def build_options(self, parent):
        box = ttk.LabelFrame(parent, text="2 · Algorithm & options", padding=10)
        box.pack(fill="x", pady=(12, 0))
        self.algorithm, self.speed = tk.StringVar(value="FCFS"), tk.StringVar(value="Normal")
        self.quantum, self.aging, self.switch_cost = tk.IntVar(value=2), tk.IntVar(), tk.IntVar()
        self.preemptive = tk.BooleanVar()
        algo = ttk.Combobox(box, textvariable=self.algorithm, values=list(ALGORITHMS),
                            state="readonly", width=16)
        algo.bind("<<ComboboxSelected>>", lambda e: self.refresh_options())
        self.w_quantum = ttk.Spinbox(box, from_=1, to=100, width=6, textvariable=self.quantum)
        self.w_preempt = ttk.Checkbutton(box, text="Preemptive", variable=self.preemptive)
        self.w_aging = ttk.Spinbox(box, from_=0, to=100, width=6, textvariable=self.aging)
        rows = [("Algorithm", algo), ("Time quantum", self.w_quantum), ("Mode", self.w_preempt),
                ("Aging every (0 = off)", self.w_aging),
                ("Context-switch cost", ttk.Spinbox(box, from_=0, to=20, width=6,
                                                    textvariable=self.switch_cost)),
                ("Animation", ttk.Combobox(box, textvariable=self.speed, values=list(SPEEDS),
                                           state="readonly", width=10))]
        for i, (label, widget) in enumerate(rows):
            ttk.Label(box, text=label).grid(row=i, column=0, sticky="w")
            widget.grid(row=i, column=1, sticky="w", pady=2)
        btns = tk.Frame(box, bg=BG)
        btns.grid(row=len(rows), column=0, columnspan=2, sticky="we", pady=(10, 0))
        ttk.Button(btns, text="Run  ▶", style="Accent.TButton", command=self.on_run).pack(
            side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(btns, text="Compare all", style="Navy.TButton",
                   command=self.on_compare).pack(side="left", fill="x", expand=True)
        self.refresh_options()

    def build_results(self, parent):
        box = ttk.LabelFrame(parent, text="3 · Gantt chart", padding=8)
        box.pack(fill="x")
        self.gantt = GanttCanvas(box)
        self.gantt.pack(fill="x", expand=True)
        box = ttk.LabelFrame(parent, text="4 · Results", padding=8)
        box.pack(fill="both", expand=True, pady=(12, 0))
        self.rtable = self.make_table(box, ("PID", "Arrival", "Burst", "Priority", "Completion",
                                            "Turnaround", "Waiting", "Response"), 90, 6)
        cards = tk.Frame(box, bg=BG)
        cards.pack(fill="x", pady=(8, 0))
        self.cards = {}
        for key, title in (("avg_waiting", "Avg waiting"), ("avg_turnaround", "Avg turnaround"),
                           ("avg_response", "Avg response"), ("cpu_utilization", "CPU utilization"),
                           ("throughput", "Throughput"), ("switches", "Context switches")):
            card = tk.Frame(cards, bg="white", highlightbackground="#dbe2ec", highlightthickness=1)
            card.pack(side="left", fill="x", expand=True, padx=(0, 6))
            tk.Label(card, text=title, bg="white", fg="#6b7a8f",
                     font=("Segoe UI", 9)).pack(anchor="w", padx=8, pady=(6, 0))
            self.cards[key] = tk.Label(card, text="–", bg="white", fg=NAVY,
                                       font=("Segoe UI", 15, "bold"))
            self.cards[key].pack(anchor="w", padx=8, pady=(0, 6))

    @staticmethod
    def make_table(parent, titles, width, height):
        table = ttk.Treeview(parent, columns=titles, show="headings", height=height)
        for t in titles:
            table.heading(t, text=t)
            table.column(t, width=width, anchor="center")
        table.pack(fill="both", expand=True)
        return table

    def refresh_options(self):
        """Enable only the options the chosen algorithm uses."""
        a = self.algorithm.get()
        self.w_quantum.state(["!disabled" if a == "Round Robin" else "disabled"])
        for w in (self.w_preempt, self.w_aging):
            w.state(["!disabled" if a == "Priority" else "disabled"])

    # ---------- process table (F1) ----------
    def set_processes(self, processes):
        self.processes = list(processes)
        self.ptable.delete(*self.ptable.get_children())
        for p in self.processes:
            self.ptable.insert("", "end", iid=p.pid, values=(p.pid, p.arrival, p.burst, p.priority))
        n = 1
        while f"P{n}" in {p.pid for p in self.processes}:
            n += 1
        self.entries["PID"].delete(0, "end")
        self.entries["PID"].insert(0, f"P{n}")

    def show_example(self, name):
        self.set_processes([Process(*row) for row in EXAMPLES[name]])

    def read_form(self):
        e = self.entries
        return make_process(e["PID"].get(), e["Arrival"].get(), e["Burst"].get(), e["Priority"].get())

    def on_select(self, _event):
        for sel in self.ptable.selection()[:1]:
            for name, v in zip(("PID", "Arrival", "Burst", "Priority"), self.ptable.item(sel, "values")):
                self.entries[name].delete(0, "end")
                self.entries[name].insert(0, v)

    def on_add(self):
        try:
            p = self.read_form()
            if any(q.pid == p.pid for q in self.processes):
                raise ValueError(f"{p.pid} already exists — use Update to change it.")
            if len(self.processes) >= 50:
                raise ValueError("The simulator supports up to 50 processes.")
        except ValueError as err:
            return messagebox.showerror("Invalid process", str(err))
        self.set_processes(self.processes + [p])

    def on_update(self):
        sel = self.ptable.selection()
        if not sel:
            return messagebox.showinfo("Update", "Select a process in the table first.")
        try:
            p = self.read_form()
            if p.pid != sel[0] and any(q.pid == p.pid for q in self.processes):
                raise ValueError(f"{p.pid} already exists.")
        except ValueError as err:
            return messagebox.showerror("Invalid process", str(err))
        self.set_processes([p if q.pid == sel[0] else q for q in self.processes])

    def on_delete(self):
        sel = set(self.ptable.selection())
        self.set_processes([p for p in self.processes if p.pid not in sel])

    def on_random(self):
        try:
            self.set_processes(random_workload(int(self.random_count.get())))
        except (ValueError, tk.TclError) as err:
            messagebox.showerror("Random workload", str(err))

    # ---------- run & compare ----------
    def read_options(self):
        try:
            return Options(int(self.quantum.get()), bool(self.preemptive.get()),
                           int(self.aging.get()), int(self.switch_cost.get()))
        except tk.TclError:
            raise ValueError("Options must be whole numbers.") from None

    def on_run(self):
        """The Run button: core -> metrics -> draw. The GUI calculates nothing itself."""
        try:
            result = run(self.algorithm.get(), self.processes, self.read_options())
        except ValueError as err:
            return messagebox.showerror("Cannot run", str(err))
        rows, summary = compute_metrics(result)
        self.last = (result, rows, summary)
        self.gantt.play(result, SPEEDS[self.speed.get()])
        print(result.algorithm, "\n" + text_gantt(result.timeline), "\n")   # simple Gantt
        self.rtable.delete(*self.rtable.get_children())
        for r in rows:
            self.rtable.insert("", "end", values=list(r.values()))
        for key, label in self.cards.items():
            v = summary[key]
            label.config(text=f"{v:.1f}%" if key == "cpu_utilization" else
                         f"{v:.3f}" if key == "throughput" else
                         f"{v:.2f}" if isinstance(v, float) else str(v))

    def on_compare(self):
        try:
            summaries = compare_all(self.processes, self.read_options())
        except ValueError as err:
            return messagebox.showerror("Cannot compare", str(err))
        CompareWindow(self, summaries)

    # ---------- files (F12) ----------
    def on_save(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path:
            save_workload(path, self.processes)

    def on_load(self):
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv"), ("All", "*.*")])
        if path:
            try:
                self.set_processes(load_workload(path))
            except (OSError, ValueError, KeyError) as err:
                messagebox.showerror("Cannot load file", str(err))

    def on_export(self):
        if not self.last:
            return messagebox.showinfo("Export", "Run an algorithm first.")
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path:
            export_results(path, *self.last)


class CompareWindow(tk.Toplevel):
    """F10 window: bar charts + table of all algorithms on the same processes."""

    def __init__(self, master, summaries):
        super().__init__(master)
        self.title("Compare all algorithms")
        self.geometry("1000x700")
        self.configure(bg=BG)
        try:
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            from matplotlib.figure import Figure
        except ImportError as err:
            messagebox.showerror("Matplotlib missing",
                                 f"Install it with:  pip install matplotlib\n\n{err}", parent=self)
            return self.destroy()
        best = min(summaries, key=lambda s: s["avg_waiting"])
        bottom = tk.Frame(self, bg=BG)
        bottom.pack(side="bottom", fill="x", padx=10, pady=8)
        tk.Label(bottom, bg=BG, fg=NAVY, font=("Segoe UI", 11, "bold"),
                 text=f"★ Lowest average waiting time: {best['algorithm']}").pack(side="left")
        cols = ("Algorithm", "Avg waiting", "Avg turnaround", "Avg response", "CPU %",
                "Throughput", "Switches")
        table = ttk.Treeview(self, columns=cols, show="headings", height=len(summaries))
        for c in cols:
            table.heading(c, text=c)
            table.column(c, width=230 if c == "Algorithm" else 120, anchor="center")
        for s in summaries:
            table.insert("", "end", values=(("★ " if s is best else "") + s["algorithm"],
                                            f"{s['avg_waiting']:.2f}", f"{s['avg_turnaround']:.2f}",
                                            f"{s['avg_response']:.2f}", f"{s['cpu_utilization']:.1f}",
                                            f"{s['throughput']:.3f}", s["switches"]))
        table.pack(side="bottom", fill="x", padx=10)
        fig = Figure(figsize=(9, 4.6), dpi=100)
        plot_comparison(summaries, fig)
        FigureCanvasTkAgg(fig, master=self).get_tk_widget().pack(fill="both", expand=True)


if __name__ == "__main__":
    SchedLabApp().mainloop()
