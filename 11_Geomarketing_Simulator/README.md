# MCI Geomarketing Simulator

An interactive simulation of the **Multiplicative Competitive Interaction (MCI) model**
for supermarket location analysis, designed as teaching material for undergraduate /
graduate lectures in spatial data analysis and geomarketing.

> Baviera-Puig, A., Buitrago-Vera, J., & Escribá-Pérez, C. (2016).
> *Geomarketing Models in Supermarket Location Strategies.*
> **Journal of Business Economics and Management**, 17(6), 1205–1221.
> doi: 10.3846/16111699.2015.1113198

---

## What is in this folder

| File / folder | Purpose |
| --- | --- |
| `app.py` | Streamlit web app — the interactive simulation. |
| `.streamlit/config.toml` | Theme configuration (blue colour scheme). |
| `paper/` | Source paper (Baviera-Puig et al. 2016). |
| `README.md` | This file. |

---

## Running the app

**Requirements:** Python 3.11+, conda environment `gisenv`.

```bash
conda activate gisenv
pip install plotly          # if not already installed
streamlit run app.py
```

The app opens at `http://localhost:8501`.

---

## The MCI model

The **Multiplicative Competitive Interaction (MCI) model** (Nakanishi & Cooper 1974)
computes the probability that a consumer at location *i* chooses supermarket *j*:

```
P_ij = ( A_j · d_ij^{-λ} ) / Σ_k ( A_k · d_ik^{-λ} )
```

where **A_j** is the composite attractiveness of store *j* and **λ** is the distance
sensitivity parameter.

**Attractiveness A_j** combines:

| Attribute | Source in paper | Proxy in app |
| --- | --- | --- |
| Floor area (m²) | Nielsen database | Slider 400–4 000 m² |
| Quality / ease of access | Manager survey (0–10) | Quality slider |
| Years operative | Nielsen database | Years slider |
| Parking | Site visit (binary) | Checkbox |

Binary variable transformation: `parking = e ≈ 2.72` if available, else `1`
(Mahajan & Jain 1977).

**Key paper finding:** distance is the single most important variable
(100 % normalised importance), followed by ease of pedestrian access (32 %)
and sociodemographic trade area characteristics.

---

## App tabs

| Tab | What it shows |
| --- | --- |
| 🗺 **Trade Areas** | Colour-coded map of dominant store per location; 400 m trade area circles. |
| 📊 **Choice Probability** | Continuous P_ij heatmap for a selected store. |
| 🆕 **New Store Scenario** | Impact on market shares when a new competitor opens. |
| 📈 **Sensitivity Analysis** | Market share curves over λ ∈ [0.5, 3.0]. |
| 👥 **Consumer Simulation** | Monte Carlo consumer placement + animated shopping trips. |
| 📚 **Exercises** | Four-level student exercises. |

---

## What we simplified vs. the paper

| Paper (Castellón de la Plana) | This simulation |
| --- | --- |
| 19 real supermarkets | 2–5 configurable synthetic stores |
| 9 899 road sections (census units) | 80 × 80 continuous grid |
| Sociodemographic PCA factors (4 components) | Single subjective quality score |
| Zeta-squared transformation of interval variables | Direct normalised scores |
| OLS / GLS / neural-network calibration | Parameters set interactively |
| Loyalty-scheme sales data as ground truth | Population-weighted P_ij |

---

## Teaching plan (2 × 90 min)

**Session 1 — Method walkthrough (90 min)**

1. Introduce the MCI formula and the paper's research question (≈ 30 min).
2. Live demo of the app: tabs 1–4 with the default 5-store configuration (≈ 30 min).
3. Pair discussion — which parameter matters most for strategy? (≈ 30 min).

**Session 2 — Hands-on lab (90 min)**

1. Level 1 exercises — sidebar and tab exploration (≈ 20 min).
2. Level 2 exercises — interpret results and write a short briefing (≈ 40 min).
3. Level 3–4 exercises as take-home — code extensions and paper connection.

---

## Key findings from Baviera-Puig et al. (2016)

- Distance has **100 % normalised importance** — the strongest predictor by far.
- **Ease of pedestrian access** ranks second (32 %).
- **Sociodemographic characteristics** of the trade area (% unemployed 30 %,
  % separated 29 %) matter as much as store features.
- Neural networks outperformed OLS and GLS (R² = 88 % vs. 84 %).
- Adding **spatial non-stationarity** (relative distances between stores, Equation 6)
  changes which variables dominate — useful for multi-store network analysis.
- A single store's error in the sales forecast was −6.71 %, demonstrating
  practical utility for opening-decision budgeting.

---

## Contact / Feedback

Teaching material for the *Spatial Data Analysis* course.
Suggestions, pull requests and bug reports are welcome.
