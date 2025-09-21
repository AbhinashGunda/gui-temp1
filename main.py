# main.py
import tkinter as tk
from tkinter import ttk, messagebox
from config import WINDOW_TITLE, WINDOW_SIZE
from db.db_manager import DBManager
from ui.sidebar import Sidebar
from ui.tabs import Tabs
from ui.client_detail_tabs import ClientDetailTabs
from ui.views.client_view import ClientView
from ui.views.merchant_view import MerchantView
from ui.views.ratesheet_view import RatesheetView
from ui.views.importer_view import ImporterView

class NetFXApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(WINDOW_TITLE)
        self.geometry(WINDOW_SIZE)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # DB
        self.db = DBManager()

        # menu bar (new)
        self._build_menubar()

        # Sidebar
        self.sidebar = Sidebar(self, self.on_item_selected)
        self.sidebar.grid(row=0, column=0, sticky='ns')

        # Tabs area (main workspace)
        self.tabs = Tabs(self)
        self.tabs.grid(row=0, column=1, sticky='nsew')

        # keep references to popup windows to avoid garbage collection
        self._popups = []
        # keep references to global merchant/ratesheet popups so we can refresh them on create
        self._global_popup_refs = {'merchants': None, 'ratesheets': None}

    # ----------------------
    # Menu bar & create popups
    # ----------------------
    def _build_menubar(self):
        menubar = tk.Menu(self)
        create_menu = tk.Menu(menubar, tearoff=0)
        create_menu.add_command(label="c_client", command=self.open_create_client_popup)
        create_menu.add_command(label="c_merchant", command=self.open_create_merchant_popup)
        create_menu.add_command(label="c_ratesheet", command=self.open_create_ratesheet_popup)
        # separator + importer entry
        create_menu.add_separator()
        create_menu.add_command(label="Insert via Excel/CSV", command=self.open_insert_file_popup)
        menubar.add_cascade(label="Create", menu=create_menu)
        self.config(menu=menubar)

    def _center_popup(self, popup, w=400, h=220):
        screen_w = popup.winfo_screenwidth()
        screen_h = popup.winfo_screenheight()
        x = max(0, (screen_w // 2) - (w // 2))
        y = max(0, (screen_h // 2) - (h // 2))
        popup.geometry(f"{w}x{h}+{x}+{y}")

    def open_create_client_popup(self):
        popup = tk.Toplevel(self)
        popup.title("Create Client")
        self._center_popup(popup, 420, 240)
        popup.transient(self)
        popup.grab_set()

        frm = ttk.Frame(popup, padding=8)
        frm.pack(fill='both', expand=True)

        ttk.Label(frm, text="SDS ID (integer)").grid(row=0, column=0, sticky='w')
        sds_ent = ttk.Entry(frm); sds_ent.grid(row=0, column=1, sticky='we')

        ttk.Label(frm, text="Entity Name").grid(row=1, column=0, sticky='w')
        name_ent = ttk.Entry(frm); name_ent.grid(row=1, column=1, sticky='we')

        ttk.Label(frm, text="Bank User Id").grid(row=2, column=0, sticky='w')
        bank_ent = ttk.Entry(frm); bank_ent.grid(row=2, column=1, sticky='we')

        ttk.Label(frm, text="Timezone").grid(row=3, column=0, sticky='w')
        tz_ent = ttk.Entry(frm); tz_ent.grid(row=3, column=1, sticky='we')

        ttk.Label(frm, text="End of Day Agg Time").grid(row=4, column=0, sticky='w')
        eod_ent = ttk.Entry(frm); eod_ent.grid(row=4, column=1, sticky='we')

        def on_create_client():
            try:
                sds = int(sds_ent.get().strip())
            except ValueError:
                messagebox.showerror("Validation", "SDS ID must be an integer")
                return
            name = name_ent.get().strip()
            if not name:
                messagebox.showerror("Validation", "Entity Name is required")
                return
            bank = bank_ent.get().strip() or None
            tz = tz_ent.get().strip() or None
            eod = eod_ent.get().strip() or None
            try:
                self.db.insert_client(sds, name, bank, tz, eod)
                messagebox.showinfo("Success", f"Client {sds} created")
                popup.destroy()
            except Exception as ex:
                messagebox.showerror("DB Error", str(ex))

        btn = ttk.Button(frm, text="Create", command=on_create_client)
        btn.grid(row=6, column=0, columnspan=2, pady=8)

        # layout tweak
        frm.grid_columnconfigure(1, weight=1)

    def open_create_merchant_popup(self):
        popup = tk.Toplevel(self)
        popup.title("Create Merchant")
        self._center_popup(popup, 420, 240)
        popup.transient(self)
        popup.grab_set()

        frm = ttk.Frame(popup, padding=8)
        frm.pack(fill='both', expand=True)

        ttk.Label(frm, text="Merchant Name").grid(row=0, column=0, sticky='w')
        name_ent = ttk.Entry(frm); name_ent.grid(row=0, column=1, sticky='we')

        ttk.Label(frm, text="Merchant Code").grid(row=1, column=0, sticky='w')
        code_ent = ttk.Entry(frm); code_ent.grid(row=1, column=1, sticky='we')

        # choose client for the merchant
        ttk.Label(frm, text="Client (select)").grid(row=2, column=0, sticky='w')
        clients = self.db.fetch_all_clients()
        client_names = [f"{c['sds_id']} - {c['entity_name']}" for c in clients]
        client_combo = ttk.Combobox(frm, values=client_names, state='readonly')
        client_combo.grid(row=2, column=1, sticky='we')
        if client_names:
            client_combo.current(0)

        def on_create_merchant():
            name = name_ent.get().strip()
            if not name:
                messagebox.showerror("Validation", "Merchant name required"); return
            code = code_ent.get().strip() or None
            sel = client_combo.get()
            if not sel:
                messagebox.showerror("Validation", "Select a client"); return
            client_sds = int(sel.split(' - ')[0])
            try:
                mid = self.db.insert_merchant(client_sds, name, code)
                messagebox.showinfo("Success", f"Merchant created with id {mid}")
                popup.destroy()
                # refresh global merchant popup if open
                if self._global_popup_refs.get('merchants'):
                    self._global_popup_refs['merchants'].event_generate('<<refresh>>')
            except Exception as ex:
                messagebox.showerror("DB Error", str(ex))

        ttk.Button(frm, text="Create", command=on_create_merchant).grid(row=4, column=0, columnspan=2, pady=8)
        frm.grid_columnconfigure(1, weight=1)

    def open_create_ratesheet_popup(self):
        popup = tk.Toplevel(self)
        popup.title("Create Ratesheet")
        self._center_popup(popup, 480, 320)
        popup.transient(self)
        popup.grab_set()

        frm = ttk.Frame(popup, padding=8)
        frm.pack(fill='both', expand=True)

        # Optional merchant selection
        ttk.Label(frm, text="Merchant (optional)").grid(row=0, column=0, sticky='w')
        # show list of merchants with client name
        merchants = self.db.fetch_all_merchants()
        merchant_vals = ['(none)'] + [f"{m['merchant_id']} - {m['merchant_name']} ({m.get('client_name','')})" for m in merchants]
        merchant_combo = ttk.Combobox(frm, values=merchant_vals, state='readonly')
        merchant_combo.grid(row=0, column=1, sticky='we')
        merchant_combo.current(0)

        # client selection (required)
        ttk.Label(frm, text="Client (required)").grid(row=1, column=0, sticky='w')
        clients = self.db.fetch_all_clients()
        client_vals = [f"{c['sds_id']} - {c['entity_name']}" for c in clients]
        client_combo = ttk.Combobox(frm, values=client_vals, state='readonly')
        client_combo.grid(row=1, column=1, sticky='we')
        if client_vals:
            client_combo.current(0)

        ttk.Label(frm, text="Effective Date (YYYY-MM-DD)").grid(row=2, column=0, sticky='w')
        eff_ent = ttk.Entry(frm); eff_ent.grid(row=2, column=1, sticky='we')

        ttk.Label(frm, text="Expiry Date (YYYY-MM-DD)").grid(row=3, column=0, sticky='w')
        exp_ent = ttk.Entry(frm); exp_ent.grid(row=3, column=1, sticky='we')

        ttk.Label(frm, text="Rate Details").grid(row=4, column=0, sticky='w')
        details_ent = ttk.Entry(frm); details_ent.grid(row=4, column=1, sticky='we')

        def on_create_ratesheet():
            sel_client = client_combo.get()
            if not sel_client:
                messagebox.showerror("Validation", "Select a client"); return
            client_sds = int(sel_client.split(' - ')[0])
            msel = merchant_combo.get()
            merchant_id = None
            if msel and msel != '(none)':
                merchant_id = int(msel.split(' - ')[0])
            eff = eff_ent.get().strip() or None
            exp = exp_ent.get().strip() or None
            details = details_ent.get().strip() or None
            try:
                rid = self.db.insert_ratesheet(client_sds, merchant_id, eff, exp, details)
                messagebox.showinfo("Success", f"Ratesheet created id {rid}")
                popup.destroy()
                # refresh global ratesheet popup if open
                if self._global_popup_refs.get('ratesheets'):
                    self._global_popup_refs['ratesheets'].event_generate('<<refresh>>')
            except Exception as ex:
                messagebox.showerror("DB Error", str(ex))

        ttk.Button(frm, text="Create", command=on_create_ratesheet).grid(row=6, column=0, columnspan=2, pady=8)
        frm.grid_columnconfigure(1, weight=1)

    # ----------------------
    # New: Insert via Excel/CSV popup
    # ----------------------
    def open_insert_file_popup(self):
        """
        Open a popup containing the ImporterView (ui.views.importer_view.ImporterView).
        """
        popup = tk.Toplevel(self)
        popup.title("Insert via Excel/CSV")
        # reasonable default size
        popup.geometry("700x360")
        popup.transient(self)
        # Create the ImporterView inside the popup and pack it
        frame = ImporterView(popup, self.db)
        frame.pack(fill='both', expand=True)

        # Allow importer to trigger refreshes on this popup's toplevel
        def on_close():
            try:
                frame.destroy()
            except Exception:
                pass
            popup.destroy()
        popup.protocol("WM_DELETE_WINDOW", on_close)
        return popup

    # ----------------------
    # Existing app behaviour
    # ----------------------
    def open_popup(self, title: str, frame_ctor, size=(900, 600), role_key=None):
        popup = tk.Toplevel(self)
        popup.title(title)
        width, height = size
        screen_w = popup.winfo_screenwidth()
        screen_h = popup.winfo_screenheight()
        x = max(0, (screen_w // 2) - (width // 2))
        y = max(0, (screen_h // 2) - (height // 2))
        popup.geometry(f"{width}x{height}+{x}+{y}")
        frame = frame_ctor(popup)
        frame.pack(fill='both', expand=True)
        self._popups.append(popup)

        # store reference if caller wants automatic refresh hooks
        if role_key:
            self._global_popup_refs[role_key] = popup

            # attach a custom '<<refresh>>' virtual event handler to the popup root
            def _on_refresh(event=None):
                try:
                    # if frame implements load(), call it
                    if hasattr(frame, 'load'):
                        frame.load()
                except Exception:
                    pass
            popup.bind('<<refresh>>', _on_refresh)

        def _on_close():
            try:
                if role_key and self._global_popup_refs.get(role_key) is popup:
                    self._global_popup_refs[role_key] = None
                self._popups.remove(popup)
            except Exception:
                pass
            popup.destroy()
        popup.protocol("WM_DELETE_WINDOW", _on_close)
        return popup

    def on_item_selected(self, text):
        if text == 'Clients':
            self.tabs.open_tab('clients_list', 'Clients', self.clients_list_frame)
        elif text == 'Merchants':
            # open MerchantView in a popup window (global - pass client_sds_id = None)
            # also register role_key so the create dialog can refresh it
            self.open_popup("Merchants", lambda parent: MerchantView(parent, self.db, None), size=(900,600), role_key='merchants')
        elif text == 'Client Ratesheets':
            self.open_popup("Client Ratesheets", lambda parent: RatesheetView(parent, self.db, None), size=(1000,600), role_key='ratesheets')
        else:
            self.tabs.open_tab(text.lower(), text, lambda master: ttk.Frame(master))

    def clients_list_frame(self, master):
        frame = ttk.Frame(master, padding=10)
        cols = ('sds_id', 'entity_name', 'bank_user_id')
        tree = ttk.Treeview(frame, columns=cols, show='headings')
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=150)
        tree.pack(fill='both', expand=True)
        for row in self.db.fetch_all_clients():
            tree.insert('', 'end', values=(row['sds_id'], row['entity_name'], row['bank_user_id']))

        def on_double(e):
            iid = tree.identify_row(e.y)
            if not iid:
                return
            values = tree.item(iid, 'values')
            sds = int(values[0])
            title = f"Client {sds}"
            self.tabs.open_tab(f'client_{sds}', title, lambda master: ClientDetailTabs(master, self.db, sds))
        tree.bind('<Double-1>', on_double)
        return frame

    def on_closing(self):
        for p in list(self._popups):
            try:
                p.destroy()
            except Exception:
                pass
        self.db.close()
        self.destroy()

if __name__ == '__main__':
    app = NetFXApp()
    app.protocol('WM_DELETE_WINDOW', app.on_closing)
    app.mainloop()
