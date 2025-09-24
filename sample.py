"""
Excel Table Viewer (improved)

Features included:
- Browse and load Excel files (sheet chooser)
- Sample-based column width auto-sizing
- Column click -> sort (toggles asc/desc)
- Pagination (Next / Prev, configurable page size)
- Search/filter across all columns
- Export visible page to PDF
- Double-click to copy a row; Ctrl+C to copy selected rows
- Proper dialog parenting and defensive error handling
- Status bar showing rows/cols and page info

Dependencies:
- pandas
- tkinter (standard library)
"""

import os
import math
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font as tkfont
import pandas as pd
import re
# ----------------- Config -----------------
PAGE_SIZE_OPTIONS = [50, 100, 200, 500]  # choices for page size
DEFAULT_PAGE_SIZE = 200

# --------------- Globals ------------------
root = tk.Tk()
root.title("Excel Table Viewer")
root.geometry("1100x650")

current_df = None         # full DataFrame loaded from file
filtered_df = None        # DataFrame after applying search filter
page_index = 0            # zero-based page index
page_size = DEFAULT_PAGE_SIZE
sort_states = {}          # column -> bool (True means descending next toggle)

# ----------------- Utility Functions -----------------

def _first_nonempty_row_index(path, sheet):
    """
    Heuristic: find the first row index that has > half columns non-null.
    Returns 0-based index suitable for pandas.read_excel(header=...).
    """
    # Read small chunk without headers to inspect first ~20 rows
    try:
        tmp = pd.read_excel(path, sheet_name=sheet, header=None, nrows=40)
    except Exception:
        return 0
    for idx in range(len(tmp)):
        row = tmp.iloc[idx]
        non_null_count = row.notna().sum()
        # tolerance: at least 30% of total columns non-empty OR at least 3 non-empty cells
        if non_null_count >= max(3, int(0.3 * tmp.shape[1])):
            return idx
    return 0

def _normalize_multiindex_columns(cols):
    """
    If pandas returned MultiIndex columns (multi-row header),
    collapse into single string 'part1 | part2' ignoring empty parts.
    """
    if hasattr(cols, "levels") and isinstance(cols, pd.MultiIndex):
        new_cols = []
        for col in cols:
            # col is tuple of header parts
            parts = [str(p).strip() for p in col if (p is not None and str(p).strip() != "")]
            txt = " | ".join(parts) if parts else "Unnamed"
            new_cols.append(txt)
        return new_cols
    else:
        # normal Index
        return [str(c) for c in cols]

def _make_unique_columns(cols):
    """
    Ensure column names are unique by appending suffixes where needed.
    """
    seen = {}
    new_cols = []
    for c in cols:
        base = str(c)
        if base == "" or re.match(r"Unnamed", base, flags=re.IGNORECASE):
            base = "Unnamed"
        if base not in seen:
            seen[base] = 0
            new_cols.append(base)
        else:
            seen[base] += 1
            new_cols.append(f"{base}__{seen[base]}")
    return new_cols

def _clean_loaded_df(df):
    """
    Clean up the DataFrame after read_excel:
    - Drop columns that are entirely NaN
    - Drop rows that are entirely NaN
    - Forward-fill to propagate merged cell values (common in Excel)
    - Strip whitespace from string cells
    - Remove duplicate empty columns
    """
    # Drop fully empty columns and rows
    df = df.dropna(axis=1, how="all")
    df = df.dropna(axis=0, how="all")

    # If empty after this, return as-is
    if df.shape[0] == 0 or df.shape[1] == 0:
        return df

    # Strip strings
    df = df.applymap(lambda v: v.strip() if isinstance(v, str) else v)

    # Forward-fill to emulate merged-cells behavior (both axis)
    df = df.ffill(axis=0).ffill(axis=1)

    # Reset index to ensure sequential integer index for Treeview
    df = df.reset_index(drop=True)
    return df

