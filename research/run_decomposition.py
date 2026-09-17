"""
Compute the nested baselines that can be computed without a weather hindcast.

Reads paper/metrics_preregistered.json and does not rewrite it.
Writes paper/decomposition_results.json.
Does not call a weather API.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.baselines import (  # noqa: E402
    SERVICE_SPEED_KN,
    baseline_1,
    baseline_2,
    baseline_3_commercial,
    baseline_3_deadline,
    baseline_4,
    commercial_speed_delta,
    network_inflation,
)
from research.navigable_mesh import (  # noqa: E402
    ATLANTIC_BOUNDS,
    JEBEL_ALI,
    NEW_YORK,
    ROTTERDAM,
    SUEZ_PORT,
    build_mesh,
    great_circle_km,
    path_crosses_bab_el_mandeb,
    path_detours_east,
    shortest_path,
)

PREREG = ROOT / "paper" / "metrics_preregistered.json"
OUT = ROOT / "paper" / "decomposition_results.json"


def _round_row(row: dict) -> dict:
    out = {}
    for key, value in row.items():
        if isinstance(value, float):
            out[key] = round(value, 4)
        else:
            out[key] = value
    return out


def one_case(name, graph, origin, destination, extra=None):
    path = shortest_path(graph, origin, destination, method="astar")
    check = shortest_path(graph, origin, destination, method="dijkstra")
    if abs(path["distance_km"] - check["distance_km"]) >= 1e-6:
        raise RuntimeError(f"A* and Dijkstra disagree on {name}")
    gc = great_circle_km(origin, destination)
    b1 = baseline_1(gc, SERVICE_SPEED_KN)
    b2 = baseline_2(path["distance_km"], SERVICE_SPEED_KN)
    b3c = baseline_3_commercial(path["distance_km"])
    b3d = baseline_3_deadline(path["distance_km"], b2["hours"])
    b4 = baseline_4(None)
    record = {
        "name": name,
        "_coords": path["coords"],
        "origin": origin,
        "destination": destination,
        "great_circle_km": round(gc, 3),
        "mesh_km": round(path["distance_km"], 3),
        "distance_ratio_mesh_over_gc": round(path["distance_km"] / gc, 4),
        "astar_dijkstra_abs_diff_km": abs(path["distance_km"] - check["distance_km"]),
        "B1": _round_row(b1),
        "B2": _round_row(b2),
        "B3_commercial": _round_row(b3c),
        "B3_deadline": _round_row(b3d),
        "B4": b4,
        "network_inflation": _round_row(network_inflation(b1, b2)),
        "commercial_speed_delta": _round_row(commercial_speed_delta(b2, b3c)),
        "deadline_speed_effect_t": round(b2["fuel_t"] - b3d["fuel_t"], 6),
    }
    if extra:
        record.update(extra(path["coords"]))
    return record


def _sample_great_circle(origin, destination, n=160):
    import math

    lat1, lon1 = math.radians(origin[0]), math.radians(origin[1])
    lat2, lon2 = math.radians(destination[0]), math.radians(destination[1])
    d = 2 * math.asin(
        math.sqrt(
            math.sin((lat2 - lat1) / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
        )
    )
    if d == 0:
        return [origin, destination]
    points = []
    for i in range(n + 1):
        f = i / n
        a = math.sin((1 - f) * d) / math.sin(d)
        b = math.sin(f * d) / math.sin(d)
        x = a * math.cos(lat1) * math.cos(lon1) + b * math.cos(lat2) * math.cos(lon2)
        y = a * math.cos(lat1) * math.sin(lon1) + b * math.cos(lat2) * math.sin(lon2)
        z = a * math.sin(lat1) + b * math.sin(lat2)
        points.append(
            (
                math.degrees(math.atan2(z, math.hypot(x, y))),
                math.degrees(math.atan2(y, x)),
            )
        )
    return points


def _polyline_file_path(origin, destination):
    """Shortest path in Shipping_Lanes_v1.geojson, with the app's 500 km port connectors.

    Returned only if the length matches the stored study figure. Otherwise the
    figure would be a different object from the ratio cited in the paper.
    """
    import networkx as nx

    geo = json.loads((ROOT / "Shipping_Lanes_v1.geojson").read_text())
    graph = nx.Graph()

    def node_id(lat, lon):
        return f"{lat:.6f}_{lon:.6f}"

    for feature in geo.get("features", []):
        geometry = feature.get("geometry") or {}
        typ = geometry.get("type")
        lines = []
        if typ == "LineString":
            lines = [geometry.get("coordinates") or []]
        elif typ == "MultiLineString":
            lines = geometry.get("coordinates") or []
        for line in lines:
            prev = None
            for lon, lat in line:
                nid = node_id(lat, lon)
                graph.add_node(nid, lat=lat, lon=lon)
                if prev is not None and not graph.has_edge(prev, nid):
                    graph.add_edge(prev, nid, weight=great_circle_km(
                        (graph.nodes[prev]["lat"], graph.nodes[prev]["lon"]),
                        (lat, lon),
                    ))
                prev = nid

    start = "origin"
    end = "destination"
    graph.add_node(start, lat=origin[0], lon=origin[1])
    graph.add_node(end, lat=destination[0], lon=destination[1])
    for nid, data in list(graph.nodes(data=True)):
        if nid in (start, end):
            continue
        for port, coord in ((start, origin), (end, destination)):
            d = great_circle_km(coord, (data["lat"], data["lon"]))
            if d <= 500.0:
                graph.add_edge(port, nid, weight=d)
    if not nx.has_path(graph, start, end):
        return None
    nodes = nx.shortest_path(graph, start, end, weight="weight")
    length = nx.path_weight(graph, nodes, weight="weight")
    if abs(length - 10087.695) > 1.0:
        print("polyline path length", length, "does not match 10087.7; not drawn")
        return None
    return [(graph.nodes[n]["lat"], graph.nodes[n]["lon"]) for n in nodes]


def write_figure(mesh_coords, origin, destination):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import shapefile
    from matplotlib.collections import PatchCollection
    from matplotlib.patches import Polygon

    out_dir = ROOT / "paper" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.4, 4.8))
    reader = shapefile.Reader(str(ROOT / "data" / "raw" / "ne_10m_land" / "ne_10m_land.shp"))
    patches = []
    for shape in reader.shapes():
        xmin, ymin, xmax, ymax = shape.bbox
        if xmax < 31 or xmin > 86 or ymax < 5 or ymin > 36:
            continue
        parts = list(shape.parts) + [len(shape.points)]
        for i in range(len(parts) - 1):
            ring = shape.points[parts[i] : parts[i + 1]]
            if len(ring) >= 3:
                patches.append(Polygon(ring, closed=True))
    ax.add_collection(
        PatchCollection(patches, facecolor="#e4dcc8", edgecolor="#6e665c", linewidths=0.25)
    )

    def xy(coords):
        return [c[1] for c in coords], [c[0] for c in coords]

    ax.plot(*xy(_sample_great_circle(origin, destination)), color="#9b2335", linestyle="--", linewidth=1.3, label="Great circle, 2,322 km")
    polyline = _polyline_file_path(origin, destination)
    if polyline:
        ax.plot(*xy(polyline), color="#c47b00", linewidth=1.15, label="Polyline file, 10,088 km")
    ax.plot(*xy(mesh_coords), color="#0b3d91", linewidth=1.5, label="Coastline mesh, 5,492 km")
    ax.scatter([origin[1], destination[1]], [origin[0], destination[0]], c="black", s=16, zorder=5)
    ax.annotate("Jebel Ali", origin[::-1], textcoords="offset points", xytext=(6, -10), fontsize=8)
    ax.annotate("Suez Canal", destination[::-1], textcoords="offset points", xytext=(-52, 6), fontsize=8)
    ax.set_xlim(32, 84)
    ax.set_ylim(8, 34)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_aspect("equal", adjustable="box")
    ax.legend(loc="upper left", frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(out_dir / "jebel_ali_suez_mesh.pdf")
    fig.savefig(out_dir / "jebel_ali_suez_mesh.png", dpi=160)
    plt.close(fig)
    print("wrote", out_dir / "jebel_ali_suez_mesh.pdf")
    stats = {"polyline_drawn": polyline is not None}
    if polyline:
        hops = [
            great_circle_km(a, b)
            for a, b in zip(polyline, polyline[1:])
        ]
        stats["polyline_vertices"] = len(polyline)
        stats["polyline_longest_edge_km"] = round(max(hops), 1)
        stats["polyline_edges_over_1000_km"] = sum(h > 1000 for h in hops)
    return stats


def main():
    prereg = json.loads(PREREG.read_text())
    if prereg.get("status") != "pre-registered":
        raise SystemExit("pre-registration file is missing or altered in status")

    arabian = build_mesh((32.0, 9.5, 62.0, 32.5), resolution=0.25, strait_half_width_deg=0.30)
    atlantic = build_mesh(ATLANTIC_BOUNDS, resolution=0.5, strait_half_width_deg=0.35)

    cases = [
        one_case(
            "Jebel Ali to Suez Canal point",
            arabian,
            JEBEL_ALI,
            (30.5852, 32.2654),
            extra=lambda coords: {
                "through_bab_el_mandeb": path_crosses_bab_el_mandeb(coords),
                "detours_east_of_62E": path_detours_east(coords, 62.0),
                "same_endpoints_as_polyline_study": True,
                "polyline_file_ratio_not_used": 4.345,
                "polyline_file_lane_km": 10087.7,
            },
        ),
        one_case(
            "Jebel Ali to Suez",
            arabian,
            JEBEL_ALI,
            SUEZ_PORT,
            extra=lambda coords: {
                "through_bab_el_mandeb": path_crosses_bab_el_mandeb(coords),
                "detours_east_of_62E": path_detours_east(coords, 62.0),
                "polyline_file_ratio_not_used": 4.345,
            },
        ),
        one_case("New York to Rotterdam", atlantic, NEW_YORK, ROTTERDAM),
    ]
    headline = cases[0]
    headline.update(write_figure(headline["_coords"], headline["origin"], headline["destination"]))
    for case in cases:
        case.pop("_coords", None)

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "preregistration": str(PREREG.name),
        "preregistration_timestamp": prereg["timestamp"],
        "weather_cache": None,
        "ais_voyages": None,
        "ais_status": "not obtained. Free feeds do not cover these crossings, and tracks were not invented.",
        "gebco": "not applied",
        "land": "Natural Earth 10m",
        "cases": cases,
        "kill_criteria_this_revision": {
            "weather_saving_reported": False,
            "percentage_against_B1_alone_reported": False,
            "reason": "B4 is not_estimated. No weather percentage is written.",
        },
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    lines = [
        "% Generated by research/run_decomposition.py. Do not edit.",
        "\\begin{table}[t]",
        "\\centering",
        "\\caption{Distance and calm-water fuel at 18 knots. B1 is the great circle. It is not a feasible voyage when that arc crosses land. The deadline column is $F_2-F_{3,\\mathrm{deadline}}$. B4 is omitted because no hindcast was cached.}",
        "\\label{tab:decomp}",
        "\\small",
        "\\begin{tabular}{lrrrrrr}",
        "\\toprule",
        "Voyage & GC (km) & Mesh (km) & Ratio & $F_1$ (t) & $F_2$ (t) & Deadline (t) \\\\",
        "\\midrule",
    ]
    short = {
        "Jebel Ali to Suez Canal point": "Jebel Ali--canal point",
        "Jebel Ali to Suez": "Jebel Ali--Suez port",
        "New York to Rotterdam": "New York--Rotterdam",
    }
    for case in cases:
        label = short.get(case["name"], case["name"])
        lines.append(
            f"{label} & {case['great_circle_km']:.0f} & {case['mesh_km']:.0f} "
            f"& {case['distance_ratio_mesh_over_gc']:.3f} "
            f"& {case['B1']['fuel_t']:.0f} & {case['B2']['fuel_t']:.0f} "
            f"& {case['deadline_speed_effect_t']:.1f} \\\\"
        )
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{table}", ""]
    (ROOT / "paper" / "decomp_table.tex").write_text("\n".join(lines), encoding="utf-8")
    stats = cases[0]
    macros = [
        "% Generated by research/run_decomposition.py. Do not edit.",
        f"\\newcommand{{\\PolylineVertices}}{{{stats.get('polyline_vertices', 0)}}}",
        f"\\newcommand{{\\PolylineLongestEdgeKm}}{{{stats.get('polyline_longest_edge_km', 0):.0f}}}",
        f"\\newcommand{{\\PolylineLongEdges}}{{{stats.get('polyline_edges_over_1000_km', 0)}}}",
        "",
    ]
    (ROOT / "paper" / "decomp_numbers.tex").write_text("\n".join(macros), encoding="utf-8")
    print("wrote", OUT)
    for case in cases:
        print(
            case["name"],
            "ratio",
            case["distance_ratio_mesh_over_gc"],
            "B1 fuel",
            case["B1"]["fuel_t"],
            "B2 fuel",
            case["B2"]["fuel_t"],
            "deadline effect",
            case["deadline_speed_effect_t"],
        )


if __name__ == "__main__":
    main()
