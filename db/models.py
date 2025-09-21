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