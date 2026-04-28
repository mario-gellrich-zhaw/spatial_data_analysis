"""
MCI Geomarketing Simulator
Multiplicative Competitive Interaction (MCI) model for supermarket location analysis.
Based on: Baviera-Puig, Buitrago-Vera & Escribá-Pérez (2016).
  Geomarketing Models in Supermarket Location Strategies.
  Journal of Business Economics and Management, 17(6), 1205–1221.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MCI Geomarketing Simulator",
    layout="wide",
    page_icon="🛒",
)

# ── Constants ──────────────────────────────────────────────────────────────────
CITY_KM = 10
GRID_N = 80

PRIMARY = "#065A82"   # ocean deep blue (matches 10_Urban_Activity_Analysis)
ACCENT  = "#F96167"   # coral

COLORS = ["#065A82", "#F96167", "#2C5F2D", "#FFC700", "#6D2E46"]

DEFAULTS = [
    dict(name="Store A", x=2.5, y=7.5, size=1200, quality=7, years=8,  parking=True),
    dict(name="Store B", x=7.5, y=7.5, size=2500, quality=6, years=15, parking=True),
    dict(name="Store C", x=5.0, y=2.5, size=900,  quality=8, years=5,  parking=False),
    dict(name="Store D", x=2.5, y=3.0, size=1800, quality=5, years=20, parking=True),
    dict(name="Store E", x=7.5, y=3.0, size=600,  quality=9, years=3,  parking=False),
]

x_lin = np.linspace(0, CITY_KM, GRID_N)
y_lin = np.linspace(0, CITY_KM, GRID_N)
XX, YY = np.meshgrid(x_lin, y_lin)

MAP_LAYOUT = dict(
    xaxis=dict(title="X (km)", range=[-0.3, CITY_KM + 0.3]),
    yaxis=dict(title="Y (km)", range=[-0.3, CITY_KM + 0.3], scaleanchor="x"),
    margin=dict(l=0, r=0, t=40, b=0),
    height=470,
    plot_bgcolor="white",
)


# ── Core model functions ───────────────────────────────────────────────────────

def make_population(mode: str) -> np.ndarray:
    """Return a (GRID_N, GRID_N) population density array."""
    if mode == "Uniform":
        return np.ones((GRID_N, GRID_N))
    # Four urban population clusters
    centers = [(2.5, 2.5, 1.0), (7.5, 7.5, 1.2), (5.0, 7.0, 0.8), (7.5, 2.5, 0.9)]
    pop = sum(
        w * np.exp(-((XX - cx) ** 2 + (YY - cy) ** 2) / 2.5)
        for cx, cy, w in centers
    )
    return pop / pop.max()


def store_attractiveness(s: dict, alpha: float, beta: float, gamma: float) -> float:
    """Composite attractiveness A_j for store s (scalar)."""
    A = (s["size"] / 1000) ** alpha
    A *= (s["quality"] / 10) ** beta
    A *= (max(s["years"], 1) / 20) ** gamma
    # Binary parking variable: exp(1)=e if parking, exp(0)=1 if not
    # (Mahajan & Jain 1977 transformation)
    A *= np.e if s["parking"] else 1.0
    return max(A, 1e-10)


def calc_mci(
    stores: list[dict],
    lam: float,
    alpha: float,
    beta: float,
    gamma: float,
) -> np.ndarray:
    """
    Compute MCI choice probabilities P_ij for all grid cells.

    Returns array of shape (n_stores, GRID_N, GRID_N).
    P_ij = A_j * d_ij^{-lam} / sum_k( A_k * d_ik^{-lam} )
    """
    n = len(stores)
    attract = np.zeros((n, GRID_N, GRID_N))
    for j, s in enumerate(stores):
        A = store_attractiveness(s, alpha, beta, gamma)
        dist = np.clip(
            np.sqrt((XX - s["x"]) ** 2 + (YY - s["y"]) ** 2), 0.05, None
        )
        attract[j] = A / dist ** lam
    total = attract.sum(axis=0)
    return attract / np.where(total > 0, total, 1e-10)


def market_shares(probs: np.ndarray, pop: np.ndarray) -> list[float]:
    """Population-weighted market shares (%) for each store."""
    return [
        float((probs[j] * pop).sum() / pop.sum() * 100)
        for j in range(probs.shape[0])
    ]


def discrete_colorscale(colors: list[str]) -> list:
    """Build a step/discrete colorscale from a list of hex colors."""
    n = len(colors)
    cs = []
    for j, c in enumerate(colors):
        cs += [[j / n, c], [(j + 1) / n, c]]
    return cs


def add_store_markers(fig, stores: list[dict], shares: list[float] | None = None):
    """Overlay square store markers with hover info."""
    for j, s in enumerate(stores):
        hover = (
            f"<b>{s['name']}</b><br>"
            f"Floor area: {s['size']} m²<br>"
            f"Quality: {s['quality']}/10<br>"
            f"Years operative: {s['years']}<br>"
            f"Parking: {'Yes' if s['parking'] else 'No'}"
        )
        if shares is not None:
            hover += f"<br><b>Market share: {shares[j]:.1f}%</b>"
        fig.add_trace(
            go.Scatter(
                x=[s["x"]],
                y=[s["y"]],
                mode="markers+text",
                marker=dict(
                    size=16,
                    color=COLORS[j % len(COLORS)],
                    symbol="square",
                    line=dict(color="white", width=2),
                ),
                text=[s["name"]],
                textposition="top center",
                textfont=dict(size=10, color="black"),
                name=s["name"],
                hovertemplate=hover + "<extra></extra>",
                showlegend=False,
            )
        )
    return fig


def sample_consumers(
    n: int,
    pop: np.ndarray,
    x_lin: np.ndarray,
    y_lin: np.ndarray,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """Sample n consumer home positions weighted by population density."""
    flat = pop.flatten()
    flat = flat / flat.sum()
    idx = rng.choice(len(flat), size=n, p=flat)
    rows, cols = np.unravel_index(idx, pop.shape)
    cell_w = x_lin[1] - x_lin[0]
    cell_h = y_lin[1] - y_lin[0]
    cx = x_lin[cols] + rng.uniform(-cell_w / 2, cell_w / 2, n)
    cy = y_lin[rows] + rng.uniform(-cell_h / 2, cell_h / 2, n)
    return np.clip(cx, 0, CITY_KM), np.clip(cy, 0, CITY_KM)


def assign_stores_array(
    cx: np.ndarray,
    cy: np.ndarray,
    stores: list[dict],
    lam: float,
    alpha: float,
    beta: float,
    gamma: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Probabilistically assign each consumer to a store using their local MCI P_ij."""
    n_c, n_s = len(cx), len(stores)
    attract = np.zeros((n_c, n_s))
    for j, s in enumerate(stores):
        A = store_attractiveness(s, alpha, beta, gamma)
        dist = np.clip(np.sqrt((cx - s["x"]) ** 2 + (cy - s["y"]) ** 2), 0.05, None)
        attract[:, j] = A / dist ** lam
    total = attract.sum(axis=1, keepdims=True)
    p_ij = attract / np.where(total > 0, total, 1e-10)
    return np.array([rng.choice(n_s, p=p_ij[i]) for i in range(n_c)])


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Model Parameters")

    with st.expander("Sensitivity Parameters", expanded=True):
        lam = st.slider(
            "λ — Distance decay",
            0.5, 3.0, 1.5, 0.1,
            help="Higher → consumers more sensitive to distance (stronger decay). "
                 "Baviera-Puig et al.: distance is the #1 variable (100% importance).",
        )
        alpha = st.slider(
            "α — Store size weight",
            0.0, 2.0, 1.0, 0.1,
            help="Sensitivity to floor area. Paper: ~14% normalized importance.",
        )
        beta = st.slider(
            "β — Quality score weight",
            0.0, 2.0, 1.0, 0.1,
            help="Sensitivity to subjective quality rating.",
        )
        gamma = st.slider(
            "γ — Years operative weight",
            0.0, 2.0, 0.5, 0.1,
            help="Sensitivity to years operative (proxy for brand recognition). "
                 "Paper: 23% normalized importance.",
        )

    with st.expander("City & Sales Settings", expanded=True):
        pop_mode = st.radio(
            "Population distribution",
            ["Uniform", "Urban clusters"],
            index=1,
            help="Uniform = equal density everywhere; "
                 "Urban clusters = realistic city centre / suburb pattern.",
        )
        food_spend = st.number_input(
            "Annual food spend per capita (€)",
            value=5000, min_value=500, max_value=20000, step=100,
        )
        pop_total = st.number_input(
            "City population",
            value=50000, min_value=5000, max_value=500000, step=5000,
        )

    st.divider()
    n_stores = st.slider("Number of supermarkets", 2, 5, 5)


