#!/usr/bin/env python3
"""
HSP Batch Data Collection Script
Purpose: Collect historical HSP data across multiple routes and time periods
Supports: Phase 1 (Winter), Phase 2 (Recent), Phase 3 (Summer)
"""

import os
import sys
import json
import time
import sqlite3
import logging
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import yaml
import argparse

logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env if present
DEFAULT_ENV_PATH = project_root / ".env"
try:
    from dotenv import load_dotenv
    try:
        load_dotenv(dotenv_path=DEFAULT_ENV_PATH, override=False)
    except (PermissionError, OSError) as exc:
        print(f"Warning: Could not load .env file ({exc})")
except ImportError:
    # dotenv is optional
    pass

try:
    from hsp_processor import HSPDataProcessor
    from hsp_validator import HSPValidator
    from retry_handler import with_retry, APIError, NetworkError
except ImportError as e:
    print(f"⚠️  Warning: Could not import required modules: {e}")
    print("Make sure hsp_processor.py, hsp_validator.py, and retry_handler.py are in the same directory")
    sys.exit(1)


class ProgressTracker:
    """Track and persist collection progress"""
    
    def __init__(self, progress_file: str):
        self.progress_file = progress_file
        self.progress = self._load_progress()
        
    def _load_progress(self) -> Dict:
        """Load progress from file"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  Could not load progress file: {e}")
        
        return {
            'started_at': None,
            'last_updated': None,
            'completed_routes': [],
            'failed_routes': [],
            'total_records': 0,
            'phase': None
        }
    
    def save_progress(self):
        """Save progress to file"""
        self.progress['last_updated'] = datetime.now().isoformat()
        os.makedirs(os.path.dirname(self.progress_file), exist_ok=True)
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, indent=2, fp=f)
    
    def mark_route_started(self, route_name: str):
        """Mark a route as started"""
        if self.progress['started_at'] is None:
            self.progress['started_at'] = datetime.now().isoformat()
        self.save_progress()
    
    def mark_route_completed(self, route_name: str, records_count: int):
        """Mark a route as completed"""
        if route_name not in self.progress['completed_routes']:
            self.progress['completed_routes'].append(route_name)
        self.progress['total_records'] += records_count
        self.save_progress()
    
    def mark_route_failed(self, route_name: str, error: str):
        """Mark a route as failed"""
        self.progress['failed_routes'].append({
            'route': route_name,
            'error': error,
            'timestamp': datetime.now().isoformat()
        })
        self.save_progress()
    
    def is_route_completed(self, route_name: str) -> bool:
        """Check if route is already completed"""
        return route_name in self.progress['completed_routes']
    
    def get_summary(self) -> Dict:
        """Get progress summary"""
        return {
            'completed': len(self.progress['completed_routes']),
            'failed': len(self.progress['failed_routes']),
            'total_records': self.progress['total_records'],
            'started_at': self.progress['started_at'],
            'last_updated': self.progress['last_updated']
        }


class HSPBatchCollector:
    """Batch collector for multiple routes and time periods"""
    
    def __init__(self, config_file: str, skip_completed: bool = True, 
                 date_from: Optional[str] = None, date_to: Optional[str] = None):
        """Initialize batch collector
        
        Args:
            config_file: Path to YAML configuration file
            skip_completed: Skip routes that are already completed
            date_from: Override start date (YYYY-MM-DD format)
            date_to: Override end date (YYYY-MM-DD format)
        """
        self.config = self._load_config(config_file)
        self.skip_completed = skip_completed
        
        # Override date range if provided
        if date_from:
            self.config['data_collection']['from_date'] = date_from
        if date_to:
            self.config['data_collection']['to_date'] = date_to
        
        # Initialize components
        # Get timezone config or use defaults
        timezone_config = self.config.get('timezone', {})
        api_tz = timezone_config.get('api_timezone', 'Europe/London')
        db_tz = timezone_config.get('database_timezone', 'UTC')
        self.processor = HSPDataProcessor(api_timezone=api_tz, database_timezone=db_tz)
        
        # Get validation config from main config or use defaults
        validation_config = self.config.get('validation', {
            'required_fields': {
                'service_metrics': ['origin_location', 'destination_location', 'toc_code'],
                'service_details': ['rid', 'date_of_service', 'toc_code']
            }
        })
        self.validator = HSPValidator(validation_config)
        
        # Database path for saving
        self.db_path = self.config['database']['path']
        
        # Progress tracking
        progress_file = self.config['output'].get('progress_file', 'data/progress.json')
        self.progress = ProgressTracker(progress_file)
        
        # Statistics
        self.stats = {
            'routes_processed': 0,
            'routes_failed': 0,
            'total_api_calls': 0,
            'total_records': 0,
            'total_time': 0,
            'start_time': None,
            'end_time': None
        }
        
        # Get credentials from environment or config
        self.email = os.getenv('HSP_EMAIL') or os.getenv('HSP_USERNAME')
        self.password = os.getenv('HSP_PASSWORD')
        
        # Fallback to config if not in environment
        if not self.email:
            self.email = self.config.get('auth', {}).get('username') or self.config.get('auth', {}).get('email')
        if not self.password:
            self.password = self.config.get('auth', {}).get('password')
        
        if not self.email or not self.password:
            error_msg = (
                "HSP_EMAIL/HSP_USERNAME and HSP_PASSWORD must be set.\n"
                "Options:\n"
                "  1. Set environment variables: export HSP_EMAIL='...' && export HSP_PASSWORD='...'\n"
                "  2. Add to .env file in project root\n"
                "  3. Add to config file under 'auth' section"
            )
            raise ValueError(error_msg)
        
        # Rate limiting - configurable from config file
        self.last_request_time = 0
        # Get request interval from config, with defaults
        request_interval_config = self.config.get('api', {}).get('request_interval', {})
        if isinstance(request_interval_config, dict):
            self.min_request_interval = request_interval_config.get('min', 3.0)
            self.max_request_interval = request_interval_config.get('max', 5.0)
        else:
            # Fallback: use old delay_between_requests if present, or defaults
            old_delay = self.config.get('data_collection', {}).get('delay_between_requests', 3.0)
            self.min_request_interval = old_delay
            self.max_request_interval = old_delay * 1.5  # 1.5x for range
        
        # Ensure minimum is at least 1 second for safety
        if self.min_request_interval < 1.0:
            self.min_request_interval = 1.0
        if self.max_request_interval < self.min_request_interval:
            self.max_request_interval = self.min_request_interval + 1.0
        
        # API configuration
        self.base_url = self.config['api']['base_url']
        self.timeout = self.config['api'].get('timeout', 180)
        if self.timeout < 120:
            self.timeout = 120  # Minimum 120 seconds
        
        print(f"✅ Initialized HSP Batch Collector")
        print(f"   Config: {config_file}")
        print(f"   Database: {self.config['database']['path']}")
        print(f"   Routes: {len(self.config['routes'])}")
        print(f"   Date Range: {self.config['data_collection']['from_date']} to {self.config['data_collection']['to_date']}")
        print(f"   Days: {self.config['data_collection']['days']}")
        print(f"   Request interval: {self.min_request_interval}-{self.max_request_interval}s")
        print(f"   Timeout: {self.timeout}s")
    
    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from YAML file
        
        Tries multiple locations:
        1. Direct path (if absolute or relative path provided)
        2. configs/ directory
        3. Current directory
        """
        config_path = Path(config_file)
        
        # If not absolute and doesn't exist, try configs/ directory
        if not config_path.is_absolute() and not config_path.exists():
            configs_dir = project_root / "configs" / config_path.name
            if configs_dir.exists():
                config_path = configs_dir
        
        # If still doesn't exist, try current directory
        if not config_path.exists():
            current_dir = Path.cwd() / config_path.name
            if current_dir.exists():
                config_path = current_dir
        
        if not config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {config_file}\n"
                f"Tried: {config_file}, {project_root / 'configs' / config_path.name}, {Path.cwd() / config_path.name}"
            )
        
        with config_path.open('r') as f:
            return yaml.safe_load(f)
    
    def _initialize_database(self):
        """Initialize database tables if needed"""
        db_path = self.config['database']['path']
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create tables if they don't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hsp_service_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                origin TEXT NOT NULL,
                destination TEXT NOT NULL,
                scheduled_departure TEXT,
                scheduled_arrival TEXT,
                toc_code TEXT NOT NULL,
                matched_services_count INTEGER,
                fetch_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(origin, destination, scheduled_departure, scheduled_arrival, toc_code)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hsp_service_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rid TEXT NOT NULL,
                date_of_service TEXT NOT NULL,
                toc_code TEXT NOT NULL,
                location TEXT NOT NULL,
                scheduled_departure TIMESTAMP,
                scheduled_arrival TIMESTAMP,
                actual_departure TIMESTAMP,
                actual_arrival TIMESTAMP,
                departure_delay_minutes INTEGER,
                arrival_delay_minutes INTEGER,
                cancellation_reason TEXT,
                fetch_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(rid, location)
            )
        """)
        
        conn.commit()
        conn.close()
        
        print(f"✅ Database initialized: {db_path}")
    
    def _get_auth_header(self) -> str:
        """
        Create Basic Authentication header
        
        Returns:
            Base64 encoded credentials
        """
        import base64
        credentials = f"{self.email}:{self.password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"
    
    def _rate_limit(self):
        """Implement rate limiting between requests (configurable random interval)"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        # Random interval between min and max (configurable)
        required_interval = random.uniform(self.min_request_interval, self.max_request_interval)
        
        if time_since_last < required_interval:
            sleep_time = required_interval - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(
        self,
        endpoint: str,
        payload: Dict
    ) -> Dict:
        """
        Make HTTP request to HSP API with error handling and retry logic
        
        Args:
            endpoint: API endpoint path
            payload: JSON payload
            
        Returns:
            API response as dict
            
        Raises:
            Various exceptions based on error type
        """
        import requests
        from retry_handler import classify_http_error, RetryHandler, APIError, NetworkError, RateLimitError
        
        url = f"{self.base_url}{endpoint}"
        
        headers = {
            'Authorization': self._get_auth_header(),
            'Content-Type': 'application/json'
        }
        
        # Rate limiting (1-3 seconds between requests)
        self._rate_limit()
        
        logger.debug(f"Making request to {url} with payload: {payload}")
        
        # Use retry handler for automatic retries
        retry_config = self.config.get('retry', {})
        retry_handler = RetryHandler(
            max_attempts=retry_config.get('max_attempts', 3),
            initial_delay=retry_config.get('initial_delay', 1.0),
            max_delay=retry_config.get('max_delay', 30.0),
            exponential_base=retry_config.get('backoff_multiplier', 2.0),  # Use exponential_base, not backoff_multiplier
            jitter=retry_config.get('jitter', True)
        )
        
        def _do_request():
            try:
                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout
                )
                
                # Check status code
                if response.status_code == 200:
                    logger.debug(f"Request successful: {response.status_code}")
                    return response.json()
                else:
                    # Classify and raise appropriate error
                    error = classify_http_error(response.status_code, response.text)
                    logger.error(f"API error: {response.status_code} - {response.text[:200]}")  # Truncate long HTML
                    raise error
            
            except requests.exceptions.Timeout as e:
                logger.error(f"Request timeout: {e}")
                raise NetworkError(f"Request timeout: {e}")
            
            except requests.exceptions.ConnectionError as e:
                logger.error(f"Connection error: {e}")
                raise NetworkError(f"Connection error: {e}")
            
            except requests.exceptions.RequestException as e:
                logger.error(f"Request exception: {e}")
                raise APIError(f"Request exception: {e}")
        
        # Execute with retry (use execute_with_retry method)
        return retry_handler.execute_with_retry(_do_request, retryable_exceptions=(APIError, NetworkError, RateLimitError))
    
    def _save_service_metrics(self, record: Dict):
        """Save service metrics record to database"""
        db_path = self.config['database']['path']
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO hsp_service_metrics
                (origin, destination, scheduled_departure, scheduled_arrival, 
                 toc_code, matched_services_count, fetch_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get('origin_location'),
                record.get('destination_location'),
                record.get('scheduled_departure_time'),
                record.get('scheduled_arrival_time'),
                record.get('toc_code'),
                record.get('matched_services_count'),
                datetime.now().isoformat()
            ))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error saving service metrics: {e}")
            raise
        finally:
            conn.close()
    
    def _save_service_details(self, record: Dict):
        """Save service details record to database"""
        db_path = self.config['database']['path']
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            locations = record.get('locations', [])
            for location in locations:
                cursor.execute("""
                    INSERT OR REPLACE INTO hsp_service_details
                    (rid, date_of_service, toc_code, location,
                     scheduled_departure, scheduled_arrival,
                     actual_departure, actual_arrival,
                     departure_delay_minutes, arrival_delay_minutes,
                     cancellation_reason, fetch_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.get('rid'),
                    record.get('date_of_service'),
                    record.get('toc_code'),
                    location.get('location'),
                    location.get('scheduled_departure'),
                    location.get('scheduled_arrival'),
                    location.get('actual_departure'),
                    location.get('actual_arrival'),
                    location.get('departure_delay_minutes'),
                    location.get('arrival_delay_minutes'),
                    location.get('cancellation_reason'),
                    datetime.now().isoformat()
                ))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error saving service details: {e}")
            raise
        finally:
            conn.close()
    
    def _is_task_completed(self, route: Dict, chunk_from_date: str, 
                           chunk_to_date: str, day_type: str) -> bool:
        """Check if a task has already been completed by checking database
        
        This checks if we have data for the specific route AND specific date chunk.
        We need to check both the route and the date range to avoid false positives.
        
        Args:
            route: Route configuration dict
            chunk_from_date: Start date of chunk (YYYY-MM-DD)
            chunk_to_date: End date of chunk (YYYY-MM-DD)
            day_type: Day type (WEEKDAY, SATURDAY, or SUNDAY) - not used in check
        
        Returns:
            True if task data already exists in database, False otherwise
        """
        db_path = self.config['database']['path']
        if not os.path.exists(db_path):
            return False
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            origin = route['from_loc']
            destination = route['to_loc']
            
            # Strategy: Check if we have data for THIS specific route AND THIS specific date chunk
            # We need to check both conditions to avoid false positives
            
            # Step 1: Check if we have service_metrics for this route AND date range
            # This is the most reliable check - metrics are linked to routes
            cursor.execute("""
                SELECT COUNT(*) 
                FROM hsp_service_metrics
                WHERE origin = ? AND destination = ?
                AND DATE(fetch_timestamp) BETWEEN ? AND ?
                AND fetch_timestamp IS NOT NULL
            """, (origin, destination, chunk_from_date, chunk_to_date))
            
            metrics_in_chunk = cursor.fetchone()[0]
            
            # If we have metrics for this route in this date chunk, task is likely done
            if metrics_in_chunk >= 3:  # At least 3 records indicates some coverage
                return True
            
            # Step 2: Check if we have service_details for this date chunk
            # (This is a secondary check - details aren't directly linked to routes)
            cursor.execute("""
                SELECT COUNT(DISTINCT date_of_service) 
                FROM hsp_service_details
                WHERE date_of_service BETWEEN ? AND ?
            """, (chunk_from_date, chunk_to_date))
            
            date_count_in_chunk = cursor.fetchone()[0]
            
            # Step 3: Check if we have service_metrics for this route (any date)
            cursor.execute("""
                SELECT COUNT(*) 
                FROM hsp_service_metrics
                WHERE origin = ? AND destination = ?
                AND fetch_timestamp IS NOT NULL
            """, (origin, destination))
            
            metrics_total = cursor.fetchone()[0]
            
            # If we have:
            # - At least 2 unique dates in this chunk (indicating some coverage)
            # - AND this route has metrics (indicating route was processed)
            # Then likely this task was already processed
            # BUT only if we have some metrics in the chunk (to avoid false positives)
            if date_count_in_chunk >= 2 and metrics_total > 0 and metrics_in_chunk > 0:
                return True
            
            # Don't use the fallback (metrics_total >= 10) because it would skip
            # all tasks for routes that have any data, even if the specific chunk is missing
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking task completion: {e}")
            return False
        finally:
            conn.close()
    
    def _fetch_single_chunk(
        self, 
        route: Dict, 
        chunk_from_date: str, 
        chunk_to_date: str, 
        day_type: str
    ) -> tuple[int, str]:
        """Fetch data for a single route, single date chunk, single day type
        
        This is the minimal unit: one route, one date chunk (≤7 days), one day type.
        Uses _make_request() method for consistent request handling.
        
        Args:
            route: Route configuration dict
            chunk_from_date: Start date of chunk (YYYY-MM-DD)
            chunk_to_date: End date of chunk (YYYY-MM-DD)
            day_type: Day type (WEEKDAY, SATURDAY, or SUNDAY)
        
        Returns:
            Tuple of (number of records collected, status)
            Status can be: 'skipped', 'completed', 'no_data', 'error'
        """
        route_name = route['name']
        
        # Check if task is already completed
        if self._is_task_completed(route, chunk_from_date, chunk_to_date, day_type):
            print(f"\n⏭️  Skipping: {route_name} | {day_type} | {chunk_from_date} to {chunk_to_date}")
            print(f"   (Data already exists in database)")
            return (0, 'skipped')  # Return 0 with 'skipped' status
        
        print(f"\n🔍 Processing: {route_name} | {day_type} | {chunk_from_date} to {chunk_to_date}")
        
        payload = {
            'from_loc': route['from_loc'],
            'to_loc': route['to_loc'],
            'from_date': chunk_from_date,
            'to_date': chunk_to_date,
            'from_time': route.get('from_time', self.config['data_collection']['from_time']),
            'to_time': route.get('to_time', self.config['data_collection']['to_time']),
            'days': day_type
        }
        
        try:
            # Use _make_request() method (similar to fetch_hsp.py)
            # This handles rate limiting (1-3 seconds) and error handling
            data = self._make_request('/serviceMetrics', payload)
            
            services = data.get('Services', [])
            if not services:
                print(f"   ⚠️  No services found")
                return (0, 'no_data')  # No data but task completed
            
            print(f"   ✅ Found {len(services)} services")
            
            # Process and save metrics immediately (one chunk at a time)
            records_saved = 0
            
            try:
                # Process service metrics (processor expects full API response)
                processed_records = self.processor.process_service_metrics(data)
                
                # Process each record from the response
                for processed_metrics in processed_records:
                    try:
                        # Validate
                        is_valid, errors = self.validator.validate_service_metrics(processed_metrics)
                        if not is_valid:
                            logger.debug(f"Validation failed: {errors}")
                            continue
                        
                        # Save to database
                        self._save_service_metrics(processed_metrics)
                        records_saved += 1
                        
                        # Fetch service details if RID available
                        rids = processed_metrics.get('rids', [])
                        if rids:
                            rid = rids[0]  # Use first RID
                            # Rate limiting is handled by _make_request()
                            details_response = self._fetch_service_details(rid)
                            if details_response:
                                # Process service details (processor expects full API response)
                                processed_detail = self.processor.process_service_details(details_response, rid)
                                if processed_detail:
                                    is_valid, errors = self.validator.validate_service_details(processed_detail)
                                    if is_valid:
                                        self._save_service_details(processed_detail)
                        
                    except Exception as e:
                        logger.warning(f"Error processing record: {e}")
                        continue
                
            except Exception as e:
                logger.warning(f"Error processing response: {e}")
                return (0, 'error')  # Error during processing
            
            print(f"   ✅ Saved {records_saved} records")
            return (records_saved, 'completed')
    
        except Exception as e:
            print(f"   ❌ Error: {e}")
            raise
    
    def _fetch_service_details(self, rid: str) -> Optional[Dict]:
        """Fetch service details for a given RID (using _make_request like fetch_hsp.py)"""
        try:
            payload = {'rid': rid}
            # Use _make_request() method (handles rate limiting and error handling)
            data = self._make_request('/serviceDetails', payload)
            # Return full response for processor (processor expects serviceAttributesDetails)
            return data
        except Exception as e:
            logger.warning(f"Error fetching service details for RID {rid}: {e}")
            return None
    
    def run_phase(self, phase_name: str = None):
        """Run batch collection for all routes in the phase
        
        Args:
            phase_name: Optional phase name for logging
        """
        self.stats['start_time'] = datetime.now()
        
        if phase_name:
            print(f"\n🚀 Starting {phase_name}")
            self.progress.progress['phase'] = phase_name
        
        # Initialize database
        self._initialize_database()
        
        # Get routes
        routes = self.config['routes']
        total_routes = len(routes)
        
        print(f"\n📊 Collection Plan:")
        print(f"   Total routes: {total_routes}")
        print(f"   Date range: {self.config['data_collection']['from_date']} to {self.config['data_collection']['to_date']}")
        print(f"   Skip completed: {self.skip_completed}")
        
        # Check for already completed routes
        if self.skip_completed:
            completed = [r for r in routes if self.progress.is_route_completed(r['name'])]
            if completed:
                print(f"\n✅ {len(completed)} routes already completed, will skip:")
                for r in completed:
                    print(f"   - {r['name']}")
        
        # Parse days parameter - HSP API only accepts single values: WEEKDAY, SATURDAY, or SUNDAY
        days_config = self.config['data_collection']['days']
        if ',' in days_config:
            # Split comma-separated values and process each separately
            day_types_raw = [d.strip() for d in days_config.split(',')]
        else:
            day_types_raw = [days_config]
        
        # Map WEEKEND to SATURDAY and SUNDAY
        day_types = []
        for day_type in day_types_raw:
            if day_type.upper() == 'WEEKEND':
                day_types.extend(['SATURDAY', 'SUNDAY'])
            else:
                day_types.append(day_type.upper())
        
        # Remove duplicates while preserving order
        seen = set()
        day_types = [d for d in day_types if d not in seen and not seen.add(d)]
        
        # Validate day types
        valid_days = ['WEEKDAY', 'SATURDAY', 'SUNDAY']
        day_types = [d for d in day_types if d in valid_days]
        
        # Split date range into ≤7 day chunks
        from_date = self.config['data_collection']['from_date']
        to_date = self.config['data_collection']['to_date']
        date_chunks = split_date_range(from_date, to_date, chunk_days=7)
        
        # Generate all combinations: route × date_chunk × day_type
        # Process one combination at a time
        total_combinations = len(routes) * len(date_chunks) * len(day_types)
        current_combination = 0
        
        print(f"\n📊 Collection Plan:")
        print(f"   Routes: {len(routes)}")
        print(f"   Date chunks: {len(date_chunks)} (≤7 days each)")
        print(f"   Day types: {len(day_types)}")
        print(f"   Total combinations: {total_combinations}")
        print(f"   Request interval: {self.min_request_interval}-{self.max_request_interval} seconds")
        print(f"   Skip completed tasks: Yes (checks database)")
        print(f"   Started: {datetime.now().isoformat()}")
        print("")
        sys.stdout.flush()  # Ensure output is written immediately
        
        # Track task completion per route
        route_task_counts = {}  # {route_name: {'total': X, 'completed': Y, 'skipped': Z, 'failed': W}}
        for route in routes:
            route_name = route['name']
            # Calculate total tasks for this route
            total_tasks_per_route = len(date_chunks) * len(day_types)
            route_task_counts[route_name] = {
                'total': total_tasks_per_route,
                'completed': 0,
                'skipped': 0,
                'failed': 0
            }
        
        # Process one combination at a time
        for route in routes:
            route_name = route['name']
            
            for chunk_from_date, chunk_to_date in date_chunks:
                for day_type in day_types:
                    current_combination += 1
                    
                    # Create unique task ID for progress tracking
                    task_id = f"{route_name}|{chunk_from_date}|{chunk_to_date}|{day_type}"
                    
                    print(f"\n{'='*70}")
                    print(f"Task {current_combination}/{total_combinations}: {task_id}")
                    print(f"{'='*70}")
                    sys.stdout.flush()  # Ensure output is written immediately
                    
                    try:
                        # Fetch single chunk (one route, one date chunk, one day type)
                        start_time = time.time()
                        records_count, task_status = self._fetch_single_chunk(
                            route, 
                            chunk_from_date, 
                            chunk_to_date, 
                            day_type
                        )
                        elapsed = time.time() - start_time
                        
                        # Update statistics
                        self.stats['total_records'] += records_count
                        self.stats['total_time'] += elapsed
                        if task_status != 'skipped':
                            self.stats['total_api_calls'] += 1
                        
                        # Track task completion based on status
                        if task_status == 'skipped':
                            route_task_counts[route_name]['skipped'] += 1
                            print(f"⏭️  Task skipped (data already exists)")
                        elif task_status == 'completed':
                            route_task_counts[route_name]['completed'] += 1
                            print(f"✅ Task completed in {elapsed:.1f}s ({records_count} records)")
                        elif task_status == 'no_data':
                            route_task_counts[route_name]['completed'] += 1
                            print(f"✅ Task completed in {elapsed:.1f}s (no services found)")
                        elif task_status == 'error':
                            route_task_counts[route_name]['failed'] += 1
                            print(f"⚠️  Task completed with errors in {elapsed:.1f}s")
                        
                        print(f"   Progress: {current_combination}/{total_combinations} tasks")
                        
                        # Rate limiting between tasks (1-3 seconds is handled by _make_request)
                        # But add a small delay between tasks for safety
                        if current_combination < total_combinations:
                            # Small delay between tasks (already have 1-3s in _make_request)
                            time.sleep(0.5)
                        
                    except Exception as e:
                        print(f"❌ Failed to process task {task_id}: {e}")
                        self.stats['routes_failed'] += 1
                        route_task_counts[route_name]['failed'] += 1
                        # Continue with next task instead of stopping
                        continue
        
        # Mark routes as completed only if all tasks are done (completed, skipped, or failed)
        print(f"\n📊 Route Completion Summary:")
        print(f"{'='*70}")
        for route in routes:
            route_name = route['name']
            counts = route_task_counts[route_name]
            total = counts['total']
            completed = counts['completed']
            skipped = counts['skipped']
            failed = counts['failed']
            done = completed + skipped + failed
            
            print(f"   {route_name}: {done}/{total} tasks done (✓{completed} completed, ⏭{skipped} skipped, ✗{failed} failed)")
            
            # Only mark as completed if all tasks are done
            if done == total:
                if route_name not in self.progress.progress.get('completed_routes', []):
                    # Count actual records for this route from database
                    route_records = 0
                    try:
                        db_path = self.config['database']['path']
                        if os.path.exists(db_path):
                            conn = sqlite3.connect(db_path)
                            cursor = conn.cursor()
                            origin = route['from_loc']
                            destination = route['to_loc']
                            cursor.execute("""
                                SELECT COUNT(*) 
                                FROM hsp_service_metrics
                                WHERE origin = ? AND destination = ?
                            """, (origin, destination))
                            route_records = cursor.fetchone()[0]
                            conn.close()
                    except Exception:
                        pass
                    
                    self.progress.mark_route_completed(route_name, route_records)
                    print(f"      ✅ Marked as completed ({route_records} records)")
            else:
                print(f"      ⚠️  Not completed yet ({total - done} tasks remaining)")
        
        self.stats['routes_processed'] = len([r for r in routes if route_task_counts[r['name']]['completed'] + route_task_counts[r['name']]['skipped'] + route_task_counts[r['name']]['failed'] == route_task_counts[r['name']]['total']])
        
        # Finalize
        self.stats['end_time'] = datetime.now()
        self._print_final_summary()
        self._save_statistics()
    
    def _print_final_summary(self):
        """Print final collection summary"""
        print(f"\n{'='*70}")
        print(f"📊 COLLECTION SUMMARY")
        print(f"{'='*70}")
        
        print(f"\n⏱️  Time:")
        print(f"   Started: {self.stats['start_time']}")
        print(f"   Ended: {self.stats['end_time']}")
        print(f"   Duration: {self.stats['total_time']:.1f}s ({self.stats['total_time']/60:.1f} minutes)")
        
        print(f"\n📈 Results:")
        print(f"   Routes processed: {self.stats['routes_processed']}")
        print(f"   Routes failed: {self.stats['routes_failed']}")
        print(f"   Total records: {self.stats['total_records']}")
        print(f"   API calls: {self.stats['total_api_calls']}")
        
        if self.stats['routes_processed'] > 0:
            avg_time = self.stats['total_time'] / self.stats['routes_processed']
            avg_records = self.stats['total_records'] / self.stats['routes_processed']
            print(f"   Avg time/route: {avg_time:.1f}s")
            print(f"   Avg records/route: {avg_records:.0f}")
        
        print(f"\n{'='*70}")
    
    def _save_statistics(self):
        """Save statistics to file"""
        stats_file = self.config['output'].get('statistics_file', 'data/stats.json')
        os.makedirs(os.path.dirname(stats_file), exist_ok=True)
        
        # Convert datetime to ISO format
        stats_to_save = self.stats.copy()
        stats_to_save['start_time'] = self.stats['start_time'].isoformat() if self.stats['start_time'] else None
        stats_to_save['end_time'] = self.stats['end_time'].isoformat() if self.stats['end_time'] else None
        
        with open(stats_file, 'w') as f:
            json.dump(stats_to_save, indent=2, fp=f)
        
        print(f"📁 Statistics saved to: {stats_file}")


def split_date_range(start_date: str, end_date: str, chunk_days: int = 14) -> List[Tuple[str, str]]:
    """Split a date range into smaller chunks
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        chunk_days: Number of days per chunk (default 14 days = 2 weeks)
    
    Returns:
        List of (from_date, to_date) tuples
    """
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    chunks = []
    current = start
    
    # Handle case where start_date == end_date (single day)
    if start == end:
        chunks.append((start_date, end_date))
        return chunks
    
    while current <= end:
        chunk_end = min(current + timedelta(days=chunk_days - 1), end)
        chunks.append((
            current.strftime('%Y-%m-%d'),
            chunk_end.strftime('%Y-%m-%d')
        ))
        current = chunk_end + timedelta(days=1)
        # Break if we've reached the end
        if chunk_end >= end:
            break
    
    return chunks


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='HSP Batch Data Collection')
    parser.add_argument('config', help='Configuration file (e.g., hsp_config_phase1.yaml)')
    parser.add_argument('--phase', help='Phase name for logging', default=None)
    parser.add_argument('--no-skip', action='store_true', help='Do not skip completed routes')
    parser.add_argument('--date-from', help='Override start date (YYYY-MM-DD)', default=None)
    parser.add_argument('--date-to', help='Override end date (YYYY-MM-DD)', default=None)
    args = parser.parse_args()
    
    try:
        collector = HSPBatchCollector(
            config_file=args.config,
            skip_completed=not args.no_skip,
            date_from=args.date_from,
            date_to=args.date_to
        )
        collector.run_phase(phase_name=args.phase)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Collection interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
