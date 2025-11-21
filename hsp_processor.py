"""
HSP Data Processor - handles data transformation and delay calculations
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pytz

logger = logging.getLogger(__name__)


class HSPDataProcessor:
    """
    Process HSP API responses and calculate delays
    """
    
    def __init__(
        self,
        api_timezone: str = "Europe/London",
        database_timezone: str = "UTC"
    ):
        """
        Initialize processor with timezone settings
        
        Args:
            api_timezone: Timezone of API data (default UK time)
            database_timezone: Timezone for database storage (default UTC)
        """
        self.api_tz = pytz.timezone(api_timezone)
        self.db_tz = pytz.timezone(database_timezone)
        logger.info(f"Initialized processor: API TZ={api_timezone}, DB TZ={database_timezone}")
    
    def parse_time(
        self,
        date_str: str,
        time_str: str,
        is_api_timezone: bool = True
    ) -> Optional[datetime]:
        """
        Parse date and time string into datetime object
        
        Args:
            date_str: Date in YYYY-MM-DD format
            time_str: Time in HHMM format (e.g., "0712")
            is_api_timezone: If True, treat as API timezone; else as DB timezone
            
        Returns:
            datetime object or None if parsing fails
        """
        if not date_str or not time_str:
            return None
        
        try:
            # Parse time string (HHMM)
            if len(time_str) != 4:
                logger.warning(f"Invalid time format: {time_str}")
                return None
            
            hour = int(time_str[:2])
            minute = int(time_str[2:])
            
            # Parse date string (YYYY-MM-DD)
            date_parts = date_str.split('-')
            if len(date_parts) != 3:
                logger.warning(f"Invalid date format: {date_str}")
                return None
            
            year, month, day = int(date_parts[0]), int(date_parts[1]), int(date_parts[2])
            
            # Create datetime object
            if is_api_timezone:
                dt = self.api_tz.localize(datetime(year, month, day, hour, minute))
            else:
                dt = self.db_tz.localize(datetime(year, month, day, hour, minute))
            
            return dt
            
        except (ValueError, AttributeError) as e:
            logger.error(f"Error parsing time {date_str} {time_str}: {e}")
            return None
    
    def convert_to_db_timezone(self, dt: datetime) -> datetime:
        """
        Convert datetime to database timezone
        
        Args:
            dt: datetime object with timezone info
            
        Returns:
            datetime in database timezone
        """
        if dt is None:
            return None
        
        if dt.tzinfo is None:
            # Assume API timezone if no timezone info
            dt = self.api_tz.localize(dt)
        
        return dt.astimezone(self.db_tz)
    
    def _parse_time_with_cross_midnight(
        self,
        date_str: str,
        time_str: str,
        reference_time: Optional[datetime] = None
    ) -> Optional[datetime]:
        """
        Parse time with cross-midnight handling
        
        If arrival time is earlier than departure time (e.g., 23:45 dep -> 00:30 arr),
        assume arrival is on the next day.
        
        Args:
            date_str: Date in YYYY-MM-DD format
            time_str: Time in HHMM format (e.g., "0030")
            reference_time: Reference time (usually departure) to detect cross-midnight
            
        Returns:
            datetime object with correct date (next day if cross-midnight detected)
        """
        if not date_str or not time_str:
            return None
        
        # Parse base time
        base_time = self.parse_time(date_str, time_str)
        if base_time is None:
            return None
        
        # If we have a reference time and arrival is earlier than departure,
        # and the time difference suggests cross-midnight (arrival hour < 6 and departure hour >= 22),
        # then arrival is on the next day
        if reference_time is not None:
            ref_hour = reference_time.hour
            arr_hour = base_time.hour
            
            # Check if this looks like cross-midnight:
            # - Reference time is late (>= 22:00)
            # - Arrival time is early (< 6:00)
            # - Arrival time is earlier than reference time
            if ref_hour >= 22 and arr_hour < 6:
                # Add one day to arrival time
                from datetime import timedelta
                base_time = base_time + timedelta(days=1)
                logger.debug(f"Cross-midnight detected: {reference_time} -> {base_time}")
        
        return base_time
    
    def calculate_delay_minutes(
        self,
        scheduled_time: Optional[datetime],
        actual_time: Optional[datetime]
    ) -> Optional[int]:
        """
        Calculate delay in minutes
        
        Args:
            scheduled_time: Scheduled datetime
            actual_time: Actual datetime
            
        Returns:
            Delay in minutes (positive for late, negative for early, None if data missing)
        """
        if scheduled_time is None or actual_time is None:
            return None
        
        # Ensure both times have timezone info
        if scheduled_time.tzinfo is None:
            scheduled_time = self.api_tz.localize(scheduled_time)
        if actual_time.tzinfo is None:
            actual_time = self.api_tz.localize(actual_time)
        
        # Calculate difference
        delta = actual_time - scheduled_time
        delay_minutes = int(delta.total_seconds() / 60)
        
        return delay_minutes
    
    def process_service_metrics(self, raw_data: Dict) -> List[Dict]:
        """
        Process serviceMetrics API response
        
        Args:
            raw_data: Raw API response
            
        Returns:
            List of processed service records
        """
        processed_records = []
        
        try:
            header = raw_data.get('header', {})
            services = raw_data.get('Services', [])
            
            logger.info(f"Processing {len(services)} services from {header.get('from_location')} "
                       f"to {header.get('to_location')}")
            
            for service in services:
                try:
                    record = self._process_single_service_metrics(service, header)
                    if record:
                        processed_records.append(record)
                except Exception as e:
                    logger.error(f"Error processing service: {e}", exc_info=True)
                    continue
            
            logger.info(f"Successfully processed {len(processed_records)} service records")
            
        except Exception as e:
            logger.error(f"Error processing service metrics: {e}", exc_info=True)
        
        return processed_records
    
    def _process_single_service_metrics(
        self,
        service: Dict,
        header: Dict
    ) -> Optional[Dict]:
        """
        Process a single service from serviceMetrics response
        """
        attrs = service.get('serviceAttributesMetrics', {})
        metrics = service.get('Metrics', [])
        
        # Extract required fields
        origin = attrs.get('origin_location')
        destination = attrs.get('destination_location')
        ptd = attrs.get('gbtt_ptd')
        pta = attrs.get('gbtt_pta')
        toc_code = attrs.get('toc_code')
        matched_services = attrs.get('matched_services')
        rids = attrs.get('rids', [])
        
        # Validate required fields
        if not all([origin, destination, toc_code]):
            logger.warning(f"Missing required fields in service: {attrs}")
            return None
        
        # Process metrics
        metrics_processed = []
        for metric in metrics:
            metrics_processed.append({
                'tolerance_value': int(metric.get('tolerance_value', 0)),
                'num_tolerance': int(metric.get('num_tolerance', 0)),
                'num_not_tolerance': int(metric.get('num_not_tolerance', 0)),
                'percent_tolerance': float(metric.get('percent_tolerance', 0)),
                'global_tolerance': metric.get('global_tolerance', False)
            })
        
        record = {
            'origin_location': origin,
            'destination_location': destination,
            'scheduled_departure_time': ptd,
            'scheduled_arrival_time': pta,
            'toc_code': toc_code,
            'matched_services_count': int(matched_services) if matched_services else 0,
            'rids': rids,
            'metrics': metrics_processed,
            'from_location': header.get('from_location'),
            'to_location': header.get('to_location')
        }
        
        return record
    
    def process_service_details(
        self,
        raw_data: Dict,
        rid: str
    ) -> Optional[Dict]:
        """
        Process serviceDetails API response
        
        Args:
            raw_data: Raw API response
            rid: RID of the service
            
        Returns:
            Processed service detail record
        """
        try:
            attrs = raw_data.get('serviceAttributesDetails', {})
            
            date_of_service = attrs.get('date_of_service')
            toc_code = attrs.get('toc_code')
            rid_returned = attrs.get('rid')
            locations = attrs.get('locations', [])
            
            # Validate
            if not all([date_of_service, toc_code, rid_returned]):
                logger.warning(f"Missing required fields in service details for RID {rid}")
                return None
            
            # Process each location
            processed_locations = []
            for loc in locations:
                processed_loc = self._process_location(loc, date_of_service)
                if processed_loc:
                    processed_locations.append(processed_loc)
            
            record = {
                'rid': rid_returned,
                'date_of_service': date_of_service,
                'toc_code': toc_code,
                'locations': processed_locations,
                'origin_location': processed_locations[0]['location'] if processed_locations else None,
                'destination_location': processed_locations[-1]['location'] if processed_locations else None
            }
            
            logger.debug(f"Processed service details for RID {rid}: {len(processed_locations)} locations")
            
            return record
            
        except Exception as e:
            logger.error(f"Error processing service details for RID {rid}: {e}", exc_info=True)
            return None
    
    def _process_location(self, location: Dict, date_of_service: str) -> Optional[Dict]:
        """
        Process a single location from service details
        
        Args:
            location: Location data from API
            date_of_service: Date string (YYYY-MM-DD)
            
        Returns:
            Processed location record
        """
        loc_code = location.get('location')
        
        # Parse times
        gbtt_ptd = location.get('gbtt_ptd', '')
        gbtt_pta = location.get('gbtt_pta', '')
        actual_td = location.get('actual_td', '')
        actual_ta = location.get('actual_ta', '')
        
        # Parse scheduled times with cross-midnight handling
        scheduled_departure = self.parse_time(date_of_service, gbtt_ptd) if gbtt_ptd else None
        scheduled_arrival = self._parse_time_with_cross_midnight(
            date_of_service, gbtt_pta, scheduled_departure
        ) if gbtt_pta else None
        
        # Parse actual times with cross-midnight handling
        actual_departure = self.parse_time(date_of_service, actual_td) if actual_td else None
        actual_arrival = self._parse_time_with_cross_midnight(
            date_of_service, actual_ta, actual_departure
        ) if actual_ta else None
        
        # Convert to DB timezone
        if scheduled_departure:
            scheduled_departure = self.convert_to_db_timezone(scheduled_departure)
        if scheduled_arrival:
            scheduled_arrival = self.convert_to_db_timezone(scheduled_arrival)
        if actual_departure:
            actual_departure = self.convert_to_db_timezone(actual_departure)
        if actual_arrival:
            actual_arrival = self.convert_to_db_timezone(actual_arrival)
        
        # Calculate delays
        departure_delay = self.calculate_delay_minutes(scheduled_departure, actual_departure)
        arrival_delay = self.calculate_delay_minutes(scheduled_arrival, actual_arrival)
        
        # Get cancellation reason
        late_canc_reason = location.get('late_canc_reason', '')
        
        record = {
            'location': loc_code,
            'scheduled_departure': scheduled_departure,
            'scheduled_arrival': scheduled_arrival,
            'actual_departure': actual_departure,
            'actual_arrival': actual_arrival,
            'departure_delay_minutes': departure_delay,
            'arrival_delay_minutes': arrival_delay,
            'cancellation_reason': late_canc_reason if late_canc_reason else None
        }
        
        return record


# Example usage and testing
if __name__ == "__main__":
    import json
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize processor
    processor = HSPDataProcessor()
    
    # Test time parsing
    dt = processor.parse_time("2024-10-15", "0712")
    print(f"Parsed time: {dt}")
    print(f"In UTC: {processor.convert_to_db_timezone(dt)}")
    
    # Test delay calculation
    scheduled = processor.parse_time("2024-10-15", "0712")
    actual = processor.parse_time("2024-10-15", "0720")
    delay = processor.calculate_delay_minutes(scheduled, actual)
    print(f"Delay: {delay} minutes")
    
    # Test with sample data
    sample_metrics = {
        "header": {
            "from_location": "EUS",
            "to_location": "MAN"
        },
        "Services": [
            {
                "serviceAttributesMetrics": {
                    "origin_location": "EUS",
                    "destination_location": "MAN",
                    "gbtt_ptd": "0712",
                    "gbtt_pta": "0920",
                    "toc_code": "AV",
                    "matched_services": "22",
                    "rids": ["202410150001"]
                },
                "Metrics": [
                    {
                        "tolerance_value": "5",
                        "num_tolerance": "18",
                        "num_not_tolerance": "4",
                        "percent_tolerance": "81.8",
                        "global_tolerance": True
                    }
                ]
            }
        ]
    }
    
    processed = processor.process_service_metrics(sample_metrics)
    print(f"\nProcessed metrics: {json.dumps(processed, indent=2, default=str)}")