# ── Title & description ────────────────────────────────────────────────────────
st.title("🛒 MCI Geomarketing Simulator")
st.markdown(
    "**Multiplicative Competitive Interaction (MCI) Model** — "
    "interactive simulation of supermarket trade area competition and market share.  \n"
    "*Baviera-Puig, Buitrago-Vera & Escribá-Pérez (2016). "
    "Geomarketing Models in Supermarket Location Strategies. "
    "Journal of Business Economics and Management, 17(6), 1205–1221.*"
)

with st.expander("ℹ️ Model Description", expanded=False):
    col_desc, col_form = st.columns([3, 2])
    with col_desc:
        st.markdown(
            """
**Core idea (Nakanishi & Cooper 1974):** Each supermarket exerts an *attraction force* on
consumers that increases with store quality and decreases with distance. The probability that
a consumer chooses a store is its attraction divided by the total attraction of all stores.

**Attractiveness A_j** combines objective store features (size, years operative, parking) and
a subjective quality score (managerial judgement on a 0–10 scale).

**Binary variable** (parking): transformed as exp(1) = *e* if available, exp(0) = 1 if not
(Mahajan & Jain 1977).

**Key finding:** Distance is the single most important variable (100% normalised importance),
followed by ease of pedestrian access (32%) and sociodemographic trade area characteristics.

**Sales estimation:** multiply market share × city population × annual food spend per capita.
            """
        )
    with col_form:
        st.markdown("**Choice probability:**")
        st.latex(
            r"P_{ij} = \frac{A_j \cdot d_{ij}^{-\lambda}}{\displaystyle\sum_{k=1}^{n} A_k \cdot d_{ik}^{-\lambda}}"
        )
        st.markdown("**Store attractiveness:**")
        st.latex(
            r"A_j = \left(\frac{\text{Size}_j}{1000}\right)^{\!\alpha}"
            r"\cdot \left(\frac{\text{Quality}_j}{10}\right)^{\!\beta}"
            r"\cdot \left(\frac{\text{Years}_j}{20}\right)^{\!\gamma}"
            r"\cdot p_j"
        )
        st.caption(
            "p_j = e ≈ 2.72 if parking available, else 1  |  "
            "d_ij = Euclidean distance (km)  |  "
            "λ, α, β, γ = sensitivity parameters"
        )


