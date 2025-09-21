# db/db_manager.py
import sqlite3
from pathlib import Path
from .models import Client, Merchant, ClientRatesheet
from config import DB_PATH

class DBManager:
    def __init__(self, path=DB_PATH):
        self.path = Path(path)
        print(f"[DBManager] opening DB at: {self.path.resolve()}")
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.ensure_schema()
        self._ensure_seeded_children()

    def ensure_schema(self):
        cur = self.conn.cursor()
        cur.execute(Client.create_table_sql())
        cur.execute(Merchant.create_table_sql())
        cur.execute(ClientRatesheet.create_table_sql())
        cur.execute("CREATE INDEX IF NOT EXISTS idx_merchants_client ON merchants(client_sds_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ratesheets_client ON client_ratesheets(client_sds_id)")
        self.conn.commit()

        cur.execute("SELECT COUNT(1) as c FROM clients")
        count = cur.fetchone()["c"]
        if count == 0:
            print("[DBManager] clients table empty — seeding clients")
            self._insert_sample_clients()
        else:
            print(f"[DBManager] clients present: {count}")

    def _insert_sample_clients(self):
        cur = self.conn.cursor()
        try:
            clients = [
                (43468172, 'TOMIAREFMNGMCU', 'bankuser1', 'UTC+0', '04:53'),
                (45430188, 'Amazon', 'bankuser2', 'UTC+0', '05:00'),
                (80014612, 'Systirch', 'bankuser3', 'UTC+1', '23:30'),
            ]
            cur.executemany(
                'INSERT OR IGNORE INTO clients(sds_id, entity_name, bank_user_id, timezone, end_of_day) VALUES (?,?,?,?,?)',
                clients
            )
            self.conn.commit()
            print(f"[seed] inserted/ignored {len(clients)} clients")
        except Exception as ex:
            self.conn.rollback()
            print("[seed] ERROR inserting clients:", ex)
            raise

    def _ensure_seeded_children(self):
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(1) as c FROM merchants")
        merchants_count = cur.fetchone()["c"]
        if merchants_count == 0:
            print("[DBManager] merchants table empty — seeding merchants & ratesheets")
            self._insert_sample_merchants_and_ratesheets()
        else:
            print(f"[DBManager] merchants present: {merchants_count}")

        cur.execute("SELECT COUNT(1) as c FROM client_ratesheets")
        rs_count = cur.fetchone()["c"]
        print(f"[DBManager] ratesheets present: {rs_count}")

    def _insert_sample_merchants_and_ratesheets(self):
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT sds_id FROM clients")
            clients = [row["sds_id"] for row in cur.fetchall()]
            if not clients:
                print("[seed] no clients present; aborting merchant/ratesheet seed")
                return

            merchants_to_seed = [
                (43468172, 'Tomia Merchant A', 'TMA'),
                (43468172, 'Tomia Merchant B', 'TMB'),
                (45430188, 'Amazon Merchant', 'AMZ'),
            ]

            inserted_merchant_map = {}
            for client_sds, name, code in merchants_to_seed:
                cur.execute("SELECT 1 FROM clients WHERE sds_id = ?", (client_sds,))
                if cur.fetchone() is None:
                    print(f"[seed] skipping merchant '{name}' because client {client_sds} not found")
                    continue
                cur.execute(
                    'INSERT INTO merchants(client_sds_id, merchant_name, merchant_code) VALUES (?,?,?)',
                    (client_sds, name, code)
                )
                mid = cur.lastrowid
                inserted_merchant_map[name] = mid
                print(f"[seed] inserted merchant '{name}' id={mid} for client {client_sds}")
            self.conn.commit()

            ratesheets_to_seed = [
                ('Tomia Merchant A', 43468172, '2025-01-01', '2025-12-31', 'Rates: A'),
                ('Tomia Merchant B', 43468172, '2024-06-01', '2025-05-31', 'Rates: B'),
                ('Amazon Merchant', 45430188, '2025-02-01', '2026-02-01', 'Amazon rates'),
                (None, 80014612, '2025-03-01', '2026-03-01', 'Systirch general rates'),
            ]
            rs_inserted = 0
            for merchant_name, client_sds, eff, exp, details in ratesheets_to_seed:
                merchant_id = inserted_merchant_map.get(merchant_name) if merchant_name else None
                cur.execute("SELECT 1 FROM clients WHERE sds_id = ?", (client_sds,))
                if cur.fetchone() is None:
                    print(f"[seed] skipping ratesheet for client {client_sds} (client not found)")
                    continue
                cur.execute(
                    'INSERT INTO client_ratesheets(client_sds_id, merchant_id, effective_date, expiry_date, rate_details) VALUES (?,?,?,?,?)',
                    (client_sds, merchant_id, eff, exp, details)
                )
                rs_inserted += 1
            self.conn.commit()
            print(f"[seed] inserted {rs_inserted} ratesheets")
        except Exception as ex:
            self.conn.rollback()
            print("[seed] ERROR inserting merchants/ratesheets:", ex)
            raise

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
            'INSERT OR IGNORE INTO clients(sds_id, entity_name, bank_user_id, timezone, end_of_day) VALUES (?,?,?,?,?)',
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

    def fetch_all_merchants(self):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT m.*, c.entity_name AS client_name "
            "FROM merchants m "
            "LEFT JOIN clients c ON m.client_sds_id = c.sds_id "
            "ORDER BY m.merchant_name"
        )
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

    def fetch_all_ratesheets(self):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT r.*, c.entity_name AS client_name, m.merchant_name "
            "FROM client_ratesheets r "
            "LEFT JOIN clients c ON r.client_sds_id = c.sds_id "
            "LEFT JOIN merchants m ON r.merchant_id = m.merchant_id "
            "ORDER BY r.effective_date DESC"
        )
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
