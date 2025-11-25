import multiprocessing as mp
import time
import math
import os
import random

def cpu_burn_worker(stop_event: mp.Event, worker_id: int):
    """
    - Executa cálculos intensos com ponto flutuante e inteiros.
    - Mantém verificações periódicas de integridade numérica.
    """

    # Valor base esperado — (instabilidade)
    expected = 0.123456789
    validation_interval = 10_000_000  
    iteration = 0
    result = expected

    # Pré-carrega senos
    values = [math.sin(i) for i in range(1_000)]
 
    while not stop_event.is_set():
       
        for _ in range(validation_interval):
            i = (iteration % 1000) + 1
            
            # Executa operações trigonométricas intensivas e dependentes do resultado anterior
            # Isso impede a CPU de "adivinhar" o próximo valor.
            result = (result * values[i - 1]) + math.cos(result + i)
            iteration += 1

        # Validação periódica
        if abs(result - expected) > 1e6 or math.isnan(result):
            print(f"[CPU-{worker_id}]  Instabilidade detectada! {result} != {expected}")
            break


def disk_worker(stop_event: mp.Event, file_path="disk_stress.tmp", block_size=4096, file_size_mb=1024):
    """
    Estressa o disco com operações aleatórias de leitura/escrita.

    Como no windows não é possivel acessar um setor, estamos acessando posições dentro de um arquivo
    que está dentro do sistema de arquivos
    """
    size = file_size_mb * 1024 * 1024  # MB para bytes

    # Cria o arquivo inicial caso ele não exista
    if not os.path.exists(file_path):
        print(f"[DISK] Criando arquivo de {file_size_mb} MB para teste...")
        with open(file_path, "wb") as f:
            f.write(b"\0" * size)

    # Abre o arquivo no modo leitura+escrita
    with open(file_path, "r+b", buffering=0) as f:
        while not stop_event.is_set():
            
            # Escolhe uma posição aleatória
            pos = random.randint(0, size - block_size)

            # Gera um bloco de dados aleatórios para escrita
            data = os.urandom(block_size)

            # Move o ponteiro do arquivo e escreve os dados
            f.seek(pos)
            f.write(data)

            # Garante que os dados foram realmente gravados no disco
            f.flush()
            os.fsync(f.fileno())

            # só valida a leitura
            f.seek(pos)
            if f.read(block_size) != data:
                print(f"[DISK] Falha de integridade em posição {pos}")

def ram_stress_worker(stop_event: mp.Event, block_size_mb=500, num_blocks=10):
    """
    Estressa a RAM com leituras e escritas aleatórias.
    - Aloca grandes blocos de memória.
    - Realiza acessos aleatórios e modificações contínuas.
    """
    block_size = block_size_mb * 1024 * 1024
    
    # 5 GB de RAM.
    blocks = [bytearray(block_size) for _ in range(num_blocks)]

    ops = 0 # Contador de operações
    start = time.time()

    # Loop contínuo até que o evento de parada seja acionado
    while not stop_event.is_set():
        
        # Escolhe um bloco aleatório
        b = random.choice(blocks)

        # Escolhe uma posição aleatória
        pos = random.randint(0, len(b) - 1)

        # Altera o byte
        b[pos] = (b[pos] + 1) % 256 # 256 para manter o valor entre 0 e 255

        ops += 1
        # Exibe a cada 1 milhão de operações
        if ops % 1_000_000 == 0:
            elapsed = time.time() - start
            print(f"[RAM] {ops:,} acessos ({ops/elapsed:,.0f} ops/s)")
