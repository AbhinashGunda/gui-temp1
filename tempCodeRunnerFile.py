from db.db_manager import DBManager
db = DBManager()
print("Clients:", db.fetch_all_clients())
# pick one client id you see and run:
print("Merchants for first client:", db.fetch_merchants_by_client(db.fetch_all_clients()[0]['sds_id']))
print("Ratesheets for first client:", db.fetch_ratesheets_by_client(db.fetch_all_clients()[0]['sds_id']))
db.close()
