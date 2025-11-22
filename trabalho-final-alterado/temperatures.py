#!/usr/bin/env python3
"""
Monitor de temperatura da CPU - Versão Simplificada
Retorna apenas a temperatura média da CPU
"""

import clr
import time
import os
import sys

# Carregar DLL do LibreHardwareMonitor
dll_path = os.path.join(os.path.dirname(__file__), 'LibreHardwareMonitorLib.dll')

if not os.path.exists(dll_path):
    print(f"❌ ERRO: LibreHardwareMonitorLib.dll não encontrada em {dll_path}")
    sys.exit(1)

clr.AddReference(dll_path)
from LibreHardwareMonitor import Hardware


class MonitorCPU:
    def __init__(self):
        self.computer = Hardware.Computer()
        self.computer.IsCpuEnabled = True
        self.computer.Open()

        # Primeira leitura forçada
        time.sleep(0.5)
        for hw in self.computer.Hardware:
            hw.Update()
            for subhw in hw.SubHardware:
                subhw.Update()

    def get_cpu_temperature(self):
        """
        Retorna a temperatura média da CPU em Celsius
        """
        temps = []

        for hw in self.computer.Hardware:
            hw.Update()
            for subhw in hw.SubHardware:
                subhw.Update()

            if hw.HardwareType == Hardware.HardwareType.Cpu:
                for sensor in hw.Sensors:
                    if sensor.SensorType == Hardware.SensorType.Temperature and sensor.Value:
                        valor = float(sensor.Value)
                        if valor > 0:
                            temps.append(valor)

        return sum(temps) / len(temps) if temps else None

    def close_monitor(self):
        """Fecha a conexão com o hardware"""
        self.computer.Close()


# ============= EXEMPLO DE USO =============

if __name__ == "__main__":
    monitor = MonitorCPU()
    temp = monitor.get_cpu_temperature()
    print(temp)
    monitor.close_monitor()
