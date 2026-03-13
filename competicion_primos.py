import multiprocessing
import time
import sys
import math
import queue as q_module
import os

def is_prime(n):
    """
    Función optimizada para verificar si un número es primo.
    Uso de math.isqrt para calcular el límite una sola vez, 
    y división por saltos de 6k +/- 1 para maximizar la velocidad base.
    """
    if n <= 1:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
        
    limit = math.isqrt(n)
    i = 5
    while i <= limit:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True
#comen tario

def worker(worker_id, num_workers, shared_queue, stop_event, base_num):
    """
    Worker que revisa números con un patrón de stride (pasos).
    Esto evita el cuello de botella (overhead) de un proceso maestro
    asignando rangos a los trabajadores.
    Todo el CPU se usa en matemática pura y envío a la cola.
    """
    start_num = base_num + 2 * worker_id
    step = 2 * num_workers
    num = start_num
    
    local_primes = []
    
    # Optimizaciones de variables locales (más veloces en el bucle de Python)
    _is_prime = is_prime
    _append = local_primes.append
    _put = shared_queue.put
    _is_set = stop_event.is_set
    
    while not _is_set():
        if _is_prime(num):
            _append(num)
            # Enviar a la queue en grandes bloques para no ahogar la tubería (Pipe IPC)
            if len(local_primes) >= 1000:
                _put(local_primes)
                local_primes = []
                _append = local_primes.append
        num += step
        
    # Si queda algún sobrante, vacíalo a la cola antes de terminar
    if local_primes:
        _put(local_primes)

def main():
    TIME_LIMIT = 3 * 60  # 3 minutos (180 segundos) por defecto
    CACHE_FILE = None
    
    # Permitir al usuario pasar el límite de tiempo mediante la línea de comandos
    if len(sys.argv) > 1:
        try:
            TIME_LIMIT = int(sys.argv[1])
        except ValueError:
            print(f"Argumento inválido. Usando el tiempo por defecto: {TIME_LIMIT}s")
            
    if len(sys.argv) > 2:
        CACHE_FILE = sys.argv[2]

    num_cpus = multiprocessing.cpu_count()
    
    shared_queue = multiprocessing.Queue()
    stop_event = multiprocessing.Event()
    
    highest_prime = 0
    total_primes_found = 0
    
    # === SISTEMA DE CACHÉ ===
    if CACHE_FILE and os.path.exists(CACHE_FILE):
        print(f"[*] Cargando cache desde '{CACHE_FILE}'...")
        with open(CACHE_FILE, 'r') as f:
            for line in f:
                if line.strip():
                    p = int(line.strip())
                    print(p)  # Imprime los cacheados como solicitado
                    total_primes_found += 1
                    if p > highest_prime:
                        highest_prime = p
        
    print("=" * 60)
    print(f"[*] INICIO DE BUSQUEDA DE NUMEROS PRIMOS (COMPETICION)")
    print(f"[*] CPUs utilizadas : {num_cpus}")
    print(f"[*] Tiempo limite   : {TIME_LIMIT} segundos")
    if CACHE_FILE:
        print(f"[*] Archivo Cache   : {CACHE_FILE} (cargados: {total_primes_found} primos)")
    print(f"[*] Estrategia      : Particion matematica + Queue IPC por lotes")
    print("=" * 60)
    
    # Preparar apertura de cache para escritura si se provee
    cache_f = None
    if CACHE_FILE:
        cache_f = open(CACHE_FILE, 'a')
        
    # Inicializar el bloque para la cola usando la caché como base
    if highest_prime < 2:
        shared_queue.put([2])
        base_num = 3
    else:
        # Asegurar que la simiente de base para los procesos sea un impar 
        # mayor al número más alto cacheados.
        base_num = highest_prime + 1 if highest_prime % 2 == 0 else highest_prime + 2
    
    workers = []
    # Lanzar los procesos
    for i in range(num_cpus):
        p = multiprocessing.Process(target=worker, args=(i, num_cpus, shared_queue, stop_event, base_num))
        workers.append(p)
        p.start()
        
    start_time = time.time()
    last_print_time = start_time
    
    try:
        while True:
            elapsed_time = time.time() - start_time
            if elapsed_time >= TIME_LIMIT:
                break
                
            try:
                # Extraer números de la Queue (evitando que la RAM colapse por acumulación)
                primes_chunk = shared_queue.get(timeout=0.5)
                total_primes_found += len(primes_chunk)
                
                # Imprimir cada número primo encontrado conforme salen de la cola
                for prime in primes_chunk:
                    print(prime)
                    if cache_f:
                        cache_f.write(f"{prime}\n")
                        # Flush manual si quieres asegurarte, pero python bufferiza en disco.
                
                # Buscar el máximo de este bloque
                max_in_chunk = max(primes_chunk)
                if max_in_chunk > highest_prime:
                    highest_prime = max_in_chunk
                    
            except q_module.Empty:
                pass
            
            # Feedback a la terminal cada 5 segundos
            if time.time() - last_print_time >= 5:
                print(f"[*] [Progreso] {elapsed_time:.1f}s / {TIME_LIMIT}s | "
                      f"Total primos: {total_primes_found:,} | "
                      f"Max detectado: {highest_prime:,}")
                last_print_time = time.time()
                
    except KeyboardInterrupt:
        print("\n[!] Cierre manual detectado.")
        
    print(f"\n[*] {TIME_LIMIT} segundos completados. Emitiendo aviso de cierre a trabajadores...")
    stop_event.set()
    
    # Damos tiempo (buffer de 1s) para que envíen sus últimas colecciones descubiertas a la Queue
    time.sleep(1) 
    while not shared_queue.empty():
        try:
            primes_chunk = shared_queue.get_nowait()
            total_primes_found += len(primes_chunk)
            
            for prime in primes_chunk:
                print(prime)
                if cache_f:
                    cache_f.write(f"{prime}\n")
                
            max_in_chunk = max(primes_chunk)
            if max_in_chunk > highest_prime:
                highest_prime = max_in_chunk
        except q_module.Empty:
            break
            
    # Garantizar desconexiones limpias con el OS
    for idx, p in enumerate(workers):
        p.join(timeout=2)
        if p.is_alive():
            p.terminate()
            
    print("\n" + "=" * 60)
    print("RESULTADOS DE LA COMPETICION".center(60))
    print("=" * 60)
    print(f"[*] Total de numeros analizados y confirmados : {total_primes_found:,}")
    print(f"[*] EL NUMERO PRIMO MAS GRANDE LOGRADO FUE    : {highest_prime:,}")
    print("=" * 60)
    
    if cache_f:
        cache_f.close()

if __name__ == '__main__':
    # Importante en SO Windows para evitar repeticiones en colas concurrentes
    multiprocessing.freeze_support()
    main()
