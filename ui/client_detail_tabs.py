# ui/client_detail_tabs.py
import tkinter as tk
from tkinter import ttk
# ui/client_detail_tabs.py
# replace imports at top with:
from .views.merchant_view import MerchantView
from .views.ratesheet_view import RatesheetView


class ClientDetailTabs(ttk.Notebook):
    """Sub-tabs for a single client's Merchants and Ratesheets."""
    def __init__(self, master, db, client_sds_id, **kwargs):
        super().__init__(master, **kwargs)
        self.db = db
        self.client_sds_id = client_sds_id
        self._build()

    def _build(self):
        mframe = MerchantView(self, self.db, self.client_sds_id)
        self.add(mframe, text='Merchants')
        rframe = RatesheetView(self, self.db, self.client_sds_id)
        self.add(rframe, text='Client Ratesheets')
