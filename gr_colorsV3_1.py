#!/usr/bin/env python3
"""
gr_colorsV3_1.py

Generate a golden-ratio HSV color palette with a Tkinter GUI preview.
Inputs: number of colors, starting hue, saturation, value, tint, and preview/SVG columns.
Outputs: selectable color-index text in the GUI; optional CSV and SVG exports.

Example:
    python gr_colorsV3_1.py
    python gr_colorsV3_1.py --cli --number 16 --saturation 0.67 --value 0.90 --tint 1.0
    python gr_colorsV3_1.py --cli --number 16 --columns 4 --svg-output palette.svg
"""

import argparse
import colorsys
import csv
import html
import math
import os
import sys
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk

GOLDEN_RATIO_CONJUGATE = 0.618033988749895
DEFAULT_NUMBER = 16
DEFAULT_SATURATION = 0.67
DEFAULT_VALUE = 0.90
DEFAULT_TINT = 1.00
DEFAULT_START_HUE = 0.0
DEFAULT_PREVIEW_COLUMNS = 4

TEXT_COLUMNS = ["index", "hue", "saturation", "value", "tint_T", "hex", "rgb", "base_hex", "base_rgb"]
ICON_RELATIVE_PATH = os.path.join("assets", "gr_colors_icon.png")


def clamp_float(value, min_value=0.0, max_value=1.0):
    """Return value clipped into [min_value, max_value]."""
    return max(min_value, min(max_value, float(value)))


def validate_columns(columns):
    """Validate and return a positive preview/SVG column count."""
    columns = int(columns)
    if columns < 1:
        raise ValueError("Preview/SVG columns must be >= 1.")
    return columns


def hsv_to_rgb255(hue, saturation, value):
    """Convert HSV values in [0, 1] to integer RGB values in [0, 255]."""
    hue = hue % 1.0
    saturation = clamp_float(saturation)
    value = clamp_float(value)
    r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
    return int(round(r * 255)), int(round(g * 255)), int(round(b * 255))


def apply_tint(rgb, tint):
    """
    Mix an RGB color with white using the requested T convention.

    tint / T = 1.0 keeps the original color.
    tint / T = 0.0 gives pure white.
    """
    tint = clamp_float(tint)
    r, g, b = rgb
    return (
        int(round(tint * r + (1.0 - tint) * 255)),
        int(round(tint * g + (1.0 - tint) * 255)),
        int(round(tint * b + (1.0 - tint) * 255)),
    )


def rgb_to_hex(rgb):
    """Convert an RGB tuple to #RRGGBB."""
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def readable_text_color(rgb):
    """Choose black or white text for readable labels on the color swatch."""
    r, g, b = rgb
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#000000" if luminance >= 150 else "#ffffff"


def resource_path(relative_path):
    """Return a resource path that also works in PyInstaller bundles."""
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def set_window_icon(root):
    """Set the Tk window icon when the optional icon asset is available."""
    icon_path = resource_path(ICON_RELATIVE_PATH)
    if not os.path.exists(icon_path):
        return
    try:
        icon = tk.PhotoImage(file=icon_path)
    except tk.TclError:
        return
    root.iconphoto(True, icon)
    root._gr_colors_icon = icon


def generate_colors(
    number,
    saturation=DEFAULT_SATURATION,
    value=DEFAULT_VALUE,
    tint=DEFAULT_TINT,
    start_hue=DEFAULT_START_HUE,
):
    """Generate color records using hue = start_hue + index * golden_ratio_conjugate."""
    number = int(number)
    if number < 0:
        raise ValueError("number must be >= 0")

    saturation = clamp_float(saturation)
    value = clamp_float(value)
    tint = clamp_float(tint)
    start_hue = float(start_hue) % 1.0

    rows = []
    for index in range(number):
        hue = (start_hue + index * GOLDEN_RATIO_CONJUGATE) % 1.0
        base_rgb = hsv_to_rgb255(hue, saturation, value)
        final_rgb = apply_tint(base_rgb, tint)
        rows.append({
            "index": index,
            "hue": hue,
            "saturation": saturation,
            "value": value,
            "tint": tint,
            "base_rgb": base_rgb,
            "base_hex": rgb_to_hex(base_rgb),
            "rgb": final_rgb,
            "hex": rgb_to_hex(final_rgb),
        })
    return rows


