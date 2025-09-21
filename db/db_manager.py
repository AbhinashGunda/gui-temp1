# db/db_manager.py
import sqlite3
from pathlib import Path
from .models import Client, Merchant, ClientRatesheet
from config import DB_PATH

class DBManager:
    def __init__(self, path=DB_PATH):
        self.path = Path(path)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        # Enable foreign key enforcement in SQLite
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.ensure_schema()

    def ensure_schema(self):
        cur = self.conn.cursor()
        # Create tables in parent -> child order
        cur.execute(Client.create_table_sql())
        cur.execute(Merchant.create_table_sql())
        cur.execute(ClientRatesheet.create_table_sql())
        # Useful indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_merchants_client ON merchants(client_sds_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ratesheets_client ON client_ratesheets(client_sds_id)")
        self.conn.commit()

        # Seed sample data if clients empty
        cur.execute("SELECT COUNT(1) as c FROM clients")
        if cur.fetchone()["c"] == 0:
            self._insert_sample()

    def _insert_sample(self):
        cur = self.conn.cursor()
        clients = [
            (43468172, 'TOMIAREFMNGMCU', 'bankuser1', 'UTC+0', '04:53'),
            (45430188, 'Amazon', 'bankuser2', 'UTC+0', '05:00'),
            (80014612, 'Systirch', 'bankuser3', 'UTC+1', '23:30'),
        ]
        cur.executemany(
            'INSERT INTO clients(sds_id, entity_name, bank_user_id, timezone, end_of_day) VALUES (?,?,?,?,?)',
            clients
        )
        # add merchants
        cur.executemany(
            'INSERT INTO merchants(client_sds_id, merchant_name, merchant_code) VALUES (?,?,?)',
            [
                (43468172, 'Tomia Merchant A', 'TMA'),
                (43468172, 'Tomia Merchant B', 'TMB'),
                (45430188, 'Amazon Merchant', 'AMZ'),
            ]
        )
        # add ratesheets
        cur.executemany(
            'INSERT INTO client_ratesheets(client_sds_id, merchant_id, effective_date, expiry_date, rate_details) VALUES (?,?,?,?,?)',
            [
                (43468172, 1, '2025-01-01', '2025-12-31', 'Rates: A'),
                (43468172, 2, '2024-06-01', '2025-05-31', 'Rates: B'),
                (45430188, 3, '2025-02-01', '2026-02-01', 'Amazon rates'),
            ]
        )
        self.conn.commit()

    # ---- Client CRUD ----
    def fetch_all_clients(self):
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM clients ORDER BY entity_name')
        return [dict(row) for row in cur.fetchall()]

    def fetch_client_by_sds(self, sds_id):
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM clients WHERE sds_id = ?', (sds_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def insert_client(self, sds_id, entity_name, bank_user_id=None, timezone=None, end_of_day=None):
        cur = self.conn.cursor()
        cur.execute(
            'INSERT INTO clients(sds_id, entity_name, bank_user_id, timezone, end_of_day) VALUES (?,?,?,?,?)',
            (sds_id, entity_name, bank_user_id, timezone, end_of_day)
        )
        self.conn.commit()
        return cur.lastrowid

    def update_client(self, sds_id, data: dict):
        if not data:
            return 0
        keys = []
        vals = []
        for k, v in data.items():
            keys.append(f"{k} = ?")
            vals.append(v)
        vals.append(sds_id)
        sql = f"UPDATE clients SET {', '.join(keys)} WHERE sds_id = ?"
        cur = self.conn.cursor()
        cur.execute(sql, vals)
        self.conn.commit()
        return cur.rowcount

    def delete_client(self, sds_id):
        cur = self.conn.cursor()
        cur.execute('DELETE FROM clients WHERE sds_id = ?', (sds_id,))
        self.conn.commit()
        return cur.rowcount

    # ---- Merchant CRUD ----
    def fetch_merchants_by_client(self, client_sds_id):
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM merchants WHERE client_sds_id = ? ORDER BY merchant_name', (client_sds_id,))
        return [dict(row) for row in cur.fetchall()]

    def fetch_merchant_by_id(self, merchant_id):
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM merchants WHERE merchant_id = ?', (merchant_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def insert_merchant(self, client_sds_id, merchant_name, merchant_code=None):
        cur = self.conn.cursor()
        cur.execute(
            'INSERT INTO merchants (client_sds_id, merchant_name, merchant_code) VALUES (?, ?, ?)',
            (client_sds_id, merchant_name, merchant_code)
        )
        self.conn.commit()
        return cur.lastrowid

    def update_merchant(self, merchant_id, data: dict):
        if not data:
            return 0
        keys = []
        vals = []
        for k, v in data.items():
            keys.append(f"{k} = ?")
            vals.append(v)
        vals.append(merchant_id)
        sql = f"UPDATE merchants SET {', '.join(keys)} WHERE merchant_id = ?"
        cur = self.conn.cursor()
        cur.execute(sql, vals)
        self.conn.commit()
        return cur.rowcount

    def delete_merchant(self, merchant_id):
        cur = self.conn.cursor()
        cur.execute('DELETE FROM merchants WHERE merchant_id = ?', (merchant_id,))
        self.conn.commit()
        return cur.rowcount

    # ---- Ratesheet CRUD ----
    def fetch_ratesheets_by_client(self, client_sds_id):
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM client_ratesheets WHERE client_sds_id = ? ORDER BY effective_date DESC', (client_sds_id,))
        return [dict(row) for row in cur.fetchall()]

    def fetch_ratesheets_by_merchant(self, merchant_id):
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM client_ratesheets WHERE merchant_id = ? ORDER BY effective_date DESC', (merchant_id,))
        return [dict(row) for row in cur.fetchall()]

    def fetch_ratesheet_by_id(self, ratesheet_id):
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM client_ratesheets WHERE ratesheet_id = ?', (ratesheet_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def insert_ratesheet(self, client_sds_id, merchant_id, effective_date, expiry_date, rate_details):
        cur = self.conn.cursor()
        cur.execute(
            'INSERT INTO client_ratesheets (client_sds_id, merchant_id, effective_date, expiry_date, rate_details) VALUES (?, ?, ?, ?, ?)',
            (client_sds_id, merchant_id, effective_date, expiry_date, rate_details)
        )
        self.conn.commit()
        return cur.lastrowid

    def update_ratesheet(self, ratesheet_id, data: dict):
        if not data:
            return 0
        keys = []
        vals = []
        for k, v in data.items():
            keys.append(f"{k} = ?")
            vals.append(v)
        vals.append(ratesheet_id)
        sql = f"UPDATE client_ratesheets SET {', '.join(keys)} WHERE ratesheet_id = ?"
        cur = self.conn.cursor()
        cur.execute(sql, vals)
        self.conn.commit()
        return cur.rowcount

    def delete_ratesheet(self, ratesheet_id):
        cur = self.conn.cursor()
        cur.execute('DELETE FROM client_ratesheets WHERE ratesheet_id = ?', (ratesheet_id,))
        self.conn.commit()
        return cur.rowcount

    # ---- Close ----
    def close(self):
        self.conn.close()
