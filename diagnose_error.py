#!/usr/bin/env python3
"""
Diagnose 500 error in NAS File Doctor
"""
import requests
import json

BASE_URL = "http://localhost:5001"

def test_endpoint(name, method, path, data=None):
    """Test an API endpoint"""
    print(f"\nTesting {name}...")
    print(f"  {method} {BASE_URL}{path}")
    
    try:
        if method == "GET":
            resp = requests.get(f"{BASE_URL}{path}", timeout=5)
        elif method == "POST":
            resp = requests.post(f"{BASE_URL}{path}", json=data, timeout=5)
            
        print(f"  Status: {resp.status_code}")
        
        if resp.status_code == 500:
            print(f"  Error: {resp.text[:200]}")
        elif resp.status_code == 200:
            try:
                data = resp.json()
                print(f"  Response: {json.dumps(data, indent=2)[:200]}...")
            except:
                print(f"  Response: {resp.text[:200]}")
                
    except requests.exceptions.ConnectionError:
        print("  ✗ Connection refused - app not running")
    except requests.exceptions.Timeout:
        print("  ✗ Request timed out")
    except Exception as e:
        print(f"  ✗ Error: {e}")

# Test all endpoints
print("NAS File Doctor Diagnostic")
print("=" * 50)

# Basic endpoints
test_endpoint("Home Page", "GET", "/")
test_endpoint("API Status", "GET", "/api/status")
test_endpoint("Index Stats", "GET", "/api/index/stats")

# Search endpoint
test_endpoint("Search Test", "GET", "/api/search?q=test")

# Browse endpoint  
test_endpoint("Browse Root", "GET", "/api/browse?path=/")
test_endpoint("Browse HDD2", "GET", "/api/browse?path=/HDD2")

# Debug endpoints
test_endpoint("Debug List Root", "GET", "/api/debug/list-root")
test_endpoint("Debug Sample Files", "GET", "/api/debug/sample-files")

print("\n" + "=" * 50)
print("Diagnostic complete")