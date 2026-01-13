import time
import math
import logging

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# ---------------------------------------------------------------------
# Load noisy data
# ---------------------------------------------------------------------
def load_data():
    logging.info("Loading data...")
    values = []
    for i in range(1000):
        time.sleep(0.0008)
        values.append((i * 0.5) % 50 + abs(math.sin(i)))
    logging.info("Data loaded")
    return values


# ---------------------------------------------------------------------
# Normalize dataset
# ---------------------------------------------------------------------
def normalize_values(values):
    logging.info("Normalizing values...")
    max_val = max(values) or 1
    return [v / max_val for v in values]


# ---------------------------------------------------------------------
# Compute statistics (clean — no print)
# ---------------------------------------------------------------------
def compute_statistics(values):
    logging.info("Computing statistics...")
    if not values:
        return {}

    total = sum(values)
    mean = total / len(values)

    var = sum((v - mean) ** 2 for v in values) / len(values)
    std = math.sqrt(var)

    return {
        "mean": mean,
        "stddev": std,
        "min": min(values),
        "max": max(values),
    }


# ---------------------------------------------------------------------
# Heavy, inefficient processing — now cleaned
# ---------------------------------------------------------------------
def heavy_processing(values):
    logging.info("Starting heavy processing...")
    results = []

    for v in values:
        # Removed unnecessary print
        time.sleep(0.0007)
        results.append(math.sin(v) + math.sqrt(abs(v)))

    logging.info("Heavy processing complete")
    return results


# ---------------------------------------------------------------------
# Pipeline orchestrator (clean!)
# ---------------------------------------------------------------------
def pipeline():
    logging.info("Pipeline started")

    data = load_data()
    normalized = normalize_values(data)
    stats = compute_statistics(normalized)
    results = heavy_processing(normalized)

    logging.info("Pipeline finished")
    return {
        "stats": stats,
        "result_sample": results[:5],
        "count": len(results),
    }


if __name__ == "__main__":
    output = pipeline()
    logging.info(output)