# ── Store configuration ────────────────────────────────────────────────────────
with st.expander("🏪 Supermarket Configuration", expanded=True):
    store_cols = st.columns(n_stores)
    stores = []
    for i, col in enumerate(store_cols):
        d = DEFAULTS[i]
        with col:
            color_dot = (
                f'<span style="color:{COLORS[i]};font-size:18px">■</span> '
                f'**{d["name"]}**'
            )
            st.markdown(color_dot, unsafe_allow_html=True)
            stores.append(
                {
                    "name":    st.text_input("Name", d["name"], key=f"n{i}"),
                    "x":       st.slider("X (km)", 0.5, 9.5, d["x"], 0.5, key=f"x{i}"),
                    "y":       st.slider("Y (km)", 0.5, 9.5, d["y"], 0.5, key=f"y{i}"),
                    "size":    st.slider("Floor area (m²)", 400, 4000, d["size"], 100, key=f"s{i}"),
                    "quality": st.slider("Quality (1–10)", 1, 10, d["quality"], key=f"q{i}"),
                    "years":   st.slider("Years operative", 1, 30, d["years"], key=f"yr{i}"),
                    "parking": st.checkbox("Parking", d["parking"], key=f"p{i}"),
                }
            )


# ── Compute MCI ────────────────────────────────────────────────────────────────
pop = make_population(pop_mode)
probs = calc_mci(stores, lam, alpha, beta, gamma)
shares = market_shares(probs, pop)
est_sales = [s / 100 * pop_total * food_spend / 1e6 for s in shares]


# ── Results layout ─────────────────────────────────────────────────────────────
st.header("Results")
left, right = st.columns([3, 2])


# ── Right column: market share summary ────────────────────────────────────────
with right:
    st.subheader("Market Shares & Estimated Sales")

    df_res = pd.DataFrame(
        {
            "Store":           [s["name"] for s in stores],
            "Share (%)":       [round(v, 1) for v in shares],
            "Est. Sales (€M)": [round(v, 2) for v in est_sales],
            "Size (m²)":       [s["size"] for s in stores],
            "Quality":         [s["quality"] for s in stores],
            "Years":           [s["years"] for s in stores],
            "Parking":         ["Yes" if s["parking"] else "No" for s in stores],
        }
    )

    fig_bar = px.bar(
        df_res,
        x="Share (%)",
        y="Store",
        orientation="h",
        color="Store",
        color_discrete_sequence=COLORS[:n_stores],
        text="Share (%)",
        height=max(220, 60 + n_stores * 50),
    )
    fig_bar.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig_bar.update_layout(
        showlegend=False,
        margin=dict(l=0, r=55, t=10, b=0),
        xaxis=dict(title="Market Share (%)", range=[0, max(shares) * 1.3]),
        yaxis_title="",
    )
    st.plotly_chart(fig_bar, use_container_width=True)
    st.dataframe(df_res.set_index("Store"), use_container_width=True)

    st.subheader("Attractiveness Scores A_j")
    attract_df = pd.DataFrame(
        {
            "Store": [s["name"] for s in stores],
            "A_j":   [round(store_attractiveness(s, alpha, beta, gamma), 3) for s in stores],
        }
    ).set_index("Store")
    st.dataframe(attract_df, use_container_width=True)
    st.caption(
        "A_j is the composite attractiveness before distance weighting. "
        "Higher A_j gives an advantage over all distances."
    )


