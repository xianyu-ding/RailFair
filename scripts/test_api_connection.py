"""Test all National Rail API connections."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import Config, logger
from src.data_collection import HSPClient


def print_header(text: str):
    """Print formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def test_configuration():
    """Test configuration loading."""
    print_header("Configuration Test")
    
    summary = Config.get_summary()
    print(f"\n📁 Project Root: {summary['project_root']}")
    print(f"📊 Data Directory: {summary['data_dir']}")
    print(f"📝 Log Level: {summary['log_level']}")
    
    print("\n🔑 Credentials Status:")
    for service, status in summary['credentials_status'].items():
        status_icon = "✅" if status else "❌"
        print(f"  {status_icon} {service}: {'Configured' if status else 'Missing'}")
    
    return all(summary['credentials_status'].values())


def test_hsp_api():
    """Test Historical Service Performance API."""
    print_header("HSP API Connection Test")
    
    if not Config.HSP_USERNAME or not Config.HSP_PASSWORD:
        print("❌ HSP credentials not configured in .env file")
        print("   Please set HSP_USERNAME and HSP_PASSWORD")
        return False
    
    try:
        client = HSPClient(timeout=60)
        print(f"\n🔗 Connecting to: {Config.HSP_SERVICE_METRICS_URL}")
        print(f"👤 Username: {Config.HSP_USERNAME}")
        
        success = client.test_connection()
        
        if success:
            print("\n✅ HSP API connection successful!")
            print("\n📊 Attempting to fetch sample data...")
            
            # Try to get a small sample
            from datetime import datetime, timedelta
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            
            data = client.get_service_metrics(
                from_loc="PAD",
                to_loc="OXF",
                from_date=yesterday,
                to_date=yesterday,
                from_time="0800",
                to_time="0900",
                days="WEEKDAY"
            )
            
            if data:
                services = data.get("Services", [])
                print(f"✅ Retrieved {len(services)} service records")
                
                if services:
                    sample = services[0]
                    print(f"\n📋 Sample service:")
                    print(f"   Service ID: {sample.get('serviceAttributesMetrics', {}).get('rids', 'N/A')}")
                    print(f"   Origin: {sample.get('serviceAttributesMetrics', {}).get('origin_location', 'N/A')}")
                    print(f"   Destination: {sample.get('serviceAttributesMetrics', {}).get('destination_location', 'N/A')}")
            
            return True
        else:
            print("\n❌ HSP API connection failed")
            return False
            
    except Exception as e:
        print(f"\n❌ Error testing HSP API: {e}")
        logger.exception("HSP API test error")
        return False


def test_darwin_connectivity():
    """Test Darwin API configuration (connection test requires STOMP)."""
    print_header("Darwin API Configuration Check")
    
    if not Config.DARWIN_USERNAME or not Config.DARWIN_PASSWORD:
        print("❌ Darwin credentials not configured in .env file")
        print("   Please set DARWIN_USERNAME and DARWIN_PASSWORD")
        return False
    
    print(f"🔗 Darwin Host: {Config.DARWIN_MESSAGING_HOST}")
    print(f"🔌 STOMP Port: {Config.DARWIN_STOMP_PORT}")
    print(f"📡 Live Feed Topic: {Config.DARWIN_LIVE_FEED_TOPIC}")
    print(f"👤 Username: {Config.DARWIN_USERNAME}")
    
    print("\n⚠️  Note: Full Darwin Push Port connection test requires STOMP client")
    print("   This will be implemented in data collection pipeline")
    
    return True


def test_knowledgebase_api():
    """Test Knowledgebase API configuration."""
    print_header("Knowledgebase API Configuration Check")
    
    if not Config.KB_USERNAME or not Config.KB_PASSWORD:
        print("❌ Knowledgebase credentials not configured in .env file")
        print("   Please set KB_USERNAME and KB_PASSWORD")
        return False
    
    print(f"🔗 KB API URL: {Config.KB_API_BASE_URL}")
    print(f"👤 Username: {Config.KB_USERNAME}")
    
    print("\n⚠️  Note: Knowledgebase API client will be implemented in Day 2")
    
    return True


def main():
    """Run all API tests."""
    print("\n🚂 UK Rail Delay Predictor - API Connection Tests")
    print("=" * 60)
    
    results = {
        "Configuration": test_configuration(),
        "HSP API": test_hsp_api(),
        "Darwin API Config": test_darwin_connectivity(),
        "Knowledgebase API Config": test_knowledgebase_api()
    }
    
    # Summary
    print_header("Test Summary")
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:12} {test_name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 All API connection tests passed!")
        print("   You're ready to start data collection.")
    else:
        print("\n⚠️  Some tests failed. Please check:")
        print("   1. Your .env file has all required credentials")
        print("   2. Your network can reach National Rail APIs")
        print("   3. Your credentials are correct and active")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
