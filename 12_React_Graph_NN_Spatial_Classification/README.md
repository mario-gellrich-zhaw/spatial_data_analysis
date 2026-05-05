# Graph-based Geodemographic Segmentation Lab

An interactive graph visualisation of **graph neural network-style geodemographic classification**, designed as teaching material for undergraduate / graduate lectures in spatial data analysis and geomarketing.

> De Sabbata S, Liu P (2023).
> *A graph neural network framework for spatial geodemographic classification.*
> **International Journal of Geographical Information Science**, 37(12), 2464–2486.
> doi: 10.1080/13658816.2023.2266495

---

## What is in this folder

| File / folder | Purpose |
| --- | --- |
| `graph_geodemographic_lab.jsx` | Main React component — the interactive lab. |
| `src/main.jsx` | Vite / React entry point. |
| `index.html` | HTML shell. |
| `package.json` | npm dependencies (React 18, Vite, lodash). |
| `vite.config.js` | Vite dev server configuration. |
| `paper/` | Source paper (De Sabbata & Liu 2023). |
| `README.md` | This file. |

---

## Running the app

**Requirements:** Node.js 18+, npm.

```bash
cd 12_React_Graph_NN_Spatial_Classification
npm install
npm run dev
```

The app opens at `http://localhost:5173`.

---

## What the app demonstrates

The lab simulates a **graph database** (Neo4j-style) over 25–120 synthetic locations in the Zürich region. Each location node carries four sociodemographic attributes (income, age, population density, digital affinity). Two relationship types are built automatically:

| Relationship | Logic |
| --- | --- |
| `[:NEAR]` | K nearest neighbours by Haversine distance |
| `[:SIMILAR_TO]` | Pairs whose normalised feature distance falls below a threshold |

**Community detection** runs weighted label propagation on the resulting graph and colours nodes by discovered community.

### Key controls

| Control | Effect |
| --- | --- |
| Nodes slider | Number of synthetic locations (25–120) |
| K slider | Nearest-neighbour count for `[:NEAR]` edges |
| Sim slider | Similarity threshold for `[:SIMILAR_TO]` edges |
| Edge filter pills | Show all edges / NEAR only / SIMILAR_TO only |
| Labels checkbox | Toggle distance / type labels on edges |
| Detect communities | Run label propagation; colour nodes by cluster |
| Reset | Clear clustering and return to raw graph |

The graph uses a **pure-JS force simulation** (no D3): repulsion between all node pairs, spring attraction along filtered edges, and a weak centre-gravity term. Nodes are draggable; the canvas supports pan and scroll-to-zoom.

---

## Connection to the paper

De Sabbata & Liu (2023) propose replacing hand-crafted spatial weights matrices with a **graph neural network** that learns both spatial proximity and feature similarity simultaneously. This lab simplifies that idea into an interactive form:

| Paper | This lab |
| --- | --- |
| GNN learns edge weights end-to-end | Edge weights fixed by distance / feature thresholds |
| UK Output Areas (census units) | Synthetic Zürich locations from 8 archetypes |
| Trained on real census attributes | Simulated income, age, density, digital affinity |
| GNN embedding → k-means clustering | Weighted label propagation on the graph |
| Accuracy evaluated against ACORN classes | Dominant true-label per cluster shown as hint |

---

## Teaching plan (1 × 90 min)

**Part 1 — Concept introduction (30 min)**

1. Briefly introduce geodemographic segmentation and why geography matters (≈ 10 min).
2. Show the Cypher query bar — discuss what a graph representation buys over a plain attribute table (≈ 10 min).
3. Live demo: build the graph, inspect a node's property panel and relationships (≈ 10 min).

**Part 2 — Hands-on exploration (60 min)**

1. **Exercise 1 (easy):** Set K = 2, Sim = 0.5 and run community detection. How many communities form? What is the dominant true label in each cluster?
2. **Exercise 2 (medium):** Increase Sim from 0.5 to 1.5. How does the number of `[:SIMILAR_TO]` edges change? Does the number of detected communities grow or shrink? Why?
3. **Exercise 3 (medium):** Switch the edge filter to NEAR only, then to SIMILAR_TO only, and re-run detection each time. Which relationship type drives more cohesive communities?
4. **Exercise 4 (advanced):** Read Section 3 of De Sabbata & Liu (2023). What additional information does a GNN capture that label propagation on a fixed graph cannot? Write a short paragraph (≈ 150 words).

---

## Contact / Feedback

Teaching material for the *Spatial Data Analysis* course.
Suggestions, pull requests and bug reports are welcome.
