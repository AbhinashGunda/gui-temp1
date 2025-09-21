# ==========================
import tkinter as tk
from tkinter import ttk, messagebox

class ClientView(ttk.Frame):
    FIELDS = [
        ('sds_id', 'Sds Id'),
        ('entity_name', 'Entity Name'),
        ('bank_user_id', 'Bank User Id'),
        ('timezone', 'Timezone'),
        ('end_of_day', 'End Of Day Agg Time'),
    ]

    def __init__(self, master, db: object, sds_id=None):
        super().__init__(master)
        self.db = db
        self.sds_id = sds_id
        self.entries = {}
        self._build()
        if sds_id is not None:
            self.load(sds_id)

    def _build(self):
        frm = ttk.Frame(self, padding=10)
        frm.pack(fill='both', expand=True)
        for i, (field, label) in enumerate(self.FIELDS):
            ttk.Label(frm, text=label).grid(row=i, column=0, sticky='w', pady=4)
            ent = ttk.Entry(frm)
            ent.grid(row=i, column=1, sticky='we', pady=4)
            frm.grid_columnconfigure(1, weight=1)
            self.entries[field] = ent
            # Make sds_id readonly
            if field == 'sds_id':
                ent.config(state='readonly')
        btns = ttk.Frame(frm)
        btns.grid(row=len(self.FIELDS), column=0, columnspan=2, pady=10)
        save = ttk.Button(btns, text='Save', command=self.save)
        save.pack(side='left', padx=5)

    def load(self, sds_id):
        data = self.db.fetch_client_by_sds(sds_id)
        if not data:
            messagebox.showerror('Not found', f'Client {sds_id} not found')
            return
        for k, ent in self.entries.items():
            val = data.get(k) if data.get(k) is not None else ''
            # if readonly field, temporarily make normal to set
            if k == 'sds_id':
                ent.config(state='normal')
                ent.delete(0, 'end')
                ent.insert(0, str(val))
                ent.config(state='readonly')
            else:
                ent.delete(0, 'end')
                ent.insert(0, str(val))

    def save(self):
        # gather editable fields
        payload = {}
        for k, ent in self.entries.items():
            if k == 'sds_id':
                sds_id = ent.get()
                continue
            payload[k] = ent.get()
        try:
            updated = self.db.update_client(int(sds_id), payload)
            messagebox.showinfo('Saved', f'Updated rows: {updated}')
        except Exception as e:
            messagebox.showerror('Error', str(e))