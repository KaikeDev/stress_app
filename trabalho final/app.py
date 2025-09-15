import tkinter as tk
from tkinter import ttk, messagebox
import multiprocessing as mp
from workers import cpu_worker, ram_worker, disk_worker


class SystemStressApp:
    def __init__(self, root):
        self.root = root
        self.root.title("System Stress Test")

        # Variáveis
        self.hours = tk.IntVar(value=0)
        self.minutes = tk.IntVar(value=1)
        self.status_text = tk.StringVar(value="Idle")
        self.time_left = tk.StringVar(value="Time left: 00:00:00")

        self.stress_cpu = tk.BooleanVar(value=True)
        self.stress_ram = tk.BooleanVar(value=False)
        self.stress_disk = tk.BooleanVar(value=False)

        self.stop_event = None
        self.processes = []
        self.remaining = 0
        self.running = False

        # Layout
        frame = ttk.Frame(root, padding=10)
        frame.grid(row=0, column=0)

        ttk.Label(frame, text="Run test for:").grid(row=0, column=0, sticky="w")
        tk.Spinbox(frame, from_=0, to=23, width=5, textvariable=self.hours).grid(row=0, column=1)
        ttk.Label(frame, text="hours").grid(row=0, column=2, padx=5)
        tk.Spinbox(frame, from_=0, to=59, width=5, textvariable=self.minutes).grid(row=0, column=3)
        ttk.Label(frame, text="minutes").grid(row=0, column=4, padx=5)

        # Checkbox para escolher componentes
        ttk.Checkbutton(frame, text="CPU", variable=self.stress_cpu).grid(row=1, column=0, sticky="w")
        ttk.Checkbutton(frame, text="RAM", variable=self.stress_ram).grid(row=1, column=1, sticky="w")
        ttk.Checkbutton(frame, text="Disk", variable=self.stress_disk).grid(row=1, column=2, sticky="w")

        # Botões
        self.start_button = ttk.Button(frame, text="Start", command=self.start_test)
        self.start_button.grid(row=2, column=0, pady=10)
        self.stop_button = ttk.Button(frame, text="Stop", command=self.stop_test, state="disabled")
        self.stop_button.grid(row=2, column=1, pady=10)
        self.quit_button = ttk.Button(frame, text="Quit", command=root.destroy)
        self.quit_button.grid(row=2, column=2, pady=10)

        # Status
        ttk.Label(frame, textvariable=self.status_text, foreground="blue").grid(row=3, column=0, columnspan=5, pady=5)
        ttk.Label(frame, textvariable=self.time_left, font=("Arial", 12, "bold"), foreground="red").grid(row=4, column=0, columnspan=5, pady=5)

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
            for i in range(mp.cpu_count()):
                p = mp.Process(target=cpu_worker, args=(self.stop_event, i), daemon=True)
                p.start()
                self.processes.append(p)

        # RAM
        if self.stress_ram.get():
            p = mp.Process(target=ram_worker, args=(self.stop_event,), daemon=True)
            p.start()
            self.processes.append(p)

        # Disk
        if self.stress_disk.get():
            for i in range(8):  # número de workers de disco
                file_path = f"disk_stress_{i}.tmp"
                p = mp.Process(target=disk_worker, args=(self.stop_event, file_path), daemon=True)
                p.start()
                self.processes.append(p)

        # Agenda término automático
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
        messagebox.showinfo("System Stress", "O teste foi concluído!")
        self.status_text.set("Stopped.")
