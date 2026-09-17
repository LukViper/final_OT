#!/usr/bin/env python3
"""One-off generator for the journal-readiness status document."""

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor


OUT = Path(__file__).resolve().parent / "Journal_readiness_status.docx"


def shade(cell, hex_color):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = tcPr.makeelement(qn("w:shd"), {
        qn("w:fill"): hex_color,
        qn("w:val"): "clear",
    })
    tcPr.append(shd)


def set_run_font(run, name="Calibri", size=11, bold=False, color=None):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    run.bold = bold
    if color is not None:
        run.font.color.rgb = RGBColor(*color)


def add_heading_styled(doc, text, level):
    heading = doc.add_heading(text, level=level)
    for run in heading.runs:
        set_run_font(run, size=16 if level == 1 else 13, bold=True, color=(0x1F, 0x3A, 0x5F))
    return heading


def para(doc, text, bold=False, italic=False, size=11, space_after=8):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.space_before = Pt(0)
    run = p.add_run(text)
    set_run_font(run, size=size, bold=bold)
    run.italic = italic
    return p


def bullet(doc, text, level=0):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.left_indent = Cm(1.25 + 0.5 * level)
    p.paragraph_format.space_after = Pt(3)
    run = p.add_run(text)
    set_run_font(run, size=11)
    return p


def add_table(doc, headers, rows, col_widths=None):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    table.autofit = True
    for i, header in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = ""
        run = cell.paragraphs[0].add_run(header)
        set_run_font(run, size=10, bold=True, color=(255, 255, 255))
        shade(cell, "1F3A5F")
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            cell = table.rows[r + 1].cells[c]
            cell.text = ""
            run = cell.paragraphs[0].add_run(str(value))
            set_run_font(run, size=10)
            if r % 2 == 1:
                shade(cell, "F4F7FB")
    if col_widths:
        for row in table.rows:
            for idx, width in enumerate(col_widths):
                row.cells[idx].width = Cm(width)
    doc.add_paragraph()
    return table


