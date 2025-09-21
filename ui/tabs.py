# ui/tabs.py
import tkinter as tk
from tkinter import ttk

class Tabs(ttk.Notebook):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        # Right-click menu for closing tabs
        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="Close Tab", command=self._close_current_tab)
        self.menu.add_command(label="Close Others", command=self._close_other_tabs)
        self.menu.add_command(label="Close All", command=self._close_all_tabs)
        # Bind right-click (Button-3). On macOS, you may need Button-2 or to use <Button-2>
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
        try:
            clicked = self.index(f"@{event.x},{event.y}")
        except Exception:
            clicked = None
        if clicked is not None:
            self._right_clicked_tab = clicked
            self.menu.tk_popup(event.x_root, event.y_root)

    def _close_current_tab(self):
        if hasattr(self, '_right_clicked_tab'):
            tab_id = self.tabs()[self._right_clicked_tab]
            self.forget(tab_id)
            del self._right_clicked_tab

    def _close_other_tabs(self):
        if not hasattr(self, '_right_clicked_tab'):
            return
        keep = self.tabs()[self._right_clicked_tab]
        for t in list(self.tabs()):
            if t != keep:
                self.forget(t)
        del self._right_clicked_tab

    def _close_all_tabs(self):
        for t in list(self.tabs()):
            self.forget(t)