def row_to_text_values(row):
    """Return one color record as text values ordered by TEXT_COLUMNS."""
    r, g, b = row["rgb"]
    br, bg, bb = row["base_rgb"]
    return [
        str(row["index"]),
        "{:.6f}".format(row["hue"]),
        "{:.3f}".format(row["saturation"]),
        "{:.3f}".format(row["value"]),
        "{:.3f}".format(row["tint"]),
        row["hex"],
        "{},{},{}".format(r, g, b),
        row["base_hex"],
        "{},{},{}".format(br, bg, bb),
    ]


def aligned_text_lines(rows):
    """Format color rows as visually aligned, selectable text lines."""
    value_rows = [row_to_text_values(row) for row in rows]
    widths = []
    for col_index, header in enumerate(TEXT_COLUMNS):
        values = [values[col_index] for values in value_rows]
        widths.append(max(len(header), *(len(value) for value in values)) if values else len(header))

    def format_values(values):
        return "  ".join(value.ljust(widths[i]) for i, value in enumerate(values))

    lines = [format_values(TEXT_COLUMNS)]
    lines.extend(format_values(values) for values in value_rows)
    return lines


def rows_to_text(rows):
    """Format color rows as selectable aligned text."""
    return "\n".join(aligned_text_lines(rows)) + "\n"


def save_rows_csv(rows, output_path):
    """Save generated colors to CSV."""
    with open(output_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "index",
            "hue",
            "saturation",
            "value",
            "tint_T",
            "hex",
            "red",
            "green",
            "blue",
            "base_hex",
            "base_red",
            "base_green",
            "base_blue",
        ])
        for row in rows:
            r, g, b = row["rgb"]
            br, bg, bb = row["base_rgb"]
            writer.writerow([
                row["index"],
                "{:.9f}".format(row["hue"]),
                "{:.6f}".format(row["saturation"]),
                "{:.6f}".format(row["value"]),
                "{:.6f}".format(row["tint"]),
                row["hex"],
                r,
                g,
                b,
                row["base_hex"],
                br,
                bg,
                bb,
            ])


def svg_escape(text):
    """Escape text for safe insertion into SVG."""
    return html.escape(str(text), quote=True)


