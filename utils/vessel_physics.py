"""
Calm-water power prediction for the vessels used by the router.

The numerical model is Holtrop and Mennen (1982) with the 1984 coefficient
updates, implemented in ``holtrop_mennen``. Fouling is not applied here: the
hull-fouling module is the only fouling penalty, so the two are not stacked.
"""

from typing import Dict

from utils.holtrop_mennen import (
    HullParticulars,
    fuel_for_distance,
    panamax_container,
    predict_resistance,
)


def _ulcc() -> HullParticulars:
    """Representative ULCC particulars. Not used in the reported experiments."""
    L, B, T, Cb, Cm = 330.0, 58.0, 22.0, 0.83, 0.995
    return HullParticulars(
        name="ULCC tanker",
        L=L,
        B=B,
        T=T,
        displacement_m3=Cb * L * B * T,
        Cb=Cb,
        Cm=Cm,
        Cwp=0.88,
        Abt=20.0,
        hb=6.0,
        At=0.0,
        Sapp=180.0,
        lcb_percent=-2.5,
        Cstern=-10.0,
        k2=1.4,
        sfoc_g_per_kwh=175.0,
        propulsive_efficiency=0.68,
        shaft_efficiency=0.97,
        air_area_m2=400.0,
    )


class VesselPhysics:
    """Backward-compatible wrapper around the Holtrop--Mennen predictor."""

    def __init__(self, vessel_type: str = "Panamax_Container"):
        if vessel_type in ("ULCC_Tanker", "ULCC"):
            self.hull = _ulcc()
        else:
            self.hull = panamax_container()
        self.vessel_type = self.hull.name

    def calculate_resistance(self, speed_knots: float, water_temp: float = 15.0) -> Dict:
        res = predict_resistance(self.hull, speed_knots, water_temp)
        return {
            "speed_knots": speed_knots,
            "total_resistance_kN": res["total_resistance_kN"],
            "effective_power_kW": res["ehp_kW"],
            "brake_power_kW": res["bhp_kW"],
            "fuel_rate_tpd": res["fuel_rate_tpd"],
            "froude": res["froude"],
            "in_applicability_range": res["in_applicability_range"],
            "components_kN": {
                "viscous": res["viscous_N"] / 1000.0,
                "wave_making": res["wave_N"] / 1000.0,
                "bulbous_bow": res["bulb_N"] / 1000.0,
                "appendage": res["appendage_N"] / 1000.0,
                "transom": res["transom_N"] / 1000.0,
                "correlation": res["correlation_N"] / 1000.0,
                "air": res["air_N"] / 1000.0,
            },
        }

    def fuel_consumption(
        self,
        distance_km: float,
        speed_knots: float,
        water_temp: float = 15.0,
        days_since_cleaning: int = 0,
    ) -> float:
        """
        Clean-hull fuel for a distance at constant speed through water.

        ``days_since_cleaning`` is accepted for call-site compatibility and
        ignored. Apply ``HullFoulingModel`` once, at voyage level.
        """
        del days_since_cleaning
        return fuel_for_distance(self.hull, distance_km, speed_knots, water_temp)


vessel_physics = VesselPhysics("Panamax_Container")


if __name__ == "__main__":
    vp = VesselPhysics()
    print(vp.vessel_type)
    for speed in (12, 16, 18, 20, 22, 24):
        res = vp.calculate_resistance(speed)
        print(
            f"{speed:2d} kn  {res['total_resistance_kN']:8.1f} kN  "
            f"{res['brake_power_kW']/1000:6.2f} MW  {res['fuel_rate_tpd']:6.1f} t/day"
        )
