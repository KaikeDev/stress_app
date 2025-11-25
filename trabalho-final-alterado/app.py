import tkinter as tk
from tkinter import ttk, messagebox
import multiprocessing as mp
from workers import cpu_burn_worker, ram_stress_worker, disk_worker
import psutil

class SystemStressApp:
    def __init__(self, root):
        self.root = root
        self.root.title("System Stress Test")

        # Variáveis
        self.hours = tk.IntVar(value=0)
        self.minutes = tk.IntVar(value=1)
        self.stress_cpu = tk.BooleanVar(value=True)
        self.stress_ram = tk.BooleanVar(value=False)
        self.stress_disk = tk.BooleanVar(value=False)
        self.status_text = tk.StringVar(value="Idle")
        self.time_left = tk.StringVar(value="Time left: 00:00:00")

        self.stop_event = None
        self.processes = []
        self.remaining = 0
        self.running = False

        self.build_ui()

    def build_ui(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.grid(row=0, column=0)

        ttk.Label(frame, text="Run test for:").grid(row=0, column=0)
        tk.Spinbox(frame, from_=0, to=23, width=5, textvariable=self.hours).grid(row=0, column=1)
        ttk.Label(frame, text="hours").grid(row=0, column=2)
        tk.Spinbox(frame, from_=0, to=59, width=5, textvariable=self.minutes).grid(row=0, column=3)
        ttk.Label(frame, text="minutes").grid(row=0, column=4)

        ttk.Checkbutton(frame, text="CPU", variable=self.stress_cpu).grid(row=1, column=0)
        ttk.Checkbutton(frame, text="RAM", variable=self.stress_ram).grid(row=1, column=1)
        ttk.Checkbutton(frame, text="Disk", variable=self.stress_disk).grid(row=1, column=2)

        self.allowed_cpus = list(range(mp.cpu_count()))

        self.aff_button = ttk.Button(frame, text="Selecionar CPUs...", command=self.show_cpu_selector)
        self.aff_button.grid(row=2, column=2, pady=10)

        self.start_button = ttk.Button(frame, text="Start", command=self.start_test)
        self.start_button.grid(row=2, column=0, pady=10)
        self.stop_button = ttk.Button(frame, text="Stop", command=self.stop_test, state="disabled")
        self.stop_button.grid(row=2, column=1, pady=10)

        ttk.Label(frame, textvariable=self.status_text, foreground="blue").grid(row=3, column=0, columnspan=5)
        ttk.Label(frame, textvariable=self.time_left, font=("Arial", 12, "bold"), foreground="red").grid(row=4, column=0, columnspan=5)

    def show_cpu_selector(self):
        win = tk.Toplevel(self.root)
        win.title("Selecionar CPUs")
        win.grab_set()

        self.cpu_vars = []

        for i in range(mp.cpu_count()):
            var = tk.BooleanVar(value=(i in self.allowed_cpus))
            chk = ttk.Checkbutton(win, text=f"CPU {i}", variable=var)
            chk.grid(row=i, column=0, sticky="w")
            self.cpu_vars.append(var)

        def save_and_close():
            self.allowed_cpus = [i for i, v in enumerate(self.cpu_vars) if v.get()]
            if not self.allowed_cpus:
                messagebox.showerror("Erro", "Selecione pelo menos uma CPU.")
                return
            win.destroy()

        ttk.Button(win, text="Salvar", command=save_and_close).grid(row=mp.cpu_count()+1, column=0, pady=10)

    def start_test(self):
        duration = self.hours.get() * 3600 + self.minutes.get() * 60
        if duration <= 0:
            self.status_text.set("Please set duration > 0")
            return

        self.status_text.set(f"Running for {duration} seconds...")
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")

        self.stop_event = mp.Event()
        self.processes = []
        self.remaining = duration
        self.running = True
        self.update_timer()

        # CPU
        if self.stress_cpu.get():
            for core_index, core_id in enumerate(self.allowed_cpus):
                p = mp.Process(target=cpu_burn_worker, args=(self.stop_event, core_index), daemon=True)
                p.start()

                psproc = psutil.Process(p.pid)
                psproc.cpu_affinity([core_id])

                self.processes.append(p)

        # RAM
        if self.stress_ram.get():
            p = mp.Process(target=ram_stress_worker, args=(self.stop_event,), daemon=True)
            p.start()
            self.processes.append(p)

        # Disk
        if self.stress_disk.get():
            for i in range(4):
                file_path = f"disk_stress_{i}.tmp"
                p = mp.Process(target=disk_worker, args=(self.stop_event, file_path), daemon=True)
                p.start()
                self.processes.append(p)

        # Stop automático
        self.root.after(duration * 1000, self.stop_test)

    def update_timer(self):
        if self.remaining > 0 and self.running:
            h, m = divmod(self.remaining, 3600)
            m, s = divmod(m, 60)
            self.time_left.set(f"Time left: {h:02}:{m:02}:{s:02}")
            self.remaining -= 1
            self.root.after(1000, self.update_timer)
        else:
            self.time_left.set("Time left: 00:00:00")

    def stop_test(self):
        self.running = False
        if self.stop_event:
            self.stop_event.set()
        for p in self.processes:
            if p.is_alive():
                p.terminate()
        self.processes = []
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.status_text.set("Stopped.")
        messagebox.showinfo("System Stress", "O teste foi concluído!")