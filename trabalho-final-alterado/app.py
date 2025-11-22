import tkinter as tk
from tkinter import ttk, messagebox
import multiprocessing as mp
from workers import cpu_burn_worker, ram_stress_worker, disk_worker
import threading
import time

# Importar monitor de temperatura
try:
    from temperatures import MonitorCPU

    TEMP_AVAILABLE = True
except Exception as e:
    TEMP_AVAILABLE = False
    print(f"⚠️ Monitor de temperatura não disponível: {e}")


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
        self.cpu_temp = tk.StringVar(value="CPU Temp: --°C")

        self.stop_event = None
        self.processes = []
        self.remaining = 0
        self.running = False

        # Monitor de temperatura
        self.temp_monitor = None
        self.temp_thread = None
        self.temp_running = False

        self.build_ui()

        # Inicializar monitor de temperatura
        if TEMP_AVAILABLE:
            self.init_temp_monitor()

    def init_temp_monitor(self):
        """Inicializa o monitor de temperatura"""
        try:
            self.temp_monitor = MonitorCPU()
            self.temp_running = True
            self.temp_thread = threading.Thread(target=self.update_temperature, daemon=True)
            self.temp_thread.start()
        except Exception as e:
            print(f"⚠️ Não foi possível inicializar monitor: {e}")
            self.cpu_temp.set("CPU Temp: N/A")

    def update_temperature(self):
        """Thread que atualiza a temperatura constantemente"""
        while self.temp_running:
            try:
                temp = self.temp_monitor.get_cpu_temperature()
                if temp:
                    # Definir cor baseada na temperatura
                    if temp < 60:
                        color = "green"
                        status = "🟢"
                    elif temp < 80:
                        color = "orange"
                        status = "🟡"
                    else:
                        color = "#FF4444"
                        status = "🔴"

                    self.cpu_temp.set(f"CPU Temp: {temp:.1f}°C {status}")
                    self.temp_label.config(foreground=color)
                else:
                    self.cpu_temp.set("CPU Temp: --°C")
            except Exception as e:
                self.cpu_temp.set("CPU Temp: Error")

            time.sleep(1)

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

        self.start_button = ttk.Button(frame, text="Start", command=self.start_test)
        self.start_button.grid(row=2, column=0, pady=10)
        self.stop_button = ttk.Button(frame, text="Stop", command=self.stop_test, state="disabled")
        self.stop_button.grid(row=2, column=1, pady=10)

        ttk.Label(frame, textvariable=self.status_text, foreground="blue").grid(row=3, column=0, columnspan=5)
        ttk.Label(frame, textvariable=self.time_left, font=("Arial", 12, "bold"), foreground="red").grid(row=4,
                                                                                                         column=0,
                                                                                                         columnspan=5)

        # Label de temperatura
        self.temp_label = ttk.Label(frame, textvariable=self.cpu_temp, font=("Arial", 14, "bold"))
        self.temp_label.grid(row=5, column=0, columnspan=5, pady=10)

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

        # CPU: um worker por núcleo
        if self.stress_cpu.get():
            for i in range(mp.cpu_count()):
                p = mp.Process(target=cpu_burn_worker, args=(self.stop_event, i), daemon=True)
                p.start()
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

    def __del__(self):
        """Cleanup ao fechar o app"""
        self.temp_running = False
        if self.temp_monitor:
            try:
                self.temp_monitor.close_monitor()
            except:
                pass