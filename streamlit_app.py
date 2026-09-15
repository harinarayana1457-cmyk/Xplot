"""
xppnautplot — Universal .dat File Inspector & Plotter (Streamlit Web App)
=========================================================================
Runs on localhost (default: http://localhost:8501)
Features:
  - File uploader supporting arbitrary .dat files
  - Auto-detection of delimiters, comment skipping, header inference
  - Data preview table + column metadata and types
  - Plot configuration (X-axis, Multi-Y overlay, Plot types, Log scales)
  - Interactive Plotly chart with zoom, pan, hover, home tools
  - Export to PNG, SVG, PDF, or clean CSV
"""

import io
import csv
import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="xppnautplot — .dat Inspector & Plotter",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1E40AF;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 0.95rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

COMMENT_PREFIXES = ("#", "%", "//", ";")

def strip_comments(lines):
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
    sample = "\n".join(lines[:10])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
        sep = dialect.delimiter
        hits = sum(1 for l in lines[:10] if sep in l)
        if hits >= max(1, len(lines[:10]) // 2):
            return sep
    except csv.Error:
        pass

    for sep in (",", "\t", ";", "|"):
        counts = [l.count(sep) for l in lines[:10] if l.strip()]
        if counts and min(counts) > 0 and max(counts) == min(counts):
            return sep
    return None

def is_first_line_header(line, delimiter):
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
    text = None
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = file_bytes.decode(enc)
            break
        except Exception:
            continue
    if text is None:
        raise ValueError("Could not decode file with UTF-8 or Latin-1 encodings.")

    lines = text.splitlines()
    data_lines = strip_comments(lines)
    if not data_lines:
        raise ValueError("File contains no data rows (empty or only comments).")

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

    for col in df.columns:
        converted = pd.to_numeric(df[col], errors="coerce")
        if converted.notna().sum() / max(len(df), 1) >= 0.6:
            df[col] = converted

    return df, delim or "whitespace", has_header

st.sidebar.markdown("### ⬡ xppnautplot")
st.sidebar.markdown("**Universal .dat Inspector & Plotter**")
st.sidebar.markdown("---")

uploaded_file = st.sidebar.file_uploader("Upload .dat File", type=["dat", "txt", "csv"])

use_sample = st.sidebar.selectbox(
    "Or load sample data:",
    ["(None)", "sinusoidal_comma.dat", "spectrum_whitespace.dat", "tabular_tabs.dat", "semicolon_test.dat"]
)

df = None
file_name = None

if uploaded_file is not None:
    file_name = uploaded_file.name
    try:
        df, detected_sep, has_hdr = parse_dat_file(uploaded_file.getvalue())
    except Exception as e:
        st.error(f"Error parsing uploaded file: {e}")
elif use_sample != "(None)":
    sample_path = os.path.join("sample_data", use_sample)
    if os.path.exists(sample_path):
        file_name = use_sample
        with open(sample_path, "rb") as f:
            df, detected_sep, has_hdr = parse_dat_file(f.read())

st.markdown('<div class="main-header">xppnautplot Web Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Inspect, analyze, and interactively plot scientific .dat files directly in your browser.</div>', unsafe_allow_html=True)

if df is None:
    st.info("👈 Upload a `.dat` file in the sidebar or pick a sample dataset to get started.")
else:
    c1, c2, c3, c4 = st.columns(4)
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    with c1:
        st.metric("Total Rows", f"{len(df):,}")
    with c2:
        st.metric("Total Columns", f"{len(df.columns)}")
    with c3:
        st.metric("Numeric Columns", f"{len(numeric_cols)}")
    with c4:
        st.metric("Delimiter", detected_sep)

    tabs = st.tabs(["📈 Interactive Plot", "📋 Data Preview & Inspection"])

    with tabs[0]:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### Plot Settings")

        x_col = st.sidebar.selectbox("X-Axis", ["(index)"] + list(df.columns), index=0)
        
        default_y = [numeric_cols[0]] if numeric_cols else []
        if len(numeric_cols) > 1:
            default_y = [numeric_cols[0], numeric_cols[1]]

        y_cols = st.sidebar.multiselect(
            "Y-Axis (Multi-select Overlay)",
            options=list(df.columns),
            default=default_y,
        )

        plot_type = st.sidebar.selectbox(
            "Plot Type",
            ["Line", "Scatter", "Bar", "Histogram", "Step"]
        )

        col_scale1, col_scale2 = st.sidebar.columns(2)
        with col_scale1:
            log_x = st.checkbox("Log X")
        with col_scale2:
            log_y = st.checkbox("Log Y")

        st.sidebar.markdown("### Appearance")
        show_grid = st.sidebar.checkbox("Show Grid", value=True)
        chart_title = st.sidebar.text_input("Chart Title", value=f"{plot_type} Plot — {file_name}")
        x_label = st.sidebar.text_input("X Label", value=x_col if x_col != "(index)" else "Index")
        y_label = st.sidebar.text_input("Y Label", value=", ".join(y_cols) if y_cols else "Value")

        if not y_cols:
            st.warning("⚠️ Please select at least one Y-axis column from the sidebar.")
        else:
            bad_cols = [c for c in y_cols if not pd.api.types.is_numeric_dtype(df[c])]
            if bad_cols:
                st.error(f"⚠️ Selected column(s) {bad_cols} are non-numeric. Please select numeric columns for the Y axis.")
            else:
                valid_scales = True
                if log_x and x_col != "(index)":
                    if (df[x_col] <= 0).any():
                        st.error(f"Cannot use Log X scale: Column '{x_col}' has zero or negative values.")
                        valid_scales = False
                if log_y:
                    for c in y_cols:
                        if (df[c] <= 0).any():
                            st.error(f"Cannot use Log Y scale: Column '{c}' has zero or negative values.")
                            valid_scales = False

                if valid_scales:
                    fig = go.Figure()
                    x_vals = df.index if x_col == "(index)" else df[x_col]
                    colors = ["#2563EB", "#D97706", "#16A34A", "#DC2626", "#9333EA", "#0891B2"]

                    for i, y_c in enumerate(y_cols):
                        clr = colors[i % len(colors)]
                        if plot_type == "Line":
                            fig.add_trace(go.Scatter(x=x_vals, y=df[y_c], mode="lines", name=y_c, line=dict(color=clr, width=2)))
                        elif plot_type == "Scatter":
                            fig.add_trace(go.Scatter(x=x_vals, y=df[y_c], mode="markers", name=y_c, marker=dict(color=clr, size=6)))
                        elif plot_type == "Bar":
                            fig.add_trace(go.Bar(x=x_vals, y=df[y_c], name=y_c, marker=dict(color=clr)))
                        elif plot_type == "Step":
                            fig.add_trace(go.Scatter(x=x_vals, y=df[y_c], mode="lines", line_shape="hv", name=y_c, line=dict(color=clr, width=2)))
                        elif plot_type == "Histogram":
                            fig.add_trace(go.Histogram(x=df[y_c], name=y_c, marker=dict(color=clr), opacity=0.75))

                    fig.update_layout(
                        title=chart_title,
                        xaxis_title=x_label if plot_type != "Histogram" else "Value",
                        yaxis_title=y_label if plot_type != "Histogram" else "Count",
                        xaxis_type="log" if log_x and plot_type != "Histogram" else "linear",
                        yaxis_type="log" if log_y else "linear",
                        showlegend=True,
                        template="plotly_white",
                        height=560,
                        margin=dict(l=40, r=40, t=50, b=40),
                        hovermode="x unified" if plot_type != "Histogram" else "closest"
                    )

                    fig.update_xaxes(showgrid=show_grid)
                    fig.update_yaxes(showgrid=show_grid)

                    st.plotly_chart(fig, use_container_width=True)

                    st.markdown("#### 📥 Export Tools")
                    exp_col1, exp_col2 = st.columns(2)
                    with exp_col1:
                        csv_data = df.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            label="Download Cleaned CSV",
                            data=csv_data,
                            file_name=f"{file_name.rsplit('.', 1)[0]}_cleaned.csv",
                            mime="text/csv",
                        )
                    with exp_col2:
                        st.caption("💡 For high-res PNG/SVG/PDF export: Hover over the plot and click the **Camera icon 📷** in the top-right toolbar.")

    with tabs[1]:
        st.markdown("### First 20 Rows Preview")
        st.dataframe(df.head(20), use_container_width=True)

        st.markdown("### Column Details & Data Types")
        type_df = pd.DataFrame({
            "Column Name": df.columns,
            "Detected Data Type": [str(df[c].dtype) for c in df.columns],
            "Non-Null Count": [int(df[c].notna().sum()) for c in df.columns],
            "Sample Value": [str(df[c].iloc[0]) if len(df) > 0 else "" for c in df.columns],
        })
        st.dataframe(type_df, use_container_width=True)
