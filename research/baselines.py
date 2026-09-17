"""
Four nested fuel baselines.

Baseline 4 is implemented but returns status 'not_estimated' unless a frozen
weather cache is passed in. No live weather call is made. The calm-water
resistance routine is imported and not modified.

Under calm water, a convex fuel-speed curve, and a single arrival deadline,
the fuel-minimizing speed on a fixed path is the constant speed that meets
the deadline. A speed 'saving' then exists only if the comparison speed is
faster than that deadline speed. That is a commercial comparison, not a
weather-routing result. SINTEF's speed lever (EcoRouter blog) is a
weather-dependent throttle schedule at a fixed arrival; it is not reproduced
here, because no hindcast is in the cache.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.holtrop_mennen import panamax_container, predict_resistance  # noqa: E402

CO2_PER_TONNE = 3.114
BUNKER_USD_PER_T = 600.0
CHARTER_USD_PER_DAY = 25000.0
SERVICE_SPEED_KN = 18.0
HULL = panamax_container()


def fuel_tonnes(distance_km: float, speed_knots: float) -> float:
    if speed_knots <= 0 or distance_km < 0:
        raise ValueError("distance and speed must be positive")
    rate = predict_resistance(HULL, speed_knots)["fuel_rate_tpd"]
    hours = distance_km / (speed_knots * 1.852)
    return rate * hours / 24.0


def voyage_record(distance_km: float, speed_knots: float, label: str) -> dict:
    fuel = fuel_tonnes(distance_km, speed_knots)
    hours = distance_km / (speed_knots * 1.852)
    return {
        "label": label,
        "distance_km": distance_km,
        "speed_knots": speed_knots,
        "hours": hours,
        "fuel_t": fuel,
        "co2_t": fuel * CO2_PER_TONNE,
        "scenario_cost_usd": fuel * BUNKER_USD_PER_T + (hours / 24.0) * CHARTER_USD_PER_DAY,
    }


def baseline_1(great_circle_km: float, speed_knots: float = SERVICE_SPEED_KN) -> dict:
    """Infeasible sphere path, fixed service speed, calm water."""
    row = voyage_record(great_circle_km, speed_knots, "B1_great_circle_fixed_speed")
    row["feasible"] = False
    row["weather"] = "calm"
    return row


def baseline_2(mesh_distance_km: float, speed_knots: float = SERVICE_SPEED_KN) -> dict:
    """Shortest coastline-masked path, same speed, calm water."""
    row = voyage_record(mesh_distance_km, speed_knots, "B2_mesh_fixed_speed")
    row["feasible"] = True
    row["weather"] = "calm"
    return row


def baseline_3_commercial(mesh_distance_km: float, speed_min=12, speed_max=24) -> dict:
    """
    Same path. Speed minimizes bunker plus charter, with no arrival window.
    This is not the SINTEF lever.
    """
    best = None
    for speed in range(speed_min, speed_max + 1):
        row = voyage_record(mesh_distance_km, speed, "B3_commercial_speed")
        if best is None or row["scenario_cost_usd"] < best["scenario_cost_usd"]:
            best = row
    best["feasible"] = True
    best["weather"] = "calm"
    best["arrival_constraint"] = None
    return best


def baseline_3_deadline(mesh_distance_km: float, deadline_hours: float) -> dict:
    """Constant speed that meets the deadline. Calm water, so it is unique."""
    if deadline_hours <= 0:
        raise ValueError("deadline_hours must be positive")
    speed = mesh_distance_km / deadline_hours / 1.852
    row = voyage_record(mesh_distance_km, speed, "B3_deadline_speed")
    row["feasible"] = True
    row["weather"] = "calm"
    row["arrival_constraint_hours"] = deadline_hours
    return row


def baseline_4(weather_cache: dict | None) -> dict:
    """
    Time-dependent weather routing. Not estimated without a frozen cache.
    Returning a number here would invent a weather saving.
    """
    if not weather_cache:
        return {
            "label": "B4_weather",
            "status": "not_estimated",
            "reason": "No frozen wind/wave/current cache. No live API call is made.",
            "fuel_t": None,
            "co2_t": None,
        }
    raise NotImplementedError("A weather cache was supplied, but the hindcast solver is not enabled in this revision.")


def network_inflation(b1: dict, b2: dict) -> dict:
    """
    How much the great-circle baseline understates a feasible voyage.
    Positive means the realistic path uses more fuel than the sphere path
    at the same speed. That quantity is not a saving.
    """
    return {
        "fuel_increase_t": b2["fuel_t"] - b1["fuel_t"],
        "fuel_ratio": b2["fuel_t"] / b1["fuel_t"],
        "distance_ratio": b2["distance_km"] / b1["distance_km"],
    }


def commercial_speed_delta(b2: dict, b3: dict) -> dict:
    return {
        "fuel_change_t": b2["fuel_t"] - b3["fuel_t"],
        "note": "Difference against a cheaper speed with no arrival window. Not a weather-routing saving.",
    }
