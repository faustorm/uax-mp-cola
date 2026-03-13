import threading, multiprocessing, time

def cuenta():
    sum([i**2 for i in range(1000000)])

def mide_tiempo(metodo, nombre):
    inicio = time.time()
    proceso = [metodo(target=cuenta) for _ in range(4)]
    for p in proceso:
        p.start()
    for p in proceso:
        p.join()
    fin = time.time()
    print(f"{nombre}: {fin - inicio}")

if __name__ == '__main__':
    mide_tiempo(threading.Thread, "hilos")
    mide_tiempo(multiprocessing.Process, "procesos")