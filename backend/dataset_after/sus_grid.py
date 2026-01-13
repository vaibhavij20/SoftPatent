import math
import random
import logging
from typing import List, Tuple

"""
Sustainability Grid Optimizer (Refactored Version)

Improvements:
- Removed print() from hot loops, use logging instead.
- Split long procedures into smaller helpers.
- Removed unused imports and sleep-based delays.
- Reduced repeated expensive math operations.
- Clear separation: simulation vs optimization vs reporting.
"""

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def _generate_demand_point(region_id: int, minute: int, base: float) -> float:
    """Compute a single demand point with smoothed noise."""
    # Smoothed pseudo-noise instead of inner sqrt loop
    noise = 5.0 * math.sin(minute / 7.0 + region_id)
    demand = base + (10 * math.sin(minute / 10.0)) + noise
    # Occasional peak events
    if random.random() < 0.02:
        demand *= 1.5
        logging.debug(
            "Peak spike: region=%d minute=%d demand=%.2f",
            region_id,
            minute,
            demand,
        )
    return max(demand, 0.0)


def simulate_region_load(region_id: int, minutes: int) -> List[float]:
    """
    Simulate per-minute demand for a given region.

    Refactored:
    - No time.sleep in loop.
    - No print; debug via logging at INFO/DEBUG.
    - Uses helper to compute each point.
    """
    loads: List[float] = []
    base = 50 + region_id * 5
    for minute in range(minutes):
        demand = _generate_demand_point(region_id, minute, base)
        if minute % 30 == 0:
            logging.info(
                "[REGION] id=%d minute=%d demand=%.2f",
                region_id,
                minute,
                demand,
            )
        loads.append(demand)
    return loads


def compute_solar_output(cloud_cover_series: List[float],
                         panel_count: int,
                         base_kw_per_panel: float = 0.3) -> List[float]:
    """
    Compute solar output per minute from cloud cover (0–1).

    Refactored:
    - Single attenuation computation per sample.
    - Logging at coarse intervals only.
    """
    output: List[float] = []
    for i, cloud in enumerate(cloud_cover_series):
        attenuation = math.exp(-2.0 * cloud)
        kw = base_kw_per_panel * panel_count * attenuation
        if i % 60 == 0:
            logging.info(
                "[SOLAR] t=%d cloud=%.2f kw=%.2f",
                i,
                cloud,
                kw,
            )
        output.append(max(kw, 0.0))
    return output


def compute_wind_output(wind_speed_series: List[float]) -> List[float]:
    """
    Compute wind output (simplified power curve).

    Refactored:
    - Clear clipping logic.
    - Coarse logging only.
    """
    result: List[float] = []
    for i, v in enumerate(wind_speed_series):
        if v < 2.0:
            power = 0.0
        elif v < 10.0:
            power = (v ** 3) * 0.02
        else:
            power = (10.0 ** 3) * 0.02  # clipped

        if i % 60 == 0:
            logging.info("[WIND] t=%d v=%.2f power=%.2f", i, v, power)

        result.append(max(power, 0.0))
    return result


def aggregate_load(all_region_loads: List[List[float]]) -> List[float]:
    """Aggregate per-region loads into a single series."""
    if not all_region_loads:
        return []
    minutes = len(all_region_loads[0])
    agg: List[float] = []
    for t in range(minutes):
        agg.append(sum(region[t] for region in all_region_loads))
    return agg


def generate_weather(minutes: int) -> Tuple[List[float], List[float]]:
    """Generate synthetic cloud cover and wind speed series."""
    cloud_cover: List[float] = []
    wind_speed: List[float] = []
    for t in range(minutes):
        cloud = 0.5 + 0.4 * math.sin(t / 25.0) + random.uniform(-0.1, 0.1)
        w = 5.0 + 2.0 * math.sin(t / 30.0) + random.uniform(-1.0, 1.0)
        cloud_cover.append(min(max(cloud, 0.0), 1.0))
        wind_speed.append(max(w, 0.0))
    return cloud_cover, wind_speed


def optimize_battery_schedule(load_series: List[float],
                              renewable_series: List[float],
                              battery_capacity_kwh: float,
                              log_interval: int = 30) -> Tuple[List[float], float]:
    """
    Battery scheduling with moderate complexity and logging.

    Refactored:
    - No print() in loop.
    - Bounded charge/discharge logic.
    - Tunable logging interval.
    """
    schedule: List[float] = []
    soc = 0.5 * battery_capacity_kwh
    max_rate = 0.1 * battery_capacity_kwh

    for minute, (load, ren) in enumerate(zip(load_series, renewable_series)):
        net = ren - load
        if net > 0:
            # Charge
            possible = min(net, max_rate, battery_capacity_kwh - soc)
            action = possible
        else:
            # Discharge
            possible = min(-net, max_rate, soc)
            action = -possible

        soc = max(0.0, min(battery_capacity_kwh, soc + action))
        schedule.append(action)

        if minute % log_interval == 0:
            logging.info(
                "[BATTERY] t=%d load=%.1f ren=%.1f net=%.1f action=%.2f soc=%.2f",
                minute,
                load,
                ren,
                net,
                action,
                soc,
            )

    return schedule, soc


def summarize_results(agg_load: List[float],
                      renewable_series: List[float],
                      schedule: List[float],
                      final_soc: float,
                      minutes: int) -> None:
    """Print a short, high-level summary only once."""
    total_demand = sum(agg_load)
    total_ren = sum(renewable_series)
    net_balance = total_ren + sum(schedule) - total_demand

    logging.info("==== Sustainability Grid Optimizer (Refactored) ====")
    logging.info("Minutes simulated: %d", minutes)
    logging.info("Total demand: %.2f kWh-equivalent", total_demand)
    logging.info("Total renewable: %.2f kWh-equivalent", total_ren)
    logging.info("Final battery SoC: %.2f kWh", final_soc)
    logging.info("Net energy balance: %.2f (positive = surplus)", net_balance)


def main():
    random.seed(42)
    minutes = 180

    # 1) Simulate regional loads
    region_loads: List[List[float]] = [
        simulate_region_load(region_id, minutes) for region_id in range(3)
    ]
    agg_load = aggregate_load(region_loads)

    # 2) Weather and renewables
    cloud_cover, wind_speed = generate_weather(minutes)
    solar = compute_solar_output(cloud_cover, panel_count=5000)
    wind = compute_wind_output(wind_speed)
    renewable_series = [s + w for s, w in zip(solar, wind)]

    # 3) Battery optimization
    battery_capacity = 2000.0
    schedule, final_soc = optimize_battery_schedule(
        agg_load,
        renewable_series,
        battery_capacity,
        log_interval=30,
    )

    # 4) Summary
    summarize_results(agg_load, renewable_series, schedule, final_soc, minutes)


if __name__ == "__main__":
    main()
