# What a great-circle baseline measures

`paper/manuscript.tex` is an identification paper, not a weather-routing method. It compares three objects on the same endpoints: a great circle, a Natural Earth coastline mesh, and the undocumented polyline file `Shipping_Lanes_v1.geojson`. The manuscript numbers that are not literature citations come from `paper/decomp_table.tex` and `paper/decomp_numbers.tex`.

No weather percentage is reported. Automatic Identification System tracks were not available and were not invented. Author names are left blank on purpose.

## Reproduce the manuscript numbers

From this directory:

```bash
python research/run_decomposition.py
python -m pytest tests/test_navigable_mesh.py tests/test_baselines.py
```

The script reads `paper/metrics_preregistered.json` and does not rewrite it. It writes `paper/decomposition_results.json`, `paper/decomp_table.tex`, `paper/decomp_numbers.tex`, and `paper/figures/jebel_ali_suez_mesh.pdf`. Land is Natural Earth 10 m under `data/raw/ne_10m_land`. Bathymetry is not applied.

Compile from `paper/` once TeX Live is installed (`geometry`, `natbib`, `hyperref`, `booktabs`, `graphicx`, `microtype`):

```bash
cd paper
pdflatex manuscript
bibtex manuscript
pdflatex manuscript
pdflatex manuscript
```

TeX Live is not installed in the environment that produced this note, so the PDF has not been compiled here.

## Older lane-file audit

`experiments/run_study.py` still regenerates the polyline-file audit (`paper/results.json`, `paper/numbers.tex`, `paper/tables.tex`). Those files are not the evidence base of the current manuscript. The lane file has no source or date. Do not cite it as navigable water or as an Automatic Identification System product.

The repository previously reported a fuel “saving” against a fixed 15% weather allowance. That comparison has been removed.

## Reproduce the older audit

From this directory:

```bash
python experiments/run_study.py
```

No weather API key is required. The script writes:

- `paper/results.json` — full numerical record
- `paper/numbers.tex` — macros for the older audit, not for the current manuscript
- `paper/tables.tex` — the two audit tables
- `paper/figures/` — audit figures, plus the manuscript figure written by the decomposition script

It also checks that A* matches Dijkstra on every port pair, that the 20-knot fuel rate lies in a plausible band, and that the genetic algorithm’s gap against enumeration is zero on the stated instances.

Compile the manuscript from `paper/` (TeX Live, with `geometry`, `natbib`, `hyperref`, `booktabs`, and `microtype`):

```bash
cd paper
pdflatex manuscript
bibtex manuscript
pdflatex manuscript
pdflatex manuscript
```

Author names are not inferred from the repository and are left blank on purpose.

## What the study actually estimates

- Shortest paths on `Shipping_Lanes_v1.geojson` for 20 ports, compared with the great circle and with Dijkstra.
- Open-path order of mandatory hubs, by enumeration, nearest insertion, and a permutation genetic algorithm with order crossover.
- Calm-water fuel for a Panamax container ship (Holtrop and Mennen, 1982; Holtrop, 1984), plus an along-track current from a schematic climatology.
- A bunker-plus-charter speed tradeoff on Singapore–Tokyo at stated scenario prices.

The lane file has no source or date in the repository. Treat distances as properties of that file. The current model is not a reanalysis. The fouling multiplier is a capped scenario, not a fitted growth law.

## Application

`app.py` is a Flask front end on the same router. It is not how the reported numbers were produced. If you use it, set any weather keys in an untracked `.env` file; the study does not read them.

```bash
pip install -r requirements.txt
python app.py
```
