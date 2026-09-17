"""
Coastline-masked navigable mesh.

This replaces Shipping_Lanes_v1.geojson as a representation of water.
The lane file is a polyline product and is not used here.

Land is Natural Earth 10 m (public domain), read from data/raw.
A 0.25 degree cell is wider than the Suez Canal and comparable to the
Bab el-Mandeb, so those passages are opened by an explicit strait mask.
Inside the Arabian box used here, dropping that mask disconnects Jebel Ali
from Suez. It does not produce a Cape route, because the Cape is outside
the box. Mohamed,
Hendricks and Hu (arXiv:2512.01076) avoided the same problem by forcing
macro-waypoints through canals. We force the cells instead, and test that
the path actually enters the strait.

Bathymetry is not applied. GEBCO is not in the repository. At 0.25 degrees
a cell-average depth would close harbours. Draft masking is a stated gap,
not a silent substitute.
"""

from __future__ import annotations

import math
from pathlib import Path

import networkx as nx
import shapefile
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union
from shapely.prepared import prep

ROOT = Path(__file__).resolve().parents[1]
LAND_SHP = ROOT / "data" / "raw" / "ne_10m_land" / "ne_10m_land.shp"

# (lat, lon)
JEBEL_ALI = (25.0108, 55.0610)
SUEZ_PORT = (29.9668, 32.5498)
PORT_SAID = (31.2653, 32.3019)
BAB_EL_MANDEB = (12.5833, 43.3333)
NEW_YORK = (40.6892, -74.0445)
ROTTERDAM = (51.9225, 4.4792)

# Centre-lines that a 0.25 degree mask cannot resolve on its own.
STRAIT_LINES = [
    # Strait of Hormuz. A 0.25 degree land cell closes it, which traps
    # Jebel Ali in the Persian Gulf.
    [(26.60, 56.50), (26.50, 56.20), (26.20, 56.40), (25.80, 56.80), (25.40, 56.50)],
    # Suez Canal, Suez to Port Said. The cut is narrower than one cell.
    [(29.95, 32.55), (30.45, 32.34), (30.85, 32.31), (31.26, 32.30)],
    # Bab el-Mandeb and the southern Red Sea, so the path cannot be forced
    # around Africa or east to 80E by a closed raster cell.
    [(12.20, 44.20), (12.45, 43.60), (12.58, 43.33), (12.90, 43.20), (13.50, 42.80)],
    [(13.50, 42.80), (16.00, 41.20), (20.00, 38.50), (24.00, 36.50), (27.50, 34.00), (29.95, 32.55)],
]


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    radius = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def great_circle_km(origin, destination) -> float:
    return haversine_km(origin[0], origin[1], destination[0], destination[1])


def _land_in_bbox(lon0, lat0, lon1, lat1):
    reader = shapefile.Reader(str(LAND_SHP))
    geoms = []
    for shp in reader.shapes():
        xmin, ymin, xmax, ymax = shp.bbox
        if xmax < lon0 or xmin > lon1 or ymax < lat0 or ymin > lat1:
            continue
        geoms.append(shp.__geo_interface__)
    from shapely.geometry import shape
    if not geoms:
        return prep(box(lon0, lat0, lon1, lat1).difference(box(lon0, lat0, lon1, lat1)))
    return prep(unary_union([shape(g) for g in geoms]))


def _strait_mask(half_width_deg: float):
    lines = []
    for line in STRAIT_LINES:
        lines.append(LineString([(lon, lat) for lat, lon in line]))
    return unary_union(lines).buffer(half_width_deg)


def build_mesh(bounds, resolution=0.25, strait_half_width_deg=0.40, force_straits=True):
    """
    bounds: (lon_min, lat_min, lon_max, lat_max)
    Node id is (ilat, ilon) on the resolution grid.
    """
    lon0, lat0, lon1, lat1 = bounds
    land = _land_in_bbox(lon0 - 1, lat0 - 1, lon1 + 1, lat1 + 1)
    straits = _strait_mask(strait_half_width_deg) if force_straits else None

    def navigable(lat, lon) -> bool:
        point = Point(lon, lat)
        if straits is not None and straits.contains(point):
            return True
        return not land.contains(point)

    graph = nx.Graph()
    lat = lat0
    ilat = 0
    nodes = {}
    while lat <= lat1 + 1e-9:
        lon = lon0
        ilon = 0
        while lon <= lon1 + 1e-9:
            if navigable(lat, lon):
                node = (ilat, ilon)
                graph.add_node(node, lat=lat, lon=lon)
                nodes[(ilat, ilon)] = (lat, lon)
            lon = round(lon + resolution, 6)
            ilon += 1
        lat = round(lat + resolution, 6)
        ilat += 1

    offsets = [(0, 1), (1, 0), (1, 1), (1, -1)]
    for (ilat, ilon), (lat, lon) in nodes.items():
        for dlat, dlon in offsets:
            other = (ilat + dlat, ilon + dlon)
            if other not in nodes:
                continue
            olat, olon = nodes[other]
            graph.add_edge(
                (ilat, ilon),
                other,
                weight=haversine_km(lat, lon, olat, olon),
            )
    graph.graph["resolution_deg"] = resolution
    graph.graph["bounds"] = bounds
    graph.graph["land"] = "Natural Earth 10m, public domain"
    graph.graph["straits_forced"] = bool(force_straits)
    graph.graph["bathymetry"] = "not applied"
    return graph


def nearest_node(graph, lat, lon):
    best = None
    best_d = math.inf
    for node, data in graph.nodes(data=True):
        d = haversine_km(lat, lon, data["lat"], data["lon"])
        if d < best_d:
            best = node
            best_d = d
    return best, best_d


def _heuristic(graph):
    def h(u, v):
        a, b = graph.nodes[u], graph.nodes[v]
        return haversine_km(a["lat"], a["lon"], b["lat"], b["lon"])
    return h


def shortest_path(graph, origin, destination, method="astar"):
    start, start_d = nearest_node(graph, origin[0], origin[1])
    end, end_d = nearest_node(graph, destination[0], destination[1])
    if start is None or end is None:
        raise RuntimeError("mesh has no navigable nodes")
    heuristic = _heuristic(graph)
    if method == "astar":
        nodes = nx.astar_path(graph, start, end, heuristic=heuristic, weight="weight")
    elif method == "dijkstra":
        nodes = nx.shortest_path(graph, start, end, weight="weight")
    else:
        raise ValueError(method)
    length = nx.path_weight(graph, nodes, weight="weight")
    coords = [(graph.nodes[n]["lat"], graph.nodes[n]["lon"]) for n in nodes]
    return {
        "coords": coords,
        "distance_km": length,
        "snap_km": start_d + end_d,
        "method": method,
    }


def path_crosses_bab_el_mandeb(coords, tolerance_km=80.0) -> bool:
    return any(
        haversine_km(lat, lon, BAB_EL_MANDEB[0], BAB_EL_MANDEB[1]) <= tolerance_km
        for lat, lon in coords
    )


def path_detours_east(coords, lon_limit=62.0) -> bool:
    return any(lon > lon_limit for _, lon in coords)


def path_goes_south_of_gulf(coords, lat_limit=8.0) -> bool:
    """A Cape circumnavigation leaves this box; a Gulf route does not."""
    return any(lat < lat_limit for lat, _ in coords)


ARABIAN_BOUNDS = (32.0, 10.0, 60.0, 32.5)
ATLANTIC_BOUNDS = (-75.0, 35.0, 8.0, 60.0)
