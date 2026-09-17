#!/usr/bin/env python3
"""
Reproducible numerical study for the accompanying manuscript.

No external weather API is called. Every reported quantity is written to
``paper/results.json`` and ``paper/numbers.tex``.
"""

from __future__ import annotations

import contextlib
import io
import itertools
import json
import math
import random
import sys
import time
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from utils.holtrop_mennen import panamax_container, predict_resistance  # noqa: E402
from utils.hull_fouling import HullFoulingModel  # noqa: E402
from utils.ocean_currents import OceanCurrentModel  # noqa: E402
from utils.route_calculator import ShippingRouteOptimizer  # noqa: E402

PAPER = ROOT / "paper"
FIG = PAPER / "figures"
CO2_PER_TONNE_FUEL = 3.114  # IMO residual-fuel inventory factor
SERVICE_SPEED_KN = 18.0
GA_POPULATION = 24
GA_GENERATIONS = 40
GA_SEEDS = 20
BUNKER_USD_PER_T = 600.0  # scenario price, not a market quotation
CHARTER_USD_PER_DAY = 25000.0  # scenario hire, not a fixture

# Open-path instances: origin, destination, mandatory intermediate ports.
INSTANCES = [
    ("Singapore", "Tokyo", ["Hong_Kong", "Shanghai", "Busan", "Yokohama"]),
    ("Mumbai", "Shanghai", ["Colombo", "Singapore", "Hong_Kong", "Shenzhen"]),
    ("Jebel_Ali", "Singapore", ["Salalah", "Mumbai", "Colombo"]),
    ("Jakarta", "Yokohama", ["Singapore", "Manila", "Hong_Kong", "Busan"]),
    ("Melbourne", "Busan", ["Jakarta", "Singapore", "Manila", "Shanghai"]),
    ("Perth", "Tokyo", ["Jakarta", "Singapore", "Hong_Kong", "Yokohama"]),
    (
        "Mumbai",
        "Tokyo",
        ["Colombo", "Singapore", "Manila", "Hong_Kong", "Shanghai", "Busan"],
    ),
    (
        "Jebel_Ali",
        "Yokohama",
        ["Salalah", "Mumbai", "Colombo", "Singapore", "Hong_Kong", "Shanghai", "Busan"],
    ),
]


def tex_num(value, digits=1):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return f"{value:,}".replace(",", "{,}")
    return f"{value:.{digits}f}"


