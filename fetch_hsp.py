"""
HSP Data Fetcher - Main script for fetching historical service performance data
"""
import os
import sys
import logging
import base64
import requests
import yaml
import time
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime
import sqlite3
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    def load_dotenv(*_args, **_kwargs):
        return False

from hsp_processor import HSPDataProcessor
from retry_handler import (
    RetryHandler,
    with_retry,
    APIError,
    NetworkError,
    RateLimitError,
    AuthenticationError,
    ValidationError,
    classify_http_error
)

logger = logging.getLogger(__name__)


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "hsp_config.yaml"
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "railfair.db"
DEFAULT_SCHEMA_PATH = PROJECT_ROOT / "create_hsp_tables.sql"
DEFAULT_ENV_PATH = Path(__file__).resolve().parent / ".env"

# Load environment variables from .env if present
try:
    load_dotenv(dotenv_path=DEFAULT_ENV_PATH, override=False)
except (PermissionError, OSError) as exc:
    print(f"Warning: Could not load .env file ({exc})")


class HSPFetcher:
    """
    Fetch historical service performance data from HSP API
    """
    
    def __init__(self, config_path: Union[str, Path] = DEFAULT_CONFIG_PATH):
        """
        Initialize HSP fetcher
        
        Args:
            config_path: Path to configuration file
        """
        config_path = Path(config_path)
        if not config_path.is_file():
            raise FileNotFoundError(f"HSP configuration file not found at {config_path}")

        # Load configuration
        with config_path.open('r') as f:
            self.config = yaml.safe_load(f)
        
        # Setup logging
        self._setup_logging()
        
        # Get credentials from environment
        self.username = os.getenv('HSP_EMAIL') or os.getenv('HSP_USERNAME')
        self.password = os.getenv('HSP_PASSWORD')
        
        if not self.username or not self.password:
            raise ValueError(
                "Set either HSP_EMAIL or HSP_USERNAME and HSP_PASSWORD environment variables"
            )
        
        # API configuration
        self.base_url = self.config['api']['base_url']
        self.timeout = self.config['api']['timeout']
        
        # Initialize processor
        self.processor = HSPDataProcessor(
            api_timezone=self.config['timezone']['api_timezone'],
            database_timezone=self.config['timezone']['database_timezone']
        )
        
        # Initialize retry handler
        retry_config = self.config['retry']
        self.retry_handler = RetryHandler(
            max_attempts=retry_config['max_attempts'],
            initial_delay=retry_config['initial_delay'],
            max_delay=retry_config['max_delay'],
            exponential_base=retry_config['exponential_base'],
            jitter=retry_config['jitter']
        )
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = self.config['api']['rate_limit']['delay_between_requests']
        
        # Database initialization flag
        self._db_initialized = False
        
        logger.info("HSP Fetcher initialized successfully")
    
    def _setup_logging(self):
        """Configure logging"""
        log_config = self.config['logging']
        
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=getattr(logging, log_config['level']),
            format=log_config['format'],
            handlers=[
                logging.FileHandler(log_config['file']),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def _get_auth_header(self) -> str:
        """
        Create Basic Authentication header
        
        Returns:
            Base64 encoded credentials
        """
        credentials = f"{self.username}:{self.password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"
    
    def _rate_limit(self):
        """Implement rate limiting between requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(
        self,
        endpoint: str,
        payload: Dict
    ) -> Dict:
        """
        Make HTTP request to HSP API with error handling
        
        Args:
            endpoint: API endpoint path
            payload: JSON payload
            
        Returns:
            API response as dict
            
        Raises:
            Various exceptions based on error type
        """
        url = f"{self.base_url}{endpoint}"
        
        headers = {
            'Authorization': self._get_auth_header(),
            'Content-Type': 'application/json'
        }
        
        # Rate limiting
        self._rate_limit()
        
        logger.debug(f"Making request to {url} with payload: {payload}")
        
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
                logger.error(f"API error: {response.status_code} - {response.text}")
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
    
    @with_retry(
        max_attempts=3,
        initial_delay=1.0,
        retryable_exceptions=(APIError, NetworkError, RateLimitError)
    )
    def fetch_service_metrics(
        self,
        from_loc: str,
        to_loc: str,
        from_time: str,
        to_time: str,
        from_date: str,
        to_date: str,
        days: str = "WEEKDAY",
        toc_filter: Optional[List[str]] = None,
        tolerance: Optional[List[str]] = None
    ) -> Dict:
        """
        Fetch service metrics from HSP API
        
        Args:
            from_loc: Origin station CRS code (e.g., "EUS")
            to_loc: Destination station CRS code (e.g., "MAN")
            from_time: Start time in HHMM format (e.g., "0700")
            to_time: End time in HHMM format (e.g., "0800")
            from_date: Start date in YYYY-MM-DD format
            to_date: End date in YYYY-MM-DD format
            days: Day filter - "WEEKDAY", "SATURDAY", or "SUNDAY"
            toc_filter: Optional list of TOC codes to filter
            tolerance: Optional tolerance values (e.g., ["2", "5", "10"])
            
        Returns:
            API response dict
        """
        payload = {
            "from_loc": from_loc,
            "to_loc": to_loc,
            "from_time": from_time,
            "to_time": to_time,
            "from_date": from_date,
            "to_date": to_date,
            "days": days
        }
        
        if toc_filter:
            payload["toc_filter"] = toc_filter
        
        if tolerance:
            payload["tolerance"] = tolerance
        
        logger.info(
            f"Fetching service metrics: {from_loc}->{to_loc} "
            f"{from_date} to {to_date} ({days})"
        )
        
        endpoint = self.config['api']['endpoints']['service_metrics']
        response = self._make_request(endpoint, payload)
        
        logger.info(
            f"Successfully fetched service metrics: "
            f"{len(response.get('Services', []))} services"
        )
        
        return response
    
    @with_retry(
        max_attempts=3,
        initial_delay=1.0,
        retryable_exceptions=(APIError, NetworkError, RateLimitError)
    )
    def fetch_service_details(self, rid: str) -> Dict:
        """
        Fetch service details for a specific RID
        
        Args:
            rid: RID (RTTI ID) of the service
            
        Returns:
            API response dict
        """
        payload = {"rid": rid}
        
        logger.debug(f"Fetching service details for RID: {rid}")
        
        endpoint = self.config['api']['endpoints']['service_details']
        response = self._make_request(endpoint, payload)
        
        logger.debug(f"Successfully fetched service details for RID: {rid}")
        
        return response
    
    def fetch_and_process_route(
        self,
        route_config: Dict,
        fetch_details: bool = False
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Fetch and process data for a single route
        
        Args:
            route_config: Route configuration dict
            fetch_details: If True, also fetch detailed data for each service
            
        Returns:
            Tuple of (metrics_records, details_records)
        """
        logger.info(f"Processing route: {route_config['name']}")
        
        # Fetch service metrics
        try:
            metrics_response = self.fetch_service_metrics(
                from_loc=route_config['from_loc'],
                to_loc=route_config['to_loc'],
                from_time=route_config['from_time'],
                to_time=route_config['to_time'],
                from_date=self.config['date_range']['from_date'],
                to_date=self.config['date_range']['to_date'],
                days=self.config['date_range']['days'],
                tolerance=self.config['tolerance']['values']
            )
        except Exception as e:
            logger.error(f"Failed to fetch metrics for route {route_config['name']}: {e}")
            return [], []
        
        # Process metrics
        metrics_records = self.processor.process_service_metrics(metrics_response)
        logger.info(f"Processed {len(metrics_records)} metric records")
        
        # Optionally fetch details
        details_records = []
        if fetch_details and metrics_records:
            logger.info("Fetching service details...")
            
            for record in metrics_records:
                rids = record.get('rids', [])
                
                for rid in rids[:5]:  # Limit to first 5 for testing
                    try:
                        details_response = self.fetch_service_details(rid)
                        details_record = self.processor.process_service_details(
                            details_response,
                            rid
                        )
                        if details_record:
                            details_records.append(details_record)
                    except Exception as e:
                        logger.error(f"Failed to fetch details for RID {rid}: {e}")
                        continue
            
            logger.info(f"Processed {len(details_records)} detail records")
        
        return metrics_records, details_records
    
    def save_to_database(
        self,
        metrics_records: List[Dict],
        details_records: List[Dict],
        db_path: Union[str, Path] = DEFAULT_DB_PATH
    ):
        """
        Save processed records to database
        
        Args:
            metrics_records: List of processed metrics records
            details_records: List of processed details records
            db_path: Path to SQLite database
        """
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Saving {len(metrics_records)} metrics and {len(details_records)} details to database at {db_path}")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        if not self._db_initialized:
            self._initialize_database(conn)
            self._db_initialized = True
        
        try:
            # Save metrics (simplified - you may want to expand this)
            for record in metrics_records:
                cursor.execute("""
                    INSERT OR REPLACE INTO hsp_service_metrics
                    (origin, destination, scheduled_departure, scheduled_arrival, 
                     toc_code, matched_services_count, fetch_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    record['origin_location'],
                    record['destination_location'],
                    record['scheduled_departure_time'],
                    record['scheduled_arrival_time'],
                    record['toc_code'],
                    record['matched_services_count'],
                    datetime.utcnow()
                ))
            
            # Save details
            for record in details_records:
                for location in record['locations']:
                    cursor.execute("""
                        INSERT OR REPLACE INTO hsp_service_details
                        (rid, date_of_service, toc_code, location,
                         scheduled_departure, scheduled_arrival,
                         actual_departure, actual_arrival,
                         departure_delay_minutes, arrival_delay_minutes,
                         cancellation_reason, fetch_timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        record['rid'],
                        record['date_of_service'],
                        record['toc_code'],
                        location['location'],
                        location['scheduled_departure'],
                        location['scheduled_arrival'],
                        location['actual_departure'],
                        location['actual_arrival'],
                        location['departure_delay_minutes'],
                        location['arrival_delay_minutes'],
                        location['cancellation_reason'],
                        datetime.utcnow()
                    ))
            
            conn.commit()
            logger.info("Successfully saved all records to database")
            
        except Exception as e:
            logger.error(f"Error saving to database: {e}")
            conn.rollback()
            raise
        
        finally:
            conn.close()

    def _initialize_database(self, conn: sqlite3.Connection):
        """Ensure required tables exist in the SQLite database."""
        cursor = conn.cursor()

        if DEFAULT_SCHEMA_PATH.is_file():
            logger.info(f"Initializing database schema from {DEFAULT_SCHEMA_PATH}")
            with DEFAULT_SCHEMA_PATH.open('r') as schema_file:
                schema_sql = schema_file.read()
                cursor.executescript(schema_sql)
        else:
            logger.warning(
                f"Schema file not found at {DEFAULT_SCHEMA_PATH}. "
                "Creating minimal tables directly."
            )
            cursor.executescript(
                """
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
                );

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
                );
                """
            )

        conn.commit()


def main():
    """Main execution function"""
    logger.info("=" * 80)
    logger.info("HSP Data Fetcher - Day 3")
    logger.info("=" * 80)
    
    try:
        # Initialize fetcher
        fetcher = HSPFetcher()
        
        # Test with EUS-MAN route
        test_route = {
            'name': 'EUS-MAN',
            'from_loc': 'EUS',
            'to_loc': 'MAN',
            'from_time': '0700',
            'to_time': '0800'
        }
        
        logger.info(f"\nTesting with route: {test_route['name']}")
        
        # Fetch and process
        metrics, details = fetcher.fetch_and_process_route(
            test_route,
            fetch_details=True  # Also fetch details for first service
        )
        
        # Display results
        logger.info(f"\n{'=' * 80}")
        logger.info(f"Results Summary:")
        logger.info(f"  Metrics records: {len(metrics)}")
        logger.info(f"  Details records: {len(details)}")
        
        if metrics:
            logger.info(f"\nFirst metric record:")
            logger.info(f"  Route: {metrics[0]['origin_location']} -> {metrics[0]['destination_location']}")
            logger.info(f"  TOC: {metrics[0]['toc_code']}")
            logger.info(f"  Departure: {metrics[0]['scheduled_departure_time']}")
            logger.info(f"  Matched services: {metrics[0]['matched_services_count']}")
        
        if details:
            logger.info(f"\nFirst detail record:")
            logger.info(f"  RID: {details[0]['rid']}")
            logger.info(f"  Date: {details[0]['date_of_service']}")
            logger.info(f"  Locations: {len(details[0]['locations'])}")
            
            # Show first location with delay info
            if details[0]['locations']:
                loc = details[0]['locations'][0]
                logger.info(f"  First stop: {loc['location']}")
                if loc['departure_delay_minutes'] is not None:
                    logger.info(f"    Departure delay: {loc['departure_delay_minutes']} minutes")
        
        # Save to database
        fetcher.save_to_database(metrics, details)
        
        logger.info(f"\n{'=' * 80}")
        logger.info("✓ Day 3 testing completed successfully!")
        logger.info(f"{'=' * 80}\n")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
