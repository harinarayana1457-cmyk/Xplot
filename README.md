# xppnautplot

A standalone Python desktop GUI for parsing, inspecting, and plotting any .dat file — no configuration needed.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue) ![CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-navy) ![Matplotlib](https://img.shields.io/badge/Plot-Matplotlib-orange) ![License](https://img.shields.io/badge/license-MIT-green)

---

## Features

| Feature | Detail |
|---|---|
| **Auto-detection** | Delimiter (, 	 whitespace ; \|), comment rows (# % // ;), headers |
| **Encoding** | UTF-8-sig → UTF-8 → Latin-1 fallback |
| **Data preview** | Scrollable table of first 18 rows + full metadata |
| **Plot types** | Line, Scatter, Bar, Histogram, Step |
| **Axes** | Linear / Log toggle for both X and Y |
| **Multi-series** | Select multiple Y columns — overlaid on one canvas |
| **Export** | PNG (300 DPI), SVG, PDF, CSV |
| **Error handling** | Inline banner for data errors, modal for file errors |

---

## Quick Start

`ash
# 1. Clone
git clone https://github.com/harinarayana1457-cmyk/Xplot.git
cd Xplot

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch
python app.py
`

Requires **Python 3.9+**.

---

## Usage

1. Click **Browse .dat File** and open any .dat file.
2. The **Data Preview** tab shows the first 18 rows and column metadata.
3. In the left panel, choose:
   - **X Axis** — column or (index)
   - **Y Axis** — one or more numeric columns (checkboxes)
   - **Plot Type** — Line / Scatter / Bar / Histogram / Step
   - **Scale** — Log X / Log Y toggles
   - **Display** — Grid, Legend, Title, Axis labels
4. Press **▶ Plot**.
5. Use the Matplotlib toolbar (zoom, pan, home) on the canvas.
6. Export via the bottom bar: **PNG**, **SVG**, **PDF**, or **CSV Data**.

---

## Sample Data

sample_data/ contains four .dat files that exercise every parser path:

| File | Delimiter | Header | Comments |
|---|---|---|---|
| sinusoidal_comma.dat | Comma | Yes | # |
| spectrum_whitespace.dat | Whitespace | No (auto Col_0/Col_1) | % |
| 	abular_tabs.dat | Tab | Yes | ## |
| semicolon_test.dat | Semicolon | Yes | ; |

---

## Architecture

`
app.py
├── DatParser        File ingestion, delimiter/header auto-detection
├── DataInspector    Metadata extraction and row preview
├── PlotEngine       Matplotlib figure factory (5 plot types)
├── ExportManager    PNG/SVG/PDF/CSV export
└── AppUI            CustomTkinter two-pane window
`

---

## Dependencies

`
customtkinter>=5.2.2
pandas>=2.0.0
numpy>=1.24.0
matplotlib>=3.7.0
CTkMessagebox>=2.5
`

---

## License

MIT
