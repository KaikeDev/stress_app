import multiprocessing as mp
import time
import math
import hashlib
import os
import random
import numpy as np

def cpu_burn_worker(stop_event: mp.Event, worker_id: int):
    """
 
    - Multiplicar matrizes grandes repetidamente
    - Verificar se o resultado é sempre o mesmo (overclock)
    - Fazer operações trigonométricas e hashing para diversificar o tipo de carga.
    """
    rng = np.random.default_rng(worker_id)

    # Tamanho das matrizes (1024x1024 = 1 milhão de elementos)
    size = 1024  
    A = rng.random((size, size), dtype=np.float64)
    B = rng.random((size, size), dtype=np.float64)

    # Calcula o "checksum" esperado, que é a soma de todos os elementos do produto A @ B
    expected_checksum = int(np.sum(A @ B))

    while not stop_event.is_set():

        # Executa várias multiplicações no mesmo ciclo
        for _ in range(5):

            # Multiplicação de matrizes — operação intensiva de ponto flutuante
            C = A @ B

            # Soma dos resultados para validar a consistência numérica
            checksum = int(np.sum(C))

            # Cálculos extras com seno e cosseno:
            _ = np.sin(C).sum() + np.cos(C).sum()

            # Gera um hash SHA-256 dos bytes da matriz C
            # Isso força movimentação de memória
            hashlib.sha256(C.tobytes()).digest()

            # Validação de estabilidade:
            # Se o resultado da multiplicação mudar, pode indicar instabilidade
            if checksum != expected_checksum:
                raise RuntimeError(
                    f"[Worker {worker_id}] Instabilidade detectada! "
                    f"{checksum} != {expected_checksum}"
                )


def disk_worker(stop_event: mp.Event, file_path="disk_stress.tmp", block_size=4096):
    """
    Estressa o Disco com operações aleatórias de leitura e escrita.

    - Realiza acessos aleatórios de escrita e leitura para simular I/O pesado.
    - Valida a integridade dos dados após a escrita.
    """
    size = 1024 * 1024 * 1024  # 1 GB

    # Cria o arquivo se não existir
    if not os.path.exists(file_path):
        print(f"[INFO] Criando arquivo de {size / (1024**3):.1f} GB para teste...")
        with open(file_path, "wb") as f:
            chunk = b"\0" * (1024 * 1024)  # escreve em blocos de 1MB para não travar
            for _ in range(size // len(chunk)):
                f.write(chunk)
        print("[INFO] Arquivo de teste criado.")

    # Abre o arquivo para leitura/escrita binária
    with open(file_path, "r+b", buffering=0) as f:  # buffering=0 -> acesso direto
        while not stop_event.is_set():
            try:
                # Escolhe uma posição aleatória dentro do arquivo
                pos = random.randint(0, size - block_size)

                # Gera dados aleatórios e grava
                data = os.urandom(block_size)
                f.seek(pos)
                f.write(data)
                
                # Força a escrita no disco (fsync = garante que foi para o hardware)
                f.flush()
                os.fsync(f.fileno())

                # Leitura de volta para validação
                f.seek(pos)
                read_back = f.read(block_size)
                if read_back != data:
                    print(f"[ERRO] Falha na validação em posição {pos}")
            except Exception as e:
                print(f"[ERRO] {e}")

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

    # revalida checksums (detecção de corrupção)
    new_checksums = [sum(b[:1024]) for b in blocks]
    for i, (old, new) in enumerate(zip(checksums, new_checksums)):
        if old != new:
            print(f"[RAM][ALERTA] Possível corrupção detectada no bloco {i}: "
                  f"{old} -> {new}")