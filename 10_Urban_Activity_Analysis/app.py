"""
Spatiotemporal Urban Activity Patterns — Student Prototype
===========================================================

A simplified, didactic re-implementation of the methodology presented in:

    Barrena-Herrán, M., Modrego-Monforte, I., & Grijalba, O. (2025).
    Revealing Spatiotemporal Urban Activity Patterns:
    A Machine Learning Study Using Google Popular Times.
    ISPRS Int. J. Geo-Inf., 14, 221.

Instead of Google Popular Times POI data for Donostia-San Sebastián, this app
uses open pedestrian & bicycle count data for the City of Zurich (2025) to
illustrate the same pipeline:

    1. Load & explore spatiotemporal data
    2. Aggregate to hourly profiles per location
    3. Normalise profiles (shape-based comparison, like k-shape)
    4. Cluster profiles with k-means and inspect cluster centroids
    5. Map the spatial distribution of the clusters

Run:
    streamlit run app.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import altair as alt
import pydeck as pdk
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score


DATA_DIR = Path(__file__).parent / "data"

# --------------------------------------------------------------------------- #
# Page configuration
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="Spatiotemporal Urban Activity Patterns — Zurich",
    layout="wide",
    page_icon=":cityscape:",
)

PRIMARY = "#065A82"     # ocean deep blue
ACCENT = "#F96167"      # coral
LIGHT = "#F2F2F2"


CLUSTER_PALETTE = [
    "#065A82", "#F96167", "#2C5F2D", "#FFC700", "#6D2E46",
    "#028090", "#B85042",
]

# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner="Loading locations...")
def load_locations() -> pd.DataFrame:
    """Load sensor location metadata from CSV."""
    df = pd.read_csv(DATA_DIR / "locations.csv")
    return df


@st.cache_data(show_spinner="Loading hourly counts...")
def load_hourly() -> pd.DataFrame:
    """Load hourly aggregated count data from CSV."""
    df = pd.read_csv(DATA_DIR / "hourly_counts.csv", parse_dates=["date"])
    return df


@st.cache_data
def build_profiles(hourly_df: pd.DataFrame,
                   day_filter: str,
                   month_filter: tuple[int, int],
                   modality_filter: str) -> pd.DataFrame:
    """Return wide matrix (location x 24 hours) of AVERAGE counts per hour."""
    df = hourly_df.copy()
    df = df[(df["month"] >= month_filter[0]) & (df["month"] <= month_filter[1])]

    if day_filter == "Weekday (Mon-Fri)":
        df = df[df["dow"] < 5]
    elif day_filter == "Weekend (Sat-Sun)":
        df = df[df["dow"] >= 5]

    value_col = {"Pedestrian + Bike": "total",
                 "Pedestrian only": "fuss",
                 "Bike only": "velo"}[modality_filter]

    prof = (df.groupby(["FK_STANDORT", "hour"])[value_col]
              .mean()
              .unstack(fill_value=0.0))
    prof = prof.reindex(columns=range(24), fill_value=0.0)
    return prof


def normalise_profiles(prof: pd.DataFrame) -> pd.DataFrame:
    """Scale each row to peak = 100 (so we compare SHAPE, not magnitude)."""
    arr = prof.values.astype(float)
    row_max = arr.max(axis=1, keepdims=True)
    row_max[row_max == 0] = 1.0
    scaled = 100 * arr / row_max
    return pd.DataFrame(scaled, index=prof.index, columns=prof.columns)


@st.cache_data
def run_clustering(norm_prof: pd.DataFrame, n_clusters: int, seed: int = 42) -> np.ndarray:
    """Fit k-means and return integer cluster labels for each row."""
    if len(norm_prof) < n_clusters:
        return np.zeros(len(norm_prof), dtype=int)
    km = KMeans(n_clusters=n_clusters, n_init=25, random_state=seed)
    cluster_labels = km.fit_predict(norm_prof.values)
    return cluster_labels


@st.cache_data
def compute_location_weights(hourly_df: pd.DataFrame,
                             locations_df: pd.DataFrame) -> pd.DataFrame:
    """Mean total count per station merged with lat/lon — used for heatmap."""
    weights = (hourly_df.groupby("FK_STANDORT")["total"].mean()
                        .reset_index(name="weight"))
    return locations_df.merge(weights, left_on="fk_standort",
                              right_on="FK_STANDORT", how="inner")


@st.cache_data
def compute_k_scan(norm_prof: pd.DataFrame,
                   k_range: tuple[int, int]) -> pd.DataFrame:
    """Compute inertia and silhouette score for a range of k values."""
    rows = []
    for n_k in range(k_range[0], k_range[1] + 1):
        if n_k >= len(norm_prof):
            continue
        km = KMeans(n_clusters=n_k, n_init=10, random_state=42)
        labs = km.fit_predict(norm_prof.values)
        rows.append({"k": n_k,
                     "inertia": km.inertia_,
                     "silhouette": silhouette_score(norm_prof.values, labs)
                     if n_k > 1 else np.nan})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
st.sidebar.title("Controls")

page = st.sidebar.radio(
    "Section",
    [
        "1. Introduction",
        "2. Dataset exploration",
        "3. Temporal profiles",
        "4. Clustering",
        "5. Spatial analysis",
        "6. Student exercises",
    ],
)

st.sidebar.divider()
st.sidebar.caption("**Analysis parameters**")

modality = st.sidebar.selectbox(
    "Traffic modality",
    ["Pedestrian + Bike", "Pedestrian only", "Bike only"],
    index=0,
)
day_type = st.sidebar.selectbox(
    "Day type",
    ["Weekday (Mon-Fri)", "Weekend (Sat-Sun)", "All days"],
    index=0,
)
month_range = st.sidebar.slider(
    "Months to include",
    min_value=1, max_value=12, value=(1, 12),
)
k = st.sidebar.slider("Number of clusters (k)", 2, 7, 4)

# --------------------------------------------------------------------------- #
# Load data once
# --------------------------------------------------------------------------- #
locations = load_locations()
hourly = load_hourly()

profiles = build_profiles(hourly, day_type, month_range, modality)
norm_profiles = normalise_profiles(profiles)
labels = run_clustering(norm_profiles, k)
cluster_df = pd.DataFrame(
    {"FK_STANDORT": norm_profiles.index, "cluster": labels}
)
loc_cluster = locations.merge(cluster_df,
                              left_on="fk_standort",
                              right_on="FK_STANDORT",
                              how="inner")

# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #
if page == "1. Introduction":
    st.title(":cityscape: Spatiotemporal Urban Activity Patterns")
    st.caption(
        "A didactic prototype based on *Barrena-Herrán et al., 2025* — "
        "applied to Zurich pedestrian & bike counts."
    )

    col_a, col_b = st.columns([1.1, 1])
    with col_a:
        st.subheader("Research question")
        st.write(
            "**Can we discover distinct *daily activity rhythms* in a city "
            "— and do they align with urban form and function?**"
        )
        st.markdown(
            "The paper proposes a five-stage pipeline:\n"
            "1. Collect spatiotemporal activity data (POIs + Popular Times)\n"
            "2. Define a unit of analysis (morphological grid cells)\n"
            "3. Compute hourly weighted occupancy per unit\n"
            "4. Normalise profiles and cluster them with **k-shape**\n"
            "5. Analyse the spatial distribution of the clusters\n"
        )

        st.subheader("Our simplification")
        st.markdown(
            "For teaching purposes we replace step 1–3 with an **open "
            "sensor dataset** (no web scraping required) and use the simpler "
            "**k-means** algorithm in step 4. The *conceptual* workflow is "
            "identical and the students reproduce every stage themselves."
        )

    with col_b:
        st.subheader("Data in a nutshell")
        st.metric("Active counting stations", len(locations))
        st.metric("15-min observations (2025)",
                  f"{int(hourly.shape[0] * 4):,}")
        st.metric("Unique (station × hour) rows", f"{len(hourly):,}")
        st.info(
            "Source: City of Zurich Open Data "
            "(*Verkehrszählungen Fussgänger & Velo*)."
        )

    st.divider()
    st.subheader("Pipeline")
    st.graphviz_chart("""
    digraph G {
        rankdir=LR;
        node [shape=box, style="rounded,filled", fillcolor="#E8F1F8",
              fontname="Arial"];
        A [label="01 Raw counts\\n(15-min)"];
        B [label="02 Locations\\n(25 sensors)"];
        C [label="03 Hourly\\nprofiles"];
        D [label="04 Shape-\\nnormalised"];
        E [label="05 k-means\\nclusters"];
        F [label="06 Spatial\\nmap"];
        A -> C; B -> C; C -> D -> E -> F;
    }
    """)


elif page == "2. Dataset exploration":
    st.title("2 · Dataset exploration")
    st.caption("Look at the raw input before analysing it — always.")

    # Map of all active locations
    st.subheader("Counting stations in Zurich")

    view = pdk.ViewState(
        latitude=locations["lat"].mean(),
        longitude=locations["lon"].mean(),
        zoom=11.5, pitch=0,
    )
    loc_layer = pdk.Layer(
        "ScatterplotLayer",
        data=locations,
        get_position="[lon, lat]",
        get_fill_color=[139, 0, 0, 200],
        get_radius=80,
        pickable=True,
    )
    st.pydeck_chart(pdk.Deck(
        layers=[loc_layer],
        initial_view_state=view,
        tooltip={"text": "{bezeichnung}\nvelo={velo}  fuss={fuss}"},
        map_style="light",
    ))

    col1, col2 = st.columns(2)
    col1.metric("Stations counting bikes", int(locations["velo"].sum()))
    col2.metric("Stations counting pedestrians", int(locations["fuss"].sum()))

    st.subheader("Hourly counts at a single station")
    stations_with_data = set(hourly["FK_STANDORT"].unique())
    available = locations[locations["fk_standort"].isin(stations_with_data)]
    sel_name = st.selectbox("Station", available["bezeichnung"].tolist())
    sel_id = int(available.loc[available["bezeichnung"] == sel_name,
                               "fk_standort"].iloc[0])
    sub = hourly[hourly["FK_STANDORT"] == sel_id].copy()

    col1, col2 = st.columns([1.5, 1])
    with col1:
        # Weekly heatmap: day-of-week × hour
        heat = (sub.groupby(["dow", "hour"])["total"].mean()
                  .reset_index())
        heat["dow_label"] = heat["dow"].map(
            {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu",
             4: "Fri", 5: "Sat", 6: "Sun"})
        chart = alt.Chart(heat).mark_rect().encode(
            x=alt.X("hour:O", title="Hour"),
            y=alt.Y("dow_label:N", sort=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],
                    title="Day"),
            color=alt.Color("total:Q",
                            scale=alt.Scale(scheme="blues"),
                            title="Avg count"),
            tooltip=["dow_label", "hour", alt.Tooltip("total:Q", format=".1f")],
        ).properties(height=260, title="Average hourly activity heatmap")
        st.altair_chart(chart, use_container_width=True)
    with col2:
        month_ts = (sub.groupby("month")["total"].sum().reset_index())
        ts_chart = alt.Chart(month_ts).mark_bar(color=PRIMARY).encode(
            x=alt.X("month:O", title="Month (2025)"),
            y=alt.Y("total:Q", title="Total counts"),
        ).properties(height=260, title="Seasonality")
        st.altair_chart(ts_chart, use_container_width=True)

    st.caption("Tip: Change the station above to see how the rhythm changes "
               "between, e.g., a station at the Bahnhof vs. a residential "
               "street.")


elif page == "3. Temporal profiles":
    st.title("3 · Temporal profiles")
    st.caption("Step 3 of the pipeline — compute a daily 'fingerprint' for "
               "every sensor.")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Raw hourly averages")
        long = profiles.reset_index().melt(id_vars="FK_STANDORT",
                                           var_name="hour",
                                           value_name="count")
        chart = alt.Chart(long).mark_line(opacity=0.35).encode(
            x=alt.X("hour:Q", title="Hour of day"),
            y=alt.Y("count:Q", title="Avg counts per hour"),
            color=alt.Color("FK_STANDORT:N", legend=None),
            tooltip=["FK_STANDORT", "hour", "count"],
        ).properties(height=320)
        st.altair_chart(chart, use_container_width=True)
        st.caption("Absolute magnitudes differ a lot — a quiet residential "
                   "sensor is barely visible next to a busy hotspot.")

    with col2:
        st.subheader("Shape-normalised (peak = 100)")
        long_n = norm_profiles.reset_index().melt(id_vars="FK_STANDORT",
                                                  var_name="hour",
                                                  value_name="value")
        chart_n = alt.Chart(long_n).mark_line(opacity=0.4).encode(
            x=alt.X("hour:Q", title="Hour of day"),
            y=alt.Y("value:Q", title="% of own peak"),
            color=alt.Color("FK_STANDORT:N", legend=None),
            tooltip=["FK_STANDORT", "hour",
                     alt.Tooltip("value:Q", format=".1f")],
        ).properties(height=320)
        st.altair_chart(chart_n, use_container_width=True)
        st.caption("After normalisation we can compare the *shape* of the "
                   "profiles directly — this is the input for clustering.")

    with st.expander("Why normalise?"):
        st.markdown(
            "The paper uses **k-shape**, a clustering method tailored to "
            "normalised time-series. The intuition is the same as here: "
            "two sensors with a clear morning + evening commuter peak are "
            "'similar' regardless of whether one counts 500 or 5,000 "
            "pedestrians per hour. Dividing each series by its peak puts "
            "every sensor on a common [0, 100] scale."
        )


elif page == "4. Clustering":
    st.title("4 · Clustering")
    st.caption("Step 4 — group stations with similar rhythms.")

    # Elbow + Silhouette
    st.subheader("How many clusters?")
    scan = compute_k_scan(norm_profiles, (2, 7))

    col1, col2 = st.columns(2)
    with col1:
        elbow = alt.Chart(scan).mark_line(
            point=True, color=PRIMARY, strokeWidth=3).encode(
            x=alt.X("k:O", title="k", axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("inertia:Q", title="Inertia (lower = tighter)"),
        ).properties(height=280, title="Elbow method")
        st.altair_chart(elbow, use_container_width=True)
    with col2:
        sil = alt.Chart(scan).mark_line(
            point=True, color=ACCENT, strokeWidth=3).encode(
            x=alt.X("k:O", axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("silhouette:Q", title="Silhouette (higher = better)"),
        ).properties(height=280, title="Silhouette score")
        st.altair_chart(sil, use_container_width=True)

    st.info(f"Selected **k = {k}** in the sidebar. Try changing it and watch "
            "the cluster shapes below.")

    # Centroids
    st.subheader("Cluster centroids (average shape)")
    norm_with_lbl = norm_profiles.copy()
    norm_with_lbl["cluster"] = labels
    centroids = (norm_with_lbl.groupby("cluster").mean()
                              .reset_index()
                              .melt(id_vars="cluster",
                                    var_name="hour", value_name="value"))
    centroids["cluster_label"] = "C" + (centroids["cluster"] + 1).astype(str)

    color_scale = alt.Scale(
        domain=[f"C{i+1}" for i in range(k)],
        range=CLUSTER_PALETTE[:k],
    )

    cent_chart = alt.Chart(centroids).mark_line(strokeWidth=3).encode(
        x=alt.X("hour:Q", title="Hour of day"),
        y=alt.Y("value:Q", title="% of peak"),
        color=alt.Color("cluster_label:N", title="Cluster",
                        scale=color_scale),
    ).properties(height=340)
    st.altair_chart(cent_chart, use_container_width=True)

    # Cluster detail: stacked members
    st.subheader("Members per cluster")
    counts = (loc_cluster.groupby("cluster").size()
                                  .reset_index(name="n"))
    counts["cluster_label"] = "C" + (counts["cluster"] + 1).astype(str)
    bar = alt.Chart(counts).mark_bar().encode(
        x=alt.X("cluster_label:N", title="Cluster"),
        y=alt.Y("n:Q", title="# stations"),
        color=alt.Color("cluster_label:N", scale=color_scale, legend=None),
        tooltip=["cluster_label", "n"],
    ).properties(height=240)
    st.altair_chart(bar, use_container_width=True)

    with st.expander("Station list"):
        show = loc_cluster[["cluster", "bezeichnung", "velo", "fuss"]]\
            .sort_values(["cluster", "bezeichnung"])
        show["cluster"] = "C" + (show["cluster"] + 1).astype(str)
        st.dataframe(show, use_container_width=True, hide_index=True)


elif page == "5. Spatial analysis":
    st.title("5 · Spatial analysis")
    st.caption("Step 5 — where do the rhythms live?")

    def hex_to_rgb(h):
        """Convert a hex colour string to an [R, G, B, A] list."""
        h = h.lstrip("#")
        return [int(h[i:i+2], 16) for i in (0, 2, 4)] + [230]

    loc_vis = loc_cluster.copy()
    loc_vis["color"] = loc_vis["cluster"].apply(
        lambda c: hex_to_rgb(CLUSTER_PALETTE[c % len(CLUSTER_PALETTE)]))
    loc_vis["cluster_label"] = "C" + (loc_vis["cluster"] + 1).astype(str)

    col1_ctrl, col2_ctrl = st.columns([2, 1])
    with col1_ctrl:
        cluster_filter = st.multiselect(
            "Filter clusters to display",
            options=sorted(loc_vis["cluster_label"].unique()),
            default=sorted(loc_vis["cluster_label"].unique()),
        )
    with col2_ctrl:
        show_heatmap = st.toggle("Activity density heatmap", value=True)
        heatmap_opacity = st.slider("Heatmap opacity", 0.1, 1.0, 0.55, 0.05,
                                    disabled=not show_heatmap)

    loc_vis_f = loc_vis[loc_vis["cluster_label"].isin(cluster_filter)]

    view = pdk.ViewState(
        latitude=loc_vis["lat"].mean(),
        longitude=loc_vis["lon"].mean(),
        zoom=11.5, pitch=0,
    )

    # Heatmap: weighted by mean total count across all stations (not filtered)
    loc_weights = compute_location_weights(hourly, locations)
    heat_layer = pdk.Layer(
        "HeatmapLayer",
        data=loc_weights,
        get_position="[lon, lat]",
        get_weight="weight",
        radius_pixels=90,
        opacity=heatmap_opacity,
        color_range=[
            [255, 255, 204],
            [254, 217, 118],
            [254, 153,  41],
            [227,  26,  28],
            [128,   0,  38],
        ],
    )

    col_layer = pdk.Layer(
        "ScatterplotLayer",
        data=loc_vis_f,
        get_position="[lon, lat]",
        get_fill_color="color",
        get_radius=140,
        pickable=True,
    )

    layers = ([heat_layer, col_layer] if show_heatmap else [col_layer])
    st.pydeck_chart(pdk.Deck(
        layers=layers,
        initial_view_state=view,
        tooltip={"text": "{bezeichnung}\nCluster: {cluster_label}"},
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
    ))

    # Legend
    legend_cols = st.columns(len(cluster_filter) if cluster_filter else 1)
    for i, lbl in enumerate(sorted(cluster_filter)):
        color = CLUSTER_PALETTE[(int(lbl[1:]) - 1) % len(CLUSTER_PALETTE)]
        with legend_cols[i]:
            st.markdown(
                f"<div style='display:flex;align-items:center'>"
                f"<div style='width:14px;height:14px;background:{color};"
                f"border-radius:50%;margin-right:8px'></div><b>{lbl}</b></div>",
                unsafe_allow_html=True)

    # Cluster profile mini-charts
    st.subheader("Profile vs. location")
    norm_with_lbl = norm_profiles.copy()
    norm_with_lbl["cluster"] = labels
    long = norm_with_lbl.reset_index().melt(
        id_vars=["FK_STANDORT", "cluster"],
        var_name="hour", value_name="value")
    long["cluster_label"] = "C" + (long["cluster"] + 1).astype(str)
    long = long[long["cluster_label"].isin(cluster_filter)]

    chart = alt.Chart(long).mark_line(opacity=0.35).encode(
        x=alt.X("hour:Q"),
        y=alt.Y("value:Q", title="% of peak"),
        color=alt.Color("cluster_label:N",
                        scale=alt.Scale(
                            domain=[f"C{i+1}" for i in range(k)],
                            range=CLUSTER_PALETTE[:k]),
                        legend=None),
        detail="FK_STANDORT:N",
    ).properties(height=180).facet(
        column=alt.Column("cluster_label:N", title=None))
    st.altair_chart(chart, use_container_width=False)


elif page == "6. Student exercises":
    st.title("6 · Exercises for students")
    st.info("These exercises are **voluntary**. They are meant to deepen your "
            "understanding at your own pace — none of them will be graded.")

    st.markdown("""
