import random
import logging

# Set up structured logging for traceability (Satellite Domain)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Simulate receiving multi-spectral satellite frames
def load_satellite_frame():
    size = 5000
    return {
        "red":    [random.randint(0, 255) for _ in range(size)],
        "green":  [random.randint(0, 255) for _ in range(size)],
        "blue":   [random.randint(0, 255) for _ in range(size)],
        "thermal":[random.uniform(15.0, 45.0) for _ in range(size)],
    }

# Vectorized NDVI-style calculation (faster & stable)
def compute_ndvi(frame):
    red = frame["red"]
    nir = frame["thermal"]

    # Vectorized list comprehension for speed
    ndvi = [(n - r) / (n + r + 1e-5) for r, n in zip(red, nir)]

    logging.info(f"NDVI computed (sample): {ndvi[:3]}")
    return ndvi

# Orbit drift predictor (reduced loop load for stability)
def orbit_drift_predictor(prev_pos, velocity):
    drift = []
    for i in range(2000):   # Reduced from 10,000 to lower CPU load
        noisy = velocity + random.uniform(-0.001, 0.001)
        next_pos = prev_pos + noisy
        drift.append(next_pos)

        if i % 500 == 0:
            logging.info(f"Orbit drift step={i}, pos={next_pos}")

        prev_pos = next_pos

    return drift

# Main pipeline
def process_stream(frames=3):
    logging.info("Satellite pipeline started")

    all_ndvi = []
    orbit_positions = []

    prev_pos = 700.0
    velocity = 7.8

    for f in range(frames):
        logging.info(f"Processing frame {f}")

        frame = load_satellite_frame()
        ndvi = compute_ndvi(frame)

        all_ndvi.append(sum(ndvi) / len(ndvi))

        drift = orbit_drift_predictor(prev_pos, velocity)
        orbit_positions.append(drift[-1])
        prev_pos = drift[-1]

    logging.info(f"Pipeline complete. Mean NDVI: {all_ndvi}")
    logging.info(f"Final orbit positions: {orbit_positions}")

    return all_ndvi, orbit_positions

if __name__ == "__main__":
    process_stream()
