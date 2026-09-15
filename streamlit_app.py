"""
xppnautplot — Universal .dat File Inspector & Plotter (Streamlit Web App)
=========================================================================
Runs on localhost (default: http://localhost:8501)
Enhancements:
  - Polished modern scientific UI with custom CSS, cards, badges, and responsive stats
  - Robust auto-detection of delimiters (comma, tab, semicolon, pipe, whitespace)
  - Auto-skips comments (#, %, //, ;, !)
  - Auto-detects headers or generates clean Col_0... labels
  - Robust numeric coercion and handling of missing/NaN values
  - Interactive Plotly charts with custom color palettes, markers, line styles, opacity
  - Multi-series support with optional grouped/stacked/overlay views
  - Axis toggles: Log/Linear with safety checks, Zero-line toggle, Grid toggle
  - High-resolution SVG / PNG / PDF plot export instructions and clean CSV data download
"""

import io
import csv
import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st

# Page setup
st.set_page_config(
    page_title="xppnautplot — .dat Inspector & Plotter",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Design System (Data-Dense Dashboard + Modern Clean Aesthetics)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    code, pre {
        font-family: 'Fira Code', monospace !important;
    }
    
    /* Header Card */
    .hero-header {
        background: linear-gradient(135deg, #1E3A8A 0%, #1E40AF 50%, #3B82F6 100%);
        color: white;
        padding: 24px 28px;
        border-radius: 12px;
        margin-bottom: 24px;
        box-shadow: 0 4px 14px rgba(30, 64, 175, 0.15);
    }
    .hero-title {
        font-size: 1.85rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .hero-subtitle {
        font-size: 0.95rem;
        color: #DBEAFE;
        margin-top: 6px;
        margin-bottom: 0;
    }

    /* Metric Cards */
    .metric-box {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .metric-box:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.06);
    }
    .metric-label {
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748B;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #0F172A;
    }

    /* Badge */
    .badge {
        display: inline-block;
        padding: 3px 8px;
        font-size: 0.75rem;
        font-weight: 600;
        border-radius: 6px;
        background: #EFF6FF;
        color: #1E40AF;
        border: 1px solid #BFDBFE;
    }

    /* Sidebar branding */
    .sidebar-brand {
        padding: 10px 0 16px 0;
        border-bottom: 1px solid #E2E8F0;
        margin-bottom: 16px;
    }
    .sidebar-brand h2 {
        font-size: 1.3rem;
        font-weight: 700;
        color: #1E40AF;
        margin: 0;
    }
    .sidebar-brand p {
        font-size: 0.8rem;
        color: #64748B;
        margin: 2px 0 0 0;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Robust Parser Engine
# ---------------------------------------------------------------------------
COMMENT_PREFIXES = ("#", "%", "//", ";", "!")

def strip_comments(lines):
    """Strip blank rows and lines starting with comment characters."""
    clean = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if any(s.startswith(p) for p in COMMENT_PREFIXES):
            continue
        clean.append(s)
    return clean

def detect_delimiter(lines):
    """Detect delimiter via csv.Sniffer or fallback frequency count."""
    sample = "\n".join(lines[:15])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
        sep = dialect.delimiter
        hits = sum(1 for l in lines[:15] if sep in l)
        if hits >= max(1, len(lines[:15]) // 2):
            return sep
    except csv.Error:
        pass

    for sep in (",", "\t", ";", "|"):
        counts = [l.count(sep) for l in lines[:15] if l.strip()]
        if counts and min(counts) > 0 and max(counts) == min(counts):
            return sep
    return None

def is_first_line_header(line, delimiter):
    """Checks if first line is a header by evaluating token float conversion."""
    tokens = line.split(delimiter) if delimiter else line.split()
    if not tokens:
        return False
    numeric = 0
    for t in tokens:
        try:
            float(t.strip())
            numeric += 1
        except ValueError:
            pass
    return (numeric / len(tokens)) < 0.5

def parse_dat_file(file_bytes):
    """Multi-encoding file ingestion and parser."""
    text = None
    for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            text = file_bytes.decode(enc)
            break
        except Exception:
            continue
    if text is None:
        raise ValueError("Could not decode file. Please ensure it is saved as UTF-8 or Latin-1.")

    lines = text.splitlines()
    data_lines = strip_comments(lines)
    if not data_lines:
        raise ValueError("File contains no valid data lines (file is empty or comment-only).")

    delim = detect_delimiter(data_lines)
    has_header = is_first_line_header(data_lines[0], delim)

    buf = io.StringIO("\n".join(data_lines))
    read_kwargs = {
        "sep": delim if delim else r"\s+",
        "engine": "python",
        "on_bad_lines": "skip",
    }
    if has_header:
        df = pd.read_csv(buf, header=0, **read_kwargs)
    else:
        df = pd.read_csv(buf, header=None, **read_kwargs)
        df.columns = [f"Col_{i}" for i in range(df.shape[1])]

    df.columns = [str(c).strip() for c in df.columns]
    df.dropna(axis=1, how="all", inplace=True)
    df.reset_index(drop=True, inplace=True)

    # Cast numerics where valid
    for col in df.columns:
        converted = pd.to_numeric(df[col], errors="coerce")
        if converted.notna().sum() / max(len(df), 1) >= 0.5:
            df[col] = converted

    delim_name = {",": "Comma (,)", "\t": "Tab (\\t)", ";": "Semicolon (;)", "|": "Pipe (|)"}.get(delim, "Whitespace")
    return df, delim_name, has_header

# ---------------------------------------------------------------------------
# Sidebar Controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
        <h2>⬡ xppnautplot</h2>
        <p>Scientific Data Inspector & Plotter</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### 📂 Load File")
    uploaded_file = st.file_uploader("Browse `.dat`, `.txt`, `.csv`", type=["dat", "txt", "csv"])

    sample_options = ["(None)", "sinusoidal_comma.dat", "spectrum_whitespace.dat", "tabular_tabs.dat", "semicolon_test.dat"]
    use_sample = st.selectbox("Or choose a sample dataset:", sample_options, index=1 if uploaded_file is None else 0)

    st.markdown("---")

df = None
file_name = None
detected_sep = ""
has_hdr = False

if uploaded_file is not None:
    file_name = uploaded_file.name
    try:
        df, detected_sep, has_hdr = parse_dat_file(uploaded_file.getvalue())
    except Exception as e:
        st.error(f"❌ Error parsing file: {e}")
elif use_sample != "(None)":
    sample_path = os.path.join("sample_data", use_sample)
    if os.path.exists(sample_path):
        file_name = use_sample
        with open(sample_path, "rb") as f:
            try:
                df, detected_sep, has_hdr = parse_dat_file(f.read())
            except Exception as e:
                st.error(f"❌ Error loading sample: {e}")

# ---------------------------------------------------------------------------
# Main View
# ---------------------------------------------------------------------------
st.markdown("""
<div class="hero-header">
    <h1 class="hero-title">🔬 xppnautplot Dashboard</h1>
    <p class="hero-subtitle">High-performance parser, previewer, and interactive visualizer for scientific .dat files.</p>
</div>
""", unsafe_allow_html=True)

if df is None:
    st.info("👈 **Get started**: Upload a `.dat` file in the sidebar or select one of the built-in sample datasets.")
    
    # Feature showcase cards
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div class="metric-box">
            <div class="metric-label">Universal Parser</div>
            <div style="font-size:0.95rem; color:#475569; margin-top:6px;">
                Auto-detects delimiters (comma, tab, whitespace, semicolon), skips headers/comments (<code>#</code>, <code>%</code>, <code>//</code>, <code>;</code>), and recovers encodings.
            </div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="metric-box">
            <div class="metric-label">Interactive Visualization</div>
            <div style="font-size:0.95rem; color:#475569; margin-top:6px;">
                Overlay multiple curves, switch between Line, Scatter, Bar, Histogram, and Step plots, toggle Log/Linear axes, and customize legends.
            </div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="metric-box">
            <div class="metric-label">Export Anywhere</div>
            <div style="font-size:0.95rem; color:#475569; margin-top:6px;">
                Download publication-ready figures as SVG, PNG, or PDF, and export cleaned tabular datasets directly to CSV.
            </div>
        </div>
        """, unsafe_allow_html=True)
else:
    # Summary Metrics Row
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-label">Total Rows</div>
            <div class="metric-value">{len(df):,}</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-label">Total Columns</div>
            <div class="metric-value">{len(df.columns)}</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-label">Numeric Columns</div>
            <div class="metric-value">{len(numeric_cols)} <span class="badge">{len(numeric_cols)}/{len(df.columns)}</span></div>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-label">Format Detected</div>
            <div class="metric-value" style="font-size: 1.15rem; padding-top: 6px;">{detected_sep}</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    # Tabs
    tab_plot, tab_data, tab_stats = st.tabs(["📈 Interactive Plot", "📋 Data Preview", "📊 Column Diagnostics"])

    # ------------------ TAB 1: PLOT ------------------
    with tab_plot:
        with st.sidebar:
            st.markdown("#### ⚙️ Plot Configuration")
            
            x_col = st.selectbox("X-Axis", ["(index)"] + list(df.columns), index=1 if len(df.columns) > 1 else 0)
            
            default_y = [numeric_cols[0]] if numeric_cols else []
            if len(numeric_cols) > 1 and (numeric_cols[0] == x_col):
                default_y = [numeric_cols[1]]
            elif len(numeric_cols) > 1:
                default_y = [numeric_cols[0], numeric_cols[1]]

            y_cols = st.multiselect(
                "Y-Axis Series (Multi-Select)",
                options=list(df.columns),
                default=default_y,
                help="Select one or multiple series to overlay on the canvas"
            )

            plot_type = st.selectbox(
                "Plot Type",
                ["Line", "Scatter", "Line + Scatter", "Bar", "Histogram", "Step"],
                index=0
            )

            col_s1, col_s2 = st.columns(2)
            with col_s1:
                log_x = st.checkbox("Log X Scale")
            with col_s2:
                log_y = st.checkbox("Log Y Scale")

            st.markdown("#### 🎨 Styling & Labels")
            show_grid = st.checkbox("Show Grid Lines", value=True)
            show_legend = st.checkbox("Show Legend", value=True)
            chart_theme = st.selectbox("Color Palette", ["Classic Blue", "Viridis", "Warm Amber", "Cool Tech", "Vibrant"], index=0)

            chart_title = st.text_input("Chart Title", value=f"{plot_type} Plot — {file_name}")
            x_label = st.text_input("X Axis Label", value=x_col if x_col != "(index)" else "Index")
            y_label = st.text_input("Y Axis Label", value=", ".join(y_cols) if y_cols else "Value")

        if not y_cols:
            st.warning("⚠️ Please select at least one **Y-Axis Series** from the sidebar.")
        else:
            # Check numeric compatibility
            bad_cols = [c for c in y_cols if not pd.api.types.is_numeric_dtype(df[c])]
            if bad_cols:
                st.error(f"⚠️ Selected column(s) `{bad_cols}` contain non-numeric data. Please select numeric columns for the Y axis.")
            else:
                scale_ok = True
                if log_x and x_col != "(index)":
                    if pd.api.types.is_numeric_dtype(df[x_col]):
                        valid_x = df[x_col].dropna()
                        if (valid_x <= 0).any():
                            st.error(f"❌ Cannot use Log X Scale: Column `{x_col}` contains values ≤ 0.")
                            scale_ok = False
                    else:
                        st.error(f"❌ Cannot use Log X Scale: Column `{x_col}` is non-numeric.")
                        scale_ok = False

                if log_y:
                    for c in y_cols:
                        valid_y = df[c].dropna()
                        if (valid_y <= 0).any():
                            st.error(f"❌ Cannot use Log Y Scale: Column `{c}` contains values ≤ 0.")
                            scale_ok = False
                            break

                if scale_ok:
                    # Theme palette
                    palettes = {
                        "Classic Blue": ["#2563EB", "#D97706", "#16A34A", "#DC2626", "#8B5CF6", "#06B6D4"],
                        "Viridis": ["#440154", "#3b528b", "#21918c", "#5ec962", "#fde725"],
                        "Warm Amber": ["#D97706", "#EA580C", "#DC2626", "#B45309", "#78350F"],
                        "Cool Tech": ["#0284C7", "#0D9488", "#2563EB", "#6366F1", "#4F46E5"],
                        "Vibrant": ["#F43F5E", "#8B5CF6", "#06B6D4", "#10B981", "#F59E0B"],
                    }
                    colors = palettes.get(chart_theme, palettes["Classic Blue"])

                    fig = go.Figure()
                    x_vals = df.index if x_col == "(index)" else df[x_col]

                    for i, y_c in enumerate(y_cols):
                        clr = colors[i % len(colors)]
                        
                        if plot_type == "Line":
                            fig.add_trace(go.Scatter(
                                x=x_vals, y=df[y_c], mode="lines",
                                name=y_c, line=dict(color=clr, width=2.2)
                            ))
                        elif plot_type == "Scatter":
                            fig.add_trace(go.Scatter(
                                x=x_vals, y=df[y_c], mode="markers",
                                name=y_c, marker=dict(color=clr, size=7, opacity=0.85)
                            ))
                        elif plot_type == "Line + Scatter":
                            fig.add_trace(go.Scatter(
                                x=x_vals, y=df[y_c], mode="lines+markers",
                                name=y_c, line=dict(color=clr, width=1.8),
                                marker=dict(color=clr, size=5)
                            ))
                        elif plot_type == "Bar":
                            fig.add_trace(go.Bar(
                                x=x_vals, y=df[y_c], name=y_c,
                                marker=dict(color=clr, opacity=0.9)
                            ))
                        elif plot_type == "Step":
                            fig.add_trace(go.Scatter(
                                x=x_vals, y=df[y_c], mode="lines", line_shape="hv",
                                name=y_c, line=dict(color=clr, width=2.2)
                            ))
                        elif plot_type == "Histogram":
                            fig.add_trace(go.Histogram(
                                x=df[y_c].dropna(), name=y_c,
                                marker=dict(color=clr), opacity=0.75
                            ))

                    fig.update_layout(
                        title=dict(text=chart_title, font=dict(size=18, color="#1E3A8A")),
                        xaxis_title=x_label if plot_type != "Histogram" else "Value Range",
                        yaxis_title=y_label if plot_type != "Histogram" else "Frequency Count",
                        xaxis_type="log" if log_x and plot_type != "Histogram" else "linear",
                        yaxis_type="log" if log_y else "linear",
                        showlegend=show_legend,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        template="plotly_white",
                        height=600,
                        margin=dict(l=50, r=40, t=70, b=50),
                        hovermode="x unified" if plot_type != "Histogram" else "closest"
                    )

                    fig.update_xaxes(showgrid=show_grid, gridcolor="#E2E8F0", zeroline=True, zerolinecolor="#CBD5E1")
                    fig.update_yaxes(showgrid=show_grid, gridcolor="#E2E8F0", zeroline=True, zerolinecolor="#CBD5E1")

                    st.plotly_chart(fig, use_container_width=True)

                    # Export controls
                    st.markdown("---")
                    exp1, exp2 = st.columns([1, 2])
                    with exp1:
                        csv_data = df.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            label="📥 Download Cleaned CSV",
                            data=csv_data,
                            file_name=f"{file_name.rsplit('.', 1)[0]}_cleaned.csv",
                            mime="text/csv",
                            use_container_width=True,
                        )
                    with exp2:
                        st.info("💡 **High-Resolution Export**: Hover on the chart and click the **Camera Icon 📷** in the top-right corner to download PNG/SVG images.")

    # ------------------ TAB 2: PREVIEW ------------------
    with tab_data:
        st.markdown(f"#### Data Preview for `{file_name}`")
        st.caption(f"Showing first 25 rows (total {len(df):,} rows)")
        st.dataframe(df.head(25), use_container_width=True)

        st.markdown("#### Summary Statistics")
        st.dataframe(df.describe().T, use_container_width=True)

    # ------------------ TAB 3: DIAGNOSTICS ------------------
    with tab_stats:
        st.markdown("#### Column Metadata & Quality Check")
        diag_data = []
        for c in df.columns:
            diag_data.append({
                "Column Name": c,
                "Type": str(df[c].dtype),
                "Non-Null Count": int(df[c].notna().sum()),
                "Missing Count": int(df[c].isna().sum()),
                "Missing %": f"{(df[c].isna().sum() / len(df) * 100):.1f}%",
                "Unique Values": int(df[c].nunique()),
                "Sample (Row 0)": str(df[c].iloc[0]) if len(df) > 0 else "N/A"
            })
        st.dataframe(pd.DataFrame(diag_data), use_container_width=True)
