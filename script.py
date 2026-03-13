import time
import multiprocessing

def producer(nombre, cola):
    while True:
        timestamp_seconds = time.time()
        cola.put(f"{nombre},9,Hola amigo {timestamp_seconds}")
        time.sleep(0.1)

def consumer(cola):
    while cola.qsize() > 0:
        print(cola.get())
        print(cola.qsize())
        time.sleep(0.1)

if __name__ == '__main__':

    cola = multiprocessing.Queue()

    producers = []
    consumers = []

    for _ in range(5):
        producers.append(multiprocessing.Process(target=producer,args=("Carlos", cola)))

    for _ in range(3):
        consumers.append(multiprocessing.Process(target=consumer,args=(cola,)))

    for p in producers:
        p.start()

    for c in consumers:
        c.start()

    for p in producers:
        p.join()

    for c in consumers:
        c.join()
