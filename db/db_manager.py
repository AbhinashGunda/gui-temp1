import sqlite3
from pathlib import Path
from .models import Client
from config import DB_PATH

class DBManager:
    def __init__(self, path=DB_PATH):
        self.path = Path(path)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.ensure_schema()

    def ensure_schema(self):
        cur = self.conn.cursor()
        cur.execute(Client.create_table_sql())
        self.conn.commit()
        # Insert sample data if empty
        cur.execute("SELECT COUNT(1) as c FROM clients")
        if cur.fetchone()["c"] == 0:
            self._insert_sample()

    def _insert_sample(self):
        sample = [
            (43468172, 'TOMIAREFMNGMCU', 'bankuser1', 'UTC+0', '04:53'),
            (45430188, 'Amazon', 'bankuser2', 'UTC+0', '05:00'),
            (80014612, 'Systirch', 'bankuser3', 'UTC+1', '23:30'),
        ]
        cur = self.conn.cursor()
        cur.executemany(
            'INSERT INTO clients(sds_id, entity_name, bank_user_id, timezone, end_of_day) VALUES (?,?,?,?,?)',
            sample
        )
        self.conn.commit()

    def fetch_all_clients(self):
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM clients ORDER BY entity_name')
        return [dict(row) for row in cur.fetchall()]

    def fetch_client_by_sds(self, sds_id):
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM clients WHERE sds_id = ?', (sds_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def update_client(self, sds_id, data: dict):
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

    def close(self):
        self.conn.close()
