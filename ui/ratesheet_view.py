# ui/ratesheet_view.py
import tkinter as tk
from tkinter import ttk, messagebox

class RatesheetView(ttk.Frame):
    """Shows ratesheets for a specific client and allows add/edit/delete."""
    def __init__(self, master, db, client_sds_id):
        super().__init__(master)
        self.db = db
        self.client_sds_id = client_sds_id
        self._build()
        self.load()

    def _build(self):
        frm = ttk.Frame(self, padding=8)
        frm.pack(fill='both', expand=True)
        lbl = ttk.Label(frm, text=f"Ratesheets for Client {self.client_sds_id}", font=(None, 12))
        lbl.pack(anchor='w')

        cols = ('ratesheet_id','merchant_id','effective_date','expiry_date')
        self.tree = ttk.Treeview(frm, columns=cols, show='headings', height=8)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=140)
        self.tree.pack(fill='both', expand=True, pady=6)

        btns = ttk.Frame(frm)
        btns.pack(fill='x')
        ttk.Button(btns, text='Add', command=self.add_popup).pack(side='left', padx=4)
        ttk.Button(btns, text='Edit', command=self.edit_selected).pack(side='left', padx=4)
        ttk.Button(btns, text='Delete', command=self.delete_selected).pack(side='left', padx=4)

    def load(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        rates = self.db.fetch_ratesheets_by_client(self.client_sds_id)
        for rs in rates:
            self.tree.insert('', 'end', values=(rs['ratesheet_id'], rs.get('merchant_id'), rs.get('effective_date'), rs.get('expiry_date')))

    def add_popup(self):
        popup = tk.Toplevel(self)
        popup.title('Add Ratesheet')
        ttk.Label(popup, text='Merchant ID (optional)').grid(row=0, column=0)
        mid = ttk.Entry(popup); mid.grid(row=0, column=1)
        ttk.Label(popup, text='Effective Date').grid(row=1, column=0)
        eff = ttk.Entry(popup); eff.grid(row=1, column=1)
        ttk.Label(popup, text='Expiry Date').grid(row=2, column=0)
        exp = ttk.Entry(popup); exp.grid(row=2, column=1)
        ttk.Label(popup, text='Rate Details').grid(row=3, column=0)
        details = ttk.Entry(popup); details.grid(row=3, column=1)
        def on_ok():
            merchant_id = int(mid.get()) if mid.get().strip() else None
            self.db.insert_ratesheet(self.client_sds_id, merchant_id, eff.get().strip(), exp.get().strip(), details.get().strip())
            popup.destroy(); self.load()
        ttk.Button(popup, text='OK', command=on_ok).grid(row=4, column=0, columnspan=2)

    def edit_selected(self):
        sel = self.tree.selection()
        if not sel: messagebox.showinfo('Select', 'Select a ratesheet'); return
        vals = self.tree.item(sel[0], 'values')
        ratesheet_id = int(vals[0])
        rs = self.db.fetch_ratesheet_by_id(ratesheet_id)
        if not rs: messagebox.showerror('Error', 'Not found'); return
        popup = tk.Toplevel(self)
        popup.title('Edit Ratesheet')
        ttk.Label(popup, text='Merchant ID (optional)').grid(row=0, column=0)
        mid = ttk.Entry(popup); mid.grid(row=0, column=1); mid.insert(0, rs.get('merchant_id') or '')
        ttk.Label(popup, text='Effective Date').grid(row=1, column=0)
        eff = ttk.Entry(popup); eff.grid(row=1, column=1); eff.insert(0, rs.get('effective_date') or '')
        ttk.Label(popup, text='Expiry Date').grid(row=2, column=0)
        exp = ttk.Entry(popup); exp.grid(row=2, column=1); exp.insert(0, rs.get('expiry_date') or '')
        ttk.Label(popup, text='Rate Details').grid(row=3, column=0)
        details = ttk.Entry(popup); details.grid(row=3, column=1); details.insert(0, rs.get('rate_details') or '')
        def on_ok():
            data = {
                'merchant_id': int(mid.get()) if mid.get().strip() else None,
                'effective_date': eff.get().strip(),
                'expiry_date': exp.get().strip(),
                'rate_details': details.get().strip()
            }
            self.db.update_ratesheet(ratesheet_id, data)
            popup.destroy(); self.load()
        ttk.Button(popup, text='OK', command=on_ok).grid(row=4, column=0, columnspan=2)

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel: messagebox.showinfo('Select', 'Select a ratesheet'); return
        vals = self.tree.item(sel[0], 'values')
        ratesheet_id = int(vals[0])
        if messagebox.askyesno('Confirm', 'Delete ratesheet?'):
            self.db.delete_ratesheet(ratesheet_id)
            self.load()
