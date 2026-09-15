<div align="center">

# 📊 Xplot
### Universal Scientific `.dat` File Inspector & Multi-Axis Plotting Suite

A standalone, zero-configuration Python application engineered for high-throughput scientific data exploration, automated delimiter sniffing, metadata inspection, and publication-ready multi-series plotting. Available as both a **native desktop GUI** (CustomTkinter) and an **interactive local web app** (Streamlit & Plotly).

[![Python Version](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![CustomTkinter](https://img.shields.io/badge/Desktop%20UI-CustomTkinter%205.2%2B-1E40AF?style=for-the-badge&logo=python&logoColor=white)](https://github.com/TomSchimansky/CustomTkinter)
[![Streamlit](https://img.shields.io/badge/Web%20UI-Streamlit%201.28%2B-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Plotly](https://img.shields.io/badge/Interactive-Plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)](https://plotly.com)
[![Pandas](https://img.shields.io/badge/Data-Pandas%202.0%2B-150458?style=for-the-badge&logo=pandas&logoColor=white)](https://pandas.pydata.org)
[![NumPy](https://img.shields.io/badge/Compute-NumPy%201.24%2B-013243?style=for-the-badge&logo=numpy&logoColor=white)](https://numpy.org)
[![Matplotlib](https://img.shields.io/badge/Engine-Matplotlib%203.7%2B-11557C?style=for-the-badge&logo=python&logoColor=white)](https://matplotlib.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=for-the-badge)]()

<br>

<p align="center">
  <a href="#-key-features"><b>Explore Features</b></a> •
  <a href="#-system-architecture"><b>Architecture</b></a> •
  <a href="#-quick-start"><b>Quick Start</b></a> •
  <a href="#-modes-of-operation"><b>Modes of Operation</b></a> •
  <a href="#-supported-plot-types"><b>Plot Types</b></a> •
  <a href="#-sample-data-suite"><b>Sample Data</b></a> •
  <a href="#-project-structure"><b>Structure</b></a> •
  <a href="#-connect--author"><b>Connect</b></a>
</p>

</div>

---

## 📖 Overview

Scientific workflows routinely output experimental data, simulation trajectories, and instrument telemetry in arbitrary `.dat` files with varying delimiters, inconsistent comment headers, and unexpected encodings. Manually formatting these files before plotting slows down analysis.

**Xplot** eliminates this friction. Providing both a **native CustomTkinter desktop interface** and a **browser-based Streamlit web dashboard**, Xplot ingests any `.dat` file, automatically sniffs delimiters and encodings, previews the parsed schema, and provides an interactive canvas for exploratory multi-axis plotting and 300 DPI publication exports.

---

## ✨ Key Features

| Capability | Technical Implementation & User Benefit |
| :--- | :--- |
| **Zero-Config Delimiter Sniffing** | Uses Python `csv.Sniffer` coupled with heuristic frequency voting across commas (`,`), tabs (`\t`), semicolons (`;`), pipes (`\|`), and whitespace fallback (`\s+`). |
| **Resilient Encoding Cascade** | Automatically attempts `utf-8-sig` &rarr; `utf-8` &rarr; `latin-1` with graceful replacement handling, eliminating character encoding errors across legacy laboratory files. |
| **Intelligent Header Inference** | Calculates numeric token ratios per row to auto-detect header lines vs. numerical data. Unlabelled datasets automatically receive indexed `Col_0`, `Col_1`, etc. |
| **Robust Comment Stripping** | Automatically ignores leading comment rows marked by `#`, `%`, `//`, or `;`, isolating pure numerical matrices without pre-cleaning. |
| **Dual GUI Interfaces** | Run as a standalone native desktop application (`app.py` with CustomTkinter) or as a responsive local web dashboard (`streamlit_app.py` with Streamlit & Plotly). |
| **Live Metadata & Data Preview** | Embedded interactive table view displays the first rows of parsed records alongside total row count, column dimensions, and detected column dtypes. |
| **Multi-Series Overlay** | Dynamically generates selectors for every numeric column detected in the dataset, allowing arbitrary multi-series overlays on a single canvas. |
| **Dual-Axis Scale Switching** | Independent Linear / Log toggles for both X and Y axes with built-in validation preventing math domain errors on non-positive values. |
| **Publication-Ready Export** | Direct export pipeline supporting 300 DPI high-resolution PNGs, vector SVGs, vector PDFs, and normalized comma-separated CSVs. |
| **Accessible & Responsive UX** | Designed to WCAG 4.5:1 contrast standards with 44px touch targets, clean layouts, custom color cycles, and comprehensive keyboard tab indexing. |

---

## 🏛️ System Architecture

The following diagram illustrates Xplot's modular dataflow—from raw byte ingestion through parsing, schema inspection, interactive rendering, and high-resolution export across both runtime targets:

```mermaid
flowchart TD
    subgraph INGESTION ["📥 Ingestion & Preprocessing"]
        A["Arbitrary .dat File"] --> B["DatParser Engine"]
        B --> C["Encoding Fallback Cascade<br>(UTF-8-sig &rarr; UTF-8 &rarr; Latin-1)"]
        C --> D["Comment Stripper<br>(Prefixes: #, %, //, ;)"]
        D --> E["Delimiter Sniffer<br>(Comma, Tab, Whitespace, Semicolon, Pipe)"]
        E --> F["Header Inferrer & Column Auto-Labeller"]
        F --> G["Numeric Coercion (Threshold &ge; 60%)"]
    end

    subgraph RUNTIMES ["💻 Dual Frontend Runtimes"]
        G --> H1["Desktop Engine (app.py)<br>CustomTkinter 5.2 + ttk.Treeview"]
        G --> H2["Web Dashboard (streamlit_app.py)<br>Streamlit 1.28 + Plotly Graph Objects"]
    end

    subgraph RENDERING ["📈 Plotting & Visualization"]
        H1 --> I1["Matplotlib FigureCanvasTkAgg<br>(TkAgg + NavigationToolbar)"]
        H2 --> I2["Plotly Interactive Chart Engine<br>(Unified Hover, Pan & Dynamic Zoom)"]
        I1 --> J["5 Scientific Plot Types<br>(Line, Scatter, Bar, Step, Histogram)"]
        I2 --> J
    end

    subgraph EXPORT ["💾 Export Pipeline"]
        J --> K1["High-Res Publication PNG (300 DPI)"]
        J --> K2["Vector Graphic (SVG)"]
        J --> K3["Vector Document (PDF)"]
        J --> K4["Normalized Dataset (CSV)"]
    end
```

---

## 🚀 Quick Start

### Prerequisites
* **Python 3.9+** installed on your system.

### 1. Clone the Repository
```bash
git clone https://github.com/harinarayana1457-cmyk/Xplot.git
cd Xplot
```

### 2. Create and Activate a Virtual Environment
```bash
# On Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# On macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Choose Your Interface

#### Option A: Native Desktop GUI (Recommended for Offline Analysis)
```bash
python app.py
```

#### Option B: Streamlit Web Dashboard (Recommended for Browser Access)
```bash
streamlit run streamlit_app.py
```
*Access the dashboard at `http://localhost:8501` in your browser.*

---

## 🖥️ Modes of Operation

### 1. Desktop Mode (`app.py`)
A fast, lightweight CustomTkinter application featuring:
* Two-pane data-dense layout with persistent controls.
* Embedded `ttk.Treeview` for inspecting the first 18 records and column data types.
* Matplotlib figure canvas with complete navigation toolbar (zoom rectangle, pan, home, configure subplots).
* Quick-export action bar for one-click 300 DPI PNG, SVG, PDF, and CSV saving.

### 2. Browser Web Dashboard (`streamlit_app.py`)
A modern Streamlit web application providing:
* Sidebar file uploader supporting `.dat`, `.txt`, and `.csv`.
* Pre-loaded sample data selector for immediate one-click testing.
* Interactive Plotly charts with responsive hover inspect tooltips and crosshairs.
* In-browser cleaned CSV download button and high-res vector snapshot tools.

---

## 📊 Supported Plot Types

| Plot Archetype | Primary Use Case | Rendering Characteristics |
| :--- | :--- | :--- |
| **Line Plot** | Continuous time series & parameter sweeps | High-clarity $1.8\text{px}$ lines with $90\%$ alpha and distinct accessible color palette. |
| **Scatter Plot** | Discontinuous measurements, correlation, and cluster inspection | $20\text{pt}$ markers with $75\%$ alpha to expose overlapping point density. |
| **Bar Chart** | Discrete measurements, bin aggregates, and categorised tallies | $0.6$ bar width with balanced contrast borders. |
| **Step Plot** | Digital waveforms, state transitions, and stepwise integration | Exact midpoint step geometry (`where="mid"`) for discrete signal fidelity. |
| **Histogram** | Probability distributions, noise characterization, and spread | Automatic binning (`bins="auto"`) with clean white edge separation. |

---

## 🧪 Sample Data Suite

Xplot ships with sample datasets in `sample_data/` covering diverse scientific format combinations:

| Dataset | Delimiter | Header Present | Comment Marker | Description |
| :--- | :--- | :--- | :--- | :--- |
| `sinusoidal_comma.dat` | Comma (`,`) | Yes (`time,voltage,...`) | `#` | Multi-phase AC sinusoidal waveforms and instantaneous power |
| `spectrum_whitespace.dat` | Whitespace (`\s+`) | No (`Col_0`, `Col_1`) | `%` | Optical emission spectrum with auto-assigned column headers |
| `tabular_tabs.dat` | Tab (`\t`) | Yes | `##` | Kinetic reaction rate telemetry formatted in strict tab stops |
| `semicolon_test.dat` | Semicolon (`;`) | Yes | `;` | European-style semicolon delimited instrumentation logs |

---

## 📁 Project Structure

```
Xplot/
├── app.py                     # Native CustomTkinter desktop application (1,000+ LOC)
│   ├── DatParser              # Resilient file ingestion, encoding cascade & delimiter sniffer
│   ├── DataInspector          # Schema extraction, column types & preview table generator
│   ├── PlotEngine             # Matplotlib figure builder supporting 5 scientific archetypes
│   ├── ExportManager          # Multi-format exporter (300 DPI PNG, SVG, PDF, CSV)
│   └── AppUI                  # CustomTkinter reactive two-pane desktop interface
├── streamlit_app.py           # Browser-based Streamlit web dashboard with Plotly
├── requirements.txt           # Python dependencies (CustomTkinter, Streamlit, Plotly, Pandas, etc.)
├── sample_data/               # Test suites covering whitespace, commas, tabs & semicolons
│   ├── semicolon_test.dat
│   ├── sinusoidal_comma.dat
│   ├── spectrum_whitespace.dat
│   └── tabular_tabs.dat
└── README.md                  # Comprehensive technical documentation & architecture guide
```

---

## 📦 Dependencies

| Package | Minimum Version | Purpose |
| :--- | :--- | :--- |
| [`customtkinter`](https://customtkinter.tomschimansky.com/) | `5.2.2` | Modern, high-DPI desktop windowing and widgets |
| [`streamlit`](https://streamlit.io/) | `1.28.0` | Reactive browser-based web dashboard framework |
| [`plotly`](https://plotly.com/) | `5.17.0` | Interactive web charts with zoom, pan, and hover cards |
| [`pandas`](https://pandas.pydata.org/) | `2.0.0` | High-performance tabular data ingestion and manipulation |
| [`numpy`](https://numpy.org/) | `1.24.0` | Numerical array operations and mathematical primitives |
| [`matplotlib`](https://matplotlib.org/) | `3.7.0` | Publication-grade 2D visualization and canvas rendering |
| [`CTkMessagebox`](https://github.com/Akash-Ramghar/CTkMessagebox) | `2.5` | Native CustomTkinter modal dialogs and alert banners |

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.

---

## 🔗 Connect & Author

**Harinarayana Avvari**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Harinarayana%20Avvari-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/harinarayana-avvari-324209341/)
[![GitHub](https://img.shields.io/badge/GitHub-harinarayana1457--cmyk-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/harinarayana1457-cmyk)

<div align="center">
  <sub>Engineered with precision for scientific research and rapid data exploration.</sub>
</div>
