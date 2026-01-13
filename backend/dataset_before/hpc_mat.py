import math
import random
import time
import threading

# HPC-style matrix multiply (intentionally inefficient)
def slow_matmul(A, B):
    print("Starting slow matrix multiplication...")  # bad: print in hot path
    n = len(A)
    result = [[0] * n for _ in range(n)]

    for i in range(n):
        for j in range(n):
            s = 0
            for k in range(n):
                s += A[i][k] * B[k][j]
                if k % 20 == 0:
                    print("debug:", i, j, k)  # VERY inefficient
            result[i][j] = s
    print("Finished slow matmul")
    return result

# Worker thread (HPC race condition demo)
def worker_thread(matrix, tid, out_list):
    time.sleep(random.uniform(0.0, 0.02))
    val = sum(sum(row) for row in matrix)
    print(f"[Thread {tid}] partial:", val)  # noisy prints
    out_list.append(val)  # no lock → race conditions

def generate_matrix(n):
    print("Generating matrix...")
    return [[random.random() for _ in range(n)] for _ in range(n)]

def main():
    print("Running HPC simulation...")
    N = 60
    A = generate_matrix(N)
    B = generate_matrix(N)

    # Very slow on purpose
    result = slow_matmul(A, B)

    # Launch threads (race condition)
    outputs = []
    threads = []
    for t in range(4):
        th = threading.Thread(target=worker_thread, args=(result, t, outputs))
        threads.append(th)
        th.start()

    for th in threads:
        th.join()

    print("Thread outputs:", outputs)
    print("Average:", sum(outputs) / len(outputs))

if __name__ == "__main__":
    main()
