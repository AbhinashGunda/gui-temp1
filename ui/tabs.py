import tkinter as tk
from tkinter import ttk

class Tabs(ttk.Notebook):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        # Create a right-click menu for tabs
        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="Close Tab", command=self._close_current_tab)

        # Bind right-click on tab area
        self.bind("<Button-3>", self._show_context_menu)

    def open_tab(self, key, title, frame_ctor):
        # If tab already exists, select it
        for tab_id in self.tabs():
            if self.tab(tab_id, "text") == title:
                self.select(tab_id)
                return
        # Otherwise create new one
        frame = frame_ctor(self)
        self.add(frame, text=title)
        self.select(frame)

    def _show_context_menu(self, event):
        # Identify which tab was right-clicked
        clicked_tab = self.index(f"@{event.x},{event.y}") if self.index("end") else None
        if clicked_tab is not None:
            self._right_clicked_tab = clicked_tab
            self.menu.tk_popup(event.x_root, event.y_root)

    def _close_current_tab(self):
        if hasattr(self, "_right_clicked_tab"):
            tab_id = self.tabs()[self._right_clicked_tab]
            self.forget(tab_id)
            self._right_clicked_tab = None
