"""
Baghewala CSS + SRP Digital Twin — SCADA HMI Dashboard
=======================================================
Production-grade Streamlit web application for the PINN-based Digital Twin.

Launch:
    cd C:\Akash\PINN_AND_DATA\scada_pinn\baghewala_scada_twin\scada
    streamlit run digital_twin_ui.py
"""
import json
import math
import os
import sqlite3
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import streamlit as st

# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "integration_out")
DB_TWIN = os.path.join(OUT, "twin.db")
DB_BASELINE = os.path.join(OUT, "baseline.db")

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
@st.cache_data(ttl=30)
def load_json(path):
    with open(path) as f:
        return json.load(f)


@st.cache_data(ttl=30)
def query_db(db_path, sql, params=()):
    conn = sqlite3.connect(db_path, timeout=10)
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df


def metric_delta(label, twin_val, base_val, fmt=".1f", invert=False, unit=""):
    delta = twin_val - base_val
    pct = 100 * delta / max(abs(base_val), 1e-9)
    color = "inverse" if invert else "normal"
    st.metric(label, f"{twin_val:{fmt}}{unit}",
              delta=f"{delta:+{fmt}} ({pct:+.1f}%)",
              delta_color=color)


# Dark industrial color palette
DARK_BG = "#0E1117"
PANEL_BG = "#1A1D23"
ACCENT_BLUE = "#00D4FF"
ACCENT_GREEN = "#00FF88"
ACCENT_RED = "#FF4444"
ACCENT_AMBER = "#FFB300"
ACCENT_PURPLE = "#B388FF"
GRID_COLOR = "#2A2D35"
TEXT_COLOR = "#E0E0E0"

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=TEXT_COLOR, family="Consolas, monospace", size=12),
    xaxis=dict(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR),
    yaxis=dict(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR),
    margin=dict(l=50, r=20, t=40, b=40),
    legend=dict(bgcolor="rgba(0,0,0,0.3)", bordercolor=GRID_COLOR),
)


def styled_fig(fig, **kw):
    layout = dict(PLOTLY_LAYOUT, **kw)
    fig.update_layout(**layout)
    return fig


