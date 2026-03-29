import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '')))

from models.db import db
import pymongo

if db is not None:
    try:
        # 1. Network Ping Test
        db.command('ping')
        print("✅ MongoDB Connection: Online and Reachable")

        # 2. Fetch with explicit sorting
        # We sort by timestamp descending (-1) to get the newest first
        alerts = list(db.alerts.find({}, {'_id': 0}).sort("timestamp", pymongo.DESCENDING))
        
        print(f"📊 Total Alerts in Database: {len(alerts)}")
        
        if alerts:
            print(f"🔥 Most Recent Alert: {alerts[0]}") # Newest is now at index 0
        else:
            print("⚪ No alerts found in the collection.")

    except Exception as e:
        print(f"❌ Error during database test: {e}")
else:
    print("❌ Database connection failed. Check your .env MONGO_URI and network.")