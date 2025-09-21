# ui/merchant_view.py
import tkinter as tk
from tkinter import ttk, messagebox

class MerchantView(ttk.Frame):
    """Shows merchants for a specific client and allows add/edit/delete.

    If client_sds_id is None, shows a global list (client_name column included).
    """
    def __init__(self, master, db, client_sds_id):
        super().__init__(master)
        self.db = db
        self.client_sds_id = client_sds_id
        self._build()
        # load will be called if client_scoped or global
        self.load()

    def _build(self):
        frm = ttk.Frame(self, padding=8)
        frm.pack(fill='both', expand=True)
        title = f"Merchants for Client {self.client_sds_id}" if self.client_sds_id else "Merchants (All Clients)"
        lbl = ttk.Label(frm, text=title, font=(None, 12))
        lbl.pack(anchor='w')

        # superset columns so global view can show client_name
        cols = ('merchant_id', 'merchant_name', 'merchant_code', 'client_name')
        self.tree = ttk.Treeview(frm, columns=cols, show='headings', height=12)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=150)
        self.tree.pack(fill='both', expand=True, pady=6)

        btns = ttk.Frame(frm)
        btns.pack(fill='x')
        ttk.Button(btns, text='Add', command=self.add_popup).pack(side='left', padx=4)
        ttk.Button(btns, text='Edit', command=self.edit_selected).pack(side='left', padx=4)
        ttk.Button(btns, text='Delete', command=self.delete_selected).pack(side='left', padx=4)

    def load(self):
        print(f"[MerchantView] load() called for client_sds_id={self.client_sds_id}")
        for r in self.tree.get_children():
            self.tree.delete(r)

        if self.client_sds_id is None:
            merchants = self.db.fetch_all_merchants()
            for m in merchants:
                self.tree.insert('', 'end', values=(m['merchant_id'], m['merchant_name'], m.get('merchant_code',''), m.get('client_name','')))
        else:
            merchants = self.db.fetch_merchants_by_client(self.client_sds_id)
            for m in merchants:
                self.tree.insert('', 'end', values=(m['merchant_id'], m['merchant_name'], m.get('merchant_code',''), ''))

    def add_popup(self):
        popup = tk.Toplevel(self)
        popup.title('Add Merchant')

        ttk.Label(popup, text='Name').grid(row=0, column=0)
        name = ttk.Entry(popup); name.grid(row=0, column=1)

        ttk.Label(popup, text='Code').grid(row=1, column=0)
        code = ttk.Entry(popup); code.grid(row=1, column=1)

        # if global view, allow choosing client
        client_choice = None
        if self.client_sds_id is None:
            ttk.Label(popup, text='Client (select)').grid(row=2, column=0)
            clients = self.db.fetch_all_clients()
            client_ids = [str(c['sds_id']) for c in clients]
            client_names = [f"{c['sds_id']} - {c['entity_name']}" for c in clients]
            client_choice = ttk.Combobox(popup, values=client_names, state='readonly')
            client_choice.grid(row=2, column=1)
            if client_names:
                client_choice.current(0)

        def on_ok():
            nm = name.get().strip()
            if not nm:
                messagebox.showerror('Error', 'Name required'); return
            code_val = code.get().strip() or None
            target_client = self.client_sds_id
            if self.client_sds_id is None:
                sel = client_choice.get()
                if not sel:
                    messagebox.showerror('Error', 'Select client'); return
                target_client = int(sel.split(' - ')[0])
            self.db.insert_merchant(target_client, nm, code_val)
            popup.destroy()
            self.load()

        ttk.Button(popup, text='OK', command=on_ok).grid(row=3, column=0, columnspan=2)

    def edit_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo('Select', 'Select a merchant'); return
        vals = self.tree.item(sel[0], 'values')
        merchant_id = int(vals[0])
        merchant = self.db.fetch_merchant_by_id(merchant_id)
        if not merchant:
            messagebox.showerror('Error', 'Not found'); return
        popup = tk.Toplevel(self)
        popup.title('Edit Merchant')
        ttk.Label(popup, text='Name').grid(row=0, column=0)
        name = ttk.Entry(popup); name.grid(row=0, column=1); name.insert(0, merchant['merchant_name'])
        ttk.Label(popup, text='Code').grid(row=1, column=0)
        code = ttk.Entry(popup); code.grid(row=1, column=1); code.insert(0, merchant.get('merchant_code',''))

        def on_ok():
            self.db.update_merchant(merchant_id, {'merchant_name': name.get().strip(), 'merchant_code': code.get().strip()})
            popup.destroy(); self.load()
        ttk.Button(popup, text='OK', command=on_ok).grid(row=2, column=0, columnspan=2)

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo('Select', 'Select a merchant'); return
        vals = self.tree.item(sel[0], 'values')
        merchant_id = int(vals[0])
        if messagebox.askyesno('Confirm', 'Delete merchant?'):
            self.db.delete_merchant(merchant_id)
            self.load()