def set_busy(state=True):
    """Set cursor and disable main buttons briefly while loading."""
    cursor = "watch" if state else ""
    root.config(cursor=cursor)
    for w in (browse_btn, load_btn, export_btn, btn_prev, btn_next):
        try:
            w.config(state="disabled" if state else "normal")
        except Exception:
            pass
    root.update_idletasks()

def clear_tree():
    """Remove all rows and reset columns/headings in the Treeview."""
    # Delete all items
    for iid in tree.get_children():
        tree.delete(iid)
    # Clear column definitions
    tree["columns"] = ()
    # Remove heading text if any
    # (Treeview.heading requires a column name; guarded here)
    # Nothing else needed — headings will be reconfigured when we display new df.

def update_status():
    """Update status label with counts and page info."""
    global filtered_df, page_index, page_size
    if filtered_df is None:
        status_var.set("No data loaded.")
        return
    total_rows = len(filtered_df)
    total_cols = len(filtered_df.columns)
    if total_rows == 0:
        status_var.set(f"0 rows, {total_cols} columns.")
        return
    start = page_index * page_size + 1
    end = min((page_index + 1) * page_size, total_rows)
    status_var.set(f"Rows {start}-{end} of {total_rows} | Columns: {total_cols} | Page {page_index+1}/{math.ceil(total_rows/page_size)}")

def slice_current_page():
    """Return a slice (DataFrame) for the current page from filtered_df."""
    global filtered_df, page_index, page_size
    if filtered_df is None:
        return None
    start = page_index * page_size
    end = start + page_size
    return filtered_df.iloc[start:end]

# ----------------- File / Loading -----------------
def browse_file():
    path = filedialog.askopenfilename(
        parent=root,
        title="Select Excel file",
        filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")],
    )
    if path:
        entry_path.config(state="normal")
        entry_path.delete(0, tk.END)
        entry_path.insert(0, path)
        entry_path.config(state="readonly")
        # load sheet names so user can pick
        try:
            set_busy(True)
            sheets = pd.ExcelFile(path).sheet_names
            sheet_combo['values'] = sheets
            if sheets:
                sheet_combo.current(0)
            else:
                sheet_combo.set('')
        except Exception as e:
            messagebox.showerror("Error reading sheets", f"Could not read sheet names:\n{e}", parent=root)
            sheet_combo['values'] = []
            sheet_combo.set('')
        finally:
            set_busy(False)

def load_file():
    """Smart load: detect header row, collapse multi-row headers, clean merged cells."""
    global current_df, filtered_df, page_index, sort_states
    file_path = entry_path.get().strip()
    if not file_path:
        messagebox.showwarning("No file", "Please select a file first.", parent=root)
        return
    if not os.path.exists(file_path):
        messagebox.showerror("Not found", "Selected file does not exist.", parent=root)
        return

    sheet = sheet_combo.get().strip()
    if not sheet:
        messagebox.showwarning("No sheet", "Please select a sheet to load.", parent=root)
        return

    try:
        set_busy(True)
        # Heuristic: determine header row index (0-based)
        header_idx = _first_nonempty_row_index(file_path, sheet)
        # Try reading with header at header_idx; pandas will produce MultiIndex if multiple header rows
        df = pd.read_excel(file_path, sheet_name=sheet, header=header_idx)
        # Normalize columns (handle MultiIndex headers)
        cols = _normalize_multiindex_columns(df.columns)
        cols = _make_unique_columns(cols)
        df.columns = cols

        # If first actual data row still looks like header placeholders (many "Unnamed"), try header_idx+1
        unnamed_ratio = sum(1 for c in cols if re.match(r"Unnamed", str(c), flags=re.IGNORECASE)) / max(1, len(cols))
        if unnamed_ratio > 0.4 and header_idx + 1 < 10:
            # Try next row as header
            try:
                df2 = pd.read_excel(file_path, sheet_name=sheet, header=header_idx+1)
                cols2 = _normalize_multiindex_columns(df2.columns)
                cols2 = _make_unique_columns(cols2)
                df2.columns = cols2
                # If this produced fewer unnamed columns, use df2
                unnamed_ratio2 = sum(1 for c in cols2 if re.match(r"Unnamed", str(c), flags=re.IGNORECASE)) / max(1, len(cols2))
                if unnamed_ratio2 < unnamed_ratio:
                    df = df2
            except Exception:
                pass

        # Clean dataframe (drop empty cols/rows, forward fill merged cells)
        df = _clean_loaded_df(df)

        current_df = df
        filtered_df = current_df.copy()
        page_index = 0
        sort_states = {}
        display_current_page()
    except Exception as e:
        messagebox.showerror("Read error", f"Failed to read sheet:\n{e}", parent=root)
    finally:
        set_busy(False)

