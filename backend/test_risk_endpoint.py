import requests
import json
import sys

BASE_URL = "http://localhost:8090/api/v1"

def test_risk_endpoint():
    print("Testing Risk API endpoint...")
    years = [2024, 2025]
    
    for year in years:
        print(f"\n--- Fiscal Year: {year} ---")
        try:
            url = f"{BASE_URL}/dashboard/risk?fiscal_year={year}"
            print(f"GET {url}")
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                print("Response OK")
                print(f"High Risk Count: {len(data.get('high_risk', []))}")
                print(f"Medium Risk Count: {len(data.get('medium_risk', []))}")
                print(f"Low Risk Count: {len(data.get('low_risk', []))}")
                print(f"Distribution: {json.dumps(data.get('risk_distribution', {}), indent=2)}")
                
                if data.get('high_risk'):
                    print("Sample High Risk Item:")
                    print(json.dumps(data['high_risk'][0], indent=2))
            else:
                print(f"Error: {response.status_code}")
                print(response.text)
                
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    test_risk_endpoint()
