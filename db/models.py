# db/models.py

class Client:
    @staticmethod
    def create_table_sql():
        return (
            "CREATE TABLE IF NOT EXISTS clients ("
            "sds_id INTEGER PRIMARY KEY, "
            "entity_name TEXT NOT NULL, "
            "bank_user_id TEXT, "
            "timezone TEXT, "
            "end_of_day TEXT"
            ")"
        )

class Merchant:
    @staticmethod
    def create_table_sql():
        return (
            "CREATE TABLE IF NOT EXISTS merchants ("
            "merchant_id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "client_sds_id INTEGER NOT NULL, "
            "merchant_name TEXT NOT NULL, "
            "merchant_code TEXT, "
            "created_at TEXT DEFAULT CURRENT_TIMESTAMP, "
            "FOREIGN KEY(client_sds_id) REFERENCES clients(sds_id) ON DELETE CASCADE"
            ")"
        )

class ClientRatesheet:
    @staticmethod
    def create_table_sql():
        return (
            "CREATE TABLE IF NOT EXISTS client_ratesheets ("
            "ratesheet_id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "client_sds_id INTEGER NOT NULL, "
            "merchant_id INTEGER, "
            "effective_date TEXT, "
            "expiry_date TEXT, "
            "rate_details TEXT, "
            "created_at TEXT DEFAULT CURRENT_TIMESTAMP, "
            "FOREIGN KEY(client_sds_id) REFERENCES clients(sds_id) ON DELETE CASCADE, "
            "FOREIGN KEY(merchant_id) REFERENCES merchants(merchant_id) ON DELETE SET NULL"
            ")"
        )
