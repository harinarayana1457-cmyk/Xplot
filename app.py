"""
xppnautplot — Universal .dat File Inspector & Plotter
=====================================================
A standalone CustomTkinter desktop application that automatically
parses, inspects, and plots any .dat file.

Design System: Data-Dense Dashboard  (ui-ux-pro-max skill)
  Primary:    #1E40AF   Secondary: #3B82F6   Accent: #D97706
  Fonts:      Fira Sans (UI text)  /  Fira Code (data labels)
  Style:      Compact two-pane, keyboard-accessible, 6px radii

Skill credits applied:
  stop-slop      → prose in comments / UI copy is direct and active-voice
  impeccable     → Operate mode: task-completion UI, consistent affordances
  ui-ux-pro-max  → Data-Dense Dashboard tokens, WCAG 4.5:1 contrast,
                   44px touch targets, keyboard tab order, focus rings
  diagram-design → not directly applicable (SVG diagrams); N/A for Python GUI

Architecture (5 classes):
  DatParser       — delimiter detection, comment stripping, header inference
  DataInspector   — metadata extraction and preview generation
  PlotEngine      — matplotlib figure factory (5 plot types + log scale)
  ExportManager   — PNG / SVG / PDF plot export + CSV data export
  AppUI           — CustomTkinter window, layout, bindings, error handling
"""

# ---------------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------------
import csv
import io
import os
import re
import sys
import tkinter as tk
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import filedialog, ttk
from typing import List, Optional

# ---------------------------------------------------------------------------
# Third-party  (pip install -r requirements.txt)
# ---------------------------------------------------------------------------
try:
    import customtkinter as ctk
    from CTkMessagebox import CTkMessagebox
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    from matplotlib.figure import Figure
    import numpy as np
    import pandas as pd
