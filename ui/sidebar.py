# ui/sidebar.py
import tkinter as tk
from tkinter import ttk

class Sidebar(ttk.Frame):
    def __init__(self, master, on_select, **kwargs):
        super().__init__(master, width=260, relief='groove', **kwargs)
        self.grid_propagate(False)
        self.on_select = on_select
        self._build()

    def _build(self):
        tree = ttk.Treeview(self, show='tree')
        tree.pack(fill='both', expand=True)
        netfx = tree.insert('', 'end', text='NetFX', open=True)
        tree.insert(netfx, 'end', text='Dual Control')
        tree.insert(netfx, 'end', text='System Configuration')
        tree.insert(netfx, 'end', text='Clients')
        tree.insert(netfx, 'end', text='Merchants')
        tree.insert(netfx, 'end', text='Intermediaries')
        tree.insert(netfx, 'end', text='GET Limits')
        tree.insert(netfx, 'end', text='Client Ratesheets')
        tree.insert(netfx, 'end', text='Reports')
        tree.bind('<<TreeviewSelect>>', self._on_select)
        self.tree = tree

    def _on_select(self, event):
        sel = event.widget.selection()
        if not sel:
            return
        text = event.widget.item(sel[0], 'text')
        # call callback with the item text
        self.on_select(text)
