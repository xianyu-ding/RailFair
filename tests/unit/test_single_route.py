#!/usr/bin/env python3
"""
Test script for single route and single day
Quick test to verify API connection and data retrieval
"""
import os
import sys
import json
import base64
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
project_root = Path(__file__).parent
DEFAULT_ENV_PATH = project_root / ".env"
try:
    load_dotenv(dotenv_path=DEFAULT_ENV_PATH, override=False)
except Exception:
    pass

# Get credentials
email = os.getenv('HSP_EMAIL') or os.getenv('HSP_USERNAME')
password = os.getenv('HSP_PASSWORD')

if not email or not password:
    print("❌ Error: HSP_EMAIL/HSP_USERNAME and HSP_PASSWORD must be set")
    print("\nOptions:")
    print("  1. Set environment variables:")
    print("     export HSP_EMAIL='your_email@example.com'")
    print("     export HSP_PASSWORD='your_password'")
    print("  2. Or add to .env file in project root")
    sys.exit(1)

# Test parameters (can be overridden via command line)
test_route = {
    'from_loc': sys.argv[1] if len(sys.argv) > 1 else 'EUS',
    'to_loc': sys.argv[2] if len(sys.argv) > 2 else 'MAN',
    'from_date': sys.argv[3] if len(sys.argv) > 3 else '2024-10-01',
    'to_date': sys.argv[4] if len(sys.argv) > 4 else '2024-10-01',
    'from_time': sys.argv[5] if len(sys.argv) > 5 else '0600',
    'to_time': sys.argv[6] if len(sys.argv) > 6 else '2200',
    'days': sys.argv[7] if len(sys.argv) > 7 else 'WEEKDAY'
}

print("=" * 70)
print("  Single Route Test - HSP API")
print("=" * 70)
print(f"\nRoute: {test_route['from_loc']} -> {test_route['to_loc']}")
print(f"Date: {test_route['from_date']} to {test_route['to_date']}")
print(f"Time: {test_route['from_time']} - {test_route['to_time']}")
print(f"Days: {test_route['days']}")
print(f"\nCredentials: {email[:3]}*** (masked)")
print()

# API configuration
base_url = "https://hsp-prod.rockshore.net/api/v1"
url = f"{base_url}/serviceMetrics"
timeout = 180

# Prepare request
params = {
    'from_loc': test_route['from_loc'],
    'to_loc': test_route['to_loc'],
    'from_date': test_route['from_date'],
    'to_date': test_route['to_date'],
    'from_time': test_route['from_time'],
    'to_time': test_route['to_time'],
    'days': test_route['days']
}

# Authentication
credentials = f"{email}:{password}"
auth_header = f"Basic {base64.b64encode(credentials.encode()).decode()}"
headers = {
    'Authorization': auth_header,
    'Content-Type': 'application/json'
}

print("🔍 Sending request to HSP API...")
print(f"   URL: {url}")
print(f"   Timeout: {timeout}s")
print()

