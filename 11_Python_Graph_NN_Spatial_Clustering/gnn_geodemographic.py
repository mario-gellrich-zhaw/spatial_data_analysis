"""
Graph Convolutional Network for spatial geodemographic clustering.

Architecture: 2-layer GCN encoder + linear decoder (graph autoencoder).
Training: MSE reconstruction of normalised features via SGD with momentum.
Clustering: K-Means on 8-dimensional node embeddings.

Reference: De Sabbata S, Liu P (2023). IJGIS 37(12), 2464-2486.
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def flat_coords(geometry):
    if geometry["type"] == "Polygon":
        return geometry["coordinates"][0]
    if geometry["type"] == "MultiPolygon":
        return geometry["coordinates"][0][0]
    return []


def centroid(coords):
    c = np.asarray(coords, dtype=float)
    return c.mean(axis=0)   # [lng, lat]


def haversine_km(p1, p2):
    R = 6371.0
    lng1, lat1 = np.radians(p1)
    lng2, lat2 = np.radians(p2)
    dlat, dlng = lat2 - lat1, lng2 - lng1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlng / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


ZURICH = np.array([8.541, 47.376])

# ---------------------------------------------------------------------------
# Load real socio-economic features from Excel
# ---------------------------------------------------------------------------

FEAT_KEYS = ["income", "pop_density", "foreign_pct", "emp_rate"]


def load_features_from_json(features, json_path):
    """Load features from a previously exported features.json."""
    with open(json_path) as fh:
        feat = json.load(fh)
    nodes = []
    for f in features:
        bfs = str(int(f["properties"]["BFS"]))
        cen = centroid(flat_coords(f["geometry"]))
        dist = haversine_km(cen, ZURICH)
        d = feat[bfs]
        nodes.append({
            "bfs":         bfs,
            "name":        f["properties"]["NAME"],
            "district":    f["properties"]["BEZIRKSNAM"],
            "lng":         round(float(cen[0]), 4),
            "lat":         round(float(cen[1]), 4),
            "dist_km":     round(float(dist), 2),
            "income":      d["income"],
            "pop_density": d["popDens"],
            "foreign_pct": d["frgPct"],
            "emp_rate":    d["empRate"],
        })
    return nodes


def load_features(features, excel_path):
    """
    Load municipality features from Excel.
      income      = mean_taxable_income / 1000  (kCHF, mean taxable income per taxpayer)
      pop_density = pop_dens  (/km²)
      foreign_pct = frg_pct   (%)
      emp_rate    = emp / pop * 100  (%)

    Missing values are imputed from the mean of the 5 spatially nearest municipalities
    that have a valid value for that column.
    """
    df = pd.read_excel(
        excel_path,
        sheet_name="data_for_import",
        usecols=["bfs_number", "pop", "pop_dens", "frg_pct", "emp", "mean_taxable_income"],
    ).set_index("bfs_number")

    zh_bfs = [int(f["properties"]["BFS"]) for f in features]
    zh = df.loc[zh_bfs].copy()

    # Pre-compute centroids for spatial imputation
    centroids = {
        int(f["properties"]["BFS"]): centroid(flat_coords(f["geometry"]))
        for f in features
    }

    def spatial_mean(bfs, col, k=5):
        """Mean of col over the k nearest municipalities that have a valid value."""
        cen = centroids[bfs]
        candidates = [
            (haversine_km(cen, centroids[b]), zh.at[b, col])
            for b in zh_bfs
            if b != bfs and pd.notna(zh.at[b, col])
        ]
        candidates.sort(key=lambda x: x[0])
        return float(np.mean([v for _, v in candidates[:k]]))

    nodes = []
    for f in features:
        bfs = int(f["properties"]["BFS"])
        row = zh.loc[bfs]
        cen = centroids[bfs]
        dist = haversine_km(cen, ZURICH)

        pop    = float(row["pop"])
        income = (
            float(row["mean_taxable_income"]) / 1000
            if pd.notna(row["mean_taxable_income"])
            else spatial_mean(bfs, "mean_taxable_income") / 1000
        )
        emp = (
            float(row["emp"])
            if pd.notna(row["emp"])
            else spatial_mean(bfs, "emp")
        )
        emp_rate = round(emp / pop * 100, 1) if pop > 0 else 0.0

        nodes.append({
            "bfs":         str(bfs),
            "name":        f["properties"]["NAME"],
            "district":    f["properties"]["BEZIRKSNAM"],
            "lng":         round(float(cen[0]), 4),
            "lat":         round(float(cen[1]), 4),
            "dist_km":     round(float(dist), 2),
            "income":      round(income, 1),
            "pop_density": round(float(row["pop_dens"]), 1),
            "foreign_pct": round(float(row["frg_pct"]), 1),
            "emp_rate":    emp_rate,
        })
    return nodes

# ---------------------------------------------------------------------------
# Spatial adjacency from shared boundary coordinates
# ---------------------------------------------------------------------------

def build_adjacency(features):
    n = len(features)
    coord_sets = [
        {f"{x:.5f},{y:.5f}" for x, y in flat_coords(f["geometry"])}
        for f in features
    ]
    adj = [[] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if len(coord_sets[i] & coord_sets[j]) >= 2:
                adj[i].append(j)
                adj[j].append(i)
    return adj

# ---------------------------------------------------------------------------
# Normalised adjacency  D^{-½} (A + I) D^{-½}   (Kipf & Welling 2017)
# ---------------------------------------------------------------------------

def normalised_adj(adj, n):
    A = np.eye(n, dtype=float)
    for i, nbrs in enumerate(adj):
        for j in nbrs:
            A[i, j] = 1.0
    d_inv_sqrt = np.diag(1.0 / np.sqrt(A.sum(axis=1)))
    return d_inv_sqrt @ A @ d_inv_sqrt

# ---------------------------------------------------------------------------
# GCN layer with SGD + momentum backprop
# ---------------------------------------------------------------------------

class GCNLayer:
    def __init__(self, in_dim, out_dim, seed):
        rng   = np.random.default_rng(seed)
        scale = np.sqrt(2.0 / in_dim)
        self.W  = rng.normal(0, scale, (in_dim, out_dim))
        self.b  = np.zeros(out_dim)
        self.vW = np.zeros_like(self.W)
        self.vb = np.zeros_like(self.b)

    def forward(self, A_hat, X, relu=True):
        self._A, self._X = A_hat, X
        self._pre = A_hat @ X @ self.W + self.b
        return np.maximum(0, self._pre) if relu else self._pre

    def backward(self, grad_out, relu=True, lr=0.01, momentum=0.9):
        grad = grad_out * (self._pre > 0).astype(float) if relu else grad_out
        self.vW = momentum * self.vW - lr * (self._X.T @ self._A.T @ grad)
        self.vb = momentum * self.vb - lr * grad.sum(axis=0)
        self.W += self.vW
        self.b += self.vb
        return self._A @ grad @ self.W.T

# ---------------------------------------------------------------------------
# Graph Autoencoder:  GCN-encoder  →  linear decoder  →  feature reconstruction
# ---------------------------------------------------------------------------

class GCNAutoencoder:
    def __init__(self, in_dim, hidden=16, embed=8, layers=2):
        dims = [in_dim] + [hidden] * (layers - 1) + [embed]
        self.enc = [GCNLayer(dims[i], dims[i + 1], seed=1337 + i) for i in range(layers)]
        rng = np.random.default_rng(9999)
        self.Wd  = rng.normal(0, np.sqrt(2.0 / embed), (embed, in_dim))
        self.bd  = np.zeros(in_dim)
        self.vWd = np.zeros_like(self.Wd)
        self.vbd = np.zeros_like(self.bd)
        self._Z  = None

    def forward(self, A_hat, X):
        H = X
        for layer in self.enc:
            H = layer.forward(A_hat, H, relu=True)
        self._Z = H
        X_rec   = self._Z @ self.Wd + self.bd
        return X_rec, self._Z

    def backward(self, grad_rec, A_hat, lr=0.01, momentum=0.9):
        self.vWd = momentum * self.vWd - lr * (self._Z.T @ grad_rec)
        self.vbd = momentum * self.vbd - lr * grad_rec.sum(axis=0)
        self.Wd += self.vWd
        self.bd += self.vbd
        grad = grad_rec @ self.Wd.T
        for layer in reversed(self.enc):
            grad = layer.backward(grad, relu=True, lr=lr, momentum=momentum)

# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------

def train_autoencoder(A_hat, X_norm, hidden=16, embed=8, layers=2, epochs=400, lr=0.015, verbose=True):
    model = GCNAutoencoder(in_dim=X_norm.shape[1], hidden=hidden, embed=embed, layers=layers)
    for ep in range(epochs):
        X_rec, Z = model.forward(A_hat, X_norm)
        loss     = float(np.mean((X_rec - X_norm) ** 2))
        grad     = 2.0 * (X_rec - X_norm) / X_norm.size
        model.backward(grad, A_hat, lr=lr)
        if verbose and (ep % 80 == 0 or ep == epochs - 1):
            print(f"  epoch {ep:4d}/{epochs}   MSE = {loss:.6f}")
    _, Z = model.forward(A_hat, X_norm)
    return Z

# ---------------------------------------------------------------------------
# Main pipeline (callable from Flask without spawning a subprocess)
# ---------------------------------------------------------------------------

def run_pipeline(k=5, layers=2, verbose=True):
    base = Path(__file__).parent
    excel_path = base.parent / "municipality_data_with_taxable_income.xlsx"
    K = int(k)
    LAYERS = int(layers)

    if verbose:
        print("-" * 55)
        print("Graph-NN Geodemographic Segmentation")
        print("-" * 55)

    if verbose:
        print("\n[1/5] Loading GeoJSON ...")
    with open(base / "GEN_A4_GEMEINDEN_2019_epsg4326.json") as fh:
        geo = json.load(fh)
    features = geo["features"]
    if verbose:
        print(f"      {len(features)} municipalities")

    feat_json = base / "features.json"
    if feat_json.exists():
        if verbose:
            print("\n[2/5] Loading socio-economic features from features.json ...")
        nodes = load_features_from_json(features, feat_json)
        src = feat_json.name
    elif excel_path.exists():
        if verbose:
            print("\n[2/5] Loading socio-economic features from Excel ...")
        nodes = load_features(features, excel_path)
        src = excel_path.name
    else:
        raise FileNotFoundError(f"No feature source found: expected {feat_json} or {excel_path}")
    X_raw = np.array([[n[k] for k in FEAT_KEYS] for n in nodes], dtype=float)
    scaler = StandardScaler()
    X_norm = scaler.fit_transform(X_raw)
    if verbose:
        print(f"      Features: {FEAT_KEYS}")
        print(f"      Source: {src}")

    if verbose:
        print("\n[3/5] Building spatial adjacency graph ...")
    adj = build_adjacency(features)
    edge_count = sum(len(a) for a in adj) // 2
    degrees = [len(a) for a in adj]
    if verbose:
        print(f"      {edge_count} edges  (mean degree {np.mean(degrees):.1f})")

    dims_str = "->".join(["4"] + ["16"] * (LAYERS - 1) + ["8"])
    if verbose:
        print(f"\n[4/5] Training GCN autoencoder ({LAYERS} layers: {dims_str}) ...")
    A_hat = normalised_adj(adj, len(nodes))
    Z = train_autoencoder(A_hat, X_norm, hidden=16, embed=8, layers=LAYERS, epochs=400, lr=0.015, verbose=verbose)

    if verbose:
        print(f"\n[5/5] K-Means clustering (k={K}) ...")
    km = KMeans(n_clusters=K, random_state=42, n_init=20)
    labels = km.fit_predict(Z)

    # ── Print cluster profiles ──────────────────────────────────────────────
    if verbose:
        print("\n" + "-" * 55)
        print("Cluster profiles")
        print("-" * 55)
        for c in range(K):
            idx     = [i for i, l in enumerate(labels) if l == c]
            members = [nodes[i] for i in idx]
            avg     = lambda key: float(np.mean([m[key] for m in members]))
            names   = ", ".join(m["name"] for m in members[:5])
            if len(members) > 5:
                names += f" +{len(members)-5}"
            print(f"\nCluster {c+1}  ({len(members)} municipalities)")
            print(f"  income      {avg('income'):.1f}k CHF")
            print(f"  density     {avg('pop_density'):.0f}/km^2")
            print(f"  foreign     {avg('foreign_pct'):.1f}%")
            print(f"  emp. rate   {avg('emp_rate'):.1f}%")
            print(f"  places:     {names}")

    # ── Export cluster_results.json for web app ─────────────────────────────
    results = {
        "k":      K,
        "method": f"GCN autoencoder ({LAYERS}-layer, {dims_str}) + K-Means",
        "clusters": {n["bfs"]: int(labels[i]) for i, n in enumerate(nodes)},
        "nodes": [
            {**n, "cluster": int(labels[i]), "embed": Z[i].tolist()}
            for i, n in enumerate(nodes)
        ],
    }
    out = base / "cluster_results.json"
    with open(out, "w") as fh:
        json.dump(results, fh, indent=2)
    if verbose:
        print(f"\n[OK] Results written to {out.name}")

    # ── Export features.json for interactive JS GNN ─────────────────────────
    feat_export = {
        n["bfs"]: {
            "income":  n["income"],
            "popDens": n["pop_density"],
            "frgPct":  n["foreign_pct"],
            "empRate": n["emp_rate"],
        }
        for n in nodes
    }
    feat_out = base / "features.json"
    with open(feat_out, "w") as fh:
        json.dump(feat_export, fh, indent=2)
    if verbose:
        print(f"[OK] Features written to {feat_out.name}")
        print("  Open the web app and click 'Load Python Results'.")
        print("-" * 55)

    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--layers", type=int, default=2)
    args = parser.parse_args()
    run_pipeline(k=args.k, layers=args.layers, verbose=True)
