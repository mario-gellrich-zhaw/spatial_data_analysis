# Spatiotemporal Urban Activity Patterns — Zurich Prototype

A didactic re-implementation of the methodology presented in:

> Barrena-Herrán, M., Modrego-Monforte, I., & Grijalba, O. (2025).
> *Revealing Spatiotemporal Urban Activity Patterns: A Machine Learning Study
> Using Google Popular Times.*
> **ISPRS Int. J. Geo-Inf.** 14, 221.

applied to **open pedestrian & bicycle count data for the City of Zurich (2025)**,
designed for use in undergraduate / graduate lectures.

## What is in this folder

| File / folder | Purpose |
| --- | --- |
| `app.py` | Streamlit web app — the interactive prototype. |
| `data/locations.csv` | 25 active Zurich counting stations with WGS84 coordinates. |
| `data/hourly_counts.csv` | 207 k hourly aggregated counts (pedestrian + bike, in/out). |
| `Spatiotemporal_Urban_Activity_Patterns.pptx` | 20-slide lecture deck. |
| `README.md` | This file. |

## Running the app

**Requirements:** Python 3.10+.

```bash
pip install streamlit pandas numpy scikit-learn altair pydeck
streamlit run app.py
```

The app has six pages, navigable via the left sidebar:

1. **Introduction** — paper summary and pipeline diagram.
2. **Dataset exploration** — interactive map of the 25 stations and a
   day-of-week × hour heatmap for any single station.
3. **Temporal profiles** — raw hourly profiles vs. shape-normalised profiles
   (peak = 100).
4. **Clustering** — elbow & silhouette diagnostics, cluster centroids and
   member list.
5. **Spatial analysis** — stations coloured by cluster on the Zurich map, with
   small-multiple profile charts.
6. **Student exercises** — four levels of tasks, from sidebar tweaking
   (Level 1) to replicating the paper's k-shape method (Level 4).

Sidebar controls: traffic modality (pedestrian only / bike only / both), day
type (weekday / weekend / all), month range, and `k`.

## What we reproduced from the paper

| Paper stage | Paper (Donostia) | This prototype (Zurich) |
| --- | --- | --- |
| **1. Raw data** | 1,378 POIs × Google Popular Times | 25 sensors × 15-min counts, full 2025 |
| **2. Unit of analysis** | Morphological Voronoi grid | Sensor location |
| **3. Hourly weighted occupancy** | Σ (P_i / P_j) × GPT_i | Σ counts per hour |
| **4. Time-series clustering** | **k-shape** (`tslearn`), 5 clusters | **k-means** (`sklearn`), adjustable `k` |
| **5. Spatial analysis** | NNA + Kernel Density Estimation | Coloured scatter map + facetted profiles |

The simplification from **k-shape → k-means** is didactic: k-means is built
into `scikit-learn`, easier to explain, and exposes the students to the
concepts of inertia and silhouette. Exercise 10 in the app asks them to swap
k-means for k-shape and discuss the differences.

## Teaching plan (2 × 90 min)

**Session 1 — Method walkthrough (90 min)**

1. Slides 1-13 (≈ 30 min).
2. Live demo of the Streamlit app, navigating pages 1 → 5 (≈ 30 min).
3. Pair discussion — what do the four clusters "mean" for Zurich? (≈ 30 min).

**Session 2 — Hands-on lab (90 min)**

1. Level 1 exercises — sidebar exploration (≈ 20 min).
2. Level 2 exercises — narrative interpretation + 1-page briefing (≈ 40 min).
3. Level 3-4 exercises as homework — swap algorithm, add weather /
   holidays, stability analysis.

## Data licences

- Pedestrian & bicycle counts: Stadt Zürich Open Data, reused under the
  city's open-data terms. Please cite the City of Zurich as source.
- Paper figures described in the slides are reproductions / paraphrases of
  the published figures by Barrena-Herrán et al. (2025), cited accordingly.

## Contact / Feedback

The prototype was prepared as teaching material. Suggestions, pull
requests and bug reports are welcome.
