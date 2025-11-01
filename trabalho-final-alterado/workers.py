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


def cpu_burn_worker(stop_event: mp.Event, worker_id: int):
    """Estressa CPU fortemente e valida resultados numéricos
     Multiplica matrizes grandes repetidamente e checa se o resultado é consistente.
    """
    rng = np.random.default_rng(worker_id)
    size = 1024  
    A = rng.random((size, size), dtype=np.float64)
    B = rng.random((size, size), dtype=np.float64)

    expected_checksum = int(np.sum(A @ B))  # soma inteira aproximada

    while not stop_event.is_set():
        # repete várias multiplicações no mesmo loop
        for _ in range(5):
            C = A @ B
            checksum = int(np.sum(C))

            # cálculos extras para estressar FPU e ALU
            _ = np.sin(C).sum() + np.cos(C).sum()
            hashlib.sha256(C.tobytes()).digest()

            if checksum != expected_checksum:
                raise RuntimeError(
                    f"[Worker {worker_id}] Instabilidade detectada! "
                    f"{checksum} != {expected_checksum}"
                )



def disk_worker(stop_event: mp.Event, file_path="disk_stress.tmp", block_size=4096):
    """Estressa Disco com escrita/leitura em posições aleatórias
    Gera acessos aleatórios de escrita e leitura em um arquivo grande para testar velocidade e integridade do disco.
    """
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

def ram_stress_worker(stop_event, block_size_mb=500, num_blocks=20, page_size=4096):
    """
    Estressa a RAM através de leitura e escrita aleatória em blocos grandes.
    
    - Aloca grandes blocos de memória (bytearrays).
    - Acessa endereços aleatórios alinhados a cache line / página.
    - Faz leituras e escritas pseudoaleatórias para causar page faults.
    """
    block_size_bytes = block_size_mb * 1024 * 1024
    total_allocated = block_size_bytes * num_blocks / (1024 * 1024)
    blocks = [bytearray(block_size_bytes) for _ in range(num_blocks)]

    print(f"[RAM] Alocados {num_blocks} blocos de {block_size_mb} MB = {total_allocated:.1f} MB totais")

    # pequenas verificações iniciais (checksum parcial)
    checksums = [sum(b[:1024]) for b in blocks]

    # contadores para estatísticas
    ops = 0
    start_time = time.time()

    while not stop_event.is_set():
        # Escolhe bloco aleatório
        i = random.randrange(num_blocks)
        b = blocks[i]

        # Escolhe posição alinhada à página (multiplo de page_size)
        max_offset = len(b) - page_size
        offset = (random.randrange(max_offset // page_size) * page_size)

        # Lê um pedaço (cache line / página)
        chunk = memoryview(b)[offset:offset+64]  # leitura leve (64 bytes)
        checksum = sum(chunk)

        # Escrita pseudoaleatória: altera 1 byte
        pos = offset + random.randint(0, 63)
        new_val = (b[pos] + checksum) & 0xFF
        b[pos] = new_val

        # Validação simples: lê de volta
        _ = b[pos]

        ops += 1

        # imprime de tempos em tempos
        if ops % 1_000_000 == 0:
            elapsed = time.time() - start_time
            print(f"[RAM] {ops:,} acessos aleatórios em {elapsed:.1f}s "
                  f"({ops/elapsed:,.0f} ops/s)")

    print("[RAM] Teste encerrado. Verificando integridade...")

    # revalida checksums (detecção de corrupção)
    new_checksums = [sum(b[:1024]) for b in blocks]
    for i, (old, new) in enumerate(zip(checksums, new_checksums)):
        if old != new:
            print(f"[RAM][ALERTA] Possível corrupção detectada no bloco {i}: "
                  f"{old} -> {new}")