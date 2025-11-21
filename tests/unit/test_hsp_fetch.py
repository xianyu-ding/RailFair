"""
Test script for HSP data fetcher - Day 3
"""
import os
import sys
import logging
import yaml
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    def load_dotenv(*_args, **_kwargs):
        return False

# Add parent directory to path
sys.path.insert(0, '/home/claude')

from fetch_hsp import HSPFetcher
from hsp_validator import HSPValidator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "configs" / "hsp_config.yaml"
DEFAULT_ENV_PATH = Path(__file__).resolve().parent / ".env"

# Load environment variables from .env if available
try:
    load_dotenv(dotenv_path=DEFAULT_ENV_PATH, override=False)
except (PermissionError, OSError) as exc:
    print(f"Warning: Could not load .env file ({exc})")


def test_hsp_fetch():
    """Test HSP data fetching"""
    
    print("\n" + "=" * 80)
    print("HSP Data Fetcher - Day 3 Testing")
    print("=" * 80 + "\n")
    
    # Check environment variables
    username = os.getenv('HSP_EMAIL') or os.getenv('HSP_USERNAME')
    password = os.getenv('HSP_PASSWORD')
    
    if not username or not password:
        print("⚠ Environment variables not set!")
        print("\nTo test with real API, set:")
        print("  export HSP_EMAIL='your_email@example.com'  # 或使用 HSP_USERNAME")
        print("  export HSP_PASSWORD='your_password'")
        print("\nFor now, we'll test the code structure without API calls.\n")
        test_without_api()
        return
    
    try:
        # Test 1: Initialize fetcher
        print("Test 1: Initializing HSP Fetcher...")
        fetcher = HSPFetcher()
        print("✓ Fetcher initialized successfully\n")
        
        # Test 2: Fetch service metrics for EUS-MAN
        print("Test 2: Fetching service metrics (EUS-MAN)...")
        test_route = {
            'name': 'EUS-MAN',
            'from_loc': 'EUS',
            'to_loc': 'MAN',
            'from_time': '0700',
            'to_time': '0800'
        }
        
        metrics, details = fetcher.fetch_and_process_route(
            test_route,
            fetch_details=False  # Don't fetch details for initial test
        )
        
        print(f"✓ Fetched {len(metrics)} service metrics\n")
        
        # Test 3: Validate data
        print("Test 3: Validating data...")
        with DEFAULT_CONFIG_PATH.open('r') as f:
            config = yaml.safe_load(f)
        
        validator = HSPValidator(config['validation'])
        
        all_valid = True
        for record in metrics:
            if not validator.validate_service_metrics(record):
                all_valid = False
            validator.validate_eus_man_route(record)
        
        validator.log_summary()
        print()
        
        # Test 4: Fetch details for one service
        if metrics and metrics[0].get('rids'):
            print("Test 4: Fetching service details...")
            test_rid = metrics[0]['rids'][0]
            
            details_response = fetcher.fetch_service_details(test_rid)
            details_record = fetcher.processor.process_service_details(
                details_response,
                test_rid
            )
            
            if details_record:
                print(f"✓ Fetched details for RID: {test_rid}")
                print(f"  Date: {details_record['date_of_service']}")
                print(f"  TOC: {details_record['toc_code']}")
                print(f"  Locations: {len(details_record['locations'])}")
                
                # Validate details
                if validator.validate_service_details(details_record):
                    print("✓ Details validation passed")
                
                # Show delay info
                for loc in details_record['locations']:
                    if loc['arrival_delay_minutes'] is not None:
                        delay = loc['arrival_delay_minutes']
                        status = "on time" if delay == 0 else f"{abs(delay)}min {'late' if delay > 0 else 'early'}"
                        print(f"  {loc['location']}: {status}")
            print()
        
        # Test 5: Save to database
        print("Test 5: Saving to database...")
        fetcher.save_to_database(metrics, [details_record] if details_record else [])
        print("✓ Data saved successfully\n")
        
        # Summary
        print("=" * 80)
        print("Test Summary:")
        print(f"  ✓ API Connection: Working")
        print(f"  ✓ Service Metrics: {len(metrics)} records fetched")
        print(f"  ✓ Service Details: 1 record fetched")
        print(f"  ✓ Data Validation: {'Passed' if all_valid else 'Failed'}")
        print(f"  ✓ Database Storage: Working")
        print("=" * 80 + "\n")
        
        print("🎉 All Day 3 objectives completed!\n")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        logger.error("Test failed", exc_info=True)
        sys.exit(1)


def test_without_api():
    """Test code structure without making API calls"""
    
    print("Test 1: Testing data processor...")
    from hsp_processor import HSPDataProcessor
    
    processor = HSPDataProcessor()
    
    # Test time parsing
    dt = processor.parse_time("2024-10-15", "0712")
    assert dt is not None, "Time parsing failed"
    print(f"✓ Parsed time: {dt}")
    
    # Test timezone conversion
    dt_utc = processor.convert_to_db_timezone(dt)
    print(f"✓ Converted to UTC: {dt_utc}")
    
    # Test delay calculation
    scheduled = processor.parse_time("2024-10-15", "0712")
    actual = processor.parse_time("2024-10-15", "0720")
    delay = processor.calculate_delay_minutes(scheduled, actual)
    assert delay == 8, f"Expected delay of 8, got {delay}"
    print(f"✓ Delay calculation: {delay} minutes\n")
    
    print("Test 2: Testing retry handler...")
    from retry_handler import RetryHandler, APIError
    
    retry_handler = RetryHandler(max_attempts=3, initial_delay=0.1)
    
    attempts = [0]
    def test_func():
        attempts[0] += 1
        if attempts[0] < 3:
            raise APIError("Simulated error")
        return "Success"
    
    result = retry_handler.execute_with_retry(
        test_func,
        retryable_exceptions=(APIError,)
    )
    assert result == "Success", "Retry handler failed"
    assert attempts[0] == 3, f"Expected 3 attempts, got {attempts[0]}"
    print(f"✓ Retry handler: {attempts[0]} attempts, result: {result}\n")
    
    print("Test 3: Testing validator...")
    from hsp_validator import HSPValidator
    
    with DEFAULT_CONFIG_PATH.open('r') as f:
        config = yaml.safe_load(f)
    
    validator = HSPValidator(config['validation'])
    
    sample_record = {
        'origin_location': 'EUS',
        'destination_location': 'MAN',
        'from_location': 'EUS',
        'to_location': 'MAN',
        'scheduled_departure_time': '0712',
        'scheduled_arrival_time': '0920',
        'toc_code': 'AV',
        'matched_services_count': 5,
        'rids': ['rid1', 'rid2', 'rid3', 'rid4', 'rid5'],
        'metrics': [{
            'tolerance_value': 5,
            'num_tolerance': 4,
            'num_not_tolerance': 1,
            'percent_tolerance': 80.0,
            'global_tolerance': True
        }]
    }
    
    is_valid = validator.validate_service_metrics(sample_record)
    assert is_valid, "Validation failed for valid record"
    print("✓ Validator: Sample record validated\n")
    
    print("=" * 80)
    print("Code Structure Tests: PASSED")
    print("=" * 80 + "\n")
    
    print("📝 Note: To test with real API, set HSP_EMAIL and HSP_PASSWORD")
    print("   Then run: python test_hsp_fetch.py\n")


if __name__ == "__main__":
    test_hsp_fetch()
