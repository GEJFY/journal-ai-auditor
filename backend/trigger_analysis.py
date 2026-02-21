import requests
import time
import json

BASE_URL = "http://localhost:8090/api/v1"

def trigger_analysis():
    print("Triggering Batch Analysis for 2024...")
    
    # Start Batch Job
    try:
        response = requests.post(f"{BASE_URL}/batch/start", json={
            "mode": "full",
            "fiscal_year": 2024
        })
        
        if response.status_code == 200:
            job_data = response.json()
            job_id = job_data['job_id']
            print(f"Job started: {job_id}")
            
            # Poll status
            while True:
                status_res = requests.get(f"{BASE_URL}/batch/status/{job_id}")
                if status_res.status_code == 200:
                    status_data = status_res.json()
                    status = status_data['status']
                    print(f"Status: {status} - Processed: {status_data.get('total_entries', 0)}")
                    
                    if status in ['completed', 'failed']:
                        print(f"Job finished with status: {status}")
                        print(json.dumps(status_data, indent=2))
                        break
                else:
                    print("Failed to get status")
                    break
                
                time.sleep(2)
        else:
            print(f"Failed to start job: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    trigger_analysis()
