# ui/views/importer_view.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tools.importer.engine import read_key_value_file, insert_from_parsed

class ImporterView(ttk.Frame):
    """
    Importer UI that accepts an Excel (.xlsx) or CSV (.csv) file where keys are of the
    form table>field (e.g. client>sds_id, merchant>merchant_name, ratesheet>effective_date).
    It shows a small preview of parsed values and performs insertion.
    """
    def __init__(self, master, db, **kwargs):
        super().__init__(master, **kwargs)
        self.db = db
        self.path_var = tk.StringVar()
        self.parsed = None
        self._build()

    def _build(self):
        frm = ttk.Frame(self, padding=10)
        frm.pack(fill='both', expand=True)

        ttk.Label(frm, text="Select .xlsx or .csv with keys in 'table>field' format").grid(row=0, column=0, columnspan=3, sticky='w', pady=(0,8))

        entry = ttk.Entry(frm, textvariable=self.path_var)
        entry.grid(row=1, column=0, sticky='we', padx=(0,6))
        frm.grid_columnconfigure(0, weight=1)

        def on_browse():
            p = filedialog.askopenfilename(title='Select file', filetypes=[('Excel files','*.xlsx *.xlsm'), ('CSV files','*.csv'), ('All files','*.*')])
            if p:
                self.path_var.set(p)
                self._try_preview(p)
        ttk.Button(frm, text="Browse...", command=on_browse).grid(row=1, column=1, sticky='e')

        ttk.Button(frm, text="Preview", command=lambda: self._try_preview(self.path_var.get())).grid(row=1, column=2, sticky='e', padx=(6,0))

        # preview area (readonly text widget)
        self.preview = tk.Text(frm, height=12, wrap='none')
        self.preview.grid(row=2, column=0, columnspan=3, sticky='nsew', pady=(8,0))
        frm.grid_rowconfigure(2, weight=1)

        btns = ttk.Frame(frm)
        btns.grid(row=3, column=0, columnspan=3, pady=(8,0), sticky='ew')
        ttk.Button(btns, text="Import", command=self._on_import).pack(side='left')
        ttk.Button(btns, text="Clear", command=self._clear).pack(side='left', padx=(6,0))

        note = ("Note: file must use keys like 'client>sds_id', 'client>entity_name', "
                "'merchant>merchant_name', 'ratesheet>effective_date', etc.")
        ttk.Label(frm, text=note, justify='left').grid(row=4, column=0, columnspan=3, sticky='w', pady=(8,0))

    def _try_preview(self, path):
        path = (path or '').strip()
        if not path:
            messagebox.showerror("Error", "Select a file first")
            return
        try:
            parsed = read_key_value_file(path)
            self.parsed = parsed
            # show nice preview in text widget
            self.preview.config(state='normal')
            self.preview.delete('1.0', tk.END)
            if not parsed:
                self.preview.insert(tk.END, "(no key/value pairs found)\n")
            else:
                for table, fields in parsed.items():
                    self.preview.insert(tk.END, f"[{table}]\n")
                    for k, v in fields.items():
                        self.preview.insert(tk.END, f"  {k} => {v}\n")
                    self.preview.insert(tk.END, "\n")
            self.preview.config(state='disabled')
        except Exception as ex:
            messagebox.showerror("Error reading file", str(ex))
            self.parsed = None

    def _on_import(self):
        if not self.parsed:
            # try to preview first
            path = (self.path_var.get() or '').strip()
            if not path:
                messagebox.showerror("Error", "Select a file first")
                return
            try:
                self.parsed = read_key_value_file(path)
            except Exception as ex:
                messagebox.showerror("Error reading file", str(ex))
                return

        try:
            res = insert_from_parsed(self.db, self.parsed)
            messagebox.showinfo("Imported", f"Insert summary: {res}")
            # trigger refresh on toplevel window so open views can refresh
            try:
                self.winfo_toplevel().event_generate('<<refresh>>')
            except Exception:
                pass
            # clear preview & path after successful import
            self._clear()
        except Exception as ex:
            messagebox.showerror("Import error", str(ex))

    def _clear(self):
        self.path_var.set('')
        self.parsed = None
        self.preview.config(state='normal')
        self.preview.delete('1.0', tk.END)
        self.preview.config(state='disabled')
