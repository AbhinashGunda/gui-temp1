import tkinter as tk
from tkinter import ttk
from config import WINDOW_TITLE, WINDOW_SIZE
from db.db_manager import DBManager
from ui.sidebar import Sidebar
from ui.tabs import Tabs
from ui.client_view import ClientView

class NetFXApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(WINDOW_TITLE)
        self.geometry(WINDOW_SIZE)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # DB
        self.db = DBManager()

        # Sidebar
        self.sidebar = Sidebar(self, self.on_item_selected)
        self.sidebar.grid(row=0, column=0, sticky='ns')

        # Tabs area
        self.tabs = Tabs(self)
        self.tabs.grid(row=0, column=1, sticky='nsew')

    def on_item_selected(self, text):
        # Open a tab depending on selection
        if text == 'Clients':
            # Open clients list tab
            self.tabs.open_tab('clients_list', 'Clients', self.clients_list_frame)
        else:
            # generic
            self.tabs.open_tab(text.lower(), text, lambda master: ttk.Frame(master))

    def clients_list_frame(self, master):
        frame = ttk.Frame(master, padding=10)
        # Treeview with clients
        cols = ('sds_id', 'entity_name', 'bank_user_id')
        tree = ttk.Treeview(frame, columns=cols, show='headings')
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=150)
        tree.pack(fill='both', expand=True)
        # populate
        for row in self.db.fetch_all_clients():
            tree.insert('', 'end', values=(row['sds_id'], row['entity_name'], row['bank_user_id']))
        # double click to open client tab
        def on_double(e):
            iid = tree.identify_row(e.y)
            if not iid:
                return
            values = tree.item(iid, 'values')
            sds = int(values[0])
            title = f"Client {sds}"
            self.tabs.open_tab(f'client_{sds}', title, lambda master: ClientView(master, self.db, sds))
        tree.bind('<Double-1>', on_double)
        return frame

    def on_closing(self):
        self.db.close()
        self.destroy()

if __name__ == '__main__':
    app = NetFXApp()
    app.protocol('WM_DELETE_WINDOW', app.on_closing)
    app.mainloop()