try:
    # Make request
    response = requests.post(url, json=params, headers=headers, timeout=timeout)
    
    print(f"📡 Response Status: {response.status_code}")
    print()
    
    if response.status_code == 200:
        data = response.json()
        
        # Extract services
        services = data.get('Services', [])
        print(f"✅ Success! Found {len(services)} service(s)")
        print()
        
        if len(services) > 0:
            print("=" * 70)
            print("  First Service Details")
            print("=" * 70)
            
            first_service = services[0]
            
            # Extract serviceAttributesMetrics (according to official API docs)
            attrs = first_service.get('serviceAttributesMetrics', {})
            metrics = first_service.get('Metrics', [])
            
            # Display key information from serviceAttributesMetrics
            print(f"\nOrigin: {attrs.get('origin_location', 'N/A')}")
            print(f"Destination: {attrs.get('destination_location', 'N/A')}")
            print(f"Scheduled Departure (gbtt_ptd): {attrs.get('gbtt_ptd', 'N/A')}")
            print(f"Scheduled Arrival (gbtt_pta): {attrs.get('gbtt_pta', 'N/A')}")
            print(f"TOC Code: {attrs.get('toc_code', 'N/A')}")
            print(f"Matched Services: {attrs.get('matched_services', 'N/A')}")
            
            # Display RIDs if available
            rids = attrs.get('rids', [])
            if rids:
                print(f"\nRIDs ({len(rids)}):")
                for i, rid in enumerate(rids[:5], 1):  # Show first 5
                    print(f"  {i}. {rid}")
                if len(rids) > 5:
                    print(f"  ... and {len(rids) - 5} more")
            else:
                print("\n⚠️  No RIDs found in response")
            
            # Display metrics if available
            if metrics:
                print(f"\nMetrics ({len(metrics)} tolerance values):")
                for metric in metrics[:3]:  # Show first 3
                    tolerance = metric.get('tolerance_value', 'N/A')
                    num_tol = int(metric.get('num_tolerance', 0))
                    num_not_tol = int(metric.get('num_not_tolerance', 0))
                    percent = float(metric.get('percent_tolerance', 0))
                    global_tol = metric.get('global_tolerance', False)
                    print(f"  Tolerance {tolerance}min: {num_tol}/{num_tol + num_not_tol} ({percent:.1f}%) [global: {global_tol}]")
            else:
                print("\n⚠️  No metrics found in response")
            
            print("\n" + "=" * 70)
            print("  Full Response Structure")
            print("=" * 70)
            print("\nTop-level keys:", list(data.keys()))
            if 'header' in data:
                print("\nHeader:", data['header'])
            if services:
                print("\nFirst service keys:", list(first_service.keys()))
                if 'serviceAttributesMetrics' in first_service:
                    print("  serviceAttributesMetrics keys:", list(first_service['serviceAttributesMetrics'].keys()))
                if 'Metrics' in first_service:
                    print(f"  Metrics count: {len(first_service['Metrics'])}")
            
            # Save sample response
            sample_file = Path("data/raw/hsp") / f"test_{test_route['from_loc']}_{test_route['to_loc']}_{test_route['from_date']}.json"
            sample_file.parent.mkdir(parents=True, exist_ok=True)
            with open(sample_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"\n💾 Sample response saved to: {sample_file}")
            
        else:
            print("⚠️  No services found for this route/date combination")
            print("\nPossible reasons:")
            print("  - No services run on this day type")
            print("  - Date is too far in the future (HSP only has historical data)")
            print("  - Date is before historical data availability (typically 2016+)")
            print("  - Route combination doesn't exist")
            print("\n💡 Tip: Try a date in the past, e.g., 2024-10-01")
        
        print("\n" + "=" * 70)
        print("  Test Summary")
        print("=" * 70)
        print(f"✅ API Connection: Working")
        print(f"✅ Authentication: Success")
        print(f"✅ Data Retrieval: {len(services)} service(s) returned")
        print(f"✅ Response Time: {response.elapsed.total_seconds():.2f}s")
        
    else:
        print(f"❌ API Error: {response.status_code}")
        print(f"\nResponse body:")
        try:
            error_data = response.json()
            print(json.dumps(error_data, indent=2))
        except:
            print(response.text[:500])  # First 500 chars
        
        print("\n" + "=" * 70)
        print("  Test Summary")
        print("=" * 70)
        print(f"✅ API Connection: Working")
        print(f"✅ Authentication: Success")
        print(f"❌ Data Retrieval: Failed (Status {response.status_code})")

except requests.exceptions.Timeout as e:
    print(f"❌ Request Timeout: {e}")
    print(f"\nThe request took longer than {timeout} seconds.")
    print("Try:")
    print("  - Reducing the date range (use single day)")
    print("  - Reducing the time window")
    print("  - Using a different day type")

except requests.exceptions.ConnectionError as e:
    print(f"❌ Connection Error: {e}")
    print("\nCheck your internet connection and API endpoint.")

except Exception as e:
    print(f"❌ Unexpected Error: {e}")
    import traceback
    traceback.print_exc()

print()

