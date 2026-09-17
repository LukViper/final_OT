"""
Holtrop--Mennen calm-water resistance (Holtrop and Mennen, 1982; Holtrop, 1984).

The previous in-tree model multiplied the wave-resistance coefficient c1 by 1e-9
because c1 was formed with the block coefficient rather than Holtrop's c7.
This module follows the published regression: ITTC-1957 friction, the 1984
form factor, appendage, bulb, transom and correlation terms, and wave
resistance with the c7 definition of Holtrop (1984).

Applicability is the regression envelope Fn in [0.10, 0.45], not a towing-tank
substitute. Outside that envelope the implementation still returns a number,
but ``in_applicability_range`` is False and callers should not treat it as a
design prediction.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict


KNOT_TO_MS = 0.514444
G = 9.81
RHO_SEA_15C = 1025.0
NU_SEA_15C = 1.19e-6


@dataclass(frozen=True)
class HullParticulars:
    """Principal particulars used by the resistance regression."""

    name: str
    L: float
    B: float
    T: float
    displacement_m3: float
    Cb: float
    Cm: float
    Cwp: float
    Abt: float
    hb: float
    At: float
    Sapp: float
    lcb_percent: float
    Cstern: float
    k2: float
    sfoc_g_per_kwh: float
    propulsive_efficiency: float
    shaft_efficiency: float
    air_area_m2: float = 250.0
    air_drag_coefficient: float = 0.8

    @property
    def Cp(self) -> float:
        return self.Cb / self.Cm


def panamax_container() -> HullParticulars:
    """
    Internally consistent Panamax container-ship particulars.

    Beam is the Panama limit (32.2 m), not the 40 m value previously labelled
    Panamax. Displacement matches Cb * L * B * T.
    """
    L, B, T, Cb, Cm = 280.0, 32.2, 12.5, 0.65, 0.98
    return HullParticulars(
        name="Panamax container ship",
        L=L,
        B=B,
        T=T,
        displacement_m3=Cb * L * B * T,
        Cb=Cb,
        Cm=Cm,
        Cwp=0.78,
        Abt=12.0,
        hb=3.5,
        At=8.0,
        Sapp=90.0,
        lcb_percent=-1.0,
        Cstern=0.0,
        k2=1.5,
        sfoc_g_per_kwh=170.0,
        propulsive_efficiency=0.70,
        shaft_efficiency=0.97,
        air_area_m2=280.0,
    )


def _seawater(temp_c: float) -> tuple[float, float]:
    """Mild density and viscosity adjustment about the 15 C seawater reference."""
    rho = RHO_SEA_15C - 0.25 * (temp_c - 15.0)
    # Vogel-like scaling about the 15 C seawater reference; not a full ITS-90 model.
    nu = NU_SEA_15C * math.exp(1810.0 * (1.0 / (temp_c + 273.15) - 1.0 / 288.15))
    return rho, nu


def wetted_surface(h: HullParticulars) -> float:
    """Holtrop--Mennen wetted-surface regression."""
    return (
        h.L
        * (2.0 * h.T + h.B)
        * math.sqrt(h.Cm)
        * (
            0.453
            + 0.4425 * h.Cb
            - 0.2862 * h.Cm
            - 0.003467 * (h.B / h.T)
            + 0.3696 * h.Cwp
        )
        + 2.38 * h.Abt / h.Cb
    )


def half_entrance_angle_deg(h: HullParticulars, Lr: float) -> float:
    """Holtrop regression for the half-angle of entrance, degrees."""
    exponent = (
        -((h.L / h.B) ** 0.80856)
        * ((1.0 - h.Cwp) ** 0.30484)
        * ((1.0 - h.Cp - 0.0225 * h.lcb_percent) ** 0.6367)
        * ((Lr / h.B) ** 0.34574)
        * ((100.0 * h.displacement_m3 / h.L ** 3) ** 0.16302)
    )
    return 1.0 + 89.0 * math.exp(exponent)


def predict_resistance(
    h: HullParticulars,
    speed_knots: float,
    water_temp_c: float = 15.0,
) -> Dict[str, float]:
    """
    Calm-water resistance and constant-SFOC fuel rate at one speed.

    Returns component forces in newtons and fuel in tonnes per day at the
    corresponding brake power. Air drag is reported separately and is included
    in ``total_resistance_N`` because it is part of the operational power
    demand, but it is not part of the Holtrop hydrodynamic residual.
    """
    if speed_knots <= 0:
        raise ValueError("speed_knots must be positive")

    V = speed_knots * KNOT_TO_MS
    rho, nu = _seawater(water_temp_c)
    Fn = V / math.sqrt(G * h.L)
    Rn = V * h.L / nu
    Cf = 0.075 / (math.log10(Rn) - 2.0) ** 2
    S = wetted_surface(h)

    Lr = h.L * (1.0 - h.Cp + 0.06 * h.Cp * h.lcb_percent / (4.0 * h.Cp - 1.0))
    if Lr <= 0:
        raise ValueError("length of run is non-positive; check Cp and lcb")

    tl = h.T / h.L
    if tl > 0.05:
        c12 = tl ** 0.2228446
    elif tl > 0.02:
        c12 = 48.20 * (tl - 0.02) ** 2.078 + 0.479948
    else:
        c12 = 0.479948
    c13 = 1.0 + 0.003 * h.Cstern
    form_arg = 0.95 - h.Cp
    lcb_arg = 1.0 - h.Cp + 0.0225 * h.lcb_percent
    if form_arg <= 0 or lcb_arg <= 0:
        raise ValueError("form-factor arguments are non-positive; hull is outside the regression")
    one_plus_k1 = c13 * (
        0.93
        + c12
        * (h.B / Lr) ** 0.92497
        * form_arg ** (-0.521448)
        * lcb_arg ** 0.6906
    )

    q = 0.5 * rho * V * V
    Rf = q * S * Cf
    Rv = Rf * one_plus_k1
    Rapp = q * h.Sapp * h.k2 * Cf

    ratio_bl = h.B / h.L
    if ratio_bl < 0.11:
        c7 = 0.229577 * ratio_bl ** (1.0 / 3.0)
    elif ratio_bl <= 0.25:
        c7 = ratio_bl
    else:
        c7 = 0.5 - 0.0625 / ratio_bl

    iE = half_entrance_angle_deg(h, Lr)
    c1 = 2223105.0 * c7 ** 3.78613 * (h.T / h.B) ** 1.07961 * (90.0 - iE) ** (-1.37565)

    if h.Abt <= 0:
        c2 = 1.0
        c3 = 0.0
        Rb = 0.0
    else:
        c3 = 0.56 * h.Abt ** 1.5 / (h.B * h.T * (0.31 * math.sqrt(h.Abt) + h.T - h.hb))
        c2 = math.exp(-1.89 * math.sqrt(max(c3, 0.0)))
        Pb = 0.56 * math.sqrt(h.Abt) / (h.T - 1.5 * h.hb)
        immersion = h.T - h.hb - 0.25 * math.sqrt(h.Abt)
        if Pb <= 0 or immersion <= 0:
            Rb = 0.0
        else:
            Fni = V / math.sqrt(G * immersion + 0.15 * V * V)
            Rb = (
                0.11
                * math.exp(-3.0 * Pb ** (-2))
                * Fni ** 3
                * h.Abt ** 1.5
                * rho
                * G
                / (1.0 + Fni * Fni)
            )

    c5 = 1.0 - 0.8 * h.At / (h.B * h.T * h.Cm) if h.At > 0 else 1.0
    if h.At > 0:
        fnt = V / math.sqrt(2.0 * G * h.At / (h.B + h.B * h.Cwp))
        c6 = 0.2 * (1.0 - 0.2 * fnt) if fnt < 5.0 else 0.0
        Rtr = q * h.At * max(c6, 0.0)
    else:
        Rtr = 0.0

    if h.Cp < 0.80:
        c16 = 8.07981 * h.Cp - 13.8673 * h.Cp ** 2 + 6.984388 * h.Cp ** 3
    else:
        c16 = 1.73014 - 0.7067 * h.Cp
    m1 = (
        0.0140407 * h.L / h.T
        - 1.75254 * h.displacement_m3 ** (1.0 / 3.0) / h.L
        - 4.79323 * h.B / h.L
        - c16
    )
    volume_ratio = h.L ** 3 / h.displacement_m3
    if volume_ratio < 512.0:
        c15 = -1.69385
    elif volume_ratio <= 1726.91:
        c15 = -1.69385 + (h.L / h.displacement_m3 ** (1.0 / 3.0) - 8.0) / 2.36
    else:
        c15 = 0.0

    if h.L / h.B < 12.0:
        lam = 1.446 * h.Cp - 0.03 * h.L / h.B
    else:
        lam = 1.446 * h.Cp - 0.36

    d = -0.9
    m2 = c15 * h.Cp ** 2 * math.exp(-0.1 * Fn ** (-2))
    m4 = c15 * 0.4 * math.exp(-0.034 * Fn ** (-3.29))
    c17 = (
        6919.3
        * h.Cm ** (-1.3346)
        * (h.displacement_m3 / h.L ** 3) ** 2.00977
        * (h.L / h.B - 2.0) ** 1.40692
    )
    m3 = -7.2035 * (h.B / h.L) ** 0.326869 * (h.T / h.B) ** 0.605375

    def _wave(c_front: float, m_front: float) -> float:
        return (
            c_front
            * c2
            * c5
            * h.displacement_m3
            * rho
            * G
            * math.exp(m_front * Fn ** d + m2 * math.cos(lam / Fn ** 2))
        )

    # Low-Fn formula uses m1; the high-Fn formula uses c17 and m3 (Holtrop 1984).
    # The transitional blend follows the usual 0.40--0.55 interpolation.
    if Fn <= 0.40:
        Rw = _wave(c1, m1)
    elif Fn >= 0.55:
        Rw = _wave(c17, m3)
    else:
        rw40 = _wave(c1, m1)
        # Evaluate the high-Fn expression at the same speed; the published
        # interpolation is between the two formulas, not between two speeds.
        rw55_formula = (
            c17
            * c2
            * c5
            * h.displacement_m3
            * rho
            * G
            * math.exp(m3 * Fn ** d + m4 * math.cos(lam / Fn ** 2))
        )
        weight = (Fn - 0.40) / 0.15
        Rw = (1.0 - weight) * rw40 + weight * rw55_formula

    c4 = min(h.T / h.L, 0.04)
    Ca = (
        0.006 * (h.L + 100.0) ** (-0.16)
        - 0.00205
        + 0.003 * math.sqrt(h.L / 7.5) * h.Cb ** 4 * c2 * (0.04 - c4)
    )
    Ra = q * S * Ca
    Rair = 0.5 * 1.225 * V * V * h.air_area_m2 * h.air_drag_coefficient

    hydrodynamic = Rv + Rapp + Rw + Rb + Rtr + Ra
    total = hydrodynamic + Rair
    ehp_kw = total * V / 1000.0
    bhp_kw = ehp_kw / (h.propulsive_efficiency * h.shaft_efficiency)
    fuel_tpd = bhp_kw * h.sfoc_g_per_kwh * 24.0 / 1.0e6

    return {
        "speed_knots": speed_knots,
        "froude": Fn,
        "reynolds": Rn,
        "wetted_surface_m2": S,
        "one_plus_k1": one_plus_k1,
        "c1": c1,
        "c7": c7,
        "entrance_angle_deg": iE,
        "friction_N": Rf,
        "viscous_N": Rv,
        "wave_N": Rw,
        "bulb_N": Rb,
        "appendage_N": Rapp,
        "transom_N": Rtr,
        "correlation_N": Ra,
        "air_N": Rair,
        "hydrodynamic_N": hydrodynamic,
        "total_resistance_N": total,
        "total_resistance_kN": total / 1000.0,
        "ehp_kW": ehp_kw,
        "bhp_kW": bhp_kw,
        "fuel_rate_tpd": fuel_tpd,
        "in_applicability_range": 0.10 <= Fn <= 0.45 and 0.55 <= h.Cp <= 0.85,
    }


def fuel_for_distance(
    h: HullParticulars,
    distance_km: float,
    speed_knots: float,
    water_temp_c: float = 15.0,
) -> float:
    """Tonnes of fuel to cover ``distance_km`` at constant speed through water."""
    res = predict_resistance(h, speed_knots, water_temp_c)
    speed_kmh = speed_knots * 1.852
    hours = distance_km / speed_kmh
    return res["fuel_rate_tpd"] * hours / 24.0
