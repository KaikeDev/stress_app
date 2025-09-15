import multiprocessing as mp
import time
import math
import hashlib
import random
import os

def cpu_worker(stop_event: mp.Event, worker_id: int):
    """Worker que estressa CPU usando cálculos matemáticos e hash"""
    s = 0.0
    rnd = random.Random(worker_id)
    while not stop_event.is_set():
        v = rnd.random()
        for _ in range(200):
            s += math.sqrt(v)
            hashlib.sha256(f"{s}-{v}".encode()).digest()
        time.sleep(0)  # libera GIL rapidamente

def ram_worker(stop_event: mp.Event, block_size_mb=50):
    """Worker que estressa RAM alocando blocos de memória"""
    blocks = []
    while not stop_event.is_set():
        try:
            blocks.append(bytearray(block_size_mb * 1024 * 1024))  # MB
            time.sleep(0.01)
        except MemoryError:
            if blocks:
                blocks.pop(0)
            time.sleep(0.01)

def disk_worker(stop_event: mp.Event, file_path="disk_stress.tmp", block_size_mb=512):
    """Worker que estressa disco escrevendo/leitura intensiva"""
    block = os.urandom(block_size_mb * 1024 * 1024)

    # Garante que o arquivo exista com um tamanho grande
    with open(file_path, "wb") as f:
        for _ in range(20):  # cria ~10 GB se block_size=512 MB
            f.write(block)
        f.flush()
        os.fsync(f.fileno())

    while not stop_event.is_set():
        try:
            # Escrita aleatória
            with open(file_path, "rb+") as f:
                pos = random.randint(0, os.path.getsize(file_path) - len(block))
                f.seek(pos)
                f.write(block)
                f.flush()
                os.fsync(f.fileno())

            # Leitura aleatória
            with open(file_path, "rb") as f:
                pos = random.randint(0, os.path.getsize(file_path) - len(block))
                f.seek(pos)
                _ = f.read(len(block))

        except Exception as e:
            print(f"Erro no disco: {e}")
            time.sleep(0.01)

    if os.path.exists(file_path):
        os.remove(file_path)
