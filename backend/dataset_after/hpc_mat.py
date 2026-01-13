"""
High-Performance Matrix Simulation (HPC Demo)
Refactored for:
- Structured logging (no print())
- Thread-safe writing using Lock
- Removed unused imports
- More predictable behavior for profiling/benchmarking
"""

import time
import threading
import logging
import random

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# -------------------------------
# Slow matrix multiplication (intentionally slow)
# -------------------------------
def slow_matmul(A, B):
    """Very slow O(n^3) matrix multiplication for benchmarking."""
    n = len(A)
    result = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            s = 0
            for k in range(n):
                s += A[i][k] * B[k][j]
            result[i][j] = s
    return result


# -------------------------------
# Worker thread (safe)
# -------------------------------
def worker_thread(result_matrix, t_id, outputs, lock):
    """
    Worker thread that computes a random summary value
    from the matrix. Uses thread-safe writes.
    """
    rnd = random.uniform(0, 1)
    partial = sum(sum(row) for row in result_matrix) * rnd

    with lock:
        outputs.append(partial)

    logging.debug(f"Thread {t_id} finished partial={partial}")


# -------------------------------
# Main pipeline
# -------------------------------
def main():
    # Create small matrices for simulation
    N = 40
    A = [[random.uniform(0, 1) for _ in range(N)] for _ in range(N)]
    B = [[random.uniform(0, 1) for _ in range(N)] for _ in range(N)]

    logging.info("Starting slow matrix multiply...")
    start = time.time()

    # Very slow (intentionally)
    result = slow_matmul(A, B)

    duration = time.time() - start
    logging.info(f"Matrix multiply completed in {duration:.3f} sec")

    # Thread work
    outputs = []
    threads = []
    lock = threading.Lock()

    logging.info("Launching worker threads...")
    for t in range(4):
        th = threading.Thread(target=worker_thread, args=(result, t, outputs, lock))
        threads.append(th)
        th.start()

    for t in threads:
        t.join()

    avg_val = sum(outputs) / len(outputs) if outputs else 0.0
    logging.info(f"Average aggregated partial: {avg_val:.5f}")

    return {
        "duration_sec": duration,
        "num_threads": 4,
        "avg_partial": avg_val,
        "matrix_size": N
    }


if __name__ == "__main__":
    out = main()
    logging.info(out)