def save_rows_svg(rows, output_path, panel_columns=DEFAULT_PREVIEW_COLUMNS):
    """Save a shareable SVG palette using the same column count as the GUI preview."""
    panel_columns = validate_columns(panel_columns)

    swatch_w = 150
    swatch_h = 92
    gap = 14
    margin = 24
    header_h = 88
    display_rows = max(1, int(math.ceil(float(len(rows)) / float(panel_columns))) if rows else 1)
    width = margin * 2 + panel_columns * swatch_w + max(0, panel_columns - 1) * gap
    height = header_h + margin + display_rows * swatch_h + max(0, display_rows - 1) * gap

    if rows:
        saturation = rows[0]["saturation"]
        value = rows[0]["value"]
        tint = rows[0]["tint"]
        start_hue = rows[0]["hue"]
    else:
        saturation = DEFAULT_SATURATION
        value = DEFAULT_VALUE
        tint = DEFAULT_TINT
        start_hue = DEFAULT_START_HUE

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'.format(
            w=width, h=height
        ),
        '<rect x="0" y="0" width="100%" height="100%" fill="#ffffff"/>',
        '<text x="{x}" y="32" font-family="Arial, Helvetica, sans-serif" font-size="20" font-weight="700" fill="#111111">Golden-ratio HSV color palette</text>'.format(
            x=margin
        ),
        '<text x="{x}" y="56" font-family="Arial, Helvetica, sans-serif" font-size="12" fill="#333333">Hue formula: H_i = (H start + i * 0.618033988749895) mod 1; H = hue.</text>'.format(
            x=margin
        ),
        '<text x="{x}" y="75" font-family="Arial, Helvetica, sans-serif" font-size="12" fill="#333333">H start={h:.3f}, S={s:.3f}, V={v:.3f}, T={t:.3f}; grid uses {c} column(s) and {r} row(s).</text>'.format(
            x=margin, h=start_hue, s=saturation, v=value, t=tint, c=panel_columns, r=display_rows
        ),
    ]

    for i, row in enumerate(rows):
        col = i % panel_columns
        grid_row = i // panel_columns
        x = margin + col * (swatch_w + gap)
        y = header_h + grid_row * (swatch_h + gap)
        fill = row["hex"]
        text_color = readable_text_color(row["rgb"])
        r, g, b = row["rgb"]
        lines.append('<g id="color_{index}">'.format(index=row["index"]))
        lines.append(
            '<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" ry="10" fill="{fill}" stroke="#333333" stroke-width="1"/>'.format(
                x=x, y=y, w=swatch_w, h=swatch_h, fill=fill
            )
        )
        lines.append(
            '<text x="{x}" y="{y}" font-family="Arial, Helvetica, sans-serif" font-size="13" font-weight="700" fill="{c}">index {idx}</text>'.format(
                x=x + 10, y=y + 22, c=text_color, idx=row["index"]
            )
        )
        lines.append(
            '<text x="{x}" y="{y}" font-family="Arial, Helvetica, sans-serif" font-size="13" fill="{c}">{hex}</text>'.format(
                x=x + 10, y=y + 43, c=text_color, hex=svg_escape(fill)
            )
        )
        lines.append(
            '<text x="{x}" y="{y}" font-family="Arial, Helvetica, sans-serif" font-size="12" fill="{c}">RGB {r}, {g}, {b}</text>'.format(
                x=x + 10, y=y + 64, c=text_color, r=r, g=g, b=b
            )
        )
        lines.append(
            '<text x="{x}" y="{y}" font-family="Arial, Helvetica, sans-serif" font-size="11" fill="{c}">H={h:.3f} (hue)</text>'.format(
                x=x + 10, y=y + 83, c=text_color, h=row["hue"]
            )
        )
        lines.append('</g>')

    lines.append('</svg>')

    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