def display_dataframe_in_tree(df: pd.DataFrame):
    """
    Display DataFrame page in treeview. This version expects df to be a proper rectangular
    DataFrame with unique column names (as produced by the loader).
    """
    clear_tree()
    if df is None or df.empty:
        update_status()
        return

    # Ensure columns are strings and unique
    cols = [str(c) for c in df.columns]
    cols = _make_unique_columns(cols)
    tree["columns"] = cols
    tree["show"] = "headings"

    # Configure headings with sort command
    for col in cols:
        tree.heading(col, text=col, anchor="w", command=lambda _col=col: treeview_sort_column(_col))
        tree.column(col, width=120, anchor="w", minwidth=50, stretch=False)

    # Insert rows, flatten multi-line text but keep it readable
    df_display = df.fillna("")
    rows = df_display.to_numpy().tolist()
    for r in rows:
        # limit cell length to avoid huge single cells, but preserve content
        safe_vals = []
        for x in r:
            s = "" if pd.isna(x) else str(x)
            # replace newlines with space so Treeview doesn't visually cramp lines
            s = s.replace("\r", " ").replace("\n", " ")
            # optionally truncate very long strings to keep UI responsive
            if len(s) > 500:
                s = s[:497] + "..."
            safe_vals.append(s)
        tree.insert("", tk.END, values=safe_vals)

    # Auto-adjust column widths using header + a small sample
    try:
        tmp = tkfont.Font(font=("TkDefaultFont", 9))
        sample_rows = rows if len(rows) <= 200 else rows[:200]
        for i, col in enumerate(cols):
            # consider header and sample values
            sample_texts = [str(col)] + [str(r[i]) for r in sample_rows if len(r) > i]
            max_text = max(sample_texts, key=len) if sample_texts else str(col)
            new_w = min(max(100, tmp.measure(max_text) + 20), 500)
            tree.column(col, width=new_w)
    except Exception:
        pass

    if tree.get_children():
        tree.see(tree.get_children()[0])

    update_status()


def display_current_page():
    """Get slice for current page and render it."""
    page_df = slice_current_page()
    display_dataframe_in_tree(page_df)

# ----------------- Sorting / Filtering -----------------
def treeview_sort_column(col):
    """
    Sort the entire filtered_df by column `col` and redisplay first page.
    Sorting toggles between ascending/descending.
    """
    global filtered_df, sort_states, page_index
    if filtered_df is None or col not in filtered_df.columns:
        return

    # Toggle descending state
    descending = sort_states.get(col, False)
    try:
        # Try natural dtype sort first
        filtered_df.sort_values(by=col, ascending=not descending, inplace=True, kind="mergesort")
    except Exception:
        # Fallback: string-based sort
        filtered_df.sort_values(by=col, key=lambda s: s.astype(str), ascending=not descending, inplace=True, kind="mergesort")

    # Update toggle for next click
    sort_states[col] = not descending
    page_index = 0
    display_current_page()