### Level 1 — Reproduce
1. In the sidebar, switch **modality** between *Pedestrian only* and *Bike only*.
   Do you get the same number of clusters with the same stations in them?
2. Compare **weekday** vs. **weekend** clustering. Which stations change group?
3. Change the **month range** to summer (6–8) vs. winter (12–2).
   Which rhythms are seasonally stable?

### Level 2 — Explain
4. For k = 4, describe each cluster centroid in one sentence
   (commuter peak, evening peak, flat profile, leisure pattern, ...).
5. Look up two of the stations on a map — do the clusters you find
   match what you would expect given the land use there?

### Level 3 — Extend
6. Replace `KMeans` with another algorithm (e.g. `AgglomerativeClustering`
   or `tslearn.KShape`). Does the clustering change?
7. Add weather or holiday data. Does a different rhythm emerge on rainy days?
8. Add a 2-D embedding (PCA or UMAP of the 24-dim profiles) and color it
   by cluster to check separability.
9. Compute a *cluster stability* score by running k-means with 20 random
   seeds and measuring how often two stations end up in the same cluster.

### Level 4 — Connect to the paper
10. The paper uses k-shape because it is robust to time shifts. Construct
    a toy example (two sine waves offset by 1 hour) where k-means assigns
    them to different clusters but k-shape assigns them to the same cluster.
""")

    st.divider()
    st.caption("Have fun exploring urban rhythms! — "
               "`spatiotemporal-urban-activity` prototype")

# --------------------------------------------------------------------------- #
# Footer
# --------------------------------------------------------------------------- #
st.sidebar.divider()
st.sidebar.caption(
    "Data: Stadt Zürich Open Data · Method: "
    "Barrena-Herrán et al., ISPRS Int. J. Geo-Inf. 14 (2025) 221"
)
