import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.baselines import baseline_2, baseline_3_deadline, baseline_4


def test_deadline_speed_effect_is_zero_in_calm_water():
    path_km = 4000.0
    fixed = baseline_2(path_km, 18.0)
    deadline = baseline_3_deadline(path_km, fixed["hours"])
    assert abs(fixed["fuel_t"] - deadline["fuel_t"]) < 1e-6


def test_weather_baseline_is_not_invented():
    row = baseline_4(None)
    assert row["status"] == "not_estimated"
    assert row["fuel_t"] is None