class Study:
    def __init__(self):
        self.hull = panamax_container()
        self.fouling = HullFoulingModel()
        self.currents = OceanCurrentModel()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.opt = ShippingRouteOptimizer(seed=42)
        self.graph = self.opt.sea_graph

    def great_circle(self, a, b):
        return self.opt._calculate_distance_km(self.opt.PORT_LOCATIONS[a], self.opt.PORT_LOCATIONS[b])

    def lane_distance(self, a, b):
        _, dist = self.opt.port_paths.get((a, b), (None, math.inf))
        return dist

    def path_coords(self, a, b):
        nodes, dist = self.opt.port_paths.get((a, b), (None, math.inf))
        if not nodes or not math.isfinite(dist):
            return None, math.inf
        return self.opt._nodes_to_latlon(nodes), dist

    def sequence_distance(self, seq):
        total = 0.0
        for u, v in zip(seq, seq[1:]):
            d = self.lane_distance(u, v)
            if not math.isfinite(d):
                return math.inf
            total += d
        return total

    def sequence_fuel(self, seq, speed_knots, month):
        """Calm-water Holtrop fuel with along-track current, clean hull."""
        fuel = 0.0
        for u, v in zip(seq, seq[1:]):
            coords, dist = self.path_coords(u, v)
            if coords is None:
                return math.inf
            for p, q in zip(coords, coords[1:]):
                seg = self.opt._haversine(p[0], p[1], q[0], q[1])
                if seg <= 0:
                    continue
                bearing = self.opt._bearing_deg(p[0], p[1], q[0], q[1])
                mid = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
                current = self.currents.along_track(mid[0], mid[1], month, bearing)
                sog = max(speed_knots + current["along_knots"], 1.0)
                calm = predict_resistance(self.hull, speed_knots)["fuel_rate_tpd"]
                hours = seg / (sog * 1.852)
                fuel += calm * hours / 24.0
        return fuel

    def network(self):
        g = self.graph
        sea_nodes = [n for n in g.nodes if str(n).startswith("sea_")]
        degrees = [d for n, d in g.degree if str(n).startswith("sea_")]
        components = nx.number_connected_components(g)
        ports = list(self.opt.PORT_LOCATIONS)
        port_component = nx.node_connected_component(g, ports[0])
        sea_in_port_component = sum(1 for n in port_component if str(n).startswith("sea_"))
        disconnected = []
        for a, b in itertools.permutations(ports, 2):
            if not math.isfinite(self.lane_distance(a, b)):
                disconnected.append([a, b])
        return {
            "n_ports": len(ports),
            "n_sea_nodes": len(sea_nodes),
            "n_edges": g.number_of_edges(),
            "n_components": components,
            "sea_nodes_in_port_component": sea_in_port_component,
            "mean_sea_degree": sum(degrees) / len(degrees),
            "port_connection_threshold_km": self.opt.PORT_CONNECTION_THRESHOLD_KM,
            "n_disconnected_ordered_pairs": len(disconnected),
            "disconnected_pairs": disconnected,
        }

    def path_comparison(self):
        ports = list(self.opt.PORT_LOCATIONS)
        rows = []
        astar_equal = 0
        compared = 0
        t_astar = 0.0
        t_dij = 0.0
        # One Dijkstra tree per origin, compared with the cached A* distances.
        for origin in ports:
            others = [p for p in ports if p != origin]
            t0 = time.perf_counter()
            try:
                lengths = nx.single_source_dijkstra_path_length(self.graph, origin, weight="weight")
            except nx.NodeNotFound:
                lengths = {}
            t_dij += time.perf_counter() - t0
            t1 = time.perf_counter()
            for dest in others:
                # Recompute A* so the timing is not the cache.
                self.opt._astar_between.cache_clear()
                _, astar_d = self.opt._astar_between(origin, dest)
            t_astar += time.perf_counter() - t1
            for dest in others:
                _, astar_d = self.opt.port_paths[(origin, dest)]
                gc = self.great_circle(origin, dest)
                dij = lengths.get(dest, math.inf)
                both = math.isfinite(astar_d) and math.isfinite(dij)
                if both:
                    compared += 1
                    if abs(astar_d - dij) < 1e-6:
                        astar_equal += 1
                rows.append(
                    {
                        "origin": origin,
                        "destination": dest,
                        "great_circle_km": None if not math.isfinite(gc) else round(gc, 3),
                        "lane_km": None if not math.isfinite(astar_d) else round(astar_d, 3),
                        "dijkstra_km": None if not math.isfinite(dij) else round(dij, 3),
                        "detour_ratio": None
                        if not (math.isfinite(astar_d) and gc > 0)
                        else round(astar_d / gc, 4),
                    }
                )
        finite = [r for r in rows if r["detour_ratio"] is not None]
        ratios = [r["detour_ratio"] for r in finite]
        ratios_sorted = sorted(ratios)
        return {
            "n_ordered_pairs": len(rows),
            "n_connected": len(finite),
            "astar_dijkstra_matches": astar_equal,
            "astar_dijkstra_compared": compared,
            "mean_detour": sum(ratios) / len(ratios),
            "median_detour": ratios_sorted[len(ratios_sorted) // 2],
            "max_detour": max(ratios),
            "min_detour": min(ratios),
            "mean_lane_km": sum(r["lane_km"] for r in finite) / len(finite),
            "mean_gc_km": sum(r["great_circle_km"] for r in finite) / len(finite),
            "seconds_astar_recomputed": t_astar,
            "seconds_dijkstra": t_dij,
            "rows": rows,
        }

    def _order_crossover(self, a, b, rng):
        child = self.opt._crossover(["S"] + a + ["T"], ["S"] + b + ["T"], a, rng.randrange(2**31))
        return child[1:-1]

    def _ga(self, hubs, cost_fn, seed):
        rng = random.Random(seed)
        pop = [hubs[:]]
        while len(pop) < GA_POPULATION:
            trial = hubs[:]
            rng.shuffle(trial)
            pop.append(trial)
        evaluations = 0
        best = None
        best_cost = math.inf

        def evaluate(individual):
            nonlocal evaluations, best, best_cost
            evaluations += 1
            value = cost_fn(individual)
            if value < best_cost:
                best = individual[:]
                best_cost = value
            return value

        scores = [(evaluate(ind), ind) for ind in pop]
        for gen in range(GA_GENERATIONS):
            scores.sort(key=lambda item: item[0])
            elite = [ind[:] for _, ind in scores[:2]]
            children = elite[:]
            while len(children) < GA_POPULATION:
                contenders = [scores[rng.randrange(len(scores))][1] for _ in range(3)]
                parent_a = min(contenders, key=cost_fn)
                contenders = [scores[rng.randrange(len(scores))][1] for _ in range(3)]
                parent_b = min(contenders, key=cost_fn)
                child = self._order_crossover(parent_a, parent_b, rng)
                if rng.random() < 0.3 and len(child) >= 2:
                    i, j = rng.sample(range(len(child)), 2)
                    child[i], child[j] = child[j], child[i]
                children.append(child)
            pop = children
            scores = [(evaluate(ind), ind) for ind in pop]
            scores.sort(key=lambda item: item[0])
        return {"order": ["origin"] + best + ["destination"], "cost": best_cost, "evaluations": evaluations}

    def _exact(self, hubs, cost_fn):
        best = None
        best_cost = math.inf
        evaluations = 0
        for perm in itertools.permutations(hubs):
            evaluations += 1
            value = cost_fn(list(perm))
            if value < best_cost:
                best_cost = value
                best = list(perm)
        return {"order": best, "cost": best_cost, "evaluations": evaluations}

    def _nearest_insertion(self, hubs, cost_fn, start, end):
        """Open-path nearest insertion on the metric closure. One construction, not a search."""
        remaining = hubs[:]
        route = []
        while remaining:
            best_increase = math.inf
            best_hub = None
            best_pos = None
            for hub in remaining:
                for pos in range(len(route) + 1):
                    trial = route[:pos] + [hub] + route[pos:]
                    increase = cost_fn(trial)
                    if increase < best_increase:
                        best_increase = increase
                        best_hub = hub
                        best_pos = pos
            route = route[:best_pos] + [best_hub] + route[best_pos:]
            remaining.remove(best_hub)
        return {"order": route, "cost": cost_fn(route)}

    def sequencing(self):
        records = []
        for origin, dest, hubs in INSTANCES:
            def distance_cost(order, origin=origin, dest=dest):
                return self.sequence_distance([origin] + order + [dest])

            def fuel_cost(order, origin=origin, dest=dest):
                return self.sequence_fuel([origin] + order + [dest], SERVICE_SPEED_KN, 1)

            exact_d = self._exact(hubs, distance_cost)
            exact_f = self._exact(hubs, fuel_cost)
            insertion = self._nearest_insertion(hubs, distance_cost, origin, dest)
            gaps = []
            evals = []
            successes = 0
            for seed in range(GA_SEEDS):
                ga = self._ga(hubs, distance_cost, seed)
                gap = (ga["cost"] - exact_d["cost"]) / exact_d["cost"] * 100
                gaps.append(gap)
                evals.append(ga["evaluations"])
                if abs(ga["cost"] - exact_d["cost"]) < 1e-6:
                    successes += 1
            listed = distance_cost(hubs)
            reversed_km = distance_cost(list(reversed(hubs)))
            records.append(
                {
                    "origin": origin,
                    "destination": dest,
                    "n_hubs": len(hubs),
                    "n_permutations": math.factorial(len(hubs)),
                    "listed_order_km": round(listed, 1),
                    "exact_distance_km": round(exact_d["cost"], 1),
                    "exact_order": [origin] + exact_d["order"] + [dest],
                    "insertion_km": round(insertion["cost"], 1),
                    "insertion_gap_pct": round((insertion["cost"] - exact_d["cost"]) / exact_d["cost"] * 100, 3),
                    "listed_gap_pct": round((listed - exact_d["cost"]) / exact_d["cost"] * 100, 3),
                    "reversed_gap_pct": round((reversed_km - exact_d["cost"]) / exact_d["cost"] * 100, 3),
                    "ga_mean_gap_pct": round(sum(gaps) / len(gaps), 4),
                    "ga_max_gap_pct": round(max(gaps), 4),
                    "ga_success_rate": successes / GA_SEEDS,
                    "ga_evaluations": evals[0],
                    "exact_distance_order": exact_d["order"],
                    "exact_fuel_order": exact_f["order"],
                    "orders_differ_under_current": exact_d["order"] != exact_f["order"],
                    "exact_fuel_t": round(exact_f["cost"], 2),
                    "fuel_of_distance_optimum_t": round(fuel_cost(exact_d["order"]), 2),
                }
            )
        return {
            "service_speed_kn": SERVICE_SPEED_KN,
            "ga_population": GA_POPULATION,
            "ga_generations": GA_GENERATIONS,
            "ga_seeds": GA_SEEDS,
            "month": 1,
            "instances": records,
        }

    def resistance_curve(self):
        rows = []
        for speed in range(12, 25):
            res = predict_resistance(self.hull, speed)
            rows.append(
                {
                    "speed_knots": speed,
                    "froude": round(res["froude"], 4),
                    "resistance_kN": round(res["total_resistance_kN"], 2),
                    "viscous_kN": round(res["viscous_N"] / 1000, 2),
                    "wave_kN": round(res["wave_N"] / 1000, 2),
                    "other_kN": round(
                        (res["total_resistance_N"] - res["viscous_N"] - res["wave_N"]) / 1000, 2
                    ),
                    "bhp_MW": round(res["bhp_kW"] / 1000, 3),
                    "fuel_tpd": round(res["fuel_rate_tpd"], 2),
                    "in_range": res["in_applicability_range"],
                }
            )
        return {
            "particulars": {
                "name": self.hull.name,
                "L_m": self.hull.L,
                "B_m": self.hull.B,
                "T_m": self.hull.T,
                "displacement_m3": round(self.hull.displacement_m3, 1),
                "Cb": self.hull.Cb,
                "Cp": round(self.hull.Cp, 4),
                "Cm": self.hull.Cm,
                "Cwp": self.hull.Cwp,
                "S_m2": round(predict_resistance(self.hull, 18)["wetted_surface_m2"], 1),
                "sfoc_g_per_kwh": self.hull.sfoc_g_per_kwh,
                "propulsive_efficiency": self.hull.propulsive_efficiency,
                "one_plus_k1": round(predict_resistance(self.hull, 18)["one_plus_k1"], 3),
            },
            "curve": rows,
        }

    def fouling_curve(self):
        rows = []
        for days in (0, 30, 90, 180, 270, 365):
            result = self.fouling.calculate_fouling_penalty(days, [28.0], [35.0])
            rows.append(
                {
                    "days": days,
                    "multiplier": result["fuel_multiplier"],
                    "penalty_percent": result["total_penalty_percent"],
                    "level": result["fouling_level"],
                }
            )
        return {"sst_c": 28.0, "salinity_psu": 35.0, "rows": rows}

    def corridors(self):
        pairs = [
            ("Singapore", "Tokyo"),
            ("Hong_Kong", "Yokohama"),
            ("Mumbai", "Singapore"),
            ("Shanghai", "Singapore"),
            ("Jakarta", "Melbourne"),
        ]
        rows = []
        for origin, dest in pairs:
            coords, dist = self.path_coords(origin, dest)
            gc = self.great_circle(origin, dest)
            for month, label in ((1, "January"), (7, "July")):
                fuel = self.sequence_fuel([origin, dest], SERVICE_SPEED_KN, month)
                calm_rate = predict_resistance(self.hull, SERVICE_SPEED_KN)["fuel_rate_tpd"]
                calm = calm_rate * (dist / (SERVICE_SPEED_KN * 1.852)) / 24.0
                rows.append(
                    {
                        "origin": origin,
                        "destination": dest,
                        "month": label,
                        "lane_km": round(dist, 1),
                        "great_circle_km": round(gc, 1),
                        "calm_fuel_t": round(calm, 2),
                        "current_fuel_t": round(fuel, 2),
                        "current_delta_pct": round((calm - fuel) / calm * 100, 2),
                        "co2_t": round(fuel * CO2_PER_TONNE_FUEL, 1),
                    }
                )
        return {"speed_knots": SERVICE_SPEED_KN, "rows": rows}

    def speed_tradeoff(self):
        origin, dest = "Singapore", "Tokyo"
        _, dist = self.path_coords(origin, dest)
        rows = []
        for speed in range(12, 25):
            fuel = self.sequence_fuel([origin, dest], speed, 1)
            hours = 0.0
            coords, _ = self.path_coords(origin, dest)
            for p, q in zip(coords, coords[1:]):
                seg = self.opt._haversine(p[0], p[1], q[0], q[1])
                bearing = self.opt._bearing_deg(p[0], p[1], q[0], q[1])
                current = self.currents.along_track(
                    (p[0] + q[0]) / 2, (p[1] + q[1]) / 2, 1, bearing
                )
                sog = max(speed + current["along_knots"], 1.0)
                hours += seg / (sog * 1.852)
            days = hours / 24.0
            fouled = fuel * self.fouling.calculate_fouling_penalty(90, [28.0], [35.0])["fuel_multiplier"]
            cost = fuel * BUNKER_USD_PER_T + days * CHARTER_USD_PER_DAY
            rows.append(
                {
                    "speed_knots": speed,
                    "hours": round(hours, 2),
                    "days": round(days, 3),
                    "fuel_t": round(fuel, 2),
                    "fuel_fouled_90d_t": round(fouled, 2),
                    "co2_t": round(fuel * CO2_PER_TONNE_FUEL, 1),
                    "scenario_cost_usd": round(cost, 0),
                }
            )
        best = min(rows, key=lambda r: r["scenario_cost_usd"])
        return {
            "origin": origin,
            "destination": dest,
            "lane_km": round(dist, 1),
            "bunker_usd_per_t": BUNKER_USD_PER_T,
            "charter_usd_per_day": CHARTER_USD_PER_DAY,
            "economic_speed_knots": best["speed_knots"],
            "economic_cost_usd": best["scenario_cost_usd"],
            "economic_fuel_t": best["fuel_t"],
            "economic_hours": best["hours"],
            "rows": rows,
        }

    def figures(self, resistance, paths, fouling, tradeoff):
        FIG.mkdir(parents=True, exist_ok=True)
        plt.rcParams.update(
            {
                "font.family": "serif",
                "font.size": 10,
                "axes.labelsize": 11,
                "axes.titlesize": 11,
                "pdf.fonttype": 42,
            }
        )
        speeds = [r["speed_knots"] for r in resistance["curve"]]

        fig, ax = plt.subplots(figsize=(6.2, 3.8))
        ax.plot(speeds, [r["viscous_kN"] for r in resistance["curve"]], label="Viscous")
        ax.plot(speeds, [r["wave_kN"] for r in resistance["curve"]], label="Wave-making")
        ax.plot(speeds, [r["resistance_kN"] for r in resistance["curve"]], label="Total", color="black")
        ax.set_xlabel("Speed through water (knots)")
        ax.set_ylabel("Resistance (kN)")
        ax.legend(frameon=False)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(FIG / "resistance.pdf")
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(6.2, 3.8))
        ratios = [r["detour_ratio"] for r in paths["rows"] if r["detour_ratio"] is not None]
        ax.hist(ratios, bins=16, color="#4c78a8", edgecolor="white")
        ax.axvline(paths["median_detour"], color="black", linestyle="--", label="Median")
        ax.set_xlabel("Lane distance / great-circle distance")
        ax.set_ylabel("Ordered port pairs")
        ax.legend(frameon=False)
        ax.grid(True, axis="y", alpha=0.3)
        fig.tight_layout()
        fig.savefig(FIG / "detour.pdf")
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(6.2, 3.8))
        ax.plot(
            [r["days"] for r in fouling["rows"]],
            [r["multiplier"] for r in fouling["rows"]],
            marker="o",
            color="#e45756",
        )
        ax.set_xlabel("Days since cleaning")
        ax.set_ylabel("Fuel multiplier")
        ax.set_ylim(1.0, max(r["multiplier"] for r in fouling["rows"]) + 0.02)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(FIG / "fouling.pdf")
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(6.2, 3.8))
        ax.plot(
            [r["hours"] for r in tradeoff["rows"]],
            [r["fuel_t"] for r in tradeoff["rows"]],
            marker="o",
            color="#54a24b",
        )
        star = next(r for r in tradeoff["rows"] if r["speed_knots"] == tradeoff["economic_speed_knots"])
        ax.scatter([star["hours"]], [star["fuel_t"]], color="black", zorder=3, label="Scenario minimum")
        ax.set_xlabel("Voyage time (h)")
        ax.set_ylabel("Fuel (t)")
        ax.legend(frameon=False)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(FIG / "pareto.pdf")
        plt.close(fig)

    def write_numbers(self, payload):
        p = payload
        net, paths, seq, res, foul, trade = (
            p["network"],
            p["paths"],
            p["sequencing"],
            p["resistance"],
            p["fouling"],
            p["tradeoff"],
        )
        fuel20 = next(r for r in res["curve"] if r["speed_knots"] == 20)
        fuel18 = next(r for r in res["curve"] if r["speed_knots"] == 18)
        foul90 = next(r for r in foul["rows"] if r["days"] == 90)
        gaps = [row["ga_max_gap_pct"] for row in seq["instances"]]
        successes = [row["ga_success_rate"] for row in seq["instances"]]
        reversed_gaps = [row["reversed_gap_pct"] for row in seq["instances"]]
        n_differ = sum(1 for row in seq["instances"] if row["orders_differ_under_current"])
        service = next(r for r in trade["rows"] if r["speed_knots"] == 18)
        hk = next(
            r
            for r in p["corridors"]["rows"]
            if r["origin"] == "Hong_Kong" and r["destination"] == "Yokohama" and r["month"] == "January"
        )
        sh = next(
            r
            for r in p["corridors"]["rows"]
            if r["origin"] == "Shanghai" and r["destination"] == "Singapore" and r["month"] == "January"
        )
        macros = {
            "NPorts": tex_num(net["n_ports"], 0),
            "NSeaNodes": tex_num(net["n_sea_nodes"], 0),
            "NEdges": tex_num(net["n_edges"], 0),
            "NComponents": tex_num(net["n_components"], 0),
            "MeanDegree": tex_num(net["mean_sea_degree"], 2),
            "NDisconnected": tex_num(net["n_disconnected_ordered_pairs"], 0),
            "NPairs": tex_num(paths["n_ordered_pairs"], 0),
            "NConnected": tex_num(paths["n_connected"], 0),
            "AstarMatches": tex_num(paths["astar_dijkstra_matches"], 0),
            "MeanDetour": tex_num(paths["mean_detour"], 3),
            "MedianDetour": tex_num(paths["median_detour"], 3),
            "MaxDetour": tex_num(paths["max_detour"], 3),
            "MinDetour": tex_num(paths["min_detour"], 3),
            "MeanLaneKm": tex_num(paths["mean_lane_km"], 0),
            "MeanGcKm": tex_num(paths["mean_gc_km"], 0),
            "SecondsAstar": tex_num(paths["seconds_astar_recomputed"], 2),
            "SecondsDijkstra": tex_num(paths["seconds_dijkstra"], 2),
            "Displacement": tex_num(res["particulars"]["displacement_m3"], 0),
            "WettedSurface": tex_num(res["particulars"]["S_m2"], 0),
            "FormFactor": tex_num(res["particulars"]["one_plus_k1"], 3),
            "FuelEighteen": tex_num(fuel18["fuel_tpd"], 1),
            "FuelTwenty": tex_num(fuel20["fuel_tpd"], 1),
            "PowerTwenty": tex_num(fuel20["bhp_MW"], 1),
            "ResistanceTwenty": tex_num(fuel20["resistance_kN"], 0),
            "FoulingNinety": tex_num(foul90["penalty_percent"], 1),
            "FoulingMultiplier": tex_num(foul90["multiplier"], 3),
            "GaMaxGap": tex_num(max(gaps), 2),
            "GaMinSuccess": tex_num(min(successes) * 100, 0),
            "NCurrentOrderChanges": tex_num(n_differ, 0),
            "NInstances": tex_num(len(seq["instances"]), 0),
            "EconomicSpeed": tex_num(trade["economic_speed_knots"], 0),
            "EconomicFuel": tex_num(trade["economic_fuel_t"], 1),
            "EconomicHours": tex_num(trade["economic_hours"], 1),
            "LaneSingaporeTokyo": tex_num(trade["lane_km"], 0),
            "BunkerPrice": tex_num(BUNKER_USD_PER_T, 0),
            "CharterRate": tex_num(CHARTER_USD_PER_DAY, 0),
            "SeaInPortComponent": tex_num(net["sea_nodes_in_port_component"], 0),
            "ReversedGapMin": tex_num(min(reversed_gaps), 1),
            "ReversedGapMax": tex_num(max(reversed_gaps), 1),
            "ServiceFuel": tex_num(service["fuel_t"], 1),
            "ServiceHours": tex_num(service["hours"], 1),
            "ServiceCost": tex_num(service["scenario_cost_usd"], 0),
            "EconomicCost": tex_num(trade["economic_cost_usd"], 0),
            "ServiceCOTwo": tex_num(service["co2_t"], 1),
            "EconomicCOTwo": tex_num(next(r["co2_t"] for r in trade["rows"] if r["speed_knots"] == trade["economic_speed_knots"]), 1),
            "CurrentBenefitMax": tex_num(hk["current_delta_pct"], 2),
            "CurrentPenalty": tex_num(sh["current_delta_pct"], 2),
            "PairsAboveOnePointFive": tex_num(sum(1 for r in paths["rows"] if r["detour_ratio"] and r["detour_ratio"] > 1.5), 0),
        }
        self._write_tables(p)

        lines = ["% Auto-generated by experiments/run_study.py. Do not edit.", ""]
        for name, value in macros.items():
            lines.append(f"\\newcommand{{\\{name}}}{{{value}}}")
        lines.append("")
        (PAPER / "numbers.tex").write_text("\n".join(lines), encoding="utf-8")
        return macros

    def _write_tables(self, payload):
        seq = payload["sequencing"]["instances"]
        lines = [
            "% Auto-generated by experiments/run_study.py. Do not edit.",
            "\\begin{table}[t]",
            "\\centering",
            "\\caption{Mandatory-waypoint instances on the lane metric. The listed order is the geographic order in the study file. The reversed order is that list read backwards. Gaps are relative to exhaustive search.}",
            "\\label{tab:sequencing}",
            "\\small",
            "\\begin{tabular}{llrrrr}",
            "\\hline",
            "Origin & Destination & Hubs & Exact (km) & Reversed gap (\\%) & GA max gap (\\%) \\\\",
            "\\hline",
        ]
        for row in seq:
            origin = row["origin"].replace("_", " ")
            dest = row["destination"].replace("_", " ")
            lines.append(
                f"{origin} & {dest} & {row['n_hubs']} & {row['exact_distance_km']:.0f} & "
                f"{row['reversed_gap_pct']:.1f} & {row['ga_max_gap_pct']:.2f} \\\\"
            )
        lines += [
            "\\hline",
            "\\end{tabular}",
            "\\end{table}",
            "",
            "\\begin{table}[t]",
            "\\centering",
            "\\caption{Lane-constrained voyages at 18~knots, clean hull. A positive current delta is a fuel reduction relative to calm water.}",
            "\\label{tab:corridors}",
            "\\small",
            "\\begin{tabular}{llrrrr}",
            "\\hline",
            "Corridor & Month & Lane (km) & GC (km) & Fuel (t) & Current delta (\\%) \\\\",
            "\\hline",
        ]
        for row in payload["corridors"]["rows"]:
            name = f"{row['origin'].replace('_', ' ')}--{row['destination'].replace('_', ' ')}"
            lines.append(
                f"{name} & {row['month']} & {row['lane_km']:.0f} & {row['great_circle_km']:.0f} & "
                f"{row['current_fuel_t']:.1f} & {row['current_delta_pct']:+.2f} \\\\"
            )
        lines += ["\\hline", "\\end{tabular}", "\\end{table}", ""]
        (PAPER / "tables.tex").write_text("\n".join(lines), encoding="utf-8")