def main():
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Cm(1.8)
    section.bottom_margin = Cm(1.8)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)
    style._element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    title.paragraph_format.space_after = Pt(2)
    run = title.add_run("Journal readiness status")
    set_run_font(run, size=22, bold=True, color=(0x1F, 0x3A, 0x5F))

    sub = doc.add_paragraph()
    sub.paragraph_format.space_after = Pt(2)
    run = sub.add_run("Lane-constrained maritime route calculator")
    set_run_font(run, size=14, color=(0x33, 0x55, 0x77))

    meta = doc.add_paragraph()
    meta.paragraph_format.space_after = Pt(12)
    run = meta.add_run("Status note for the Optimization Technique repository. 17 September 2026.")
    set_run_font(run, size=10, color=(0x66, 0x66, 0x66))
    run.italic = True

    para(
        doc,
        "This note records the audit of the original lane-file prototype and the identification manuscript written after it. The manuscript is paper/manuscript.tex. It is not a weather-routing paper, and it is not ready to submit until authors are named and a PDF is compiled.",
    )

    add_heading_styled(doc, "1. Bottom line", 1)
    para(
        doc,
        "The Flask prototype and the lane-file audit remain as they were. A coastline mesh has since been built, and paper/manuscript.tex is now the identification paper: on Jebel Ali–Suez the great circle understates feasible calm-water fuel by a factor of 2.37, while the undocumented polyline file produced 4.35 by missing the Gulf of Aden. New York–Rotterdam is only 1.09. With a fixed arrival and calm water the speed term is zero. Weather is not estimated. Automatic Identification System tracks were not invented.",
    )
    para(
        doc,
        "A reputable journal in this field (Transportation Research Part C, Ocean Engineering, Transportation Science, Transportation Research Part B or D) will not accept a claim of a new optimizer on the strength of the present results. The genetic algorithm does not beat nearest insertion. The lane file is nearly a set of polylines. The largest “detour” is a missing corridor, not a routing decision. The old 15 percent weather saving was an assumed factor and has been removed.",
    )
    para(
        doc,
        "The claim in the manuscript is narrower than Section 5 of this note. Network and deadline-speed terms are computed. The weather term and the real-voyage sample are not. Those two gaps are why this is a short identification paper and not yet an Ocean Engineering or Transportation Research Part D article on realized savings.",
    )

    add_heading_styled(doc, "2. What has already been completed", 1)

    add_heading_styled(doc, "2.1 Software that runs", 2)
    bullet(doc, "A Flask application (app.py) that accepts ports and displays routes. It was started successfully on http://127.0.0.1:5006.")
    bullet(doc, "A shipping-lane graph built from Shipping_Lanes_v1.geojson: 27,929 sea nodes, 28,903 edges including port connectors, 84 connected components, mean sea-node degree 2.04.")
    bullet(doc, "Twenty named ports. All 380 ordered pairs are connected. Port-to-port shortest paths are precomputed.")
    bullet(doc, "A* with a great-circle heuristic, and Dijkstra as a check. The two agree to 10^-6 km on all 380 pairs.")
    bullet(doc, "Mandatory-hub sequencing. The crossover is now order crossover (a permutation operator). An earlier operator concatenated both parents and was not a search of the permutation space.")
    bullet(doc, "Holtrop–Mennen calm-water resistance (Holtrop and Mennen 1982; Holtrop 1984), implemented in utils/holtrop_mennen.py. The previous code used the block coefficient in place of Holtrop’s c7 and multiplied the wave term by 10^-9. That scale factor has been removed.")
    bullet(doc, "Internally consistent Panamax particulars: length 280 m, beam 32.2 m (the Panama limit), draft 12.5 m, block coefficient 0.65, displacement 73,255 m³. A beam of 40 m previously labelled Panamax is no longer used.")
    bullet(doc, "Fuel for a distance at constant speed through water, with an along-track current correction. Following and adverse current had used the same angular test; that bug is fixed. The along-track component is what enters the speed-over-ground calculation.")
    bullet(doc, "A fouling multiplier applied once, at voyage level, not inside the resistance routine and not a second time on top of it. An invented annual bunker bill and cleaning return-on-investment have been removed from the fouling module.")
    bullet(doc, "Carbon dioxide reported with the IMO residual-fuel inventory factor 3.114 t CO2 per tonne of fuel, not 3.15.")
    bullet(doc, "The analytics fallback no longer invents demonstration totals (previously 1,247 calculations, a 65/35 algorithm split, and a fixed 15 percent “optimization”).")
    bullet(doc, "The four-dimensional route function no longer reports a saving against a hardcoded 1.15 weather factor, and no longer returns a fixed 15 percent when the forecast is missing.")

    add_heading_styled(doc, "2.2 Study, figures, and manuscript draft", 2)
    bullet(doc, "experiments/run_study.py regenerates every cited number. It does not call a weather API.")
    bullet(doc, "Outputs: paper/results.json, paper/numbers.tex, paper/tables.tex, and four figures (detour, resistance, fouling, speed–fuel Pareto).")
    bullet(doc, "A draft manuscript, paper/manuscript.tex, with paper/references.bib. Author names are intentionally blank. The draft describes the audit; it is not a submission.")
    bullet(doc, "README.md states how to reproduce the study and states that no weather-routing saving is claimed.")
    bullet(doc, "The PDF has not been compiled in this environment. TeX Live is not installed. Compilation commands are in the README.")

    add_heading_styled(doc, "2.3 Numerical results already in hand", 2)
    para(
        doc,
        "These figures come from experiments/run_study.py. They are properties of this code and this lane file. They are not sea-trial results.",
    )
    add_table(
        doc,
        ["Item", "Result"],
        [
            ["Port pairs connected", "380 of 380"],
            ["A* versus Dijkstra", "Identical distance on all 380 pairs"],
            ["Sea nodes in the port component", "3,763 of 27,929"],
            ["Median lane / great-circle ratio", "1.264"],
            ["Mean of those ratios", "1.361"],
            ["Maximum ratio", "4.345, Jebel Ali–Suez Canal, both directions"],
            ["That pair, great circle", "2,321.6 km"],
            ["That pair, shortest stored lane", "10,087.7 km, via about 80°E, then the Red Sea"],
            ["Pairs with ratio above 1.5", "96"],
            ["Hub instances enumerated", "8 instances, 3 to 7 hubs"],
            ["Geographic order versus exact optimum", "Gap 0% on every instance"],
            ["Nearest insertion versus exact optimum", "Gap 0%"],
            ["Genetic algorithm, 20 seeds", "Maximum gap 0%; success rate 100%"],
            ["Reversed hub order", "71.5% to 127.2% longer"],
            ["January current, effect on hub order", "No change on any of the 8 instances"],
            ["Current effect on fuel, 18 knots", "−2.59% (Shanghai–Singapore) to +6.31% (Hong Kong–Yokohama)"],
            ["Model fuel rate, 18 knots", "56.8 t/day"],
            ["Model fuel rate, 20 knots", "80.5 t/day; 19.7 MW brake power; 1,302 kN resistance"],
            ["Form factor 1+k1", "1.102"],
            ["Singapore–Tokyo stored lane", "5,344 km (great circle 5,311 km)"],
            ["Scenario prices", "600 USD/t bunker; 25,000 USD/day charter"],
            ["Cost-minimizing speed on that lane", "13 knots"],
            ["Fuel and time at 13 knots", "185.2 t; 211.0 h; scenario cost 330,861 USD; 576.7 t CO2"],
            ["Same lane at 18 knots", "365.6 t; 154.4 h; scenario cost 380,193 USD; 1,138.3 t CO2"],
            ["Fouling at 90 days, 28°C, 35 psu", "Multiplier 1.386 (38.6%), then capped at 40%"],
        ],
    )
    para(
        doc,
        "The Jebel Ali–Suez path was traced, not only scored. It does enter the Red Sea. Before that it runs east from the Gulf of Oman to about 80°E and only then west through the Gulf of Aden. The missing piece is a direct Arabian Sea corridor.",
        italic=True,
        size=10,
    )

    add_heading_styled(doc, "3. What those completed results are allowed to say", 1)
    para(doc, "Claims that are true, and no stronger:")
    bullet(doc, "On this file, excess distance over the great circle is not evidence that an optimizer saved fuel. The median excess is 26 percent. The extreme is a hole in the graph.")
    bullet(doc, "The graph does not offer alternative sea routes. Mean degree near 2 means the shortest path is usually a unique polyline.")
    bullet(doc, "With every hub mandatory and costs proportional to distance, fastest order and fuel-minimizing order are the same problem. Enumeration solves it up to seven hubs. Nearest insertion also solves it. The genetic algorithm is not the source of the improvement.")
    bullet(doc, "This schematic current field changes fuel by a few percent and does not reorder these eight voyages. That does not imply that real ocean currents never matter.")
    bullet(doc, "For the stated Panamax particulars, the corrected regression produces a service-speed fuel rate of the expected order. It has not been calibrated to a trial.")
    bullet(doc, "At the stated scenario prices, Singapore–Tokyo has an interior cost minimum at 13 knots. Change the charter rate and the minimum moves. It is not a universal optimum speed.")

    add_heading_styled(doc, "4. What has not been done, and why that blocks a journal", 1)
    add_table(
        doc,
        ["Gap", "Why a reviewer will reject the claim"],
        [
            ["Lane file has no source, date, or license", "Distances cannot be cited as a property of real shipping lanes."],
            ["No navigable mesh", "Land, depth, and traffic separation are not constraints. A* cannot find a route the file never stored."],
            ["No Automatic Identification System tracks", "There is no held-out voyage. The eight hub lists were chosen in the study file."],
            ["No hindcast wind, wave, or current in the reported runs", "The weather client is operational code. It is not a result. Live APIs are not reproducible."],
            ["No reference weather-routing solver", "Isochrones and time-dependent dynamic programming are the literature baselines. A genetic algorithm that ties nearest insertion is not a comparator."],
            ["Fuel model uncalibrated", "56.8 t/day at 18 knots is plausible, not validated. Specific fuel consumption does not vary with engine load, so slow steaming looks too cheap."],
            ["Currents are a few Gaussian cores", "Gulf Stream, Kuroshio, Agulhas, a schematic equatorial set, Canary Current, and two eddies. Not Copernicus Marine or OSCAR."],
            ["Fouling is a scenario", "30 days already gives 21.5 percent, and 90 days is near the 40 percent cap. This is not a fit to Schultz (2007) or an ITTC roughness procedure."],
            ["Tides and moon phase are printed, not optimized", "They are not in the objective. Emission-control areas in the app do not intersect this port set."],
            ["No uncertainty over a voyage sample", "One Singapore–Tokyo run and eight hub lists do not support a confidence interval."],
            ["Manuscript has no authors and no compiled PDF", "Administrative, but a submission cannot go out in this state."],
            ["Interface still mixes display prices", "The study uses 600 USD/t. Parts of the interface still show 650 USD/t. That must not appear as a finding."],
        ],
    )

    add_heading_styled(doc, "5. What must be added to make the project journal-worthy", 1)
    para(
        doc,
        "Do not add another algorithm to the Flask demo and call it the paper. Add an experiment that can fail. The claim worth adding is the following.",
    )
    para(
        doc,
        "A reported fuel saving from maritime route optimization is not identifiable until three components are separated: the network, the speed policy, and the weather at the time the ship is actually there. On real voyages, measure how much of the apparent saving is a hole or a detour in the baseline network, how much is slow steaming, and how much remains for wind, waves, and current.",
        italic=True,
    )
    para(
        doc,
        "That claim is the one Transportation Research Part C and Ocean Engineering can review. It is also the claim this repository is closest to, because the lane-file hole is already documented. It is not yet demonstrated outside the file.",
    )

    add_heading_styled(doc, "5.1 Data that must be added", 2)
    bullet(doc, "One ocean basin, not the world. Prefer the North Atlantic, or Asia–Europe including the Arabian Sea gap already found. Do not start from the undocumented GeoJSON as if it were navigable water.")
    bullet(doc, "A mesh, not a polyline. Suggested spacing 0.25 degrees for the first paper, 0.1 degrees only if the runs finish. Mask land and water shallower than the ship’s draft.")
    bullet(doc, "Emission-control areas and canals as attributes of edges, not as boxes that never touch the routes.")
    bullet(doc, "Frozen weather, stored with the study: Copernicus ERA5 or a wave hindcast for wind and waves; Copernicus Marine for currents; a bathymetry grid for the mask. The paper must rerun with the network disconnected.")
    bullet(doc, "A few hundred voyages whose origin, destination, and departure time come from Automatic Identification System tracks. The optimizer must not see the realized track except when the result is scored.")
    bullet(doc, "If noon reports or invoices cannot be obtained, say so in the abstract and evaluate model fuel along the realized track against model fuel along the computed track. Do not write “validated” for a model-versus-model comparison.")
    bullet(doc, "One documented hull. Keep the corrected Holtrop–Mennen code. Add a load-dependent specific fuel consumption and show the speed result with and without it.")

    add_heading_styled(doc, "5.2 Methods that must be added", 2)
    bullet(doc, "Four nested baselines, and no other reported saving:")
    bullet(doc, "Baseline 1. Great circle, fixed service speed, calm water. This is the comparison that inflates savings.", level=1)
    bullet(doc, "Baseline 2. Shortest path on the navigable mesh, same speed, calm water. This removes land, depth, and regulatory masks without giving weather any credit.", level=1)
    bullet(doc, "Baseline 3. Same path, speed chosen to minimize bunker cost plus time cost. This is the slow-steaming component.", level=1)
    bullet(doc, "Baseline 4. Time-dependent path and speed, with wind, waves, and current taken at the arrival time on each edge. Only the remainder after baselines 2 and 3 may be called a weather-routing effect.", level=1)
    bullet(doc, "Solve baseline 4 by label-setting dynamic programming. Use the isochrone method as the published reference. Do not put the genetic algorithm in the abstract unless, on this benchmark, a restricted evaluation budget beats dynamic programming. On the present instances it does not even beat nearest insertion in a way that matters, because both are exact.")
    bullet(doc, "Pre-register the metric before looking at the savings: fuel and CO2 against baseline 1, then the share removed by baseline 2, then by baseline 3, then what remains for baseline 4. Bootstrap over voyages. Repeat for two seasons. Repeat with the charter rate doubled.")
    bullet(doc, "A first engineering test of the mesh: Jebel Ali to Suez Canal must pass through the Gulf of Aden without the detour to 80°E. If it does not, the mask is wrong and every later percentage is wrong.")

    add_heading_styled(doc, "5.3 Artifacts a journal will expect", 2)
    bullet(doc, "The mesh, the voyage list, the frozen weather keys, and the script that recomputes the four baselines. No result that depends on a live weather key.")
    bullet(doc, "A manuscript whose every number is generated by that script, as numbers.tex already does for the internal study.")
    bullet(doc, "Named authors, affiliations, and a data-availability statement that does not invent a source for the old GeoJSON.")
    bullet(doc, "A compiled PDF. The current draft can stay as a supplement that documents the audit, or be rewritten around the new claim. It should not be submitted as the paper.")
    bullet(doc, "Tests that fail if A* and Dijkstra diverge, if the Jebel Ali–Suez mesh path detours to 80°E, or if a saving is reported against baseline 1 without the decomposition.")

    add_heading_styled(doc, "5.4 Kill criteria", 2)
    para(
        doc,
        "Stop, or reduce the paper to a short negative note, if any of the following is true after baselines 2 and 3:",
    )
    bullet(doc, "The weather term is inside the voyage-to-voyage noise.")
    bullet(doc, "The apparent saving against the great circle shrinks to about the size of the network correction.")
    bullet(doc, "The result appears only for corridors chosen after the runs, or only at one charter price.")
    para(
        doc,
        "Do not retune fouling rates, bunker prices, or the grid until a saving appears. Adding a neural network or another weather API will not repair a null decomposition.",
    )

    add_heading_styled(doc, "6. Suggested order of work", 1)
    add_table(
        doc,
        ["Phase", "Done when", "Do not spend this phase on"],
        [
            ["0. Freeze the prototype", "The Flask app and the present study remain as an audit. No further “optimization percentage” is added to the interface.", "New dashboard metrics."],
            ["1. Data access and one corridor", "Weather and current hindcasts are cached. The mesh sends Jebel Ali–Suez through the Gulf of Aden.", "The user interface."],
            ["2. Fifty held-out voyages", "Four baselines run. The decomposition is written down before scaling.", "Tuning the genetic algorithm."],
            ["3. Scale or stop", "A few hundred voyages if the split is stable. A short negative note if it is not.", "Searching for a basin that produces a large percentage."],
            ["4. Submission package", "Script, mesh, voyage list, PDF, author list, and a limitation sentence in the abstract.", "Claims of operational deployment."],
        ],
    )
    para(
        doc,
        "A realistic duration, with Automatic Identification System access, is on the order of nine to eighteen months. Copernicus weather and currents are free. Voyage-level bunker data usually are not. That access decision should be made before any new solver is written.",
    )

    add_heading_styled(doc, "7. Which journal, if the new work succeeds", 1)
    add_table(
        doc,
        ["If the finished result is", "Venue that can review it", "Still not enough"],
        [
            ["Apparent savings against the great circle are mostly the network, shown on hundreds of real voyages", "Transportation Research Part C; Ocean Engineering", "Eight synthetic corridors, or this GeoJSON"],
            ["Weather still saves several percent after network and speed are removed, against dynamic programming or isochrones", "Ocean Engineering; Transportation Research Part D", "A genetic algorithm with no reference solver"],
            ["A new algorithm with a proof that beats dynamic programming on the public set", "Transportation Science; Transportation Research Part B", "Order crossover. That is not that algorithm."],
        ],
    )
    para(
        doc,
        "Nature, Science, and a general promise of “most journals” are the wrong target. Those venues do not publish a Panamax fuel curve. They would look only if the decomposition changed a regulatory inventory, with external data. Do not aim there from the present code.",
    )

    add_heading_styled(doc, "8. Claims that must not appear in a submission", 1)
    bullet(doc, "A new weather-routing method, or a four-dimensional forecast benefit.")
    bullet(doc, "A genetic-algorithm improvement over known routing methods.")
    bullet(doc, "A validated fuel, fouling, tidal, or current model.")
    bullet(doc, "An emission saving, a cost saving, or an operational route recommendation for a ship operator.")
    bullet(doc, "Any percentage whose baseline is “15 percent worse weather” or “the great circle” without the decomposition in Section 5.")
    bullet(doc, "A citation of the lane file as an Automatic Identification System product. The repository does not record that provenance.")

    add_heading_styled(doc, "9. Where the completed material lives", 1)
    add_table(
        doc,
        ["Path", "Role"],
        [
            ["app.py and templates/", "Interface. Not the source of the reported study numbers."],
            ["utils/holtrop_mennen.py", "Corrected resistance model. Keep."],
            ["utils/route_calculator.py", "Lane graph, A*, order crossover. Prototype only."],
            ["utils/ocean_currents.py", "Schematic currents. Not a paper field."],
            ["utils/hull_fouling.py", "Scenario multiplier. Sensitivity only."],
            ["Shipping_Lanes_v1.geojson", "Undocumented polyline network. Do not treat as navigable water."],
            ["experiments/run_study.py", "Reproducible internal study."],
            ["paper/manuscript.tex", "Identification manuscript. Weather and AIS still absent. Authors blank."],
            ["paper/decomposition_results.json", "Mesh versus great-circle fuels. Source of the manuscript table."],
            ["paper/metrics_preregistered.json", "Formulas written before the decomposition run. Not a git commit."],
            ["paper/figures/jebel_ali_suez_mesh.pdf", "Great circle, polyline file, and coastline mesh on the same endpoints."],
            ["paper/results.json", "Full numerical record of the internal study."],
            ["paper/figures/", "Four figures from that study."],
        ],
    )

    para(
        doc,
        "Numbers in this note match paper/numbers.tex and paper/results.json as generated on 17 September 2026. If the study is rerun, regenerate this note from those files rather than editing the figures by hand.",
        italic=True,
        size=10,
    )

    doc.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
