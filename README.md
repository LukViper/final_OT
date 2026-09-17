# Lane-constrained waypoint routing

Reproducible study of mandatory-waypoint routing on a shipping-lane graph, with fuel from the Holtrop–Mennen regression. The manuscript is `paper/manuscript.tex`. Every number it cites through `paper/numbers.tex` and `paper/tables.tex` is produced by the study script, not typed in by hand.

The repository previously reported a fuel “saving” against a fixed 15% weather allowance, including when no forecast was available. That comparison has been removed. The paper does not claim a weather-routing saving.

## Reproduce the study

From this directory:

```bash
python experiments/run_study.py
```

No weather API key is required. The script writes:

- `paper/results.json` — full numerical record
- `paper/numbers.tex` — macros used in the manuscript
- `paper/tables.tex` — the two result tables
- `paper/figures/*.pdf` — the four figures

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