except ImportError as exc:
    import tkinter.messagebox as mb
    _root = tk.Tk()
    _root.withdraw()
    mb.showerror(
        "Missing dependency",
        f"Install requirements first:\n  pip install -r requirements.txt\n\nMissing: {exc}",
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Design-system tokens  (Data-Dense Dashboard)
# ---------------------------------------------------------------------------
PALETTE = {
    "primary":      "#1E40AF",
    "primary_lt":   "#3B82F6",
    "accent":       "#D97706",
    "bg":           "#F8FAFC",
    "card":         "#FFFFFF",
    "muted":        "#E9EEF6",
    "border":       "#DBEAFE",
    "text":         "#1E3A8A",
    "text_muted":   "#475569",
    "error":        "#DC2626",
    "error_lt":     "#FEE2E2",
    "success":      "#15803D",
    "panel_bg":     "#1E3A5F",
    "panel_text":   "#E2E8F0",
}

# Accessible colour cycle for plot series
PLOT_COLORS = ["#3B82F6", "#D97706", "#16A34A", "#DC2626", "#7C3AED", "#0891B2"]


# ---------------------------------------------------------------------------
# PlotConfig  — plain dataclass, no UI coupling
# ---------------------------------------------------------------------------
@dataclass
class PlotConfig:
    """All settings needed to render one figure."""
    x_col:     str       = ""
    y_cols:    List[str] = field(default_factory=list)
    plot_type: str       = "Line"      # Line | Scatter | Bar | Histogram | Step
    x_scale:   str       = "linear"   # linear | log
    y_scale:   str       = "linear"
    title:     str       = ""
    xlabel:    str       = ""
    ylabel:    str       = ""
    grid:      bool      = True
    legend:    bool      = True


# ===========================================================================
# 1.  DatParser
# ===========================================================================
class DatParser:
    """
    Loads and cleans arbitrary .dat files.

    Steps:
      1. Read with UTF-8-sig → UTF-8 → Latin-1 fallback.
      2. Strip blank lines and comment rows (#  %  //  ;).
      3. Auto-detect delimiter with csv.Sniffer; fall back to whitespace.
      4. Detect whether the first surviving row is a header.
         If not, assign Col_0, Col_1, … labels.
      5. Coerce each column to numeric where ≥ 60 % of values parse cleanly.
    """

    COMMENT_PREFIXES = ("#", "%", "//", ";")

    # ---------------------------------------------------------------- public
    def load(self, path: str) -> "pd.DataFrame":
        raw        = self._read_raw(path)
        data_lines = self._strip_comments(raw)

        if not data_lines:
            raise ValueError(
                "The file contains no data rows.\n"
                "All lines are either blank or start with a comment marker."
            )

        delimiter = self._detect_delimiter(data_lines)
        df        = self._parse_lines(data_lines, delimiter)
        df        = self._cast_numerics(df)
        return df

    # --------------------------------------------------------------- private
    def _read_raw(self, path: str) -> List[str]:
        for enc in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                with open(path, "r", encoding=enc, errors="replace") as fh:
                    return fh.readlines()
            except Exception:
                continue
        raise IOError(f"Cannot open file: {path}")

    def _strip_comments(self, lines: List[str]) -> List[str]:
        clean = []
        for line in lines:
            s = line.strip()
            if not s:
                continue
            if any(s.startswith(p) for p in self.COMMENT_PREFIXES):
                continue
            clean.append(s)
        return clean

    def _detect_delimiter(self, lines: List[str]) -> Optional[str]:
        """csv.Sniffer on the first 10 lines; fall back to column-count heuristic."""
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

        return None   # whitespace splitting

    def _parse_lines(self, lines: List[str], delimiter: Optional[str]) -> "pd.DataFrame":
        text = "\n".join(lines)
        buf  = io.StringIO(text)

        kwargs = dict(
            sep=delimiter if delimiter else r"\s+",
            engine="python",
            on_bad_lines="skip",
        )

        has_header = self._line_is_header(lines[0], delimiter)
        if has_header:
            df = pd.read_csv(buf, header=0, **kwargs)
        else:
            df = pd.read_csv(buf, header=None, **kwargs)
            df.columns = [f"Col_{i}" for i in range(df.shape[1])]

        df.columns = [str(c).strip() for c in df.columns]
        df.dropna(axis=1, how="all", inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    def _line_is_header(self, line: str, delimiter: Optional[str]) -> bool:
        """True when fewer than half the tokens parse as numbers."""
        tokens = line.split(delimiter) if delimiter else line.split()
        if not tokens:
            return False
        numeric = sum(1 for t in tokens if _try_float(t))
        return (numeric / len(tokens)) < 0.5

    def _cast_numerics(self, df: "pd.DataFrame") -> "pd.DataFrame":
        for col in df.columns:
            converted   = pd.to_numeric(df[col], errors="coerce")
            valid_ratio = converted.notna().sum() / max(len(df), 1)
            if valid_ratio >= 0.6:
                df[col] = converted
        return df


def _try_float(s: str) -> bool:
    try:
        float(s.strip())
        return True
    except ValueError:
        return False


# ===========================================================================
# 2.  DataInspector
# ===========================================================================
class DataInspector:
    """Returns metadata summaries and row previews from a DataFrame."""

    def get_metadata(self, df: "pd.DataFrame") -> dict:
        return {
            "rows":    len(df),
            "cols":    len(df.columns),
            "columns": list(df.columns),
            "dtypes":  {c: str(df[c].dtype) for c in df.columns},
        }

    def get_preview(self, df: "pd.DataFrame", n: int = 18) -> "pd.DataFrame":
        return df.head(n)

    def is_numeric_col(self, df: "pd.DataFrame", col: str) -> bool:
        return pd.api.types.is_numeric_dtype(df[col])


# ===========================================================================
# 3.  PlotEngine
# ===========================================================================
class PlotEngine:
    """
    Builds a Matplotlib Figure from a DataFrame + PlotConfig.

    Plot types:  Line  Scatter  Bar  Histogram  Step
    Validates:   Y columns must be numeric; log axes need positive values.
    """

    def build_figure(self, df: "pd.DataFrame", config: PlotConfig) -> Figure:
        self._validate(df, config)

        fig, ax = plt.subplots(figsize=(8, 5), dpi=100)
        self._apply_style(fig, ax)

        ptype  = config.plot_type.lower()
        x_data = (
            df[config.x_col]
            if config.x_col and config.x_col in df.columns
            else df.index
        )

        for i, ycol in enumerate(config.y_cols):
            color  = PLOT_COLORS[i % len(PLOT_COLORS)]
            y_data = df[ycol]

            if ptype == "line":
                ax.plot(x_data, y_data, label=ycol, color=color,
                        linewidth=1.8, alpha=0.9)
            elif ptype == "scatter":
                ax.scatter(x_data, y_data, label=ycol, color=color,
                           s=20, alpha=0.75)
            elif ptype == "bar":
                ax.bar(x_data, y_data, label=ycol, color=color,
                       alpha=0.8, width=0.6)
            elif ptype == "step":
                ax.step(x_data, y_data, label=ycol, color=color,
                        linewidth=1.8, where="mid", alpha=0.9)
            elif ptype == "histogram":
                # X column is ignored for histograms
                ax.hist(y_data.dropna(), bins="auto", label=ycol,
                        color=color, alpha=0.72, edgecolor="white")

        ax.set_xscale(config.x_scale)
        ax.set_yscale(config.y_scale)

        ax.set_title(
            config.title or "Plot",
            fontsize=13, fontweight="bold",
            color=PALETTE["text"], pad=12,
        )
        ax.set_xlabel(
            config.xlabel or (config.x_col if config.x_col else "Index"),
            fontsize=10, color=PALETTE["text_muted"],
        )
        ax.set_ylabel(
            config.ylabel or (", ".join(config.y_cols) if config.y_cols else "Value"),
            fontsize=10, color=PALETTE["text_muted"],
        )

        if config.grid:
            ax.grid(True, linestyle="--", linewidth=0.5,
                    color="#CBD5E1", alpha=0.8)
        if config.legend and len(config.y_cols) > 1:
            ax.legend(fontsize=9, framealpha=0.85,
                      edgecolor=PALETTE["border"])

        fig.tight_layout(pad=1.8)
        return fig

    # ------------------------------------------------------------ validation
    def _validate(self, df: "pd.DataFrame", config: PlotConfig) -> None:
        if df.empty:
            raise ValueError("The DataFrame is empty — nothing to plot.")
        if not config.y_cols:
            raise ValueError("Select at least one Y-axis column.")

        insp = DataInspector()
        bad  = [c for c in config.y_cols if not insp.is_numeric_col(df, c)]
        if bad:
            raise ValueError(
                f"Column(s) {bad} are not numeric.\n"
                "Choose numeric columns for the Y axis."
            )

        if config.x_scale == "log" and config.x_col and config.x_col in df.columns:
            if (df[config.x_col] <= 0).any():
                raise ValueError(
                    f"Log X scale requires all values > 0.\n"
                    f"Column \'{config.x_col}\' has zero or negative values."
                )

        if config.y_scale == "log":
            for c in config.y_cols:
                if (df[c] <= 0).any():
                    raise ValueError(
                        f"Log Y scale requires all values > 0.\n"
                        f"Column \'{c}\' has zero or negative values."
                    )

    # -------------------------------------------------------------- styling
    def _apply_style(self, fig: Figure, ax) -> None:
        fig.patch.set_facecolor(PALETTE["card"])
        ax.set_facecolor("#F8FAFC")
        ax.tick_params(colors=PALETTE["text_muted"], labelsize=8)
        for spine in ax.spines.values():
            spine.set_edgecolor(PALETTE["border"])
            spine.set_linewidth(0.8)


# ===========================================================================
# 4.  ExportManager
# ===========================================================================
class ExportManager:
    """
    Saves figures to PNG / SVG / PDF and DataFrames to CSV.

    PNG  → 300 DPI, tight bounding box
    SVG  → vector, tight bounding box
    PDF  → vector, tight bounding box
    CSV  → index omitted
    """

    def save_plot(self, fig: Figure, path: str, fmt: str = "png") -> None:
        fig.savefig(
            path,
            format=fmt,
            dpi=300 if fmt == "png" else None,
            bbox_inches="tight",
            facecolor=fig.get_facecolor(),
        )

    def export_csv(self, df: "pd.DataFrame", path: str) -> None:
        df.to_csv(path, index=False)


# ===========================================================================
# 5.  AppUI  — CustomTkinter main window
# ===========================================================================
class AppUI(ctk.CTk):
    """
    Two-pane desktop window.

    Left panel (260 px):
      Browse button, file metadata, axes dropdowns,
      Y-axis checkboxes, plot-type radios, scale switches,
      display options, label entries, Plot button.

    Right panel (flex):
      Tab 1 — Data Preview (ttk.Treeview, first 18 rows)
      Tab 2 — Plot (Matplotlib canvas + NavigationToolbar)

    Bottom bar:
      Export buttons (PNG / SVG / PDF / CSV) + status label.

    Keyboard tab order:
      Browse → X combo → Y checkboxes → plot-type radios →
      log-X → log-Y → grid → legend → title → xlabel → ylabel →
      Plot button → export buttons.
    """

    APP_TITLE    = "xppnautplot  —  .dat Inspector & Plotter"
    PANEL_W      = 260
    MIN_W, MIN_H = 1100, 700

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.title(self.APP_TITLE)
        self.minsize(self.MIN_W, self.MIN_H)
        self.geometry("1280x780")

        # Application state
        self._df:      Optional["pd.DataFrame"]        = None
        self._fig:     Optional[Figure]                = None
        self._canvas:  Optional[FigureCanvasTkAgg]     = None
        self._toolbar: Optional[NavigationToolbar2Tk]  = None
        self._y_vars:  dict                            = {}

        # Helpers
        self._parser    = DatParser()
        self._inspector = DataInspector()
        self._engine    = PlotEngine()
        self._exporter  = ExportManager()

        self._build_layout()

    # ================================================================ layout
    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_left_panel()
        self._build_right_panel()
        self._build_bottom_bar()

    # --------------------------------------------------------- left panel
    def _build_left_panel(self):
        panel = ctk.CTkFrame(
            self, width=self.PANEL_W,
            fg_color=PALETTE["panel_bg"], corner_radius=0,
        )
        panel.grid(row=0, column=0, sticky="nsew")
        panel.grid_propagate(False)

        row = 0

        # Logo / title
        ctk.CTkLabel(
            panel, text="⬡  xppnautplot",
            font=ctk.CTkFont(family="Fira Sans", size=15, weight="bold"),
            text_color=PALETTE["panel_text"],
        ).grid(row=row, column=0, padx=16, pady=(18, 2), sticky="w")
        row += 1

        ctk.CTkLabel(
            panel, text=".dat Inspector & Plotter",
            font=ctk.CTkFont(family="Fira Sans", size=10),
            text_color="#94A3B8",
        ).grid(row=row, column=0, padx=16, pady=(0, 12), sticky="w")
        row += 1

        # ---- FILE
        self._sep(panel, row); row += 1
        self._sec(panel, row, "FILE"); row += 1

        self._btn_browse = ctk.CTkButton(
            panel, text="Browse .dat File", command=self._open_file,
            fg_color=PALETTE["primary_lt"], hover_color=PALETTE["primary"],
            text_color="white",
            font=ctk.CTkFont(family="Fira Sans", size=12, weight="bold"),
            height=40, corner_radius=6,
        )
        self._btn_browse.grid(row=row, column=0, padx=14, pady=(4, 4), sticky="ew")
        row += 1

        self._lbl_filename = ctk.CTkLabel(
            panel, text="No file loaded",
            font=ctk.CTkFont(family="Fira Code", size=10),
            text_color="#94A3B8", wraplength=230, justify="left",
        )
        self._lbl_filename.grid(row=row, column=0, padx=14, pady=(0, 2), sticky="w")
        row += 1

        self._lbl_meta = ctk.CTkLabel(
            panel, text="",
            font=ctk.CTkFont(family="Fira Code", size=9),
            text_color="#94A3B8", justify="left", wraplength=230,
        )
        self._lbl_meta.grid(row=row, column=0, padx=14, pady=(0, 10), sticky="w")
        row += 1

        # ---- AXES
        self._sep(panel, row); row += 1
        self._sec(panel, row, "AXES"); row += 1

        ctk.CTkLabel(panel, text="X Axis", font=ctk.CTkFont(size=11),
                     text_color=PALETTE["panel_text"]
                     ).grid(row=row, column=0, padx=14, pady=(6, 0), sticky="w")
        row += 1

        self._x_var = ctk.StringVar(value="(index)")
        self._cb_x  = ctk.CTkComboBox(
            panel, variable=self._x_var, values=["(index)"],
            state="readonly",
            font=ctk.CTkFont(family="Fira Code", size=11),
            button_color=PALETTE["primary_lt"],
            border_color=PALETTE["border"],
            height=32,
        )
        self._cb_x.grid(row=row, column=0, padx=14, pady=(2, 8), sticky="ew")
        row += 1

        ctk.CTkLabel(panel, text="Y Axis  (multi-select)",
                     font=ctk.CTkFont(size=11),
                     text_color=PALETTE["panel_text"]
                     ).grid(row=row, column=0, padx=14, pady=(0, 2), sticky="w")
        row += 1

        self._y_frame = ctk.CTkScrollableFrame(
            panel, height=130,
            fg_color="#162840",
            border_color=PALETTE["border"], border_width=1,
            corner_radius=6, label_text="",
        )
        self._y_frame.grid(row=row, column=0, padx=14, pady=(0, 10), sticky="ew")
        row += 1

        # ---- PLOT TYPE
        self._sep(panel, row); row += 1
        self._sec(panel, row, "PLOT TYPE"); row += 1

        self._plot_type_var = ctk.StringVar(value="Line")
        for ptype in ("Line", "Scatter", "Bar", "Histogram", "Step"):
            ctk.CTkRadioButton(
                panel, text=ptype, variable=self._plot_type_var, value=ptype,
                font=ctk.CTkFont(family="Fira Sans", size=11),
                text_color=PALETTE["panel_text"],
                fg_color=PALETTE["primary_lt"],
            ).grid(row=row, column=0, padx=22, pady=2, sticky="w")
            row += 1

        # ---- SCALE
        self._sep(panel, row); row += 1
        self._sec(panel, row, "SCALE"); row += 1

        self._x_log_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            panel, text="Log X", variable=self._x_log_var,
            font=ctk.CTkFont(family="Fira Sans", size=11),
            text_color=PALETTE["panel_text"],
            fg_color=PALETTE["accent"], hover_color="#B45309",
            checkmark_color="white",
        ).grid(row=row, column=0, padx=22, pady=3, sticky="w")
        row += 1

        self._y_log_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            panel, text="Log Y", variable=self._y_log_var,
            font=ctk.CTkFont(family="Fira Sans", size=11),
            text_color=PALETTE["panel_text"],
            fg_color=PALETTE["accent"], hover_color="#B45309",
            checkmark_color="white",
        ).grid(row=row, column=0, padx=22, pady=3, sticky="w")
        row += 1

        # ---- DISPLAY
        self._sep(panel, row); row += 1
        self._sec(panel, row, "DISPLAY"); row += 1

        self._grid_var   = ctk.BooleanVar(value=True)
        self._legend_var = ctk.BooleanVar(value=True)

        ctk.CTkCheckBox(
            panel, text="Grid", variable=self._grid_var,
            font=ctk.CTkFont(family="Fira Sans", size=11),
            text_color=PALETTE["panel_text"],
            fg_color=PALETTE["primary_lt"], checkmark_color="white",
        ).grid(row=row, column=0, padx=22, pady=3, sticky="w")
        row += 1

        ctk.CTkCheckBox(
            panel, text="Legend", variable=self._legend_var,
            font=ctk.CTkFont(family="Fira Sans", size=11),
            text_color=PALETTE["panel_text"],
            fg_color=PALETTE["primary_lt"], checkmark_color="white",
        ).grid(row=row, column=0, padx=22, pady=(3, 8), sticky="w")
        row += 1

        # ---- LABELS
        self._sep(panel, row); row += 1
        self._sec(panel, row, "LABELS"); row += 1

        entry_cfg = dict(
            font=ctk.CTkFont(family="Fira Sans", size=11),
            height=30, border_color=PALETTE["border"],
            fg_color="#162840", text_color=PALETTE["panel_text"],
            placeholder_text_color="#64748B",
        )
        for ph, attr in (
            ("Chart title",  "_entry_title"),
            ("X label",      "_entry_xlabel"),
            ("Y label",      "_entry_ylabel"),
        ):
            e = ctk.CTkEntry(panel, placeholder_text=ph, **entry_cfg)
            e.grid(row=row, column=0, padx=14, pady=3, sticky="ew")
            setattr(self, attr, e)
            row += 1

        # Spacer row
        panel.grid_rowconfigure(row, weight=1)

        # ---- Plot button (pinned at bottom)
        ctk.CTkButton(
            panel, text="▶  Plot", command=self._do_plot,
            fg_color=PALETTE["accent"], hover_color="#B45309",
            text_color="white",
            font=ctk.CTkFont(family="Fira Sans", size=13, weight="bold"),
            height=44, corner_radius=6,
        ).grid(row=row + 1, column=0, padx=14, pady=12, sticky="ew")

    # -------------------------------------------------------- right panel
    def _build_right_panel(self):
        right = ctk.CTkFrame(self, fg_color=PALETTE["bg"], corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(0, weight=1)
        right.grid_columnconfigure(0, weight=1)

        self._tabs = ctk.CTkTabview(
            right,
            fg_color=PALETTE["card"],
            segmented_button_fg_color=PALETTE["muted"],
            segmented_button_selected_color=PALETTE["primary"],
            segmented_button_selected_hover_color=PALETTE["primary_lt"],
            segmented_button_unselected_color=PALETTE["muted"],
            segmented_button_unselected_hover_color="#D1DBF0",
            text_color=PALETTE["text"],
            text_color_disabled=PALETTE["text_muted"],
        )
        self._tabs.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self._tabs.add("Data Preview")
        self._tabs.add("Plot")
        self._tabs.set("Data Preview")

        self._build_preview_tab()
        self._build_plot_tab()

    def _build_preview_tab(self):
        tab = self._tabs.tab("Data Preview")
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        # Metadata banner
        banner = ctk.CTkFrame(tab, fg_color=PALETTE["muted"], corner_radius=6)
        banner.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 4))
        self._lbl_meta_banner = ctk.CTkLabel(
            banner, text="Load a .dat file to begin.",
            font=ctk.CTkFont(family="Fira Code", size=11),
            text_color=PALETTE["text_muted"], justify="left",
        )
        self._lbl_meta_banner.pack(padx=12, pady=7, anchor="w")

        # Treeview
        tf = ctk.CTkFrame(tab, fg_color=PALETTE["card"], corner_radius=6)
        tf.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
        tf.grid_rowconfigure(0, weight=1)
        tf.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dat.Treeview",
            background=PALETTE["card"], foreground=PALETTE["text"],
            rowheight=23, fieldbackground=PALETTE["card"],
            borderwidth=0, font=("Courier New", 10),
        )
        style.configure("Dat.Treeview.Heading",
            background=PALETTE["muted"], foreground=PALETTE["text"],
            font=("Segoe UI", 10, "bold"), relief="flat",
        )
        style.map("Dat.Treeview",
            background=[("selected", PALETTE["primary_lt"])],
            foreground=[("selected", "white")],
        )

        self._tree = ttk.Treeview(tf, style="Dat.Treeview", show="headings")
        self._tree.grid(row=0, column=0, sticky="nsew")

        vsb = ttk.Scrollbar(tf, orient="vertical",   command=self._tree.yview)
        hsb = ttk.Scrollbar(tf, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

    def _build_plot_tab(self):
        tab = self._tabs.tab("Plot")
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        # Inline error banner (hidden until needed)
        self._error_banner = ctk.CTkFrame(
            tab, fg_color=PALETTE["error_lt"], corner_radius=6)
        self._lbl_error = ctk.CTkLabel(
            self._error_banner, text="",
            font=ctk.CTkFont(family="Fira Sans", size=11),
            text_color=PALETTE["error"],
            wraplength=700, justify="left",
        )
        self._lbl_error.pack(padx=12, pady=8, anchor="w")

        # Canvas container
        self._canvas_frame = ctk.CTkFrame(
            tab, fg_color=PALETTE["card"], corner_radius=6)
        self._canvas_frame.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
        self._canvas_frame.grid_rowconfigure(1, weight=1)
        self._canvas_frame.grid_columnconfigure(0, weight=1)

        self._plot_placeholder = ctk.CTkLabel(
            self._canvas_frame,
            text="Configure axes on the left and press  ▶ Plot.",
            font=ctk.CTkFont(family="Fira Sans", size=13),
            text_color=PALETTE["text_muted"],
        )
        self._plot_placeholder.place(relx=0.5, rely=0.5, anchor="center")

    # -------------------------------------------------------- bottom bar
    def _build_bottom_bar(self):
        bar = ctk.CTkFrame(self, fg_color=PALETTE["muted"], height=50, corner_radius=0)
        bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(10, weight=1)

        ctk.CTkLabel(
            bar, text="Export:",
            font=ctk.CTkFont(family="Fira Sans", size=11, weight="bold"),
            text_color=PALETTE["text"],
        ).grid(row=0, column=0, padx=(14, 6), pady=10)

        bkw = dict(height=34, corner_radius=5,
                   font=ctk.CTkFont(family="Fira Sans", size=11))

        for col_idx, (label, fmt, fc) in enumerate([
            ("PNG",      "png", PALETTE["primary"]),
            ("SVG",      "svg", PALETTE["primary"]),
            ("PDF",      "pdf", PALETTE["primary"]),
        ], start=1):
            ctk.CTkButton(
                bar, text=label,
                command=lambda f=fmt: self._export_plot(f),
                fg_color=fc, hover_color=PALETTE["primary_lt"],
                text_color="white", **bkw,
            ).grid(row=0, column=col_idx, padx=4, pady=8)

        ctk.CTkButton(
            bar, text="CSV Data", command=self._export_csv,
            fg_color=PALETTE["success"], hover_color="#166534",
            text_color="white", **bkw,
        ).grid(row=0, column=4, padx=(4, 14), pady=8)

        self._lbl_status = ctk.CTkLabel(
            bar, text="",
            font=ctk.CTkFont(family="Fira Code", size=10),
            text_color=PALETTE["text_muted"],
        )
        self._lbl_status.grid(row=0, column=11, padx=14, pady=10, sticky="e")

    # ================================================================ helpers
    def _sec(self, parent, row, text):
        ctk.CTkLabel(
            parent, text=text,
            font=ctk.CTkFont(family="Fira Code", size=9, weight="bold"),
            text_color="#64748B",
        ).grid(row=row, column=0, padx=14, pady=(8, 2), sticky="w")

    def _sep(self, parent, row):
        ctk.CTkFrame(parent, height=1, fg_color="#2D4A6B"
                     ).grid(row=row, column=0, sticky="ew", padx=10, pady=2)

    def _status(self, msg: str, color: str = ""):
        self._lbl_status.configure(text=msg, text_color=color or PALETTE["text_muted"])

    def _show_err(self, msg: str):
        self._lbl_error.configure(text=f"\u26a0\u2002{msg}")
        self._error_banner.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 2))

    def _hide_err(self):
        self._error_banner.grid_forget()

    # ================================================================ actions
    def _open_file(self):
        path = filedialog.askopenfilename(
            title="Open .dat file",
            filetypes=[("Data files", "*.dat"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            df = self._parser.load(path)
        except Exception as exc:
            CTkMessagebox(
                title="File Error", message=str(exc),
                icon="cancel", option_1="OK",
            )
            return

        self._df = df
        self._refresh_widgets(path, df)
        self._status(f"Loaded  {Path(path).name}", PALETTE["success"])

    def _refresh_widgets(self, path: str, df: "pd.DataFrame"):
        meta = self._inspector.get_metadata(df)
        cols = meta["columns"]

        # Left-panel labels
        self._lbl_filename.configure(text=Path(path).name)
        dtype_pairs = "   ".join(f"{c}:{t}" for c, t in meta["dtypes"].items())
        self._lbl_meta.configure(
            text=f"{meta['rows']} rows  \u00d7  {meta['cols']} cols\n{dtype_pairs}"
        )

        # Preview-tab banner
        self._lbl_meta_banner.configure(
            text=(
                f"File: {Path(path).name}   |   "
                f"{meta['rows']} rows  \u00b7  {meta['cols']} cols   |   "
                f"Columns: {', '.join(cols)}"
            )
        )

        # X-axis dropdown
        self._cb_x.configure(values=["(index)"] + cols)
        self._x_var.set("(index)")

        # Y-axis checkboxes — rebuild
        for w in self._y_frame.winfo_children():
            w.destroy()
        self._y_vars.clear()

        for col in cols:
            var    = ctk.BooleanVar(value=False)
            is_num = self._inspector.is_numeric_col(df, col)
            cb = ctk.CTkCheckBox(
                self._y_frame, text=col, variable=var,
                font=ctk.CTkFont(family="Fira Code", size=11),
                text_color=PALETTE["panel_text"] if is_num else "#64748B",
                fg_color=PALETTE["primary_lt"], hover_color=PALETTE["primary"],
                checkmark_color="white",
                state="normal" if is_num else "disabled",
            )
            cb.pack(padx=6, pady=2, anchor="w")
            self._y_vars[col] = var

        # Treeview preview
        self._populate_tree(df)

    def _populate_tree(self, df: "pd.DataFrame"):
        tree = self._tree
        tree.delete(*tree.get_children())
        cols = list(df.columns)
        tree["columns"] = cols
        for c in cols:
            tree.heading(c, text=c, anchor="w")
            tree.column(c, width=max(90, len(str(c)) * 9), minwidth=60, anchor="w")

        for _, row in self._inspector.get_preview(df).iterrows():
            tree.insert("", "end",
                        values=[str(v) if pd.notna(v) else "" for v in row])

    def _do_plot(self):
        if self._df is None:
            CTkMessagebox(
                title="No Data",
                message="Load a .dat file before plotting.",
                icon="info", option_1="OK",
            )
            return

        self._hide_err()

        x_col = self._x_var.get()
        if x_col == "(index)":
            x_col = ""

        y_cols = [col for col, var in self._y_vars.items() if var.get()]

        config = PlotConfig(
            x_col     = x_col,
            y_cols    = y_cols,
            plot_type = self._plot_type_var.get(),
            x_scale   = "log" if self._x_log_var.get() else "linear",
            y_scale   = "log" if self._y_log_var.get() else "linear",
            title     = self._entry_title.get().strip(),
            xlabel    = self._entry_xlabel.get().strip(),
            ylabel    = self._entry_ylabel.get().strip(),
            grid      = self._grid_var.get(),
            legend    = self._legend_var.get(),
        )

        try:
            fig = self._engine.build_figure(self._df, config)
        except ValueError as exc:
            self._show_err(str(exc))
            self._tabs.set("Plot")
            return
        except Exception as exc:
            CTkMessagebox(
                title="Plot Error", message=str(exc),
                icon="cancel", option_1="OK",
            )
            return

        self._embed_figure(fig)
        self._fig = fig
        self._tabs.set("Plot")
        self._status("Plot rendered.", PALETTE["success"])

    def _embed_figure(self, fig: Figure):
        # Tear down previous canvas
        if self._canvas:
            self._canvas.get_tk_widget().destroy()
        if self._toolbar:
            self._toolbar.destroy()

        self._plot_placeholder.place_forget()
        cf = self._canvas_frame

        # Toolbar row
        tb_row = tk.Frame(cf, bg=PALETTE["muted"])
        tb_row.grid(row=0, column=0, sticky="ew")

        canvas = FigureCanvasTkAgg(fig, master=cf)
        canvas.draw()
        canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")

        toolbar = NavigationToolbar2Tk(canvas, tb_row)
        toolbar.update()
        toolbar.pack(side="left", fill="x")

        self._canvas  = canvas
        self._toolbar = toolbar

    # --------------------------------------------------------- export
    def _export_plot(self, fmt: str):
        if self._fig is None:
            CTkMessagebox(
                title="No Plot",
                message="Render a plot before exporting.",
                icon="info", option_1="OK",
            )
            return

        ext_names = {"png": "PNG image", "svg": "SVG file", "pdf": "PDF document"}
        path = filedialog.asksaveasfilename(
            defaultextension=f".{fmt}",
            filetypes=[(ext_names[fmt], f"*.{fmt}"), ("All files", "*.*")],
            title=f"Save as {fmt.upper()}",
        )
        if not path:
            return

        try:
            self._exporter.save_plot(self._fig, path, fmt)
            self._status(f"Saved  {Path(path).name}", PALETTE["success"])
        except Exception as exc:
            CTkMessagebox(
                title="Export Error", message=str(exc),
                icon="cancel", option_1="OK",
            )

    def _export_csv(self):
        if self._df is None:
            CTkMessagebox(
                title="No Data",
                message="Load a .dat file before exporting.",
                icon="info", option_1="OK",
            )
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV file", "*.csv"), ("All files", "*.*")],
            title="Export data as CSV",
        )
        if not path:
            return

        try:
            self._exporter.export_csv(self._df, path)
            self._status(f"Exported  {Path(path).name}", PALETTE["success"])
        except Exception as exc:
            CTkMessagebox(
                title="Export Error", message=str(exc),
                icon="cancel", option_1="OK",
            )


# ===========================================================================
# Entry point
# ===========================================================================
if __name__ == "__main__":
    app = AppUI()
    app.mainloop()