def apply_filter(*_):
    """
    Apply substring filter from search_entry across all columns (case-insensitive).
    Reset pagination to first page.
    """
    global current_df, filtered_df, page_index
    if current_df is None:
        return
    q = search_var.get().strip()
    if q == "":
        filtered_df = current_df.copy()
    else:
        # Build mask across all columns (quick approach: convert row to string)
        # For performance on very large frames, consider limiting or vectorized checks per column
        mask = current_df.astype(str).apply(lambda row: row.str.contains(q, case=False, na=False)).any(axis=1)
        filtered_df = current_df.loc[mask].copy()
    page_index = 0
    display_current_page()

# ----------------- Pagination -----------------
def set_page_size(new_size):
    global page_size, page_index
    page_size = int(new_size)
    page_index = 0
    display_current_page()

def prev_page():
    global page_index
    if filtered_df is None:
        return
    if page_index > 0:
        page_index -= 1
        display_current_page()

def next_page():
    global page_index, page_size
    if filtered_df is None:
        return
    max_pages = math.ceil(len(filtered_df) / page_size)
    if page_index < max_pages - 1:
        page_index += 1
        display_current_page()

# ----------------- Clipboard / Copy -----------------
def on_row_double_click(event):
    """Copy the double-clicked row to clipboard (tab-separated)."""
    item = tree.identify_row(event.y)
    if not item:
        return
    vals = tree.item(item, "values")
    root.clipboard_clear()
    root.clipboard_append("\t".join(vals))
    messagebox.showinfo("Copied", "Row copied to clipboard (tab-separated).", parent=root)

def copy_selected_rows(event=None):
    """Copy all selected rows (could be multiple) as tab-separated lines."""
    sel = tree.selection()
    if not sel:
        return
    lines = []
    for iid in sel:
        vals = tree.item(iid, "values")
        lines.append("\t".join(vals))
    text = "\n".join(lines)
    root.clipboard_clear()
    root.clipboard_append(text)
    # small non-modal feedback: change status briefly
    status_var.set(f"{len(sel)} row(s) copied to clipboard.")
    root.after(1500, update_status)

# ----------------- Export -----------------
def export_visible_to_pdf():
    """Export the currently visible page to a PDF file (uses reportlab)."""
    page_df = slice_current_page()
    if page_df is None or page_df.empty:
        messagebox.showwarning("No data", "There is no visible data to export.", parent=root)
        return

    # Ask user for save path
    fpath = filedialog.asksaveasfilename(
        parent=root,
        defaultextension=".pdf",
        filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        title="Export visible rows to PDF"
    )
    if not fpath:
        return

    # Ensure reportlab is available
    try:
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
    except ImportError:
        messagebox.showerror(
            "Missing dependency",
            "reportlab is required to export PDF. Install it with:\n\npip install reportlab",
            parent=root
        )
        return

    try:
        # Convert dataframe to a list of lists (header + rows)
        data = [list(page_df.columns)]
        # Limit the length of each cell to avoid extremely long strings in PDF layout
        def _shorten(val, maxlen=200):
            s = "" if pd.isna(val) else str(val)
            return s if len(s) <= maxlen else s[:maxlen-3] + "..."

        for _, row in page_df.iterrows():
            data.append([_shorten(v) for v in row.tolist()])

        # Build PDF
        doc = SimpleDocTemplate(fpath, pagesize=landscape(A4), leftMargin=18, rightMargin=18, topMargin=18, bottomMargin=18)
        elements = []
        styles = getSampleStyleSheet()

        # Title
        elements.append(Paragraph("Exported Table (visible page)", styles["Title"]))
        elements.append(Spacer(1, 8))

        # Create table. If the table is wide, reportlab will split to next page automatically.
        table = Table(data, repeatRows=1)
        # Basic styling
        tbl_style = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d3d3d3")),  # header bg
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
        ])
        table.setStyle(tbl_style)

        elements.append(table)
        doc.build(elements)

        messagebox.showinfo("Exported", f"Visible rows exported to:\n{fpath}", parent=root)
    except Exception as e:
        messagebox.showerror("Export failed", f"Could not export PDF:\n{e}", parent=root)

