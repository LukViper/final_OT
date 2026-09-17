"""Hard gates for the coastline mesh. Do not weaken these to make a path pass."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import networkx as nx

from research.navigable_mesh import (  # noqa: E402
    JEBEL_ALI,
    SUEZ_PORT,
    build_mesh,
    great_circle_km,
    nearest_node,
    path_crosses_bab_el_mandeb,
    path_detours_east,
    path_goes_south_of_gulf,
    shortest_path,
)

# Polyline-file defect this mesh must not reproduce.
POLYLINE_FILE_RATIO = 4.345


@pytest.fixture(scope="module")
def arabian_mesh():
    return build_mesh((32.0, 9.5, 62.0, 32.5), resolution=0.25, strait_half_width_deg=0.30)


def test_mesh_jebel_ali_suez(arabian_mesh):
    result = shortest_path(arabian_mesh, JEBEL_ALI, SUEZ_PORT, method="astar")
    coords = result["coords"]
    great_circle = great_circle_km(JEBEL_ALI, SUEZ_PORT)
    ratio = result["distance_km"] / great_circle

    assert path_crosses_bab_el_mandeb(coords), "path does not enter the Bab el-Mandeb"
    assert not path_detours_east(coords, lon_limit=62.0), "path detours toward 80E / the box wall"
    assert not path_goes_south_of_gulf(coords), "path leaves the Gulf for an African circumnavigation"
    assert ratio < 3.0, f"sea/great-circle ratio {ratio:.2f} is still the polyline-file defect"
    assert ratio < POLYLINE_FILE_RATIO
    # The great circle crosses Arabia. A feasible sea path must be longer.
    assert result["distance_km"] > great_circle


def test_unforced_mask_disconnects_jebel_ali_from_suez():
    """A 0.25 degree land mask closes Hormuz. The Cape is outside this box, so the failure mode is no path, not a circumnavigation."""
    closed = build_mesh(
        (32.0, 9.5, 62.0, 32.5),
        resolution=0.25,
        strait_half_width_deg=0.30,
        force_straits=False,
    )
    start, _ = nearest_node(closed, JEBEL_ALI[0], JEBEL_ALI[1])
    end, _ = nearest_node(closed, 30.5852, 32.2654)
    assert start is not None and end is not None
    assert closed.nodes[start]["lon"] > 54.0
    assert not nx.has_path(closed, start, end)


def test_astar_dijkstra_parity(arabian_mesh):
    astar = shortest_path(arabian_mesh, JEBEL_ALI, SUEZ_PORT, method="astar")
    dijkstra = shortest_path(arabian_mesh, JEBEL_ALI, SUEZ_PORT, method="dijkstra")
    assert abs(astar["distance_km"] - dijkstra["distance_km"]) < 1e-6
