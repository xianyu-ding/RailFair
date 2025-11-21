"""
HSP Data Validator - Validate data quality and completeness
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class HSPValidator:
    """
    Validate HSP data for quality and completeness
    """
    
    def __init__(self, config: Dict):
        """
        Initialize validator with configuration
        
        Args:
            config: Validation configuration from config file
        """
        self.config = config
        self.validation_errors = []
        self.validation_warnings = []
    
    def validate_service_metrics(self, record: Dict) -> tuple[bool, List[str]]:
        """
        Validate a service metrics record
        
        Args:
            record: Processed metrics record
            
        Returns:
            Tuple of (is_valid, errors_list)
        """
        # Clear previous errors for this validation
        current_errors = []
        is_valid = True
        record_id = f"{record.get('origin_location')}-{record.get('destination_location')}"
        
        # Check required fields
        required_fields = self.config.get('required_fields', {}).get('service_metrics', [])
        for field in required_fields:
            if field not in record or record[field] is None:
                error_msg = f"Missing required field '{field}' in record {record_id}"
                current_errors.append(error_msg)
                self.validation_errors.append(error_msg)
                is_valid = False
        
        # Validate CRS codes (3 letters)
        for field in ['origin_location', 'destination_location']:
            value = record.get(field)
            if value and (len(value) != 3 or not value.isalpha()):
                error_msg = f"Invalid CRS code '{value}' in field '{field}' for record {record_id}"
                current_errors.append(error_msg)
                self.validation_errors.append(error_msg)
                is_valid = False
        
        # Validate TOC code (2 letters)
        toc_code = record.get('toc_code')
        if toc_code and (len(toc_code) != 2 or not toc_code.isalpha()):
            self.validation_warnings.append(
                f"Invalid TOC code '{toc_code}' for record {record_id}"
            )
        
        # Validate matched services count
        matched_count = record.get('matched_services_count', 0)
        if matched_count < 0:
            error_msg = f"Negative matched_services_count {matched_count} for record {record_id}"
            current_errors.append(error_msg)
            self.validation_errors.append(error_msg)
            is_valid = False
        
        # Validate RIDs list
        rids = record.get('rids', [])
        if not isinstance(rids, list):
            error_msg = f"RIDs must be a list for record {record_id}"
            current_errors.append(error_msg)
            self.validation_errors.append(error_msg)
            is_valid = False
        elif matched_count != len(rids):
            self.validation_warnings.append(
                f"Matched count {matched_count} doesn't match RIDs list length {len(rids)} "
                f"for record {record_id}"
            )
        
        # Validate metrics
        metrics = record.get('metrics', [])
        if not isinstance(metrics, list):
            error_msg = f"Metrics must be a list for record {record_id}"
            current_errors.append(error_msg)
            self.validation_errors.append(error_msg)
            is_valid = False
        else:
            for i, metric in enumerate(metrics):
                metric_errors = self._validate_metric(metric, record_id, i)
                if metric_errors:
                    current_errors.extend(metric_errors)
                    is_valid = False
        
        return is_valid, current_errors
    
    def _validate_metric(self, metric: Dict, record_id: str, index: int) -> List[str]:
        """Validate a single metric entry
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        # Check percentages
        percent = metric.get('percent_tolerance')
        if percent is not None:
            if not (0 <= percent <= 100):
                error_msg = (
                    f"Invalid percent_tolerance {percent} (must be 0-100) "
                    f"for record {record_id}, metric {index}"
                )
                errors.append(error_msg)
                self.validation_errors.append(error_msg)
        
        # Check counts are non-negative
        for field in ['num_tolerance', 'num_not_tolerance']:
            value = metric.get(field)
            if value is not None and value < 0:
                error_msg = f"Negative {field} {value} for record {record_id}, metric {index}"
                errors.append(error_msg)
                self.validation_errors.append(error_msg)
        
        # Verify tolerance value is reasonable
        tolerance_value = metric.get('tolerance_value')
        if tolerance_value is not None and tolerance_value < 0:
            error_msg = (
                f"Negative tolerance_value {tolerance_value} "
                f"for record {record_id}, metric {index}"
            )
            errors.append(error_msg)
            self.validation_errors.append(error_msg)
        
        return errors
    
    def validate_service_details(self, record: Dict) -> tuple[bool, List[str]]:
        """
        Validate a service details record
        
        Args:
            record: Processed details record
            
        Returns:
            Tuple of (is_valid, errors_list)
        """
        # Clear previous errors for this validation
        current_errors = []
        is_valid = True
        rid = record.get('rid', 'unknown')
        
        # Check required fields
        required_fields = self.config.get('required_fields', {}).get('service_details', [])
        for field in required_fields:
            if field not in record or record[field] is None:
                error_msg = f"Missing required field '{field}' in service details for RID {rid}"
                current_errors.append(error_msg)
                self.validation_errors.append(error_msg)
                is_valid = False
        
        # Validate date format
        date_of_service = record.get('date_of_service')
        if date_of_service:
            try:
                datetime.strptime(date_of_service, '%Y-%m-%d')
            except ValueError:
                error_msg = f"Invalid date_of_service format '{date_of_service}' for RID {rid}"
                current_errors.append(error_msg)
                self.validation_errors.append(error_msg)
                is_valid = False
        
        # Validate locations
        locations = record.get('locations', [])
        if not isinstance(locations, list):
            error_msg = f"Locations must be a list for RID {rid}"
            current_errors.append(error_msg)
            self.validation_errors.append(error_msg)
            is_valid = False
        elif len(locations) == 0:
            error_msg = f"No locations found for RID {rid}"
            current_errors.append(error_msg)
            self.validation_errors.append(error_msg)
            is_valid = False
        else:
            for i, location in enumerate(locations):
                location_errors = self._validate_location(location, rid, i)
                if location_errors:
                    current_errors.extend(location_errors)
                    is_valid = False
        
        return is_valid, current_errors
    
    def _validate_location(self, location: Dict, rid: str, index: int) -> List[str]:
        """Validate a single location entry
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        loc_code = location.get('location', f'index_{index}')
        
        # Validate CRS code
        if not loc_code or len(loc_code) != 3 or not loc_code.isalpha():
            error_msg = f"Invalid location code '{loc_code}' for RID {rid}, location {index}"
            errors.append(error_msg)
            self.validation_errors.append(error_msg)
        
        # Validate delay values
        max_delay = self.config.get('max_delay_minutes', 1440)
        
        for delay_field in ['departure_delay_minutes', 'arrival_delay_minutes']:
            delay = location.get(delay_field)
            if delay is not None:
                if abs(delay) > max_delay:
                    self.validation_warnings.append(
                        f"Extreme {delay_field} value {delay} minutes "
                        f"for RID {rid}, location {loc_code}"
                    )
        
        # Check time consistency
        scheduled_arr = location.get('scheduled_arrival')
        scheduled_dep = location.get('scheduled_departure')
        actual_arr = location.get('actual_arrival')
        actual_dep = location.get('actual_departure')
        
        # If both scheduled times exist, departure should be >= arrival
        if scheduled_arr and scheduled_dep:
            if scheduled_dep < scheduled_arr:
                self.validation_warnings.append(
                    f"Scheduled departure before arrival for RID {rid}, location {loc_code}"
                )
        
        # If both actual times exist, departure should be >= arrival
        if actual_arr and actual_dep:
            if actual_dep < actual_arr:
                self.validation_warnings.append(
                    f"Actual departure before arrival for RID {rid}, location {loc_code}"
                )
        
        return errors
    
    def validate_eus_man_route(self, record: Dict) -> bool:
        """
        Special validation for EUS-MAN test route
        
        Args:
            record: Metrics or details record
            
        Returns:
            True if valid for EUS-MAN route
        """
        is_valid = True
        
        # Check if this is EUS-MAN route
        origin = record.get('origin_location') or record.get('locations', [{}])[0].get('location')
        destination = (record.get('destination_location') or 
                      record.get('locations', [{}])[-1].get('location') if record.get('locations') else None)
        
        if origin == 'EUS' and destination == 'MAN':
            # EUS-MAN specific checks
            
            # Should have reasonable journey time (approximately 2-3 hours)
            if 'scheduled_departure_time' in record and 'scheduled_arrival_time' in record:
                try:
                    dep_time = datetime.strptime(record['scheduled_departure_time'], '%H%M')
                    arr_time = datetime.strptime(record['scheduled_arrival_time'], '%H%M')
                    
                    journey_minutes = (arr_time - dep_time).total_seconds() / 60
                    
                    if journey_minutes < 90 or journey_minutes > 240:
                        self.validation_warnings.append(
                            f"Unusual EUS-MAN journey time: {journey_minutes} minutes"
                        )
                except:
                    pass
            
            logger.debug(f"EUS-MAN route validation passed for record")
        
        return is_valid
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """
        Get summary of validation results
        
        Returns:
            Dict with validation statistics
        """
        return {
            'errors_count': len(self.validation_errors),
            'warnings_count': len(self.validation_warnings),
            'errors': self.validation_errors,
            'warnings': self.validation_warnings,
            'is_valid': len(self.validation_errors) == 0
        }
    
    def reset(self):
        """Reset validation errors and warnings"""
        self.validation_errors = []
        self.validation_warnings = []
    
    def log_summary(self):
        """Log validation summary"""
        summary = self.get_validation_summary()
        
        if summary['is_valid']:
            logger.info(f"✓ Validation passed with {summary['warnings_count']} warnings")
        else:
            logger.error(f"✗ Validation failed with {summary['errors_count']} errors")
        
        if summary['errors_count'] > 0:
            logger.error("Validation errors:")
            for error in summary['errors'][:10]:  # Show first 10
                logger.error(f"  - {error}")
            if summary['errors_count'] > 10:
                logger.error(f"  ... and {summary['errors_count'] - 10} more errors")
        
        if summary['warnings_count'] > 0:
            logger.warning(f"Validation warnings: {summary['warnings_count']}")
            for warning in summary['warnings'][:5]:  # Show first 5
                logger.warning(f"  - {warning}")
            if summary['warnings_count'] > 5:
                logger.warning(f"  ... and {summary['warnings_count'] - 5} more warnings")


# Example usage
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "configs" / "hsp_config.yaml"


if __name__ == "__main__":
    import yaml
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load config
    with DEFAULT_CONFIG_PATH.open('r') as f:
        config = yaml.safe_load(f)
    
    validator = HSPValidator(config['validation'])
    
    # Test with sample data
    sample_metrics = {
        'origin_location': 'EUS',
        'destination_location': 'MAN',
        'scheduled_departure_time': '0712',
        'scheduled_arrival_time': '0920',
        'toc_code': 'AV',
        'matched_services_count': 5,
        'rids': ['rid1', 'rid2', 'rid3', 'rid4', 'rid5'],
        'metrics': [
            {
                'tolerance_value': 5,
                'num_tolerance': 4,
                'num_not_tolerance': 1,
                'percent_tolerance': 80.0,
                'global_tolerance': True
            }
        ]
    }
    
    is_valid = validator.validate_service_metrics(sample_metrics)
    validator.validate_eus_man_route(sample_metrics)
    validator.log_summary()
    
    print(f"\nValidation result: {'PASS' if is_valid else 'FAIL'}")
