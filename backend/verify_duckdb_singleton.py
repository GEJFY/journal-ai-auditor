import threading
import time
from app.db import duckdb_manager

def worker(i):
    print(f"Thread {i} start")
    try:
        with duckdb_manager.connect() as conn:
            conn.execute("SELECT 1")
        print(f"Thread {i} success")
    except Exception as e:
        print(f"Thread {i} failed: {e}")

threads = []
for i in range(5):
    t = threading.Thread(target=worker, args=(i,))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

print("Verification complete")
