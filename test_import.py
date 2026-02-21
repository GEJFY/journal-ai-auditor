import requests
import os
import sys

API_BASE = "http://localhost:8090/api/v1"
SAMPLE_FILE = "sample_data/01_chart_of_accounts.csv"

def test_import():
    if not os.path.exists(SAMPLE_FILE):
        print(f"Sample file not found: {SAMPLE_FILE}")
        return

    print(f"Testing import with {SAMPLE_FILE}...")

    # Step 1: Upload
    try:
        with open(SAMPLE_FILE, "rb") as f:
            files = {"file": (os.path.basename(SAMPLE_FILE), f, "text/csv")}
            response = requests.post(f"{API_BASE}/import/upload", files=files)
            
        if response.status_code != 200:
            print(f"Upload failed: {response.status_code}")
            print(response.text)
            return

        data = response.json()
        temp_file_id = data.get("temp_file_id")
        print(f"Upload successful. Temp ID: {temp_file_id}")

    except Exception as e:
        print(f"Upload exception: {e}")
        return

    # Step 2: Import Master
    try:
        payload = {
            "temp_file_id": temp_file_id,
            "master_type": "accounts"
        }
        response = requests.post(f"{API_BASE}/import/master", json=payload)
        
        if response.status_code != 200:
            print(f"Import failed: {response.status_code}")
            print(response.text)
            return

        result = response.json()
        print("Import successful!")
        print(result)

    except Exception as e:
        print(f"Import exception: {e}")

if __name__ == "__main__":
    test_import()
