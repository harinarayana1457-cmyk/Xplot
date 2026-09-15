"""
XPLOT STUDIO — Universal Scientific .dat Telemetry & Plot Suite
Built from scratch with modern Dark Observatory engineering aesthetics.
Runs on localhost:8501
"""

import io
import csv
import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Xplot Studio — Scientific .dat Plotter",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Visual System: Dark Observatory & Scientific Cybernetics
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

    :root {
        --bg-main: #090D16;
        --card-bg: #111827;
        --border-color: #1F2937;
        --accent-glow: #38BDF8;
        --accent-emerald: #10B981;
        --text-primary: #F3F4F6;
        --text-secondary: #9CA3AF;
    }

    .stApp {
        background-color: var(--bg-main);
        color: var(--text-primary);
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    code, pre {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Top Navigation Banner */
    .studio-navbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 16px 24px;
        background: #0F172A;
        border: 1px solid #1E293B;
        border-radius: 14px;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }
    .brand-title {
        font-size: 1.5rem;
        font-weight: 700;
        letter-spacing: -0.03em;
        background: linear-gradient(90deg, #38BDF8 0%, #818CF8 50%, #C084FC 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    .brand-tag {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: #94A3B8;
        margin-top: 2px;
    }
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 12px;
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(16, 185, 129, 0.3);
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 600;
        color: #34D399;
        font-family: 'JetBrains Mono', monospace;
    }
    .status-dot {
        width: 7px;
        height: 7px;
        background-color: #34D399;
        border-radius: 50%;
        box-shadow: 0 0 8px #34D399;
    }

    /* Metric Cards */
    .stat-card {
        background: #0F172A;
        border: 1px solid #1E293B;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .stat-card:hover {
        transform: translateY(-2px);
        border-color: #38BDF8;
    }
    .stat-label {
        font-size: 0.72rem;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.08em;
        color: #64748B;
        margin-bottom: 6px;
    }
    .stat-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #F8FAFC;
        font-family: 'JetBrains Mono', monospace;
    }
    .stat-sub {
        font-size: 0.75rem;
        color: #38BDF8;
        margin-top: 4px;
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #0B0F19;
        border-right: 1px solid #1E293B;
    }
    
    /* Tabs & Content Containers */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid #1E293B;
        padding-bottom: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 600;
        font-size: 0.88rem;
        color: #94A3B8;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1E293B !important;
        color: #38BDF8 !important;
    }

    /* Empty state */
    .empty-hero {
        background: radial-gradient(circle at 50% 50%, #1E293B 0%, #0F172A 100%);
        border: 1px dashed #334155;
        border-radius: 16px;
        padding: 48px 32px;
        text-align: center;
        margin: 20px 0;
    }
    .empty-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #F1F5F9;
        margin-bottom: 8px;
    }
    .empty-desc {
        color: #94A3B8;
        font-size: 0.95rem;
        max-width: 540px;
        margin: 0 auto;
        line-height: 1.5;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Engine: Robust Ingestion & Parser Core
# ---------------------------------------------------------------------------
COMMENT_MARKERS = ("#", "%", "//", ";", "!")

def clean_lines(lines):
    clean = []
    for l in lines:
        s = l.strip()
        if not s:
            continue
        if any(s.startswith(m) for m in COMMENT_MARKERS):
            continue
        clean.append(s)
    return clean

def detect_sep(lines):
    sample = "\n".join(lines[:20])
    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample, delimiters=",\t;|")
        delim = dialect.delimiter
        hits = sum(1 for line in lines[:20] if delim in line)
        if hits >= max(1, len(lines[:20]) // 2):
            return delim
    except Exception:
        pass

    # Frequency analysis fallback
    for sep in (",", "\t", ";", "|"):
        cnts = [l.count(sep) for l in lines[:20] if l.strip()]
        if cnts and min(cnts) > 0 and max(cnts) == min(cnts):
            return sep
    return None

def detect_header(line, sep):
    tokens = line.split(sep) if sep else line.split()
    if not tokens:
        return False
    num_count = 0
    for t in tokens:
        try:
            float(t.strip())
            num_count += 1
        except ValueError:
            pass
    return (num_count / len(tokens)) < 0.5

def ingest_dat(raw_bytes):
    text = None
    for encoding in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            text = raw_bytes.decode(encoding)
            break
        except Exception:
            continue
    if text is None:
        raise ValueError("Could not decode stream. Supported encodings: UTF-8, Latin-1, CP1252.")

    lines = clean_lines(text.splitlines())
    if not lines:
        raise ValueError("Data file is empty or contains only commented rows.")

    sep = detect_sep(lines)
    has_header = detect_header(lines[0], sep)

    buf = io.StringIO("\n".join(lines))
    df = pd.read_csv(
        buf,
        sep=sep if sep else r"\s+",
        header=0 if has_header else None,
        engine="python",
        on_bad_lines="skip"
    )

    if not has_header:
        df.columns = [f"Col_{i}" for i in range(df.shape[1])]

    df.columns = [str(c).strip() for c in df.columns]
    df.dropna(axis=1, how="all", inplace=True)
    df.reset_index(drop=True, inplace=True)

    # Convert numerics
    for c in df.columns:
        converted = pd.to_numeric(df[c], errors="coerce")
        if converted.notna().sum() / max(len(df), 1) >= 0.5:
            df[c] = converted

    format_labels = {",": "CSV / Comma", "\t": "Tab-Delimited", ";": "Semicolon", "|": "Pipe"}
    return df, format_labels.get(sep, "Whitespace / Space"), has_header

# ---------------------------------------------------------------------------
# Sidebar Controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚡ Xplot Telemetry")
    st.caption("Universal Scientific Data Engine")
    st.markdown("---")

    st.markdown("#### 📥 Data Source")
    file_upload = st.file_uploader("Upload dataset (`.dat`, `.txt`, `.csv`)", type=["dat", "txt", "csv"])
    
    samples = ["(None)", "sinusoidal_comma.dat", "spectrum_whitespace.dat", "tabular_tabs.dat", "semicolon_test.dat"]
    sample_choice = st.selectbox("Or choose a sample dataset:", samples, index=1 if file_upload is None else 0)

    st.markdown("---")

df = None
active_filename = None
detected_format = ""
header_status = False

if file_upload is not None:
    active_filename = file_upload.name
    try:
        df, detected_format, header_status = ingest_dat(file_upload.getvalue())
    except Exception as e:
        st.error(f"Ingestion error: {e}")
elif sample_choice != "(None)":
    active_filename = sample_choice
    path = os.path.join("sample_data", sample_choice)
    if os.path.exists(path):
        with open(path, "rb") as f:
            try:
                df, detected_format, header_status = ingest_dat(f.read())
            except Exception as e:
                st.error(f"Sample load error: {e}")

# ---------------------------------------------------------------------------
# Top Header Bar
# ---------------------------------------------------------------------------
status_text = "READY — DATA LOADED" if df is not None else "STANDBY — AWAITING DATA"
dot_color = "#34D399" if df is not None else "#94A3B8"
bg_pill = "rgba(16, 185, 129, 0.1)" if df is not None else "rgba(148, 163, 184, 0.1)"
border_pill = "rgba(16, 185, 129, 0.3)" if df is not None else "rgba(148, 163, 184, 0.2)"

st.markdown(f"""
<div class="studio-navbar">
    <div>
        <h1 class="brand-title">XPLOT STUDIO</h1>
        <div class="brand-tag">Scientific Visualization Engine · Laboratory Telemetry</div>
    </div>
    <div class="status-pill" style="background:{bg_pill}; border-color:{border_pill}; color:{dot_color};">
        <div class="status-dot" style="background-color:{dot_color}; box-shadow:0 0 8px {dot_color};"></div>
        {status_text}
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Dashboard Body
# ---------------------------------------------------------------------------
if df is None:
    st.markdown("""
    <div class="empty-hero">
        <div style="font-size: 2.5rem; margin-bottom: 12px;">📊</div>
        <div class="empty-title">No Dataset Loaded</div>
        <div class="empty-desc">
            Upload any arbitrary <code>.dat</code> file or choose a sample dataset from the sidebar to start parsing, inspecting, and rendering publication-grade interactive plots.
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    # Key telemetry stats
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">Total Records</div>
            <div class="stat-value">{len(df):,}</div>
            <div class="stat-sub">Indexed rows</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">Total Channels</div>
            <div class="stat-value">{len(df.columns)}</div>
            <div class="stat-sub">{len(numeric_cols)} numeric variables</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">Detected Delimiter</div>
            <div class="stat-value" style="font-size: 1.25rem; padding-top: 4px;">{detected_format}</div>
            <div class="stat-sub">Header: {"Auto-detected" if header_status else "Generated"}</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">Memory Footprint</div>
            <div class="stat-value" style="font-size: 1.25rem; padding-top: 4px;">{df.memory_usage(deep=True).sum() / 1024:.1f} KB</div>
            <div class="stat-sub">Active buffer</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    tab_vis, tab_data, tab_meta = st.tabs([
        "📈 Interactive Plotter", 
        "📋 Data Inspector", 
        "🔬 Channel Diagnostics"
    ])

    # -----------------------------------------------------------------------
    # TAB 1: INTERACTIVE PLOTTER
    # -----------------------------------------------------------------------
    with tab_vis:
        with st.sidebar:
            st.markdown("#### 🎯 Channel Mapping")
            
            x_col = st.selectbox("X-Axis Channel", ["(index)"] + list(df.columns), index=1 if len(df.columns) > 1 else 0)
            
            y_default = [numeric_cols[0]] if numeric_cols else []
            if len(numeric_cols) > 1 and numeric_cols[0] == x_col:
                y_default = [numeric_cols[1]]
            elif len(numeric_cols) > 1:
                y_default = [numeric_cols[0], numeric_cols[1]]

            y_cols = st.multiselect(
                "Y-Axis Channels (Multi-Overlay)",
                options=list(df.columns),
                default=y_default,
                help="Select channels to overlay"
            )

            st.markdown("#### 📊 Plot Archetype")
            plot_type = st.selectbox(
                "Archetype",
                ["Line Curve", "Scatter Cloud", "Line + Points", "Grouped Bar", "Histogram Distribution", "Step Transition"],
                index=0
            )

            st.markdown("#### ⚙️ Axis & Scaling")
            c_s1, c_s2 = st.columns(2)
            with c_s1:
                log_x = st.checkbox("Log X")
            with c_s2:
                log_y = st.checkbox("Log Y")

            show_grid = st.checkbox("Grid Network", value=True)
            show_legend = st.checkbox("Legend Map", value=True)

            theme_palette = st.selectbox(
                "Color System",
                ["Electric Cyan", "Neon Matrix", "Sunset Amber", "Cyberpunk Violet", "Scientific Viridis"],
                index=0
            )

            st.markdown("#### 📝 Axis Annotations")
            chart_title = st.text_input("Title", value=f"{plot_type} · {active_filename}")
            custom_xlabel = st.text_input("X Label", value=x_col if x_col != "(index)" else "Index")
            custom_ylabel = st.text_input("Y Label", value=", ".join(y_cols) if y_cols else "Signal Magnitude")

        if not y_cols:
            st.warning("⚠️ Select at least one Y-Axis Channel from the sidebar to render visualization.")
        else:
            invalid_y = [c for c in y_cols if not pd.api.types.is_numeric_dtype(df[c])]
            if invalid_y:
                st.error(f"❌ Non-numeric channels selected: `{invalid_y}`. Please select numeric columns for the Y axis.")
            else:
                scale_safe = True
                if log_x and x_col != "(index)":
                    if pd.api.types.is_numeric_dtype(df[x_col]):
                        if (df[x_col].dropna() <= 0).any():
                            st.error(f"❌ Log X scale requires all values > 0. Channel `{x_col}` has zero or negative points.")
                            scale_safe = False
                    else:
                        st.error(f"❌ Channel `{x_col}` is non-numeric; cannot scale logarithmically.")
                        scale_safe = False

                if log_y:
                    for c in y_cols:
                        if (df[c].dropna() <= 0).any():
                            st.error(f"❌ Log Y scale requires all values > 0. Channel `{c}` has zero or negative points.")
                            scale_safe = False
                            break

                if scale_safe:
                    palettes = {
                        "Electric Cyan": ["#38BDF8", "#818CF8", "#F472B6", "#FB923C", "#34D399", "#A78BFA"],
                        "Neon Matrix": ["#10B981", "#06B6D4", "#3B82F6", "#F59E0B", "#EF4444", "#EC4899"],
                        "Sunset Amber": ["#F59E0B", "#F97316", "#EF4444", "#EC4899", "#8B5CF6", "#3B82F6"],
                        "Cyberpunk Violet": ["#A855F7", "#EC4899", "#06B6D4", "#10B981", "#F59E0B", "#6366F1"],
                        "Scientific Viridis": ["#440154", "#3B528B", "#21918C", "#5EC962", "#FDE725", "#35B779"],
                    }
                    colors = palettes.get(theme_palette, palettes["Electric Cyan"])

                    fig = go.Figure()
                    x_data = df.index if x_col == "(index)" else df[x_col]

                    for i, y_c in enumerate(y_cols):
                        color = colors[i % len(colors)]
                        
                        if plot_type == "Line Curve":
                            fig.add_trace(go.Scatter(
                                x=x_data, y=df[y_c], mode="lines", name=y_c,
                                line=dict(color=color, width=2.5)
                            ))
                        elif plot_type == "Scatter Cloud":
                            fig.add_trace(go.Scatter(
                                x=x_data, y=df[y_c], mode="markers", name=y_c,
                                marker=dict(color=color, size=7, opacity=0.85)
                            ))
                        elif plot_type == "Line + Points":
                            fig.add_trace(go.Scatter(
                                x=x_data, y=df[y_c], mode="lines+markers", name=y_c,
                                line=dict(color=color, width=2), marker=dict(color=color, size=5)
                            ))
                        elif plot_type == "Grouped Bar":
                            fig.add_trace(go.Bar(
                                x=x_data, y=df[y_c], name=y_c,
                                marker=dict(color=color, opacity=0.9)
                            ))
                        elif plot_type == "Step Transition":
                            fig.add_trace(go.Scatter(
                                x=x_data, y=df[y_c], mode="lines", line_shape="hv", name=y_c,
                                line=dict(color=color, width=2.2)
                            ))
                        elif plot_type == "Histogram Distribution":
                            fig.add_trace(go.Histogram(
                                x=df[y_c].dropna(), name=y_c,
                                marker=dict(color=color), opacity=0.75
                            ))

                    fig.update_layout(
                        title=dict(
                            text=chart_title,
                            font=dict(family="Plus Jakarta Sans", size=18, color="#F8FAFC")
                        ),
                        xaxis_title=custom_xlabel if plot_type != "Histogram Distribution" else "Binned Value",
                        yaxis_title=custom_ylabel if plot_type != "Histogram Distribution" else "Occurrence Frequency",
                        xaxis_type="log" if log_x and plot_type != "Histogram Distribution" else "linear",
                        yaxis_type="log" if log_y else "linear",
                        showlegend=show_legend,
                        legend=dict(
                            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                            font=dict(color="#E2E8F0", size=11), bgcolor="rgba(15, 23, 42, 0.7)"
                        ),
                        paper_bgcolor="#0F172A",
                        plot_bgcolor="#0A0F1D",
                        font=dict(family="Plus Jakarta Sans", color="#94A3B8"),
                        height=620,
                        margin=dict(l=50, r=40, t=75, b=50),
                        hovermode="x unified" if plot_type != "Histogram Distribution" else "closest"
                    )

                    grid_style = dict(
                        showgrid=show_grid, gridcolor="#1E293B",
                        zeroline=True, zerolinecolor="#334155",
                        tickfont=dict(family="JetBrains Mono", size=10, color="#64748B")
                    )
                    fig.update_xaxes(**grid_style)
                    fig.update_yaxes(**grid_style)

                    st.plotly_chart(fig, use_container_width=True)

                    # Export Tools
                    st.markdown("#### 💾 Export Artifacts")
                    e1, e2 = st.columns([1, 2])
                    with e1:
                        csv_export = df.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            label="📥 Download Cleaned CSV",
                            data=csv_export,
                            file_name=f"{active_filename.rsplit('.', 1)[0]}_cleaned.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    with e2:
                        st.info("💡 **Camera Tool**: Hover over the top-right toolbar on the chart to export high-resolution PNG or SVG snapshots.")

    # -----------------------------------------------------------------------
    # TAB 2: DATA INSPECTOR
    # -----------------------------------------------------------------------
    with tab_data:
        st.markdown(f"#### First 30 Records of `{active_filename}`")
        st.dataframe(df.head(30), use_container_width=True)

        st.markdown("#### Statistical Moments")
        if numeric_cols:
            st.dataframe(df[numeric_cols].describe().T, use_container_width=True)
        else:
            st.info("No numeric channels detected for statistical aggregation.")

    # -----------------------------------------------------------------------
    # TAB 3: DIAGNOSTICS
    # -----------------------------------------------------------------------
    with tab_meta:
        st.markdown("#### Channel Telemetry & Missingness Map")
        meta_table = []
        for col in df.columns:
            meta_table.append({
                "Channel": col,
                "Datatype": str(df[col].dtype),
                "Populated": int(df[col].notna().sum()),
                "Missing": int(df[col].isna().sum()),
                "Completeness": f"{(df[col].notna().sum() / len(df) * 100):.1f}%",
                "Unique Values": int(df[col].nunique()),
                "First Sample": str(df[col].iloc[0]) if len(df) > 0 else "—"
            })
        st.dataframe(pd.DataFrame(meta_table), use_container_width=True)
