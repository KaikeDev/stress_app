import multiprocessing as mp
import time
import math
import hashlib
import os
import random
import numpy as np

'''
CPU: faz cálculos intensivos + detecta erros de instabilidade.

RAM: aloca muita memória e acessa aleatoriamente.

Disco: escreve/lê dados aleatórios em arquivo grande.

'''


def cpu_overclock_worker(stop_event: mp.Event, worker_id: int):
    """
    Estressa CPU com algoritmo determinístico e validação de overclock.
    Usa Lucas-Lehmer simplificado para detectar instabilidade.

    """
    p = 31  # número primo Mersenne pequeno para teste rápido
    m = (1 << p) - 1
    s = 4 + worker_id  # valor inicial diferente por worker

    while not stop_event.is_set():
        for _ in range(1000):  # loop pesado
            s = (s * s - 2) % m

        # validação determinística
        if s <= 0 or s >= m or not math.isfinite(s): #detectar overclock (ex.: valores inesperados
            raise RuntimeError(f"[Worker {worker_id}] Instabilidade detectada!")



def disk_worker(stop_event: mp.Event, file_path="disk_stress.tmp", block_size=4096):
    """Estressa Disco com escrita/leitura em posições aleatórias"""
    size = 1024 * 1024 * 1024  # 1 GB
    # se o arquivo não existir, cria um arquivo grande
    if not os.path.exists(file_path):
        with open(file_path, "wb") as f:
            f.write(b"\0" * size)
   # abre o arquivo para leitura/escrita binária
    with open(file_path, "r+b") as f:
        while not stop_event.is_set():
            pos = random.randint(0, size - block_size)
            data = os.urandom(block_size)
            f.seek(pos)
            f.write(data)
            #força o flush para garantir escrita no disco
            f.flush()
            os.fsync(f.fileno())

            # leitura de validação
            f.seek(pos)
            read_back = f.read(block_size)
            assert read_back == data

def ram_stress_worker(stop_event: mp.Event, block_size_mb=500, num_blocks=20):
    """
    Estressa RAM usando vários blocos grandes e acesso aleatório.
    - block_size_mb: tamanho de cada bloco em MB
    - num_blocks: número de blocos alocados

    aloca vários blocos grandes (ex.: bytearray) e faz acessos aleatórios de leitura/escrita em posições aleatórias
    """
    blocks = [bytearray(block_size_mb * 1024 * 1024) for _ in range(num_blocks)]
    sizes = [len(b) for b in blocks]

    print(f"[RAM] Alocados {num_blocks} blocos de {block_size_mb} MB = {block_size_mb*num_blocks} MB")

    while not stop_event.is_set():
        # escolhe bloco e posição aleatória
        i = random.randint(0, num_blocks - 1)
        pos = random.randint(0, sizes[i] - 1)
        val = (blocks[i][pos] + 1) % 256
        blocks[i][pos] = val  # escreve
        _ = blocks[i][pos]    # lê para validar

