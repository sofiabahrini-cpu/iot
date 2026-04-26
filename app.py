"""
app.py — Dashboard IoT Streamlit
Lance avec: streamlit run app.py
"""

import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import os

# ─── CONFIG PAGE ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="IoT Dashboard ESP32",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DB_PATH = "iot_data.db"

# ─── STYLES PERSONNALISÉS ─────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Header */
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #00d4aa, #7b61ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .subtitle {
        color: #888;
        font-size: 0.9rem;
        margin-top: -8px;
        margin-bottom: 24px;
    }
    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #1e1e2e 0%, #2a2a3e 100%);
        border-radius: 16px;
        padding: 20px 24px;
        border: 1px solid rgba(255,255,255,0.08);
        text-align: center;
    }
    .metric-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: #888;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 2.4rem;
        font-weight: 700;
        color: white;
        line-height: 1;
    }
    .metric-unit {
        font-size: 1rem;
        color: #aaa;
        font-weight: 400;
    }
    .metric-delta {
        font-size: 0.78rem;
        margin-top: 6px;
    }
    .delta-up   { color: #ff6b6b; }
    .delta-down { color: #00d4aa; }
    /* Badge status */
    .badge-online  { background:#00d4aa22; color:#00d4aa; padding:4px 12px; border-radius:99px; font-size:0.78rem; border:1px solid #00d4aa55; }
    .badge-offline { background:#ff6b6b22; color:#ff6b6b; padding:4px 12px; border-radius:99px; font-size:0.78rem; border:1px solid #ff6b6b55; }
    /* Section title */
    .section-title {
        font-size: 1rem;
        font-weight: 600;
        color: #ccc;
        margin-bottom: 12px;
        border-left: 3px solid #7b61ff;
        padding-left: 10px;
    }
    /* Battery bar */
    .battery-wrap { background:#1e1e2e; border-radius:12px; padding:16px; border:1px solid rgba(255,255,255,0.06); }
</style>
""", unsafe_allow_html=True)


# ─── CHARGEMENT DES DONNÉES ───────────────────────────────────────────────────
@st.cache_data(ttl=10)
def load_data(hours: int = 24) -> pd.DataFrame:
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    try:
        conn = sqlite3.connect(DB_PATH)
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        df = pd.read_sql_query(
            "SELECT * FROM readings WHERE timestamp >= ? ORDER BY timestamp ASC",
            conn,
            params=(since,),
        )
        conn.close()
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df["power_mw"] = df["volt"] * df["current_ma"]
        return df
    except Exception as e:
        st.error(f"Erreur DB : {e}")
        return pd.DataFrame()


def estimate_battery_pct(volt: float) -> float:
    """Estimation % batterie Li-ion (3.0V=0% → 4.2V=100%)."""
    pct = (volt - 3.0) / (4.2 - 3.0) * 100
    return max(0.0, min(100.0, pct))


def battery_color(pct: float) -> str:
    if pct > 60:
        return "#00d4aa"
    elif pct > 25:
        return "#f9c74f"
    else:
        return "#ff6b6b"


# ─── PLOTLY THEME COMMUN ──────────────────────────────────────────────────────
PLOT_BG   = "rgba(0,0,0,0)"
PAPER_BG  = "rgba(0,0,0,0)"
GRID_CLR  = "rgba(255,255,255,0.05)"
FONT_CLR  = "#aaaaaa"

base_layout = dict(
    paper_bgcolor=PAPER_BG,
    plot_bgcolor=PLOT_BG,
    font=dict(color=FONT_CLR, family="Inter, sans-serif"),
    margin=dict(l=10, r=10, t=30, b=10),
    xaxis=dict(showgrid=False, zeroline=False, color=FONT_CLR),
    yaxis=dict(showgrid=True, gridcolor=GRID_CLR, zeroline=False, color=FONT_CLR),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
    hovermode="x unified",
)


# ─── GAUGES ──────────────────────────────────────────────────────────────────
def gauge_fig(value, title, min_v, max_v, unit, color, thresholds=None):
    steps = [
        {"range": [min_v, max_v * 0.5], "color": "rgba(255,255,255,0.04)"},
        {"range": [max_v * 0.5, max_v * 0.8], "color": "rgba(255,255,255,0.07)"},
        {"range": [max_v * 0.8, max_v],        "color": "rgba(255,255,255,0.10)"},
    ]
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"suffix": unit, "font": {"size": 28, "color": "white"}},
        title={"text": title, "font": {"size": 13, "color": "#aaa"}},
        gauge={
            "axis": {"range": [min_v, max_v], "tickcolor": "#555", "tickfont": {"size": 10}},
            "bar": {"color": color, "thickness": 0.25},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": steps,
        },
    ))
    fig.update_layout(paper_bgcolor=PAPER_BG, font=dict(color=FONT_CLR), height=200, margin=dict(l=20, r=20, t=40, b=10))
    return fig


# ─── SPARKLINE ────────────────────────────────────────────────────────────────
def sparkline(df, col, color, title):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df[col],
        mode="lines",
        line=dict(color=color, width=2),
        fill="tozeroy",
        fillcolor=color.replace(")", ", 0.08)").replace("rgb", "rgba"),
        name=col,
    ))
    fig.update_layout(**base_layout, height=160, title=dict(text=title, font=dict(size=12, color="#ccc"), x=0))
    return fig


# ─── APP ──────────────────────────────────────────────────────────────────────
def main():
    # Sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Paramètres")
        hours = st.slider("Fenêtre temporelle (h)", 1, 168, 24, step=1)
        auto_refresh = st.toggle("Auto-refresh (10s)", value=True)
        st.divider()
        st.caption("**ESP32 → Flask → SQLite → Streamlit**")
        st.caption(f"DB : `{DB_PATH}`")

    # Header
    st.markdown('<p class="main-title">⚡ IoT Energy Dashboard</p>', unsafe_allow_html=True)

    df = load_data(hours)
    now_str = datetime.now().strftime("%H:%M:%S")

    if df.empty:
        st.warning("Aucune donnée trouvée. Vérifie que `server.py` tourne et que l'ESP32 a envoyé des mesures.")
        st.caption(f"Chemin DB : `{os.path.abspath(DB_PATH)}`")
        st.stop()

    latest = df.iloc[-1]
    prev   = df.iloc[-2] if len(df) > 1 else latest

    # Âge de la dernière mesure
    age_s = (datetime.now() - latest["timestamp"]).total_seconds()
    if age_s < 120:
        badge = '<span class="badge-online">● En ligne</span>'
    else:
        badge = f'<span class="badge-offline">● Hors ligne · {int(age_s//60)} min</span>'

    st.markdown(
        f'{badge} &nbsp; <span style="color:#666;font-size:0.8rem;">Dernière mesure : {latest["timestamp"].strftime("%d/%m %H:%M:%S")} · rafraîchi à {now_str}</span>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # ── LIGNE 1 : métriques clés ────────────────────────────────────────────
    batt_pct  = estimate_battery_pct(latest["volt"])
    batt_col  = battery_color(batt_pct)

    col1, col2, col3, col4, col5 = st.columns(5)

    def delta_html(curr, prev_v, unit, invert=False):
        diff = curr - prev_v
        sign = "+" if diff >= 0 else ""
        cls  = ("delta-down" if diff >= 0 else "delta-up") if invert else ("delta-up" if diff >= 0 else "delta-down")
        return f'<div class="metric-delta {cls}">{sign}{diff:.2f} {unit}</div>'

    with col1:
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">🌡 Température</div>
          <div class="metric-value">{latest['temp']:.1f}<span class="metric-unit">°C</span></div>
          {delta_html(latest['temp'], prev['temp'], '°C')}
        </div>""", unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">💧 Humidité</div>
          <div class="metric-value">{latest['hum']:.1f}<span class="metric-unit">%</span></div>
          {delta_html(latest['hum'], prev['hum'], '%')}
        </div>""", unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">⚡ Tension</div>
          <div class="metric-value">{latest['volt']:.2f}<span class="metric-unit">V</span></div>
          {delta_html(latest['volt'], prev['volt'], 'V', invert=True)}
        </div>""", unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">🔌 Courant</div>
          <div class="metric-value">{latest['current_ma']:.1f}<span class="metric-unit">mA</span></div>
          {delta_html(latest['current_ma'], prev['current_ma'], 'mA')}
        </div>""", unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-label" style="color:{batt_col}">🔋 Batterie</div>
          <div class="metric-value" style="color:{batt_col}">{batt_pct:.0f}<span class="metric-unit">%</span></div>
          <div class="metric-delta" style="color:#666">{latest['volt']:.2f} V</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── LIGNE 2 : jauges + graphes historique ───────────────────────────────
    g_col, hist_col = st.columns([2, 3])

    with g_col:
        st.markdown('<div class="section-title">Jauges temps réel</div>', unsafe_allow_html=True)
        gc1, gc2 = st.columns(2)
        with gc1:
            st.plotly_chart(gauge_fig(latest["temp"], "Température", -10, 60, "°C", "#ff6b6b"), use_container_width=True, config={"displayModeBar": False})
            st.plotly_chart(gauge_fig(latest["volt"], "Tension",     3.0, 4.2, "V",  "#7b61ff"), use_container_width=True, config={"displayModeBar": False})
        with gc2:
            st.plotly_chart(gauge_fig(latest["hum"], "Humidité",    0, 100, "%",  "#00aaff"), use_container_width=True, config={"displayModeBar": False})
            st.plotly_chart(gauge_fig(latest["current_ma"], "Courant", 0, 500, "mA", "#00d4aa"), use_container_width=True, config={"displayModeBar": False})

    with hist_col:
        st.markdown('<div class="section-title">Historique</div>', unsafe_allow_html=True)

        # Graphe combiné Temp + Humidité
        fig_env = go.Figure()
        fig_env.add_trace(go.Scatter(x=df["timestamp"], y=df["temp"], name="Température (°C)", line=dict(color="#ff6b6b", width=2)))
        fig_env.add_trace(go.Scatter(x=df["timestamp"], y=df["hum"],  name="Humidité (%)",     line=dict(color="#00aaff", width=2), yaxis="y2"))
        fig_env.update_layout(
            **base_layout,
            height=220,
            title=dict(text="Température & Humidité", font=dict(size=13, color="#ccc"), x=0),
            yaxis2=dict(overlaying="y", side="right", showgrid=False, color="#00aaff"),
            legend=dict(orientation="h", y=1.15, x=0, bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig_env, use_container_width=True, config={"displayModeBar": False})

        # Graphe Puissance
        fig_pwr = go.Figure()
        fig_pwr.add_trace(go.Scatter(
            x=df["timestamp"], y=df["power_mw"],
            mode="lines",
            line=dict(color="#f9c74f", width=2),
            fill="tozeroy", fillcolor="rgba(249,199,79,0.08)",
            name="Puissance (mW)",
        ))
        fig_pwr.update_layout(
            **base_layout,
            height=180,
            title=dict(text="Puissance consommée (mW)", font=dict(size=13, color="#ccc"), x=0),
        )
        st.plotly_chart(fig_pwr, use_container_width=True, config={"displayModeBar": False})

    st.markdown("---")

    # ── LIGNE 3 : santé batterie + stats ────────────────────────────────────
    bat_col, stat_col = st.columns([3, 2])

    with bat_col:
        st.markdown('<div class="section-title">Santé batterie (Tension vs Temps)</div>', unsafe_allow_html=True)
        df["batt_pct"] = df["volt"].apply(estimate_battery_pct)
        fig_bat = go.Figure()
        fig_bat.add_trace(go.Scatter(
            x=df["timestamp"], y=df["batt_pct"],
            mode="lines",
            line=dict(color=batt_col, width=2.5),
            fill="tozeroy", fillcolor=f"rgba(0,212,170,0.07)",
            name="Batterie %",
        ))
        fig_bat.add_hline(y=20, line_dash="dot", line_color="#ff6b6b", annotation_text="Seuil critique 20%", annotation_font_size=10)
        fig_bat.update_layout(**base_layout, height=200, yaxis=dict(range=[0, 105], **dict(showgrid=True, gridcolor=GRID_CLR, zeroline=False, color=FONT_CLR)))
        st.plotly_chart(fig_bat, use_container_width=True, config={"displayModeBar": False})

    with stat_col:
        st.markdown('<div class="section-title">Statistiques</div>', unsafe_allow_html=True)
        stats_data = {
            "Mesures": [len(df)],
            "T moy (°C)": [f"{df['temp'].mean():.1f}"],
            "T max (°C)": [f"{df['temp'].max():.1f}"],
            "T min (°C)": [f"{df['temp'].min():.1f}"],
            "H moy (%)": [f"{df['hum'].mean():.1f}"],
            "V moy (V)": [f"{df['volt'].mean():.2f}"],
            "I moy (mA)": [f"{df['current_ma'].mean():.1f}"],
            "P moy (mW)": [f"{df['power_mw'].mean():.1f}"],
        }
        st.dataframe(
            pd.DataFrame(stats_data).T.rename(columns={0: "Valeur"}),
            use_container_width=True,
            height=240,
        )

    # ── DONNÉES BRUTES (optionnel) ────────────────────────────────────────────
    with st.expander("📋 Données brutes"):
        st.dataframe(
            df[["timestamp", "temp", "hum", "volt", "current_ma", "power_mw"]]
            .sort_values("timestamp", ascending=False)
            .rename(columns={"timestamp": "Horodatage", "temp": "Temp (°C)", "hum": "Hum (%)", "volt": "V", "current_ma": "mA", "power_mw": "mW"})
            .reset_index(drop=True),
            use_container_width=True,
            height=260,
        )
        csv = df.to_csv(index=False)
        st.download_button("⬇ Télécharger CSV", csv, "iot_data.csv", "text/csv")

    # Auto-refresh
    if auto_refresh:
        time.sleep(10)
        st.rerun()


if __name__ == "__main__":
    main()