# ── Left column: map tabs ──────────────────────────────────────────────────────
with left:
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        ["🗺 Trade Areas", "📊 Choice Probability", "🆕 New Store Scenario",
         "📈 Sensitivity Analysis", "👥 Consumer Simulation", "📚 Exercises"]
    )

    # ── Tab 1: Trade areas ─────────────────────────────────────────────────────
    with tab1:
        dominant = np.argmax(probs, axis=0)
        cs = discrete_colorscale(COLORS[:n_stores])

        fig1 = go.Figure()

        # Colored regions: dominant store per grid cell
        fig1.add_trace(
            go.Heatmap(
                z=dominant,
                x=x_lin, y=y_lin,
                colorscale=cs,
                zmin=0, zmax=n_stores - 1,
                showscale=False,
                opacity=0.75,
                hoverinfo="skip",
            )
        )

        # Population density contours (urban cluster mode only)
        if pop_mode == "Urban clusters":
            fig1.add_trace(
                go.Contour(
                    z=pop, x=x_lin, y=y_lin,
                    showscale=False,
                    colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
                    line=dict(color="rgba(0,0,0,0.45)", width=1),
                    contours=dict(showlabels=True, labelfont=dict(size=8, color="black")),
                    name="Population density",
                    hoverinfo="skip",
                )
            )

        # 400 m trade area circles (paper: >80% of consumers come from within 400 m)
        for s in stores:
            theta = np.linspace(0, 2 * np.pi, 72)
            fig1.add_trace(
                go.Scatter(
                    x=s["x"] + 0.4 * np.cos(theta),
                    y=s["y"] + 0.4 * np.sin(theta),
                    mode="lines",
                    line=dict(color="black", width=1.2, dash="dot"),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

        add_store_markers(fig1, stores, shares)
        fig1.update_layout(
            title="Dominant trade areas  (dashed circle = 400 m radius)",
            **MAP_LAYOUT,
        )
        st.plotly_chart(fig1, use_container_width=True)
        st.caption(
            "Each colour shows the store with the highest choice probability at that location. "
            "Dashed circles mark the 400 m trade area radius — Baviera-Puig et al. report that "
            ">80 % of a supermarket's consumers come from within this distance."
        )

    # ── Tab 2: Choice probability ──────────────────────────────────────────────
    with tab2:
        sel = st.selectbox("Select store", [s["name"] for s in stores])
        j_sel = next(i for i, s in enumerate(stores) if s["name"] == sel)

        fig2 = go.Figure()
        fig2.add_trace(
            go.Heatmap(
                z=probs[j_sel],
                x=x_lin, y=y_lin,
                colorscale="Blues",
                colorbar=dict(title="P(choose)", tickformat=".0%"),
                zmin=0, zmax=1,
            )
        )
        add_store_markers(fig2, stores, shares)
        fig2.update_layout(
            title=f"Choice probability — {sel}  (market share {shares[j_sel]:.1f} %)",
            **MAP_LAYOUT,
        )
        st.plotly_chart(fig2, use_container_width=True)
        st.caption(
            "Darker blue = consumers at that location are more likely to choose this store. "
            "The probability decays with distance and increases with attractiveness A_j."
        )

    # ── Tab 3: New store scenario ──────────────────────────────────────────────
    with tab3:
        st.markdown(
            "**Simulate opening a new supermarket.** "
            "Adjust its attributes and location to see how it redistributes market share."
        )
        nc1, nc2, nc3 = st.columns(3)
        with nc1:
            new_x    = st.slider("X position (km)", 0.5, 9.5, 5.0, 0.5, key="nx")
            new_y    = st.slider("Y position (km)", 0.5, 9.5, 5.0, 0.5, key="ny")
        with nc2:
            new_size = st.slider("Floor area (m²)", 400, 4000, 1500, 100, key="nsize")
            new_qual = st.slider("Quality (1–10)", 1, 10, 7, key="nqual")
        with nc3:
            new_yrs  = st.slider("Years operative", 1, 30, 1, key="nyrs")
            new_park = st.checkbox("Parking", True, key="npark")

        new_store = dict(
            name="New Store", x=new_x, y=new_y,
            size=new_size, quality=new_qual, years=new_yrs, parking=new_park,
        )
        stores_ext   = stores + [new_store]
        probs_ext    = calc_mci(stores_ext, lam, alpha, beta, gamma)
        shares_ext   = market_shares(probs_ext, pop)
        est_ext      = [s / 100 * pop_total * food_spend / 1e6 for s in shares_ext]

        dominant_ext = np.argmax(probs_ext, axis=0)
        cs_ext = discrete_colorscale(COLORS[:n_stores] + ["#8c564b"])

        fig3 = go.Figure()
        fig3.add_trace(
            go.Heatmap(
                z=dominant_ext,
                x=x_lin, y=y_lin,
                colorscale=cs_ext,
                zmin=0, zmax=n_stores,
                showscale=False,
                opacity=0.75,
                hoverinfo="skip",
            )
        )
        add_store_markers(fig3, stores, [shares_ext[j] for j in range(n_stores)])

        # New store marker (star)
        new_share = shares_ext[-1]
        fig3.add_trace(
            go.Scatter(
                x=[new_x], y=[new_y],
                mode="markers+text",
                marker=dict(
                    size=20, color="#8c564b", symbol="star",
                    line=dict(color="white", width=2),
                ),
                text=["New Store"],
                textposition="top center",
                textfont=dict(size=10, color="black"),
                name="New Store",
                hovertemplate=(
                    f"<b>New Store</b><br>Size: {new_size} m²<br>"
                    f"Quality: {new_qual}/10<br>Parking: {'Yes' if new_park else 'No'}<br>"
                    f"<b>Market share: {new_share:.1f}%</b><extra></extra>"
                ),
                showlegend=False,
            )
        )
        fig3.update_layout(title="Trade areas after adding new store (★)", **MAP_LAYOUT)
        st.plotly_chart(fig3, use_container_width=True)

        # Impact table
        impact = pd.DataFrame(
            {
                "Store":           [s["name"] for s in stores] + ["New Store"],
                "Before (%)":      [round(shares[j], 1) for j in range(n_stores)] + ["—"],
                "After (%)":       [round(shares_ext[j], 1) for j in range(n_stores + 1)],
                "Change (pp)":     [round(shares_ext[j] - shares[j], 1) for j in range(n_stores)] + ["—"],
                "Est. Sales (€M)": [round(est_ext[j], 2) for j in range(n_stores + 1)],
            }
        ).set_index("Store")
        st.dataframe(impact, use_container_width=True)
        st.caption(
            "Negative change = market share lost to the new entrant. "
            "The MCI model assumes independence of irrelevant alternatives: "
            "each existing store loses share proportionally to its current attraction."
        )

    # ── Tab 4: Sensitivity analysis ────────────────────────────────────────────
    with tab4:
        st.markdown(
            "**How does distance sensitivity λ shape the competitive landscape?**  \n"
            "For each value of λ, market shares are recomputed with all other parameters held constant."
        )

        lam_vals   = np.arange(0.5, 3.05, 0.1)
        share_data = {s["name"]: [] for s in stores}
        for lv in lam_vals:
            p  = calc_mci(stores, lv, alpha, beta, gamma)
            sh = market_shares(p, pop)
            for j, s in enumerate(stores):
                share_data[s["name"]].append(sh[j])

        fig4 = go.Figure()
        for j, s in enumerate(stores):
            fig4.add_trace(
                go.Scatter(
                    x=lam_vals,
                    y=share_data[s["name"]],
                    mode="lines",
                    name=s["name"],
                    line=dict(color=COLORS[j], width=2.5),
                )
            )
        fig4.add_vline(
            x=lam,
            line_dash="dash",
            line_color="gray",
            annotation_text=f"Current λ = {lam}",
            annotation_position="top right",
        )
        fig4.update_layout(
            xaxis_title="Distance sensitivity λ",
            yaxis_title="Market Share (%)",
            title="Market share vs. distance sensitivity λ",
            height=420,
            margin=dict(l=0, r=0, t=40, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig4, use_container_width=True)

        st.markdown(
            "**Interpretation:**  \n"
            "- At **low λ** (≈ 0.5): distance barely matters — consumers shop at the most attractive "
            "store regardless of proximity. Larger/better stores dominate.  \n"
            "- At **high λ** (≈ 3.0): consumers strongly prefer the nearest store — stores in "
            "densely populated areas gain, remote high-quality stores lose.  \n"
            "- The paper found λ ≈ 1–2 typical for urban supermarket competition, with distance "
            "as the single strongest predictor (100 % normalised importance)."
        )

    # ── Tab 5: Consumer Simulation ─────────────────────────────────────────────
    with tab5:
        st.markdown(
            "Consumers are sampled from the population distribution and assigned to stores "
            "**probabilistically** using their local MCI choice probabilities — illustrating "
            "how individual stochastic decisions aggregate into market share."
        )

        # Controls
        sc1, sc2, sc3 = st.columns([2, 2, 1])
        with sc1:
            n_consumers = st.slider("Consumers (snapshot)", 50, 500, 200, 50, key="nc")
        with sc2:
            n_anim = st.slider("Consumers (animation)", 20, 100, 60, 10, key="na")
        with sc3:
            st.write("")
            resample = st.button("🔄 Resample")

        if "resample_count" not in st.session_state:
            st.session_state.resample_count = 0
        if resample:
            st.session_state.resample_count += 1

        rng = np.random.default_rng(st.session_state.resample_count)

        # Sample and assign consumers for snapshot
        cx, cy = sample_consumers(n_consumers, pop, x_lin, y_lin, rng)
        assign = assign_stores_array(cx, cy, stores, lam, alpha, beta, gamma, rng)
        colors_c = [COLORS[a % len(COLORS)] for a in assign]

        # ── Snapshot map + comparison ──────────────────────────────────────────
        snap_left, snap_right = st.columns([3, 2])

        with snap_left:
            fig_snap = go.Figure()
            fig_snap.add_trace(
                go.Heatmap(
                    z=np.argmax(probs, axis=0), x=x_lin, y=y_lin,
                    colorscale=discrete_colorscale(COLORS[:n_stores]),
                    zmin=0, zmax=n_stores - 1,
                    showscale=False, opacity=0.3, hoverinfo="skip",
                )
            )
            fig_snap.add_trace(
                go.Scatter(
                    x=cx, y=cy, mode="markers",
                    marker=dict(
                        color=colors_c, size=6, opacity=0.8,
                        line=dict(color="white", width=0.5),
                    ),
                    showlegend=False, hoverinfo="skip",
                )
            )
            add_store_markers(fig_snap, stores, shares)
            fig_snap.update_layout(
                title=f"{n_consumers} consumers — coloured by assigned store",
                **MAP_LAYOUT,
            )
            st.plotly_chart(fig_snap, use_container_width=True)
            st.caption(
                "Each dot is one consumer. Colour = store chosen via probabilistic MCI draw. "
                "Background shading shows dominant trade areas. "
                "Click **Resample** to draw a fresh random sample."
            )

        with snap_right:
            obs_counts = np.bincount(assign, minlength=n_stores)
            obs_shares = obs_counts / obs_counts.sum() * 100

            df_cmp = pd.DataFrame(
                {
                    "Store": [s["name"] for s in stores] * 2,
                    "Share (%)": list(shares) + list(obs_shares),
                    "Type": (
                        ["Theoretical (MCI)"] * n_stores
                        + [f"Observed (n={n_consumers})"] * n_stores
                    ),
                }
            )
            fig_cmp = px.bar(
                df_cmp,
                x="Store", y="Share (%)", color="Type",
                barmode="group",
                color_discrete_map={
                    "Theoretical (MCI)": PRIMARY,
                    f"Observed (n={n_consumers})": ACCENT,
                },
                height=290,
            )
            fig_cmp.update_layout(
                margin=dict(l=0, r=0, t=50, b=0),
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                ),
                xaxis_title="", yaxis_title="Market Share (%)",
                title="Theoretical vs. sampled",
            )
            st.plotly_chart(fig_cmp, use_container_width=True)

            rmse = float(np.sqrt(np.mean((np.array(shares) - obs_shares) ** 2)))
            st.metric(
                "RMSE (theoretical vs. observed)",
                f"{rmse:.2f} pp",
                help="Percentage points. Falls toward 0 as N grows — law of large numbers.",
            )
            st.caption(
                "Increase N and resample to watch the observed shares "
                "converge toward the theoretical MCI values."
            )

        # ── Shopping trip animation ────────────────────────────────────────────
        st.subheader("Shopping Trip Animation")
        st.caption("Press ▶ Play — consumers travel from home to their chosen store and back.")

        rng_a = np.random.default_rng(99 + st.session_state.resample_count)
        cx_a, cy_a = sample_consumers(n_anim, pop, x_lin, y_lin, rng_a)
        assign_a   = assign_stores_array(cx_a, cy_a, stores, lam, alpha, beta, gamma, rng_a)
        sx_a = np.array([stores[a]["x"] for a in assign_a])
        sy_a = np.array([stores[a]["y"] for a in assign_a])
        colors_a = [COLORS[a % len(COLORS)] for a in assign_a]

        def _consumer_scatter(x_pos, y_pos, sz: int = 7) -> go.Scatter:
            return go.Scatter(
                x=x_pos, y=y_pos, mode="markers",
                marker=dict(
                    color=colors_a, size=sz, opacity=0.85,
                    line=dict(color="white", width=0.5),
                ),
                showlegend=False, hoverinfo="skip",
            )

        N_dep, N_dwell, N_ret = 18, 8, 18
        anim_frames = []
        for i in range(N_dep):                          # depart: home → store
            t = i / (N_dep - 1)
            anim_frames.append(go.Frame(
                data=[_consumer_scatter(cx_a + t * (sx_a - cx_a), cy_a + t * (sy_a - cy_a))],
                traces=[2], name=str(len(anim_frames)),
            ))
        for _ in range(N_dwell):                        # dwell: at store
            anim_frames.append(go.Frame(
                data=[_consumer_scatter(sx_a, sy_a, sz=10)],
                traces=[2], name=str(len(anim_frames)),
            ))
        for i in range(N_ret):                          # return: store → home
            t = i / (N_ret - 1)
            anim_frames.append(go.Frame(
                data=[_consumer_scatter(sx_a + t * (cx_a - sx_a), sy_a + t * (cy_a - sy_a))],
                traces=[2], name=str(len(anim_frames)),
            ))
        anim_frames.append(go.Frame(                    # final: back home
            data=[_consumer_scatter(cx_a, cy_a)],
            traces=[2], name=str(len(anim_frames)),
        ))

        fig_anim = go.Figure(
            data=[
                # Trace 0: background trade areas (static)
                go.Heatmap(
                    z=np.argmax(probs, axis=0), x=x_lin, y=y_lin,
                    colorscale=discrete_colorscale(COLORS[:n_stores]),
                    zmin=0, zmax=n_stores - 1,
                    showscale=False, opacity=0.35, hoverinfo="skip",
                ),
                # Trace 1: store markers (static)
                go.Scatter(
                    x=[s["x"] for s in stores],
                    y=[s["y"] for s in stores],
                    mode="markers+text",
                    marker=dict(
                        size=16, color=COLORS[:n_stores], symbol="square",
                        line=dict(color="white", width=2),
                    ),
                    text=[s["name"] for s in stores],
                    textposition="top center",
                    textfont=dict(size=10, color="black"),
                    showlegend=False, hoverinfo="skip",
                ),
                # Trace 2: consumer dots (animated)
                _consumer_scatter(cx_a, cy_a),
            ],
            frames=anim_frames,
            layout=go.Layout(
                **MAP_LAYOUT,
                title=f"Shopping trips — {n_anim} consumers",
                updatemenus=[
                    dict(
                        type="buttons",
                        showactive=False,
                        y=0, x=0.5,
                        xanchor="center", yanchor="top",
                        pad=dict(t=50),
                        buttons=[
                            dict(
                                label="▶ Play",
                                method="animate",
                                args=[None, dict(
                                    frame=dict(duration=80, redraw=True),
                                    fromcurrent=True,
                                    transition=dict(duration=0),
                                    mode="immediate",
                                )],
                            ),
                            dict(
                                label="⏸ Pause",
                                method="animate",
                                args=[[None], dict(
                                    frame=dict(duration=0, redraw=False),
                                    mode="immediate",
                                    transition=dict(duration=0),
                                )],
                            ),
                        ],
                    )
                ],
            ),
        )
        st.plotly_chart(fig_anim, use_container_width=True)
        st.caption(
            "Dot colour = assigned store (matching trade area colours). "
            "Consumers depart from home, visit their chosen store, then return. "
            "The spatial pull of nearby attractive stores is visible in the flow pattern."
        )

    # ── Tab 6: Exercises ───────────────────────────────────────────────────────
    with tab6:
        st.title("📚 Student Exercises")
        st.info(
            "These exercises are **voluntary** and designed to deepen your understanding "
            "of the MCI model at your own pace. They are not graded unless your instructor "
            "specifies otherwise."
        )

        st.markdown("""
### Level 1 — Reproduce

Work entirely within the app — no coding required.

1. Open the **Sensitivity Analysis** tab. Move λ from 0.5 to 3.0 in the sidebar.
   Which store gains the most market share at high λ? Which loses the most?
   Look at each store's position relative to the population clusters and explain why.

2. Set **α (store size weight)** to 0 in the sidebar. How do the market shares change?
   What does α = 0 mean conceptually — which variable are you effectively switching off?

3. Switch the population distribution from *Urban clusters* to *Uniform*.
   Which stores gain or lose market share? Explain in terms of the MCI formula.

4. Open the **Consumer Simulation** tab. Set *Consumers (snapshot)* to 50 and click
   **Resample** five times. Write down the RMSE each time. Repeat with N = 500.
   What pattern do you observe? What statistical principle does this illustrate?

5. Open the **New Store Scenario** tab. Place a new store at X = 5, Y = 5 (city centre)
   with default attributes. Which existing store loses the most market share?
   Does the answer change if you give the new store a larger floor area?

---

### Level 2 — Explain

Interpret results and connect them to the MCI theory.

6. Store B has the largest floor area (2 500 m²). Does it always have the largest
   market share? Find a combination of λ, α, and β where Store A dominates despite
   being smaller. Explain which part of the MCI formula makes this possible.

7. In the **Consumer Simulation**, some consumers located inside a store's dominant
   trade area (coloured background) are assigned to a *different* store.
   How is this possible given the MCI formula? Why is it realistic?

8. The **Attractiveness Scores A_j** are shown in the right panel. Can a store with a
   *lower* A_j still achieve a *higher* market share than one with a higher A_j?
   Set up a concrete two-store example and identify the condition under which this happens.

9. The paper reports that distance has **100 % normalised importance** — higher than any
   other variable. Use the **Sensitivity Analysis** tab to illustrate this:
   at λ = 0.5 vs. λ = 2.5, what is the range (max − min) of market shares across the
   five stores? What is the strategic implication for a retailer choosing between a
   central and a peripheral location?

---

### Level 3 — Extend

Modify `app.py` to add new features.

10. **Add a "Number of checkouts" attribute** to each store (the paper found 20 %
    normalised importance). Add a slider (range 4–40, default 10) in the store
    configuration and extend the attractiveness formula:

    ```
    A_j = ... × (checkouts_j / 20) ** δ
    ```

    Add a sensitivity slider δ in the sidebar. How does it affect the ranking of stores?

11. **Dynamic trade area boundary.** The 400 m circle is a fixed rule of thumb.
    Replace it with the isoline where P_ij = 0.5: the location where a consumer is
    equally likely to choose store j or any other store. Use `go.Contour` on the
    `probs[j]` array. Compare how the 50 %-boundary shape varies across stores with
    different attractiveness levels.

12. **Trip distance histogram.** In the **Consumer Simulation**, add a histogram below
    the map showing the Euclidean distance each consumer travels to reach their assigned
    store. Does the shape of the distribution change when you increase λ?
    What distribution would you expect in the limiting case λ → ∞?

13. **Spatial non-stationarity (Equation 5–6 of the paper).** The extended MCI model
    makes the distance parameter consumer-specific:

    ```
    λ_i = w + q · R_i,   where R_i = max_distance_i / min_distance_i
    ```

    Implement this in `assign_stores_array`: for each consumer compute R_i across all
    stores, then use λ_i instead of the global λ. Add sliders w and q to the sidebar.
    Which consumers are most affected by this adjustment?

---

### Level 4 — Connect to the paper

14. **Logarithmic linearisation (Equation 2).** The paper transforms the MCI model
    into a linear regression by taking logs. Starting from:

    ```
    P_ij = A_j · d_ij^{-λ} / Σ_k ( A_k · d_ik^{-λ} )
    ```

    derive:

    ```
    log( P_ij / P̄_i ) = Σ_k λ_k · log( A_kj / Ā_k ) + λ · log( d_ij / d̄_i )
    ```

    where bars denote geometric means across stores. Why does this transformation
    allow ordinary least squares (OLS) to estimate the sensitivity parameters?
    What assumption does it impose on the error term?

15. **Calibration accuracy (Table 2 of the paper).** The paper achieves R² = 84–88 %.
    In our simulation "truth" is the MCI model itself, so a perfect calibration gives
    R² = 1. Simulate measurement error by adding Gaussian noise to the theoretical
    market shares, fit an OLS regression (use `sklearn.linear_model.LinearRegression`),
    and compute R². How large does the standard deviation of the noise need to be before
    R² drops below 84 %? What does this tell you about data quality requirements?

16. **Independence of irrelevant alternatives (IIA).** The MCI model assumes IIA:
    adding a new store reduces every existing store's share *proportionally* to its
    current share. Verify this in the **New Store Scenario** tab: record the market
    shares before and after adding a new store. For each existing store, compute
    `after / before`. Are all ratios equal? If not, explain why the continuous-grid
    approximation introduces small deviations from perfect IIA.
""")

        st.divider()
        st.caption(
            "Source: Baviera-Puig, Buitrago-Vera & Escribá-Pérez (2016). "
            "Geomarketing Models in Supermarket Location Strategies. "
            "Journal of Business Economics and Management, 17(6), 1205–1221."
        )