class GoldenRatioColorGUI:
    """Tkinter GUI for previewing, copying, and exporting golden-ratio HSV colors."""

    def __init__(self, root):
        self.root = root
        self.root.title("Golden-ratio HSV color generator")
        self.root.geometry("1020x720")
        self.root.minsize(880, 620)
        self.rows = []
        self._resize_after_id = None

        self.number_var = tk.IntVar(value=DEFAULT_NUMBER)
        self.start_hue_var = tk.DoubleVar(value=DEFAULT_START_HUE)
        self.saturation_var = tk.DoubleVar(value=DEFAULT_SATURATION)
        self.value_var = tk.DoubleVar(value=DEFAULT_VALUE)
        self.tint_var = tk.DoubleVar(value=DEFAULT_TINT)
        self.panel_columns_var = tk.IntVar(value=DEFAULT_PREVIEW_COLUMNS)
        self.status_var = tk.StringVar(value="")

        self.fixed_font = tkfont.nametofont("TkFixedFont").copy()
        self.fixed_font.configure(size=10)
        self.header_font = self.fixed_font.copy()
        self.header_font.configure(weight="bold")

        self._build_widgets()
        self.update_colors()

    def _build_widgets(self):
        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill=tk.BOTH, expand=True)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(0, weight=1)

        controls = ttk.LabelFrame(outer, text="Parameters", padding=10)
        controls.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        controls.columnconfigure(0, weight=1)

        ttk.Label(controls, text="Number of colors").grid(row=0, column=0, sticky="w")
        number_spin = ttk.Spinbox(
            controls,
            from_=0,
            to=1000,
            increment=1,
            textvariable=self.number_var,
            width=10,
            command=self.update_colors,
        )
        number_spin.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        number_spin.bind("<KeyRelease>", lambda event: self.update_colors())
        number_spin.bind("<FocusOut>", lambda event: self.update_colors())

        self._add_labeled_scale_entry(controls, 2, "Hue start (H)", self.start_hue_var)
        self._add_labeled_scale_entry(controls, 5, "Saturation (S)", self.saturation_var)
        self._add_labeled_scale_entry(controls, 8, "Value / brightness (V)", self.value_var)
        self._add_labeled_scale_entry(controls, 11, "Tint factor (T)", self.tint_var)

        grid_frame = ttk.LabelFrame(controls, text="Preview / SVG grid", padding=8)
        grid_frame.grid(row=14, column=0, sticky="ew", pady=(2, 10))
        grid_frame.columnconfigure(0, weight=1)

        ttk.Label(grid_frame, text="Columns").grid(row=0, column=0, sticky="w")
        columns_spin = ttk.Spinbox(
            grid_frame,
            from_=1,
            to=200,
            increment=1,
            textvariable=self.panel_columns_var,
            width=8,
            command=self.update_colors,
        )
        columns_spin.grid(row=1, column=0, sticky="ew")
        columns_spin.bind("<KeyRelease>", lambda event: self.update_colors())
        columns_spin.bind("<FocusOut>", lambda event: self.update_colors())

        ttk.Label(
            controls,
            text="Tint convention: T=1 keeps the original HSV color; T=0 gives pure white.",
            wraplength=220,
            justify=tk.LEFT,
        ).grid(row=15, column=0, sticky="ew", pady=(0, 10))

        ttk.Button(controls, text="Reset defaults", command=self.reset_defaults).grid(row=16, column=0, sticky="ew", pady=(8, 4))
        ttk.Button(controls, text="Copy color table", command=self.copy_table).grid(row=17, column=0, sticky="ew", pady=4)
        ttk.Button(controls, text="Save CSV", command=self.save_csv_dialog).grid(row=18, column=0, sticky="ew", pady=4)
        ttk.Button(controls, text="Export SVG", command=self.save_svg_dialog).grid(row=19, column=0, sticky="ew", pady=4)

        formula = (
            "Hue formula:\n"
            "H_i = (H start + i * 0.618033988749895) mod 1\n"
            "H = hue.\n\n"
            "S controls color intensity, V controls brightness, and T mixes each color with white."
        )
        ttk.Label(controls, text=formula, wraplength=220, justify=tk.LEFT).grid(row=20, column=0, sticky="ew", pady=(14, 0))

        right = ttk.Frame(outer)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(0, weight=3)
        right.rowconfigure(1, weight=2)
        right.columnconfigure(0, weight=1)

        preview_frame = ttk.LabelFrame(right, text="Preview", padding=4)
        preview_frame.grid(row=0, column=0, sticky="nsew")
        preview_frame.rowconfigure(0, weight=1)
        preview_frame.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(preview_frame, background="#ffffff", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        y_scroll = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll = ttk.Scrollbar(preview_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        x_scroll.grid(row=1, column=0, sticky="ew")
        self.canvas.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        table_frame = ttk.LabelFrame(right, text="Selectable color-index text", padding=4)
        table_frame.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.text = tk.Text(table_frame, wrap="none", height=9, undo=False, font=self.fixed_font)
        self.text.grid(row=0, column=0, sticky="nsew")
        text_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.text.yview)
        text_y.grid(row=0, column=1, sticky="ns")
        text_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.text.xview)
        text_x.grid(row=1, column=0, sticky="ew")
        self.text.configure(yscrollcommand=text_y.set, xscrollcommand=text_x.set)

        status = ttk.Label(outer, textvariable=self.status_var, anchor="w")
        status.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))

    def _add_labeled_scale_entry(self, parent, start_row, label, variable):
        ttk.Label(parent, text=label).grid(row=start_row, column=0, sticky="w")
        scale = ttk.Scale(
            parent,
            from_=0.0,
            to=1.0,
            variable=variable,
            orient=tk.HORIZONTAL,
            command=lambda value: self.update_colors(),
        )
        scale.grid(row=start_row + 1, column=0, sticky="ew")
        entry = ttk.Entry(parent, textvariable=variable, width=10)
        entry.grid(row=start_row + 2, column=0, sticky="ew", pady=(0, 10))
        entry.bind("<KeyRelease>", lambda event: self.update_colors())
        entry.bind("<FocusOut>", lambda event: self.update_colors())

    def _on_canvas_resize(self, event):
        if self._resize_after_id is not None:
            self.root.after_cancel(self._resize_after_id)
        self._resize_after_id = self.root.after(120, self.draw_preview)

    def _read_parameters(self):
        try:
            number = int(self.number_var.get())
            start_hue = float(self.start_hue_var.get()) % 1.0
            saturation = clamp_float(float(self.saturation_var.get()))
            value = clamp_float(float(self.value_var.get()))
            tint = clamp_float(float(self.tint_var.get()))
            panel_columns = validate_columns(self.panel_columns_var.get())
        except (tk.TclError, ValueError):
            raise ValueError("Please enter valid numeric parameters.")
        if number < 0:
            raise ValueError("Number of colors must be >= 0.")
        return number, start_hue, saturation, value, tint, panel_columns

    def update_colors(self):
        try:
            number, start_hue, saturation, value, tint, panel_columns = self._read_parameters()
            self.rows = generate_colors(number, saturation, value, tint, start_hue)
            display_rows = max(1, int(math.ceil(float(number) / float(panel_columns))) if number else 1)
            self.status_var.set(
                "Generated {} colors; grid {} column(s) × {} row(s); H = hue, H start={:.3f}, S={:.3f}, V={:.3f}, T={:.3f}.".format(
                    number, panel_columns, display_rows, start_hue, saturation, value, tint
                )
            )
        except ValueError as exc:
            self.status_var.set(str(exc))
            return

        self.update_text()
        self.draw_preview()

    def update_text(self):
        self.text.configure(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)

        for tag_name in self.text.tag_names():
            if tag_name.startswith("color_line_") or tag_name == "header_line":
                self.text.tag_delete(tag_name)

        lines = aligned_text_lines(self.rows)
        self.text.tag_configure("header_line", foreground="#111111", font=self.header_font)
        self.text.insert(tk.END, lines[0] + "\n", "header_line")

        for row, line in zip(self.rows, lines[1:]):
            tag_name = "color_line_{}".format(row["index"])
            self.text.tag_configure(tag_name, foreground=row["hex"], font=self.fixed_font)
            self.text.insert(tk.END, line + "\n", tag_name)

        self.text.configure(state=tk.NORMAL)

    def draw_preview(self):
        self._resize_after_id = None
        self.canvas.delete("all")
        try:
            number, start_hue, saturation, value, tint, panel_columns = self._read_parameters()
        except ValueError:
            panel_columns = DEFAULT_PREVIEW_COLUMNS

        visible_width = max(360, self.canvas.winfo_width())
        visible_height = max(260, self.canvas.winfo_height())
        pad = 12
        tile_w = max(126, int((visible_width - pad * (panel_columns + 1)) / float(panel_columns)))
        tile_h = 82
        display_rows = max(1, int(math.ceil(float(len(self.rows)) / float(panel_columns))) if self.rows else 1)

        for idx, row in enumerate(self.rows):
            col = idx % panel_columns
            grid_row = idx // panel_columns
            x0 = pad + col * (tile_w + pad)
            y0 = pad + grid_row * (tile_h + pad)
            x1 = x0 + tile_w
            y1 = y0 + tile_h
            fill = row["hex"]
            text_color = readable_text_color(row["rgb"])
            r, g, b = row["rgb"]

            self.canvas.create_rectangle(x0, y0, x1, y1, fill=fill, outline="#444444")
            self.canvas.create_text(x0 + 8, y0 + 8, anchor="nw", fill=text_color, text="index {}".format(row["index"]))
            self.canvas.create_text(x0 + 8, y0 + 30, anchor="nw", fill=text_color, text=fill)
            self.canvas.create_text(x0 + 8, y0 + 50, anchor="nw", fill=text_color, text="{},{},{}".format(r, g, b))
            self.canvas.create_text(
                x0 + 8,
                y0 + 68,
                anchor="nw",
                fill=text_color,
                text="H={:.3f} hue".format(row["hue"]),
            )

        total_w = pad * (panel_columns + 1) + panel_columns * tile_w
        total_h = pad * (display_rows + 1) + display_rows * tile_h
        self.canvas.configure(scrollregion=(0, 0, max(total_w, visible_width), max(total_h, visible_height)))

    def reset_defaults(self):
        self.number_var.set(DEFAULT_NUMBER)
        self.start_hue_var.set(DEFAULT_START_HUE)
        self.saturation_var.set(DEFAULT_SATURATION)
        self.value_var.set(DEFAULT_VALUE)
        self.tint_var.set(DEFAULT_TINT)
        self.panel_columns_var.set(DEFAULT_PREVIEW_COLUMNS)
        self.update_colors()

    def copy_table(self):
        text = rows_to_text(self.rows)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status_var.set("Copied aligned color table to clipboard.")

    def save_csv_dialog(self):
        path = filedialog.asksaveasfilename(
            title="Save color table as CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            save_rows_csv(self.rows, path)
        except OSError as exc:
            messagebox.showerror("Save failed", str(exc))
            return
        self.status_var.set("Saved CSV: {}".format(path))

    def save_svg_dialog(self):
        path = filedialog.asksaveasfilename(
            title="Export palette as SVG",
            defaultextension=".svg",
            filetypes=[("SVG files", "*.svg"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            panel_columns = validate_columns(self.panel_columns_var.get())
            save_rows_svg(self.rows, path, panel_columns)
        except (OSError, ValueError, tk.TclError) as exc:
            messagebox.showerror("Export failed", str(exc))
            return
        self.status_var.set("Saved SVG: {}".format(path))


def print_rows(rows, output_path=None):
    """Print rows to stdout or save them to CSV."""
    if output_path:
        save_rows_csv(rows, output_path)
        return
    sys.stdout.write(rows_to_text(rows))


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Generate golden-ratio HSV colors with a Tkinter GUI preview or CLI output."
    )
    parser.add_argument("--gui", action="store_true", help="Open the GUI. This is the default unless --cli is used.")
    parser.add_argument("--cli", action="store_true", help="Print or save the color table without opening the GUI.")
    parser.add_argument("-n", "--number", type=int, default=DEFAULT_NUMBER, help="Number of colors to generate.")
    parser.add_argument("--start-hue", type=float, default=DEFAULT_START_HUE, help="Starting hue / H start in [0, 1].")
    parser.add_argument("-s", "--saturation", type=float, default=DEFAULT_SATURATION, help="HSV saturation in [0, 1].")
    parser.add_argument("--value", type=float, default=DEFAULT_VALUE, help="HSV value/brightness in [0, 1].")
    parser.add_argument(
        "--tint",
        type=float,
        default=DEFAULT_TINT,
        help="Tint factor T in [0, 1]; T=1 keeps the original color and T=0 gives white.",
    )
    parser.add_argument(
        "--columns",
        "--preview-columns",
        dest="preview_columns",
        type=int,
        default=DEFAULT_PREVIEW_COLUMNS,
        help="Number of columns in the GUI preview and SVG export.",
    )
    parser.add_argument("-o", "--output", help="CSV output path for --cli mode.")
    parser.add_argument("--svg-output", help="SVG palette output path for --cli mode.")
    return parser


def run_gui():
    root = tk.Tk()
    set_window_icon(root)
    app = GoldenRatioColorGUI(root)
    root.mainloop()
    return app


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.cli:
        try:
            preview_columns = validate_columns(args.preview_columns)
            rows = generate_colors(args.number, args.saturation, args.value, args.tint, args.start_hue)
        except ValueError as exc:
            parser.error(str(exc))
        if args.svg_output:
            save_rows_svg(rows, args.svg_output, preview_columns)
        print_rows(rows, args.output)
        return 0

    try:
        run_gui()
    except tk.TclError as exc:
        sys.stderr.write("Could not open the Tkinter GUI: {}\n".format(exc))
        sys.stderr.write("Use --cli to generate colors without a display.\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
