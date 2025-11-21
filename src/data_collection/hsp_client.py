"""Historical Service Performance (HSP) API Client."""

import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import json
from pathlib import Path

from ..utils import Config, logger, RAW_DATA_DIR


class HSPClient:
    """Client for National Rail Historical Service Performance API."""
    
    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        service_details_url: Optional[str] = None,
        service_metrics_url: Optional[str] = None,
        timeout: int = 30
    ):
        """Initialize HSP client.
        
        Args:
            username: API username (default from config)
            password: API password (default from config)
            service_details_url: Service details endpoint URL
            service_metrics_url: Service metrics endpoint URL
        """
        self.username = username or Config.HSP_USERNAME
        self.password = password or Config.HSP_PASSWORD
        self.service_details_url = service_details_url or Config.HSP_SERVICE_DETAILS_URL
        self.service_metrics_url = service_metrics_url or Config.HSP_SERVICE_METRICS_URL
        self.timeout = timeout
        
        self.session = requests.Session()
        self.session.auth = (self.username, self.password)
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        
        # Create HSP data directory
        self.data_dir = RAW_DATA_DIR / "hsp"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"HSP Client initialized with base URL: {self.service_details_url}")
    
    def test_connection(self) -> bool:
        """Test API connection with a simple request.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Try to get data for yesterday (a safe test)
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            
            payload = {
                "from_loc": "PAD",   # London Paddington
                "to_loc": "OXF",     # Oxford
                "from_time": "0800",
                "to_time": "0900",
                "from_date": yesterday,
                "to_date": yesterday,
                "days": "WEEKDAY"
            }
            
            logger.info(f"Testing HSP API connection with date: {yesterday}")
            response = self.session.post(
                self.service_metrics_url,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ HSP API connection successful! Received {len(data.get('Services', []))} services")
                return True
            elif response.status_code == 401:
                logger.error("❌ HSP API authentication failed - check credentials")
                return False
            else:
                logger.error(f"❌ HSP API returned status {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ HSP API connection error: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error testing HSP API: {e}")
            return False
    
    def get_service_metrics(
        self,
        from_loc: str,
        to_loc: str,
        from_date: str,
        to_date: str,
        from_time: str = "0000",
        to_time: str = "2359",
        days: str = "WEEKDAY"
    ) -> Optional[Dict[str, Any]]:
        """Get service performance metrics for a route.
        
        Args:
            from_loc: Origin station CRS code (e.g., 'PAD')
            to_loc: Destination station CRS code (e.g., 'OXF')
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            from_time: Start time (HHMM)
            to_time: End time (HHMM)
            days: Day filter (WEEKDAY, SATURDAY, SUNDAY)
            
        Returns:
            Dict containing service metrics or None if error
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
        
        try:
            logger.info(f"Fetching service metrics: {from_loc} → {to_loc} ({from_date} to {to_date})")
            response = self.session.post(
                self.service_metrics_url,
                json=payload,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Save raw data
            filename = f"metrics_{from_loc}_{to_loc}_{from_date}_{to_date}.json"
            filepath = self.data_dir / filename
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"✅ Saved service metrics to {filepath}")
            return data
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error fetching service metrics: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching service metrics: {e}")
            return None
    
    def get_service_details(
        self,
        rid: str,
        date: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get detailed information for a specific service.
        
        Args:
            rid: Retail Service ID (RTTI ID)
            date: Service date (YYYY-MM-DD), optional
            
        Returns:
            Dict containing service details or None if error
        """
        payload = {"rid": rid}
        if date:
            payload["date"] = date
        
        try:
            log_date = date if date else "unspecified"
            logger.info(f"Fetching service details: RID={rid}, Date={log_date}")
            response = self.session.post(
                self.service_details_url,
                json=payload,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Save raw data
            filename = f"details_{rid}_{date}.json"
            filepath = self.data_dir / filename
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"✅ Saved service details to {filepath}")
            return data
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error fetching service details: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching service details: {e}")
            return None
    
    def get_sample_data(self, days_back: int = 7) -> List[Dict[str, Any]]:
        """Get sample data from popular routes for testing.
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            List of service metrics from sample routes
        """
        # Popular UK rail routes for testing
        sample_routes = [
            {"from": "PAD", "to": "OXF", "name": "Paddington → Oxford"},
            {"from": "KGX", "to": "CBG", "name": "King's Cross → Cambridge"},
            {"from": "EUS", "to": "MAN", "name": "Euston → Manchester"},
        ]
        
        results = []
        end_date = datetime.now() - timedelta(days=1)  # Yesterday
        start_date = end_date - timedelta(days=days_back)
        
        for route in sample_routes:
            logger.info(f"Fetching sample data: {route['name']}")
            data = self.get_service_metrics(
                from_loc=route["from"],
                to_loc=route["to"],
                from_date=start_date.strftime("%Y-%m-%d"),
                to_date=end_date.strftime("%Y-%m-%d"),
                from_time="0700",
                to_time="1900",
                days="WEEKDAY"
            )
            
            if data:
                results.append({
                    "route": route["name"],
                    "data": data
                })
        
        return results


if __name__ == "__main__":
    # Quick test
    client = HSPClient()
    success = client.test_connection()
    print(f"HSP API test: {'✅ Success' if success else '❌ Failed'}")