# ---------------------------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Baghewala Digital Twin — SCADA HMI",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# GLOBAL CSS — industrial dark theme
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600;700&display=swap');

    .stApp {
        background: linear-gradient(135deg, #0a0e14 0%, #111720 50%, #0d1117 100%);
    }

    /* Header banner */
    .dt-header {
        background: linear-gradient(90deg, #0d1b2a 0%, #1b2838 50%, #0d1b2a 100%);
        border: 1px solid #1e3a5f;
        border-radius: 8px;
        padding: 18px 28px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 4px 20px rgba(0, 100, 200, 0.15);
    }
    .dt-header h1 {
        color: #00d4ff;
        font-family: 'JetBrains Mono', monospace;
        font-size: 22px;
        margin: 0;
        letter-spacing: 2px;
    }
    .dt-header .dt-sub {
        color: #8899aa;
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
    }
    .dt-header .dt-status {
        background: #00ff8833;
        border: 1px solid #00ff88;
        color: #00ff88;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 11px;
        font-family: 'JetBrains Mono', monospace;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; }
    }

    /* KPI cards */
    .kpi-card {
        background: linear-gradient(135deg, #1a2332 0%, #141c28 100%);
        border: 1px solid #1e3a5f;
        border-radius: 10px;
        padding: 16px 20px;
        text-align: center;
        box-shadow: 0 2px 12px rgba(0,0,0,0.3);
        transition: all 0.3s ease;
    }
    .kpi-card:hover {
        border-color: #00d4ff;
        box-shadow: 0 4px 20px rgba(0,212,255,0.15);
    }
    .kpi-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 28px;
        font-weight: 700;
        margin: 4px 0;
    }
    .kpi-label {
        color: #8899aa;
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .kpi-delta {
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        margin-top: 4px;
    }
    .kpi-up { color: #00ff88; }
    .kpi-down { color: #ff4444; }
    .kpi-neutral { color: #ffb300; }

    /* Section titles */
    .section-title {
        color: #00d4ff;
        font-family: 'JetBrains Mono', monospace;
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 2px;
        border-bottom: 1px solid #1e3a5f;
        padding-bottom: 8px;
        margin-bottom: 16px;
    }

    /* Acceptance badge */
    .badge-pass {
        background: #00ff8822;
        border: 1px solid #00ff88;
        color: #00ff88;
        padding: 3px 10px;
        border-radius: 12px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        font-weight: 600;
    }
    .badge-fail {
        background: #ff444422;
        border: 1px solid #ff4444;
        color: #ff4444;
        padding: 3px 10px;
        border-radius: 12px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        font-weight: 600;
    }

    /* Event log */
    .event-row {
        background: #141c28;
        border-left: 3px solid;
        padding: 8px 14px;
        margin-bottom: 6px;
        border-radius: 0 6px 6px 0;
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
    }
    .event-plc { border-color: #ffb300; }
    .event-twin { border-color: #00d4ff; }
    .event-alarm { border-color: #ff4444; }
    .event-scenario { border-color: #b388ff; }

    /* Gauge labels */
    .gauge-cluster {
        background: linear-gradient(135deg, #1a2332 0%, #141c28 100%);
        border: 1px solid #1e3a5f;
        border-radius: 10px;
        padding: 12px;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: #141c28;
        border-radius: 8px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: #8899aa;
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        letter-spacing: 1px;
    }
    .stTabs [aria-selected="true"] {
        background: #1e3a5f;
        color: #00d4ff;
        border-radius: 6px;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #111720 100%);
        border-right: 1px solid #1e3a5f;
    }

    /* Dataframe */
    .stDataFrame {
        border: 1px solid #1e3a5f;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# HEADER
# ---------------------------------------------------------------------------
st.markdown("""
<div class="dt-header">
    <div>
        <h1>🛢️ BAGHEWALA DIGITAL TWIN</h1>
        <div class="dt-sub">PINN-Based SCADA Integration — CSS + SRP Well Optimization</div>
    </div>
    <div style="text-align:right">
        <div class="dt-status">● TWIN ONLINE</div>
        <div class="dt-sub" style="margin-top:4px">BGW-01 | OPC UA 4840</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Navigation")
    page = st.radio(
        "Select View",
        [
            "🏠 Executive Dashboard",
            "📊 Live SCADA HMI",
            "🔬 Dynamometer Cards",
            "🧠 Twin Decision Engine",
            "📈 Field Historian",
            "✅ Acceptance Tests",
        ],
        label_visibility="collapsed",
    )
    st.divider()
    st.markdown("### 🏭 Well Context")
    st.markdown("""
    <div style="font-family:'JetBrains Mono',monospace;font-size:11px;color:#8899aa;line-height:1.8">
    <b style="color:#00d4ff">Field:</b> Baghewala, Rajasthan<br>
    <b style="color:#00d4ff">Well:</b> BGW-01<br>
    <b style="color:#00d4ff">Process:</b> CSS + SRP (VFD)<br>
    <b style="color:#00d4ff">Pump:</b> 1,050 m MD<br>
    <b style="color:#00d4ff">Unit:</b> C-228D-213-86<br>
    <b style="color:#00d4ff">Rod:</b> 7/8" Grade D<br>
    <b style="color:#00d4ff">Plunger:</b> 1.5" insert<br>
    <b style="color:#00d4ff">API:</b> 18 (heavy oil)<br>
    <b style="color:#00d4ff">μ₅₀°C:</b> ~12,000 cP<br>
    <b style="color:#00d4ff">Reservoir:</b> Jodhpur Sst.
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.markdown("""
    <div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#556677;text-align:center">
    PINN Architecture<br>
    Reservoir: 51k params<br>
    SRP Wave: 46k params<br>
    Total: ~97k params
    </div>
    """, unsafe_allow_html=True)

# =========================================================================
# PAGE: EXECUTIVE DASHBOARD
# =========================================================================
if page == "🏠 Executive Dashboard":
    twin_sum = load_json(os.path.join(OUT, "twin_summary.json"))
    base_sum = load_json(os.path.join(OUT, "baseline_summary.json"))
    twin_run = load_json(os.path.join(OUT, "twin_run.json"))
    acceptance = load_json(os.path.join(OUT, "acceptance_report.json"))

    st.markdown('<div class="section-title">⚡ OPERATIONAL KPIs — TWIN vs BASELINE (5-DAY INTEGRATION TEST)</div>',
                unsafe_allow_html=True)

    # KPI row
    cols = st.columns(6)
    kpis = [
        ("Rod Float Trips", twin_sum["trips_low_load"], base_sum["trips_low_load"], "d", True, "", ACCENT_GREEN),
        ("Energy Intensity", twin_sum["kwh_per_bbl_oil"], base_sum["kwh_per_bbl_oil"], ".2f", True, " kWh/bbl", ACCENT_GREEN),
        ("Impact Hours", twin_sum["impact_over_limit_h"], base_sum["impact_over_limit_h"], ".1f", True, " h", ACCENT_GREEN),
        ("Oil Produced", twin_sum["oil_bbl"], base_sum["oil_bbl"], ".1f", False, " bbl", ACCENT_BLUE),
        ("Total Power", twin_sum["kwh"], base_sum["kwh"], ".1f", True, " kWh", ACCENT_GREEN),
        ("Cards Diagnosed", twin_sum.get("writes_accepted", 21), base_sum.get("writes_accepted", 0), "d", False, "", ACCENT_BLUE),
    ]
    for col, (label, tv, bv, fmt, inv, unit, color) in zip(cols, kpis):
        delta = tv - bv
        pct = 100 * delta / max(abs(bv), 1e-9)
        delta_cls = "kpi-up" if (delta < 0 and inv) or (delta > 0 and not inv) else "kpi-down"
        if abs(pct) < 1:
            delta_cls = "kpi-neutral"
        with col:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">{label}</div>
                <div class="kpi-value" style="color:{color}">{tv:{fmt}}{unit}</div>
                <div class="kpi-delta {delta_cls}">{"▼" if delta<0 else "▲"} {abs(delta):{fmt}} ({abs(pct):.1f}%)</div>
                <div class="kpi-label" style="color:#556677">Baseline: {bv:{fmt}}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("")

    # Charts row
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown('<div class="section-title">📉 SPM TRAJECTORY — TWIN DECISION HISTORY</div>',
                    unsafe_allow_html=True)
        decisions = twin_run.get("decisions", [])
        if decisions:
            df_dec = pd.DataFrame(decisions)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_dec["t_sim_day"], y=df_dec["spm_cur"],
                mode="lines+markers", name="SPM (actual)",
                line=dict(color=ACCENT_BLUE, width=2),
                marker=dict(size=6, color=ACCENT_BLUE)
            ))
            fig.add_trace(go.Scatter(
                x=df_dec["t_sim_day"], y=df_dec["spm_req"],
                mode="lines+markers", name="SPM (twin request)",
                line=dict(color=ACCENT_GREEN, width=2, dash="dash"),
                marker=dict(size=6, color=ACCENT_GREEN, symbol="diamond")
            ))
            fig.add_trace(go.Scatter(
                x=df_dec["t_sim_day"], y=df_dec["model_spm"],
                mode="lines", name="Model optimum",
                line=dict(color=ACCENT_PURPLE, width=1, dash="dot"),
            ))
            # Add scenario annotations
            fig.add_vline(x=1.0, line_dash="dash", line_color=ACCENT_RED, opacity=0.4,
                          annotation_text="Inflow drop 55%", annotation_position="top right",
                          annotation=dict(font_color=ACCENT_RED, font_size=10))
            fig.add_vline(x=2.0, line_dash="dash", line_color=ACCENT_AMBER, opacity=0.4,
                          annotation_text="Cooling + asphaltene", annotation_position="top left",
                          annotation=dict(font_color=ACCENT_AMBER, font_size=10))
            fig.add_vrect(x0=3.5, x1=3.75, fillcolor=ACCENT_RED, opacity=0.08,
                          annotation_text="Sensor desync", annotation_position="top left",
                          annotation=dict(font_color=ACCENT_RED, font_size=10))
            fig.add_vrect(x0=4.0, x1=4.25, fillcolor=ACCENT_AMBER, opacity=0.08,
                          annotation_text="Twin offline", annotation_position="top left",
                          annotation=dict(font_color=ACCENT_AMBER, font_size=10))
            styled_fig(fig, height=380, title="SPM Over Time (Simulated Days)",
                       xaxis_title="Day", yaxis_title="Strokes per Minute")
            st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.markdown('<div class="section-title">🔧 FRICTION MULTIPLIER & FILL TRACKING</div>',
                    unsafe_allow_html=True)
        if decisions:
            df_dec = pd.DataFrame(decisions)
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Scatter(
                x=df_dec["t_sim_day"], y=df_dec["friction_mult"],
                mode="lines+markers", name="Friction ×",
                line=dict(color=ACCENT_RED, width=2),
                marker=dict(size=5)
            ), secondary_y=False)
            fig.add_trace(go.Scatter(
                x=df_dec["t_sim_day"], y=df_dec["fillage"],
                mode="lines+markers", name="Pump Fillage",
                line=dict(color=ACCENT_BLUE, width=2),
                marker=dict(size=5)
            ), secondary_y=True)
            fig.add_hline(y=1.0, line_dash="dot", line_color="#555", secondary_y=False)
            fig.add_hline(y=0.85, line_dash="dot", line_color=ACCENT_AMBER, opacity=0.4,
                          secondary_y=True, annotation_text="Fillage target",
                          annotation=dict(font_color=ACCENT_AMBER, font_size=10))
            styled_fig(fig, height=380, title="Friction & Fillage vs Time",
                       yaxis_title="Friction Multiplier", yaxis2_title="Fillage (-)")
            fig.update_yaxes(gridcolor=GRID_COLOR, secondary_y=True)
            st.plotly_chart(fig, use_container_width=True)

    # Acceptance summary
    st.markdown('<div class="section-title">✅ ACCEPTANCE TEST SCORECARD</div>', unsafe_allow_html=True)
    results = acceptance.get("results", [])
    acc_cols = st.columns(min(len(results), 9))
    for c, r in zip(acc_cols, results):
        badge = "badge-pass" if r["status"] == "PASS" else "badge-fail"
        with c:
            st.markdown(f"""
            <div style="text-align:center;padding:8px">
                <div style="color:#8899aa;font-family:'JetBrains Mono';font-size:18px;font-weight:700">{r['id']}</div>
                <div class="{badge}">{r['status']}</div>
            </div>
            """, unsafe_allow_html=True)

    # Comparison bar
    st.markdown("")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-title">📊 BASELINE vs TWIN COMPARISON</div>', unsafe_allow_html=True)
        categories = ["Oil (bbl)", "Power (kWh)", "Impact (h)", "Float Trips", "Cards"]
        base_vals = [base_sum["oil_bbl"], base_sum["kwh"], base_sum["impact_over_limit_h"],
                     base_sum["trips_low_load"], base_sum["cards"]]
        twin_vals = [twin_sum["oil_bbl"], twin_sum["kwh"], twin_sum["impact_over_limit_h"],
                     twin_sum["trips_low_load"], twin_sum["cards"]]
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Baseline", x=categories, y=base_vals,
                             marker_color="#ff6666", opacity=0.8))
        fig.add_trace(go.Bar(name="Twin", x=categories, y=twin_vals,
                             marker_color=ACCENT_BLUE, opacity=0.8))
        styled_fig(fig, height=300, barmode="group")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<div class="section-title">⏱️ DECISION LATENCY DISTRIBUTION</div>', unsafe_allow_html=True)
        if decisions:
            latencies = [d["total_s"] for d in decisions]
            fig = go.Figure()
            fig.add_trace(go.Histogram(
                x=latencies, nbinsx=15,
                marker_color=ACCENT_BLUE, opacity=0.8,
                name="Latency (s)"
            ))
            fig.add_vline(x=np.median(latencies), line_dash="dash", line_color=ACCENT_GREEN,
                          annotation_text=f"Median: {np.median(latencies):.1f}s",
                          annotation=dict(font_color=ACCENT_GREEN, font_size=11))
            styled_fig(fig, height=300, xaxis_title="Seconds", yaxis_title="Count",
                       title="PINN Inference Latency")
            st.plotly_chart(fig, use_container_width=True)


# =========================================================================
# PAGE: LIVE SCADA HMI
# =========================================================================
elif page == "📊 Live SCADA HMI":
    st.markdown('<div class="section-title">🖥️ SCADA HMI — REAL-TIME TAG MONITORING</div>',
                unsafe_allow_html=True)

    # Load tag history
    tags_df = query_db(DB_TWIN, """
        SELECT t, tag, value FROM tag_history
        WHERE well='BGW-01'
        ORDER BY t
    """)

    if tags_df.empty:
        st.warning("No tag history data found in twin.db")
    else:
        # Pivot for latest values
        latest_t = tags_df["t"].max()
        latest = tags_df[tags_df["t"] == latest_t].set_index("tag")["value"].to_dict()

        # Gauge row
        st.markdown("##### 🎛️ Live Instrument Gauges")
        g_cols = st.columns(6)

        gauge_data = [
            ("SPM", "SRP/SPM", "1/min", 0, 12, ACCENT_BLUE),
            ("VFD Freq", "VFD/Frequency", "Hz", 0, 80, ACCENT_GREEN),
            ("Motor Power", "VFD/MotorPower", "kW", 0, 20, ACCENT_AMBER),
            ("Wellhead T", "Wellhead/Temperature", "°C", 30, 250, ACCENT_RED),
            ("Tubing P", "Wellhead/TubingPressure", "psi", 0, 200, ACCENT_PURPLE),
            ("Fluid Level", "Wellhead/FluidLevel_Acoustic", "ft", 0, 3500, ACCENT_BLUE),
        ]
        for col, (label, tag, unit, lo, hi, color) in zip(g_cols, gauge_data):
            val = latest.get(tag, 0)
            with col:
                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=val,
                    title=dict(text=f"<b>{label}</b><br><span style='font-size:10px;color:#888'>{unit}</span>",
                               font=dict(size=13, color=TEXT_COLOR)),
                    number=dict(font=dict(size=24, color=color, family="JetBrains Mono")),
                    gauge=dict(
                        axis=dict(range=[lo, hi], tickfont=dict(size=9, color="#666")),
                        bar=dict(color=color, thickness=0.3),
                        bgcolor="#1a1d23",
                        borderwidth=1,
                        bordercolor="#1e3a5f",
                        steps=[
                            dict(range=[lo, lo + 0.3 * (hi - lo)], color="#0d1b2a"),
                            dict(range=[lo + 0.3 * (hi - lo), lo + 0.7 * (hi - lo)], color="#111720"),
                            dict(range=[lo + 0.7 * (hi - lo), hi], color="#1a1012"),
                        ],
                    )
                ))
                fig.update_layout(
                    height=180, margin=dict(l=20, r=20, t=50, b=10),
                    paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_COLOR)
                )
                st.plotly_chart(fig, use_container_width=True)

        # Time series plots
        st.markdown("##### 📈 Tag Time Series")
        tag_groups = {
            "SRP / Rod Pump": ["SRP/SPM", "SRP/PPRL", "SRP/MPRL", "SRP/PumpFillage_POC"],
            "VFD / Motor": ["VFD/Frequency", "VFD/MotorCurrent", "VFD/MotorPower"],
            "Wellhead / Surveys": ["Wellhead/Temperature", "Wellhead/TubingPressure",
                                   "Wellhead/CasingPressure"],
        }

        selected_group = st.selectbox("Tag Group", list(tag_groups.keys()))
        selected_tags = tag_groups[selected_group]
        tag_filter = tags_df[tags_df["tag"].isin(selected_tags)]

        if not tag_filter.empty:
            fig = make_subplots(rows=len(selected_tags), cols=1,
                                shared_xaxes=True, vertical_spacing=0.04,
                                subplot_titles=selected_tags)
            colors = [ACCENT_BLUE, ACCENT_GREEN, ACCENT_RED, ACCENT_AMBER, ACCENT_PURPLE]
            for i, tag in enumerate(selected_tags):
                td = tag_filter[tag_filter["tag"] == tag]
                fig.add_trace(go.Scatter(
                    x=td["t"] / 86400, y=td["value"],
                    mode="lines", name=tag,
                    line=dict(color=colors[i % len(colors)], width=1.5),
                ), row=i + 1, col=1)
            styled_fig(fig, height=180 * len(selected_tags),
                       xaxis=dict(title="Simulated Day", gridcolor=GRID_COLOR),
                       showlegend=False)
            for i in range(len(selected_tags)):
                fig.update_yaxes(gridcolor=GRID_COLOR, row=i + 1, col=1)
                fig.update_xaxes(gridcolor=GRID_COLOR, row=i + 1, col=1)
            st.plotly_chart(fig, use_container_width=True)

        # PLC Status
        st.markdown("##### 🔒 PLC & Twin Status Tags")
        status_tags = ["PLC/Mode", "PLC/Alarm", "PLC/SimTime", "Twin/Heartbeat",
                       "SRP/RunStatus", "SRP/RunTimeFrac_24h", "Steam/Phase",
                       "Steam/DaysSinceInjectionEnd"]
        st_data = []
        for tag in status_tags:
            val = latest.get(tag, "N/A")
            st_data.append({"Tag": tag, "Value": f"{val:.2f}" if isinstance(val, float) else str(val)})
        st.dataframe(pd.DataFrame(st_data), hide_index=True, use_container_width=True)


# =========================================================================
# PAGE: DYNAMOMETER CARDS
# =========================================================================
elif page == "🔬 Dynamometer Cards":
    st.markdown('<div class="section-title">🔬 DYNAMOMETER CARD VIEWER — SURFACE & DOWNHOLE (PINN)</div>',
                unsafe_allow_html=True)

    cards_df = query_db(DB_TWIN, """
        SELECT card_id, t, spm, stroke, pos, load
        FROM cards WHERE well='BGW-01'
        ORDER BY card_id
    """)

    if cards_df.empty:
        st.warning("No card data available.")
    else:
        card_ids = cards_df["card_id"].tolist()
        col_slider, col_info = st.columns([3, 1])
        with col_slider:
            selected_id = st.select_slider(
                "Select Card ID",
                options=card_ids,
                value=card_ids[len(card_ids) // 2],
                format_func=lambda x: f"Card #{x}"
            )

        row = cards_df[cards_df["card_id"] == selected_id].iloc[0]
        pos = json.loads(row["pos"])
        load = json.loads(row["load"])
        day = row["t"] / 86400.0

        with col_info:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Card #{selected_id}</div>
                <div class="kpi-value" style="color:{ACCENT_BLUE};font-size:18px">Day {day:.2f}</div>
                <div class="kpi-label">SPM {row['spm']:.1f} | Stroke {row['stroke']:.0f}"</div>
            </div>
            """, unsafe_allow_html=True)

        col_card, col_card2 = st.columns(2)
        with col_card:
            st.markdown("##### Surface Dynamometer Card")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=pos, y=load,
                mode="lines",
                line=dict(color=ACCENT_BLUE, width=2.5),
                fill="toself",
                fillcolor="rgba(0,212,255,0.08)",
                name="Surface Card"
            ))
            styled_fig(fig, height=400,
                       xaxis_title="Position (ft)", yaxis_title="Load (lbf)",
                       title=f"Surface Card #{selected_id} — Day {day:.2f}")
            st.plotly_chart(fig, use_container_width=True)

        with col_card2:
            st.markdown("##### Card Load vs Position Waterfall")
            # Show multiple cards for comparison
            n_show = min(8, len(card_ids))
            step = max(1, len(card_ids) // n_show)
            sample_ids = card_ids[::step][:n_show]
            fig = go.Figure()
            for sid in sample_ids:
                r = cards_df[cards_df["card_id"] == sid].iloc[0]
                p = json.loads(r["pos"])
                l = json.loads(r["load"])
                d = r["t"] / 86400.0
                opacity = 0.3 if sid != selected_id else 1.0
                width = 1 if sid != selected_id else 3
                fig.add_trace(go.Scatter(
                    x=p, y=l, mode="lines",
                    name=f"Day {d:.1f}",
                    line=dict(width=width),
                    opacity=opacity,
                ))
            styled_fig(fig, height=400, xaxis_title="Position (ft)", yaxis_title="Load (lbf)",
                       title="Card Evolution Over Time")
            st.plotly_chart(fig, use_container_width=True)

        # Card statistics
        st.markdown("##### 📊 Card Statistics")
        stats_data = []
        for _, r in cards_df.iterrows():
            p = json.loads(r["pos"])
            l = json.loads(r["load"])
            stats_data.append({
                "Card ID": int(r["card_id"]),
                "Day": round(r["t"] / 86400, 2),
                "SPM": round(r["spm"], 1),
                "Stroke (in)": round(r["stroke"], 0),
                "PPRL (lbf)": round(max(l), 1),
                "MPRL (lbf)": round(min(l), 1),
                "Load Range": round(max(l) - min(l), 1),
                "Float Margin": round(min(l) / (490 * math.pi / 4 * 0.875 ** 2 / 144 * (1050 / 0.3048) *
                                                (1 - 62.4 * 0.96 / 490)), 3),
            })
        st.dataframe(pd.DataFrame(stats_data), hide_index=True, use_container_width=True, height=300)


# =========================================================================
# PAGE: TWIN DECISION ENGINE
# =========================================================================
elif page == "🧠 Twin Decision Engine":
    st.markdown('<div class="section-title">🧠 PINN DIGITAL TWIN — DECISION ENGINE & AUDIT TRAIL</div>',
                unsafe_allow_html=True)

    twin_run = load_json(os.path.join(OUT, "twin_run.json"))
    decisions = twin_run.get("decisions", [])

    if not decisions:
        st.warning("No decision data available.")
    else:
        df_dec = pd.DataFrame(decisions)

        # Startup context
        with st.expander("🔧 Twin Startup Configuration", expanded=False):
            startup = twin_run.get("startup", {})
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("**Completion**")
                st.json(startup.get("completion", {}))
            with c2:
                st.markdown("**Fluid Properties**")
                st.json(startup.get("fluid", {}))
            with c3:
                st.markdown("**Failure History**")
                st.json(startup.get("failure_history", {}))

        # Decision timeline
        st.markdown("##### 🕐 Decision Timeline")
        fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                            subplot_titles=["SPM Control", "Pump Fillage", "Rod Float Margin", "Friction Multiplier"],
                            row_heights=[0.3, 0.25, 0.25, 0.2])

        # SPM
        fig.add_trace(go.Scatter(x=df_dec["t_sim_day"], y=df_dec["spm_cur"], mode="lines+markers",
                                 name="Current SPM", line=dict(color=ACCENT_BLUE, width=2),
                                 marker=dict(size=5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_dec["t_sim_day"], y=df_dec["spm_req"], mode="lines+markers",
                                 name="Requested SPM", line=dict(color=ACCENT_GREEN, width=2, dash="dash"),
                                 marker=dict(size=5, symbol="diamond")), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_dec["t_sim_day"], y=df_dec["model_spm"], mode="lines",
                                 name="Model Optimum", line=dict(color=ACCENT_PURPLE, width=1, dash="dot")), row=1, col=1)

        # Fillage
        fig.add_trace(go.Scatter(x=df_dec["t_sim_day"], y=df_dec["fillage"], mode="lines+markers",
                                 name="Fillage", line=dict(color=ACCENT_BLUE, width=2),
                                 marker=dict(size=5)), row=2, col=1)
        fig.add_hline(y=0.85, line_dash="dot", line_color=ACCENT_AMBER, row=2, col=1)

        # Rod float margin
        fig.add_trace(go.Scatter(x=df_dec["t_sim_day"], y=df_dec["margin"], mode="lines+markers",
                                 name="Float Margin", line=dict(color=ACCENT_RED, width=2),
                                 marker=dict(size=5)), row=3, col=1)
        fig.add_hline(y=0.20, line_dash="dot", line_color=ACCENT_RED, row=3, col=1)

        # Friction
        fig.add_trace(go.Scatter(x=df_dec["t_sim_day"], y=df_dec["friction_mult"], mode="lines+markers",
                                 name="Friction ×", line=dict(color=ACCENT_AMBER, width=2),
                                 marker=dict(size=5)), row=4, col=1)

        styled_fig(fig, height=700, showlegend=True)
        for i in range(1, 5):
            fig.update_yaxes(gridcolor=GRID_COLOR, row=i, col=1)
            fig.update_xaxes(gridcolor=GRID_COLOR, row=i, col=1)
        fig.update_xaxes(title_text="Simulated Day", row=4, col=1)
        st.plotly_chart(fig, use_container_width=True)

        # Decision table
        st.markdown("##### 📋 Decision Log")
        action_filter = st.multiselect(
            "Filter by action type",
            options=df_dec["action"].str.split(":").str[0].unique().tolist(),
            default=[]
        )
        display_df = df_dec if not action_filter else df_dec[
            df_dec["action"].str.split(":").str[0].isin(action_filter)]

        display_cols = ["t_sim_day", "card_id", "action", "spm_cur", "spm_req", "rf_req",
                        "fillage", "margin", "friction_mult", "quality", "alarm", "diag_s"]
        st.dataframe(display_df[display_cols].round(3), hide_index=True,
                     use_container_width=True, height=400)

        # Audit trail from DB
        st.markdown("##### 📝 Full Audit Trail (Events Database)")
        events = query_db(DB_TWIN, """
            SELECT t, source, kind, text FROM events
            WHERE well='BGW-01' AND (source LIKE 'TWIN%' OR source='PLC')
            ORDER BY t
        """)
        if not events.empty:
            events["Day"] = (events["t"] / 86400).round(3)
            st.dataframe(events[["Day", "source", "kind", "text"]], hide_index=True,
                         use_container_width=True, height=400)


# =========================================================================
# PAGE: FIELD HISTORIAN
# =========================================================================
elif page == "📈 Field Historian":
    st.markdown('<div class="section-title">📈 MULTI-WELL FIELD HISTORIAN — 3-YEAR PRODUCTION DATA</div>',
                unsafe_allow_html=True)

    wells = query_db(DB_TWIN, "SELECT DISTINCT well FROM production_daily ORDER BY well")
    well_list = wells["well"].tolist() if not wells.empty else ["BGW-01"]
    selected_well = st.selectbox("Select Well", well_list)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📊 Production", "🌡️ CSS Cycles", "⚡ VFD/Energy", "🔧 Failures", "🧪 Well Tests"])

    with tab1:
        prod = query_db(DB_TWIN, "SELECT * FROM production_daily WHERE well=? ORDER BY date", (selected_well,))
        if not prod.empty:
            prod["date"] = pd.to_datetime(prod["date"])
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                                subplot_titles=["Daily Oil & Water Rate", "Cumulative Production"])
            fig.add_trace(go.Scatter(x=prod["date"], y=prod["oil_bpd"], name="Oil (bpd)",
                                     line=dict(color=ACCENT_GREEN, width=1.5), fill="tozeroy",
                                     fillcolor="rgba(0,255,136,0.1)"), row=1, col=1)
            fig.add_trace(go.Scatter(x=prod["date"], y=prod["water_bpd"], name="Water (bpd)",
                                     line=dict(color=ACCENT_BLUE, width=1.5), fill="tozeroy",
                                     fillcolor="rgba(0,212,255,0.05)"), row=1, col=1)
            fig.add_trace(go.Scatter(x=prod["date"], y=prod["oil_bpd"].cumsum(), name="Cum Oil",
                                     line=dict(color=ACCENT_GREEN, width=2)), row=2, col=1)
            fig.add_trace(go.Scatter(x=prod["date"], y=prod["water_bpd"].cumsum(), name="Cum Water",
                                     line=dict(color=ACCENT_BLUE, width=2)), row=2, col=1)
            styled_fig(fig, height=500)
            for i in range(1, 3):
                fig.update_yaxes(gridcolor=GRID_COLOR, row=i, col=1)
                fig.update_xaxes(gridcolor=GRID_COLOR, row=i, col=1)
            st.plotly_chart(fig, use_container_width=True)

            # Summary stats
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Avg Oil (bpd)", f"{prod['oil_bpd'].mean():.1f}")
            c2.metric("Peak Oil (bpd)", f"{prod['oil_bpd'].max():.1f}")
            c3.metric("Avg Water Cut", f"{(prod['water_bpd'] / (prod['oil_bpd'] + prod['water_bpd'] + 1e-9)).mean():.1%}")
            c4.metric("Total Days", f"{len(prod)}")

    with tab2:
        css = query_db(DB_TWIN, "SELECT * FROM css_cycles WHERE well=? ORDER BY cycle", (selected_well,))
        if not css.empty:
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.10,
                                subplot_titles=["Cycle Oil Production (bbl)", "Steam Injected (t)"])
            fig.add_trace(go.Bar(x=css["cycle"], y=css["cycle_oil_bbl"],
                                 marker_color=ACCENT_GREEN, name="Oil (bbl)", opacity=0.8), row=1, col=1)
            fig.add_trace(go.Bar(x=css["cycle"], y=css["steam_t"],
                                 marker_color=ACCENT_RED, name="Steam (t)", opacity=0.8), row=2, col=1)
            styled_fig(fig, height=450, xaxis2_title="Cycle Number")
            for i in range(1, 3):
                fig.update_yaxes(gridcolor=GRID_COLOR, row=i, col=1)
                fig.update_xaxes(gridcolor=GRID_COLOR, row=i, col=1)
            st.plotly_chart(fig, use_container_width=True)

            # CSS table
            st.dataframe(css.round(2), hide_index=True, use_container_width=True)

    with tab3:
        vfd = query_db(DB_TWIN, "SELECT * FROM vfd_daily WHERE well=? ORDER BY date", (selected_well,))
        if not vfd.empty:
            vfd["date"] = pd.to_datetime(vfd["date"])
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                                subplot_titles=["VFD Frequency & SPM", "Daily Energy (kWh)", "Motor Current (A)"])
            fig.add_trace(go.Scatter(x=vfd["date"], y=vfd["avg_spm"], name="SPM",
                                     line=dict(color=ACCENT_BLUE, width=1.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=vfd["date"], y=vfd["kwh"], name="kWh",
                                     line=dict(color=ACCENT_AMBER, width=1.5),
                                     fill="tozeroy", fillcolor="rgba(255,179,0,0.1)"), row=2, col=1)
            fig.add_trace(go.Scatter(x=vfd["date"], y=vfd["avg_current_A"], name="Current (A)",
                                     line=dict(color=ACCENT_RED, width=1.5)), row=3, col=1)
            styled_fig(fig, height=550)
            for i in range(1, 4):
                fig.update_yaxes(gridcolor=GRID_COLOR, row=i, col=1)
                fig.update_xaxes(gridcolor=GRID_COLOR, row=i, col=1)
            st.plotly_chart(fig, use_container_width=True)

    with tab4:
        fails = query_db(DB_TWIN, "SELECT * FROM rod_failures WHERE well=? ORDER BY date", (selected_well,))
        unsetting = query_db(DB_TWIN, "SELECT * FROM pump_unsetting WHERE well=? ORDER BY date", (selected_well,))

        if not fails.empty:
            st.markdown("##### 🔧 Rod Failure History")
            fig = px.scatter(fails, x="wellhead_T_degC", y="spm_before", color="mode",
                             size="downtime_days", hover_data=["date", "depth_ft"],
                             title="Rod Failures: Temperature vs SPM",
                             color_discrete_sequence=[ACCENT_RED, ACCENT_AMBER, ACCENT_PURPLE])
            styled_fig(fig, height=350, xaxis_title="Wellhead T (°C)", yaxis_title="SPM Before Failure")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(fails.round(2), hide_index=True, use_container_width=True)

        if not unsetting.empty:
            st.markdown("##### ⚠️ Pump Unsetting Events")
            st.dataframe(unsetting.round(2), hide_index=True, use_container_width=True)

    with tab5:
        tests = query_db(DB_TWIN, "SELECT * FROM well_tests WHERE well=? ORDER BY date", (selected_well,))
        if not tests.empty:
            tests["date"] = pd.to_datetime(tests["date"])
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Scatter(x=tests["date"], y=tests["oil_bpd"], mode="lines+markers",
                                     name="Oil (bpd)", line=dict(color=ACCENT_GREEN, width=2),
                                     marker=dict(size=5)), secondary_y=False)
            fig.add_trace(go.Scatter(x=tests["date"], y=tests["wellhead_T_degC"], mode="lines+markers",
                                     name="WH Temp (°C)", line=dict(color=ACCENT_RED, width=2, dash="dash"),
                                     marker=dict(size=5, symbol="triangle-up")), secondary_y=True)
            styled_fig(fig, height=350, title="Well Test Results",
                       yaxis_title="Oil Rate (bpd)", yaxis2_title="Wellhead Temp (°C)")
            fig.update_yaxes(gridcolor=GRID_COLOR, secondary_y=True)
            st.plotly_chart(fig, use_container_width=True)


# =========================================================================
# PAGE: ACCEPTANCE TESTS
# =========================================================================
elif page == "✅ Acceptance Tests":
    st.markdown('<div class="section-title">✅ INTEGRATION ACCEPTANCE TEST REPORT</div>',
                unsafe_allow_html=True)

    acceptance = load_json(os.path.join(OUT, "acceptance_report.json"))
    summary = acceptance.get("summary", {})
    results = acceptance.get("results", [])

    # Summary header
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Tests Passed</div>
            <div class="kpi-value" style="color:{ACCENT_GREEN}">{summary.get("PASS", 0)} / {summary.get("PASS", 0) + summary.get("FAIL", 0)}</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        fail_ct = summary.get("FAIL", 0)
        col = ACCENT_GREEN if fail_ct == 0 else ACCENT_RED
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Tests Failed</div>
            <div class="kpi-value" style="color:{col}">{fail_ct}</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        pct = 100 * summary.get("PASS", 0) / max(summary.get("PASS", 0) + summary.get("FAIL", 0), 1)
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Pass Rate</div>
            <div class="kpi-value" style="color:{ACCENT_GREEN}">{pct:.0f}%</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")

    # Individual tests
    for r in results:
        badge_cls = "badge-pass" if r["status"] == "PASS" else "badge-fail"
        icon = "✅" if r["status"] == "PASS" else "❌"
        with st.expander(f'{icon} **{r["id"]}** — {r["test"]}'):
            st.markdown(f'<span class="{badge_cls}">{r["status"]}</span>', unsafe_allow_html=True)
            st.markdown("")
            st.markdown(f"**Evidence:** {r.get('evidence', 'N/A')}")

    # Scenario description
    st.markdown("")
    st.markdown('<div class="section-title">🎬 TEST SCENARIO TIMELINE</div>', unsafe_allow_html=True)
    scenario_data = pd.DataFrame([
        {"Day": "0-1", "Event": "Normal production (CSS cycle 7, post-soak)", "Severity": "None"},
        {"Day": "1.0", "Event": "Near-wellbore damage — inflow drops 55%", "Severity": "High"},
        {"Day": "2.0-3.0", "Event": "Tubing cooling + asphaltene friction buildup (×6.5)", "Severity": "Critical"},
        {"Day": "3.5-3.75", "Event": "Load-cell sensor desynchronization", "Severity": "High"},
        {"Day": "4.0-4.25", "Event": "Twin service offline (6 h test)", "Severity": "High"},
        {"Day": "4.25-5.0", "Event": "Twin recovered — watchdog cleared", "Severity": "None"},
    ])
    st.dataframe(scenario_data, hide_index=True, use_container_width=True)
