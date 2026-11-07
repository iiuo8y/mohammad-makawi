"""
gui.py - the full Tkinter window with the ANIMATED Gantt chart.
Owner: Member 5 (Sara Almajali).   Functions F8 (Gantt chart) and F12 (save / load / export menus)

Layout of the window:
    +-------------------------------------------------------------------+
    |  header                                                            |
    +----------------------+--------------------------------------------+
    | 1. Processes table   | 3. Gantt chart (animated)                  |
    |    add/edit/delete   |                                            |
    |    random / example  | 4. Results table + averages                |
    | 2. Algorithm options |                                            |
    |    Run / Compare     |                                            |
    +----------------------+--------------------------------------------+

The GUI does NOT calculate anything itself. It only:
    reads the input  ->  calls core.run()  ->  calls metrics.compute()  ->  draws the result.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import compare, core, metrics, storage
from .gantt import IDLE_COLOR, SWITCH_COLOR, color_for
from .models import IDLE, SWITCH, SchedulerOptions
from .workload import example_workload, parse_process, random_workload

NAVY = "#14284b"
TEAL = "#13a19a"
BG = "#f4f7fb"
SPEEDS = {"Slow": 7.0, "Normal": 3.5, "Fast": 1.5, "Instant": 0.0}   # seconds for the whole chart


# ====================================================================== #
#  The animated Gantt chart                                               #
# ====================================================================== #
class GanttCanvas(tk.Canvas):
    """A canvas that draws the timeline and can 'play' it like a video."""

    PAD_X, BAR_Y, BAR_H = 30, 46, 54

    def __init__(self, master):
        super().__init__(master, height=170, bg="white", highlightthickness=0)
        self.result = None
        self.now = 0.0          # how much of the timeline is visible (in time units)
        self._job = None
        self.bind("<Configure>", lambda e: self.redraw())

    def show(self, result, seconds):
        """Start drawing `result`. seconds = how long the animation lasts (0 = instant)."""
        self.stop()
        self.result = result
        end = result.end_time
        if seconds <= 0 or end == 0:
            self.now = end
            self.redraw()
            return
        self.now = 0.0
        frames = max(1, int(seconds * 40))      # 40 frames per second
        step = end / frames

        def tick():
            self.now = min(end, self.now + step)
            self.redraw()
            if self.now < end:
                self._job = self.after(25, tick)
        tick()

    def stop(self):
        if self._job:
            self.after_cancel(self._job)
            self._job = None

    def finish(self):
        """Skip the animation and show the full chart."""
        if self.result:
            self.stop()
            self.now = self.result.end_time
            self.redraw()

    def redraw(self):
        self.delete("all")
        w = self.winfo_width()
        if not self.result:
            self.create_text(w / 2, 85, fill="#8a96a8", font=("Segoe UI", 11),
                             text="Add processes, choose an algorithm and press  Run  ▶")
            return

        r = self.result
        end = r.end_time or 1
        scale = (w - 2 * self.PAD_X) / end
        x = lambda t: self.PAD_X + t * scale
        pids = [p.pid for p in r.processes]
        y0, y1 = self.BAR_Y, self.BAR_Y + self.BAR_H

        self.create_text(self.PAD_X, 18, anchor="w", text=r.algorithm,
                         font=("Segoe UI", 12, "bold"), fill=NAVY)

        # background track
        self.create_rectangle(x(0), y0, x(end), y1, fill="#f0f3f8", outline="")

        running = "-"
        last_label_x = -100
        for seg in r.timeline:
            if seg.start >= self.now:
                break
            visible_end = min(seg.end, self.now)
            fill = color_for(seg.pid, pids)
            pattern = "gray50" if seg.pid == SWITCH else ""
            self.create_rectangle(x(seg.start), y0, x(visible_end), y1, fill=fill,
                                  outline="white", width=2, stipple=pattern)
            width_px = (visible_end - seg.start) * scale
            if seg.pid != IDLE and width_px > 22:
                self.create_text((x(seg.start) + x(visible_end)) / 2, (y0 + y1) / 2,
                                 text=seg.pid, fill="white" if seg.pid != SWITCH else NAVY,
                                 font=("Segoe UI", 10, "bold"))
            # time labels under the chart (skip if they would overlap)
            for t in (seg.start, visible_end) if visible_end == seg.end else (seg.start,):
                if x(t) - last_label_x >= 20 or t == 0:
                    self.create_line(x(t), y1, x(t), y1 + 5, fill="#8a96a8")
                    self.create_text(x(t), y1 + 15, text=str(t), fill="#4a5568",
                                     font=("Segoe UI", 9))
                    last_label_x = x(t)
            if seg.start <= self.now < seg.end or (self.now == seg.end == r.end_time):
                running = "idle" if seg.pid == IDLE else ("context switch" if seg.pid == SWITCH
                                                          else seg.pid)

        # the moving "now" line while the animation plays
        if self.now < r.end_time:
            self.create_line(x(self.now), y0 - 8, x(self.now), y1 + 8, fill="#d6455d", width=2)
            status = f"t = {self.now:.1f}    CPU → {running}"
        else:
            status = f"Finished at t = {r.end_time}    ·    context switches: {r.context_switches}"
        self.create_text(w - self.PAD_X, 18, anchor="e", text=status,
                         font=("Segoe UI", 10), fill="#4a5568")

        # legend
        lx = self.PAD_X
        for name, col in [(p, color_for(p, pids)) for p in pids[:10]] + \
                         [("Idle", IDLE_COLOR), ("Switch", SWITCH_COLOR)]:
            self.create_rectangle(lx, 142, lx + 12, 154, fill=col, outline="")
            self.create_text(lx + 16, 148, anchor="w", text=name, font=("Segoe UI", 8),
                             fill="#4a5568")
            lx += 22 + 7 * len(name)


# ====================================================================== #
#  The main window                                                        #
# ====================================================================== #
class SchedLabApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CPU SchedLab — Kernel Crew")
        self.geometry("1280x760")
        self.minsize(1100, 700)
        self.configure(bg=BG)
        self.processes = []
        self.last = None            # (result, rows, summary) of the last run
        self._style()
        self._menu()
        self._header()
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        left = tk.Frame(body, bg=BG, width=420)
        left.pack(side="left", fill="y")
        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))
        self._process_panel(left)
        self._options_panel(left)
        self._gantt_panel(right)
        self._results_panel(right)
        self.load_processes(example_workload())

    # ---------------- look & feel ---------------- #
    def _style(self):
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
        s.configure("Accent.TButton", background=TEAL, foreground="white",
                    font=("Segoe UI", 11, "bold"), padding=6)
        s.map("Accent.TButton", background=[("active", "#0e837d")])
        s.configure("Navy.TButton", background=NAVY, foreground="white",
                    font=("Segoe UI", 11, "bold"), padding=6)
        s.map("Navy.TButton", background=[("active", "#22406f")])

    def _menu(self):
        bar = tk.Menu(self)
        f = tk.Menu(bar, tearoff=False)
        f.add_command(label="Load workload…", command=self.on_load)
        f.add_command(label="Save workload…", command=self.on_save)
        f.add_separator()
        f.add_command(label="Export results (CSV)…", command=self.on_export)
        f.add_separator()
        f.add_command(label="Exit", command=self.destroy)
        bar.add_cascade(label="File", menu=f)
        h = tk.Menu(bar, tearoff=False)
        h.add_command(label="Key terms", command=self.on_terms)
        h.add_command(label="About", command=lambda: messagebox.showinfo(
            "About", "CPU SchedLab 1.0\nKernel Crew · Operating Systems 2211431\n"
                     "Mutah University · Dr. Wafa Altarawneh"))
        bar.add_cascade(label="Help", menu=h)
        self.config(menu=bar)

    def _header(self):
        head = tk.Frame(self, bg=NAVY, height=58)
        head.pack(fill="x", pady=(0, 12))
        tk.Label(head, text="CPU SchedLab", bg=NAVY, fg="white",
                 font=("Segoe UI", 18, "bold")).pack(side="left", padx=16, pady=10)
        tk.Label(head, text="see how the operating system decides which process runs next",
                 bg=NAVY, fg="#7fe0d6", font=("Segoe UI", 11)).pack(side="left")

    # ---------------- 1. processes ---------------- #
    def _process_panel(self, parent):
        box = ttk.LabelFrame(parent, text="1 · Processes", padding=10)
        box.pack(fill="both", expand=True)

        cols = ("pid", "arrival", "burst", "priority")
        self.ptable = ttk.Treeview(box, columns=cols, show="headings", height=7)
        for c, title in zip(cols, ("PID", "Arrival", "Burst", "Priority")):
            self.ptable.heading(c, text=title)
            self.ptable.column(c, width=85, anchor="center")
        self.ptable.pack(fill="both", expand=True)
        self.ptable.bind("<<TreeviewSelect>>", self.on_select_process)

        form = tk.Frame(box, bg=BG)
        form.pack(fill="x", pady=(8, 0))
        self.entries = {}
        for i, name in enumerate(("PID", "Arrival", "Burst", "Priority")):
            ttk.Label(form, text=name).grid(row=0, column=i, sticky="w")
            e = ttk.Entry(form, width=9)
            e.grid(row=1, column=i, padx=(0, 6))
            self.entries[name] = e
        self.entries["Priority"].insert(0, "0")

        btns = tk.Frame(box, bg=BG)
        btns.pack(fill="x", pady=(8, 0))
        for text, cmd in (("Add", self.on_add), ("Update", self.on_update),
                          ("Delete", self.on_delete), ("Clear all", self.on_clear)):
            ttk.Button(btns, text=text, command=cmd).pack(side="left", padx=(0, 6))

        gen = tk.Frame(box, bg=BG)
        gen.pack(fill="x", pady=(8, 0))
        ttk.Label(gen, text="Random:").pack(side="left")
        self.random_count = tk.IntVar(value=6)
        ttk.Spinbox(gen, from_=1, to=50, width=4, textvariable=self.random_count).pack(
            side="left", padx=4)
        ttk.Label(gen, text="processes").pack(side="left")
        ttk.Button(gen, text="Generate", command=self.on_random).pack(side="left", padx=6)
        ttk.Button(gen, text="Example", command=lambda: self.load_processes(
            example_workload())).pack(side="left")

    # ---------------- 2. options ---------------- #
    def _options_panel(self, parent):
        box = ttk.LabelFrame(parent, text="2 · Algorithm & options", padding=10)
        box.pack(fill="x", pady=(12, 0))

        self.algorithm = tk.StringVar(value="FCFS")
        self.quantum = tk.IntVar(value=2)
        self.preemptive = tk.BooleanVar(value=False)
        self.aging = tk.IntVar(value=0)
        self.switch_cost = tk.IntVar(value=0)
        self.speed = tk.StringVar(value="Normal")

        ttk.Label(box, text="Algorithm").grid(row=0, column=0, sticky="w")
        algo = ttk.Combobox(box, textvariable=self.algorithm, values=list(core.ALGORITHMS),
                            state="readonly", width=16)
        algo.grid(row=0, column=1, sticky="w", pady=2)
        algo.bind("<<ComboboxSelected>>", lambda e: self._refresh_options())

        self.w_quantum = ttk.Spinbox(box, from_=1, to=100, width=6, textvariable=self.quantum)
        self.w_preempt = ttk.Checkbutton(box, text="Preemptive", variable=self.preemptive)
        self.w_aging = ttk.Spinbox(box, from_=0, to=100, width=6, textvariable=self.aging)
        rows = [("Time quantum", self.w_quantum), ("Mode", self.w_preempt),
                ("Aging every (0 = off)", self.w_aging)]
        for i, (label, widget) in enumerate(rows, start=1):
            ttk.Label(box, text=label).grid(row=i, column=0, sticky="w")
            widget.grid(row=i, column=1, sticky="w", pady=2)

        ttk.Label(box, text="Context-switch cost").grid(row=4, column=0, sticky="w")
        ttk.Spinbox(box, from_=0, to=20, width=6, textvariable=self.switch_cost).grid(
            row=4, column=1, sticky="w", pady=2)
        ttk.Label(box, text="Animation").grid(row=5, column=0, sticky="w")
        ttk.Combobox(box, textvariable=self.speed, values=list(SPEEDS), state="readonly",
                     width=10).grid(row=5, column=1, sticky="w", pady=2)

        run = tk.Frame(box, bg=BG)
        run.grid(row=6, column=0, columnspan=2, sticky="we", pady=(10, 0))
        ttk.Button(run, text="Run  ▶", style="Accent.TButton", command=self.on_run).pack(
            side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(run, text="Compare all  📊", style="Navy.TButton",
                   command=self.on_compare).pack(side="left", fill="x", expand=True)
        self._refresh_options()

    def _refresh_options(self):
        """Enable only the options that the chosen algorithm uses."""
        a = self.algorithm.get()
        self.w_quantum.state(["!disabled"] if a == "Round Robin" else ["disabled"])
        for w in (self.w_preempt, self.w_aging):
            w.state(["!disabled"] if a == "Priority" else ["disabled"])

    # ---------------- 3 & 4. results ---------------- #
    def _gantt_panel(self, parent):
        box = ttk.LabelFrame(parent, text="3 · Gantt chart", padding=8)
        box.pack(fill="x")
        self.gantt = GanttCanvas(box)
        self.gantt.pack(fill="x", expand=True)
        self.gantt.bind("<Button-1>", lambda e: self.gantt.finish())

    def _results_panel(self, parent):
        box = ttk.LabelFrame(parent, text="4 · Results", padding=8)
        box.pack(fill="both", expand=True, pady=(12, 0))
        cols = ("pid", "arrival", "burst", "priority", "completion",
                "turnaround", "waiting", "response")
        titles = ("PID", "Arrival", "Burst", "Priority", "Completion",
                  "Turnaround", "Waiting", "Response")
        self.rtable = ttk.Treeview(box, columns=cols, show="headings", height=6)
        for c, t in zip(cols, titles):
            self.rtable.heading(c, text=t)
            self.rtable.column(c, width=90, anchor="center")
        self.rtable.pack(fill="both", expand=True)

        cards = tk.Frame(box, bg=BG)
        cards.pack(fill="x", pady=(8, 0))
        self.cards = {}
        for key, title in (("avg_waiting", "Avg waiting"), ("avg_turnaround", "Avg turnaround"),
                           ("avg_response", "Avg response"), ("cpu_utilization", "CPU utilization"),
                           ("throughput", "Throughput"), ("context_switches", "Context switches")):
            card = tk.Frame(cards, bg="white", highlightbackground="#dbe2ec",
                            highlightthickness=1)
            card.pack(side="left", fill="x", expand=True, padx=(0, 6))
            tk.Label(card, text=title, bg="white", fg="#6b7a8f",
                     font=("Segoe UI", 9)).pack(anchor="w", padx=8, pady=(6, 0))
            value = tk.Label(card, text="–", bg="white", fg=NAVY, font=("Segoe UI", 15, "bold"))
            value.pack(anchor="w", padx=8, pady=(0, 6))
            self.cards[key] = value

    # ====================================================================== #
    #  Actions                                                                #
    # ====================================================================== #
    def load_processes(self, processes):
        self.processes = list(processes)
        self.ptable.delete(*self.ptable.get_children())
        for p in self.processes:
            self.ptable.insert("", "end", iid=p.pid, values=(p.pid, p.arrival, p.burst, p.priority))
        self._next_pid()

    def _next_pid(self):
        used = {p.pid for p in self.processes}
        n = 1
        while f"P{n}" in used:
            n += 1
        self.entries["PID"].delete(0, "end")
        self.entries["PID"].insert(0, f"P{n}")

    def _read_form(self):
        e = self.entries
        return parse_process(e["PID"].get(), e["Arrival"].get(), e["Burst"].get(),
                             e["Priority"].get())

    def on_select_process(self, _event):
        sel = self.ptable.selection()
        if not sel:
            return
        values = self.ptable.item(sel[0], "values")
        for name, v in zip(("PID", "Arrival", "Burst", "Priority"), values):
            self.entries[name].delete(0, "end")
            self.entries[name].insert(0, v)

    def on_add(self):
        try:
            p = self._read_form()
            if any(q.pid == p.pid for q in self.processes):
                raise ValueError(f"{p.pid} already exists — use Update to change it.")
            if len(self.processes) >= 50:
                raise ValueError("The simulator supports up to 50 processes.")
        except ValueError as e:
            messagebox.showerror("Invalid process", str(e))
            return
        self.load_processes(self.processes + [p])

    def on_update(self):
        sel = self.ptable.selection()
        if not sel:
            messagebox.showinfo("Update", "Select a process in the table first.")
            return
        try:
            p = self._read_form()
            if p.pid != sel[0] and any(q.pid == p.pid for q in self.processes):
                raise ValueError(f"{p.pid} already exists.")
        except ValueError as e:
            messagebox.showerror("Invalid process", str(e))
            return
        self.load_processes([p if q.pid == sel[0] else q for q in self.processes])

    def on_delete(self):
        sel = set(self.ptable.selection())
        self.load_processes([p for p in self.processes if p.pid not in sel])

    def on_clear(self):
        self.load_processes([])

    def on_random(self):
        try:
            self.load_processes(random_workload(int(self.random_count.get())))
        except (ValueError, tk.TclError) as e:
            messagebox.showerror("Random workload", str(e))

    def _read_options(self):
        try:
            return SchedulerOptions(quantum=int(self.quantum.get()),
                                    preemptive=bool(self.preemptive.get()),
                                    aging_interval=int(self.aging.get()),
                                    switch_cost=int(self.switch_cost.get()))
        except tk.TclError:
            raise ValueError("Options must be whole numbers.") from None

    def on_run(self):
        try:
            result = core.run(self.algorithm.get(), self.processes, self._read_options())
        except ValueError as e:
            messagebox.showerror("Cannot run", str(e))
            return
        rows, summary = metrics.compute(result)
        self.last = (result, rows, summary)
        self.gantt.show(result, SPEEDS[self.speed.get()])

        self.rtable.delete(*self.rtable.get_children())
        for r in rows:
            self.rtable.insert("", "end", values=(r.pid, r.arrival, r.burst, r.priority,
                                                  r.completion, r.turnaround, r.waiting,
                                                  r.response))
        self.cards["avg_waiting"].config(text=f"{summary.avg_waiting:.2f}")
        self.cards["avg_turnaround"].config(text=f"{summary.avg_turnaround:.2f}")
        self.cards["avg_response"].config(text=f"{summary.avg_response:.2f}")
        self.cards["cpu_utilization"].config(text=f"{summary.cpu_utilization:.1f}%")
        self.cards["throughput"].config(text=f"{summary.throughput:.3f}")
        self.cards["context_switches"].config(text=str(summary.context_switches))

    def on_compare(self):
        try:
            summaries = compare.compare_all(self.processes, self._read_options())
        except ValueError as e:
            messagebox.showerror("Cannot compare", str(e))
            return
        CompareWindow(self, summaries)

    # ---------------- files (F12) ---------------- #
    def on_save(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV files", "*.csv")])
        if path:
            storage.save_workload(path, self.processes)

    def on_load(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("All", "*.*")])
        if not path:
            return
        try:
            self.load_processes(storage.load_workload(path))
        except (OSError, ValueError) as e:
            messagebox.showerror("Cannot load file", str(e))

    def on_export(self):
        if not self.last:
            messagebox.showinfo("Export", "Run an algorithm first.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV files", "*.csv")])
        if path:
            storage.export_results(path, *self.last)

    def on_terms(self):
        messagebox.showinfo("Key terms", "\n".join([
            "Arrival time – when the process enters the ready queue.",
            "Burst time – how long the process needs the CPU.",
            "Waiting time – total time spent waiting in the ready queue.",
            "Turnaround time – from arrival until the process finishes.",
            "Response time – from arrival until it runs for the first time.",
            "Preemption – stopping a running process to give the CPU to another.",
            "Time quantum – the fixed time slice each process gets in Round Robin.",
            "Context switch – saving one process's state (PCB) and loading another's.",
            "Aging – slowly raising the priority of a process that waits a long time.",
        ]))


class CompareWindow(tk.Toplevel):
    """F10 - bar charts + table comparing every algorithm on the same workload."""

    def __init__(self, master, summaries):
        super().__init__(master)
        self.title("Compare all algorithms")
        self.geometry("1000x700")
        self.configure(bg=BG)
        self.summaries = summaries

        try:
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            from matplotlib.figure import Figure
        except ImportError as e:
            messagebox.showerror("Matplotlib missing",
                                 f"Install it with:  pip install matplotlib\n\n{e}", parent=self)
            self.destroy()
            return

        cols = ("algorithm", "wt", "tat", "rt", "cpu", "thr", "cs")
        table = ttk.Treeview(self, columns=cols, show="headings", height=len(summaries))
        for c, t in zip(cols, ("Algorithm", "Avg waiting", "Avg turnaround", "Avg response",
                               "CPU %", "Throughput", "Switches")):
            table.heading(c, text=t)
            table.column(c, width=120 if c != "algorithm" else 230, anchor="center")
        win = compare.best(summaries)
        for s in summaries:
            table.insert("", "end", values=(("★ " if s is win else "") + s.algorithm,
                                            f"{s.avg_waiting:.2f}", f"{s.avg_turnaround:.2f}",
                                            f"{s.avg_response:.2f}", f"{s.cpu_utilization:.1f}",
                                            f"{s.throughput:.3f}", s.context_switches))
        # Pack the bottom bar and the table first, so the chart gets the space that is left.
        bottom = tk.Frame(self, bg=BG)
        bottom.pack(side="bottom", fill="x", padx=10, pady=8)
        table.pack(side="bottom", fill="x", padx=10)
        tk.Label(bottom, bg=BG, fg=NAVY, font=("Segoe UI", 11, "bold"),
                 text=f"★ Lowest average waiting time: {win.algorithm}").pack(side="left")
        ttk.Button(bottom, text="Export CSV…", command=self.on_export).pack(side="right")

        fig = Figure(figsize=(9, 4.6), dpi=100)
        compare.plot_comparison(summaries, fig)
        FigureCanvasTkAgg(fig, master=self).get_tk_widget().pack(fill="both", expand=True)

    def on_export(self):
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".csv",
                                            filetypes=[("CSV files", "*.csv")])
        if path:
            storage.export_comparison(path, self.summaries)


def main():
    SchedLabApp().mainloop()


if __name__ == "__main__":
    main()