def main():
    PAPER.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    study = Study()
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "co2_t_per_t_fuel": CO2_PER_TONNE_FUEL,
        "network": study.network(),
        "paths": None,
        "sequencing": None,
        "resistance": study.resistance_curve(),
        "fouling": study.fouling_curve(),
        "corridors": None,
        "tradeoff": None,
    }
    payload["paths"] = study.path_comparison()
    payload["sequencing"] = study.sequencing()
    payload["corridors"] = study.corridors()
    payload["tradeoff"] = study.speed_tradeoff()
    study.figures(payload["resistance"], payload["paths"], payload["fouling"], payload["tradeoff"])
    # Drop the long pair table from the TeX-facing copy but keep it in JSON.
    (PAPER / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    study.write_numbers(payload)
    print("wrote", PAPER / "results.json")
    print("sea nodes", payload["network"]["n_sea_nodes"], "edges", payload["network"]["n_edges"])
    print("connected", payload["paths"]["n_connected"], "mean detour", round(payload["paths"]["mean_detour"], 3))
    print("A* matches", payload["paths"]["astar_dijkstra_matches"])
    for row in payload["sequencing"]["instances"]:
        print(
            row["origin"],
            "->",
            row["destination"],
            "hubs",
            row["n_hubs"],
            "GA gap",
            row["ga_max_gap_pct"],
            "success",
            row["ga_success_rate"],
            "current changes order",
            row["orders_differ_under_current"],
        )
    print("economic speed", payload["tradeoff"]["economic_speed_knots"])
    assert payload["paths"]["astar_dijkstra_matches"] == payload["paths"]["astar_dijkstra_compared"]
    fuel20 = next(r for r in payload["resistance"]["curve"] if r["speed_knots"] == 20)
    assert 40 < fuel20["fuel_tpd"] < 150
    assert payload["sequencing"]["instances"]
    assert max(r["ga_max_gap_pct"] for r in payload["sequencing"]["instances"]) == 0
    assert min(r["reversed_gap_pct"] for r in payload["sequencing"]["instances"]) > 50


if __name__ == "__main__":
    main()
