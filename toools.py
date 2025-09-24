import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import os

# ---------- Functions ----------
def browse_file():
    path = filedialog.askopenfilename(
        title="Select Excel file",
        filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
    )
    if path:
        entry_path.config(state="normal")
        entry_path.delete(0, tk.END)
        entry_path.insert(0, path)
        entry_path.config(state="readonly")
        # load sheet names so user can pick
        try:
            sheets = pd.ExcelFile(path).sheet_names
            sheet_combo['values'] = sheets
            sheet_combo.current(0)
        except Exception as e:
            messagebox.showerror("Error reading sheets", f"Could not read sheet names:\n{e}")
            sheet_combo['values'] = []
            sheet_combo.set('')

def load_file():
    file_path = entry_path.get().strip()
    if not file_path:
        messagebox.showwarning("No file", "Please select a file first.")
        return
    if not os.path.exists(file_path):
        messagebox.showerror("Not found", "Selected file does not exist.")
        return

    sheet = sheet_combo.get().strip()
    if not sheet:
        messagebox.showwarning("No sheet", "Please select a sheet to load.")
        return

    try:
        df = pd.read_excel(file_path, sheet_name=sheet)
    except Exception as e:
        messagebox.showerror("Read error", f"Failed to read sheet:\n{e}")
        return

    display_dataframe_in_tree(df)

def clear_tree():
    tree.delete(*tree.get_children())
    tree["columns"] = ()
    for c in tree["show_columns"] if hasattr(tree,"show_columns") else ():
        pass

def display_dataframe_in_tree(df: pd.DataFrame):
    # Clear previous content
    for child in tree.get_children():
        tree.delete(child)
    tree["columns"] = list(df.columns)
    tree["show"] = "headings"  # hide the implicit first column

    # Configure columns
    for col in df.columns:
        tree.heading(col, text=col, anchor="w")
        tree.column(col, width=100, anchor="w", minwidth=50, stretch=True)

    # Insert rows
    # Convert NaNs to empty string for better display
    df_display = df.fillna("")
    rows = df_display.to_numpy().tolist()
    for r in rows:
        # Treeview expects each row as a sequence of column values (strings)
        tree.insert("", tk.END, values=[str(x) for x in r])

    # Auto-adjust column widths (simple heuristic)
    # measure using font metrics (optional, basic heuristic below)
    try:
        font = ("TkDefaultFont", 9)
        tmp = tk.font.Font(font=font)
        for i, col in enumerate(df.columns):
            max_text = max([str(col)] + [str(r[i]) for r in rows], key=len) if rows else str(col)
            new_w = min(max(80, tmp.measure(max_text) + 20), 400)  # clamp widths
            tree.column(col, width=new_w)
    except Exception:
        pass

    # Scroll to top
    if tree.get_children():
        tree.see(tree.get_children()[0])

# Optional: double-click a row to copy it or show details
def on_row_double_click(event):
    item = tree.identify_row(event.y)
    if not item:
        return
    vals = tree.item(item, "values")
    # For demo: copy to clipboard as tab-separated string
    root.clipboard_clear()
    root.clipboard_append("\t".join(vals))
    messagebox.showinfo("Copied", "Row copied to clipboard (tab-separated).")

# ---------- UI ----------
root = tk.Tk()
root.title("Excel Table Viewer")
root.geometry("1000x600")

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

# Middle: treeview inside a frame with scrollbars
frame_table = ttk.Frame(root)
frame_table.pack(fill="both", expand=True, padx=10, pady=(0,10))

# Vertical and horizontal scrollbars
vsb = ttk.Scrollbar(frame_table, orient="vertical")
hsb = ttk.Scrollbar(frame_table, orient="horizontal")

tree = ttk.Treeview(frame_table, columns=(), show="headings",
                    yscrollcommand=vsb.set, xscrollcommand=hsb.set)
vsb.config(command=tree.yview)
hsb.config(command=tree.xview)

vsb.pack(side="right", fill="y")
hsb.pack(side="bottom", fill="x")
tree.pack(side="left", fill="both", expand=True)

# Bind double-click on row (optional)
tree.bind("<Double-1>", on_row_double_click)

# Start
root.mainloop()