# ----------------- UI Layout -----------------
# Top controls
top_frame = ttk.Frame(root)
top_frame.pack(fill="x", padx=10, pady=8)

entry_path = ttk.Entry(top_frame, width=70, state="readonly")
entry_path.pack(side="left", padx=(0,6), expand=True, fill="x")

browse_btn = ttk.Button(top_frame, text="Browse", width=12, command=browse_file)
browse_btn.pack(side="left", padx=(0,6))

load_btn = ttk.Button(top_frame, text="Load", width=12, command=load_file)
load_btn.pack(side="left", padx=(0,6))

# Sheet chooser
sheet_lbl = ttk.Label(top_frame, text="Sheet:")
sheet_lbl.pack(side="left", padx=(6,2))
sheet_combo = ttk.Combobox(top_frame, values=[], state="readonly", width=25)
sheet_combo.pack(side="left")

# Search box
search_lbl = ttk.Label(top_frame, text="Search:")
search_lbl.pack(side="left", padx=(12,2))
search_var = tk.StringVar()
search_entry = ttk.Entry(top_frame, textvariable=search_var, width=25)
search_entry.pack(side="left", padx=(0,6))
search_entry.bind("<Return>", apply_filter)
search_entry.bind("<KeyRelease>", lambda e: None)  # optional: live filtering (disabled by default)
# We keep apply on button click to avoid heavy filtering per keystroke.
search_btn = ttk.Button(top_frame, text="Apply", width=8, command=apply_filter)
search_btn.pack(side="left", padx=(0,6))

# Middle: treeview inside a frame with scrollbars
frame_table = ttk.Frame(root)
frame_table.pack(fill="both", expand=True, padx=10, pady=(0,6))

vsb = ttk.Scrollbar(frame_table, orient="vertical")
hsb = ttk.Scrollbar(frame_table, orient="horizontal")

tree = ttk.Treeview(frame_table, columns=(), show="headings",
                    yscrollcommand=vsb.set, xscrollcommand=hsb.set)
vsb.config(command=tree.yview)
hsb.config(command=tree.xview)

vsb.pack(side="right", fill="y")
hsb.pack(side="bottom", fill="x")
tree.pack(side="left", fill="both", expand=True)

# Bindings
tree.bind("<Double-1>", on_row_double_click)
root.bind_all("<Control-c>", copy_selected_rows)
root.bind_all("<Control-C>", copy_selected_rows)

# Bottom controls: pagination, export, page size
bottom_frame = ttk.Frame(root)
bottom_frame.pack(fill="x", padx=10, pady=(0,8))

btn_prev = ttk.Button(bottom_frame, text="◀ Prev", width=10, command=prev_page)
btn_prev.pack(side="left", padx=(0,6))
btn_next = ttk.Button(bottom_frame, text="Next ▶", width=10, command=next_page)
btn_next.pack(side="left", padx=(0,6))

page_size_lbl = ttk.Label(bottom_frame, text="Page size:")
page_size_lbl.pack(side="left", padx=(12,4))
page_size_var = tk.StringVar(value=str(DEFAULT_PAGE_SIZE))
page_size_combo = ttk.Combobox(bottom_frame, values=[str(x) for x in PAGE_SIZE_OPTIONS], state="readonly", width=6, textvariable=page_size_var)
page_size_combo.pack(side="left")
page_size_combo.bind("<<ComboboxSelected>>", lambda e: set_page_size(int(page_size_var.get())))

export_btn = ttk.Button(bottom_frame, text="Export visible PDF", width=16, command=export_visible_to_pdf)
export_btn.pack(side="right", padx=(6,0))

# status bar
status_var = tk.StringVar(value="No data loaded.")
status_bar = ttk.Label(root, textvariable=status_var, relief="sunken", anchor="w")
status_bar.pack(side="bottom", fill="x")

# initialize page_size combo selection
page_size_combo.set(str(DEFAULT_PAGE_SIZE))

# ----------------- Initialize -----------------
update_status()

# Start mainloop
root.mainloop()
