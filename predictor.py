"""
Day 12: Integrated Prediction Engine
Based on Day 8 predictor.py implementation
"""

import sqlite3
from datetime import datetime, time, date
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any
from enum import Enum
from contextlib import contextmanager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfidenceLevel(Enum):
    """Confidence level based on sample size"""
    HIGH = "HIGH"           # ≥100 samples
    MEDIUM = "MEDIUM"       # 30-99 samples
    LOW = "LOW"             # 10-29 samples
    VERY_LOW = "VERY_LOW"   # <10 samples


@dataclass
class PredictionInput:
    """Input parameters for prediction"""
    origin_crs: str
    destination_crs: str
    departure_datetime: datetime
    toc: Optional[str] = None


@dataclass
class PredictionResult:
    """Comprehensive prediction result"""
    # Core predictions
    on_time_probability: float
    delay_5_probability: float
    delay_10_probability: float
    delay_30_probability: float
    expected_delay_minutes: float
    
    # Metadata
    confidence: ConfidenceLevel
    sample_size: int
    time_adjustment_factor: float
    day_adjustment_factor: float
    is_degraded: bool
    
    # Source information (required fields)
    origin: str
    destination: str
    departure_time: datetime
    
    # Optional fields (must come after required fields)
    degradation_reason: Optional[str] = None
    toc: Optional[str] = None
    prediction_timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.prediction_timestamp is None:
            self.prediction_timestamp = datetime.now()


class DelayPredictor:
    """Statistical delay predictor with time adjustments"""
    
    # Time adjustment factors based on time of day
    TIME_FACTORS = {
        # Time ranges (hour boundaries) and their adjustment factors
        (0, 6): 0.85,    # Early morning - best performance
        (6, 10): 1.15,   # Morning peak - worse performance
        (10, 16): 1.00,  # Midday - baseline
        (16, 19): 1.20,  # Evening peak - worst performance
        (19, 24): 1.05,  # Evening - slightly worse
    }
    
    # Day type adjustment
    WEEKDAY_FACTOR = 1.00
    WEEKEND_FACTOR = 0.90  # Weekends perform 10% better
    
    def __init__(self, db_path: str):
        """Initialize predictor with database path"""
        self.db_path = db_path
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def predict(self, input_params: PredictionInput) -> PredictionResult:
        """Main prediction method"""
        # Get base statistics from database
        base_stats = self._query_base_statistics(
            input_params.origin_crs,
            input_params.destination_crs,
            input_params.toc
        )
        
        if base_stats:
            # Calculate adjusted prediction
            return self._calculate_adjusted_prediction(base_stats, input_params)
        else:
            # Use degraded prediction strategy
            return self._degraded_prediction(input_params)
    
    def _query_base_statistics(self, origin: str, destination: str, 
                              toc: Optional[str]) -> Optional[Dict]:
        """Query cached statistics from database"""
        with self._get_connection() as conn:
            # Try route-level statistics (route_statistics table doesn't have toc_code)
            # Get the most recent statistics for this route
            query = """
                SELECT * FROM route_statistics
                WHERE origin = ? AND destination = ?
                ORDER BY calculation_date DESC
                LIMIT 1
            """
            result = conn.execute(query, (origin, destination)).fetchone()
            if result:
                stats = dict(result)
                # Map column names to expected format
                mapped_stats = {
                    'on_time_rate': stats.get('on_time_percentage', 0) / 100.0,
                    'delay_5_rate': stats.get('time_to_5_percentage', 0) / 100.0,
                    'delay_10_rate': stats.get('time_to_10_percentage', 0) / 100.0,
                    'delay_30_rate': stats.get('time_to_30_percentage', 0) / 100.0,
                    'avg_delay_minutes': stats.get('avg_delay_minutes', 0),
                    'total_services': stats.get('total_services', 0)
                }
                return mapped_stats
            
            # If no route-specific data, try network average from all routes
            query = """
                SELECT 
                    AVG(on_time_percentage) / 100.0 as on_time_rate,
                    AVG(time_to_5_percentage) / 100.0 as delay_5_rate,
                    AVG(time_to_10_percentage) / 100.0 as delay_10_rate,
                    AVG(time_to_30_percentage) / 100.0 as delay_30_rate,
                    AVG(avg_delay_minutes) as avg_delay_minutes,
                    SUM(total_services) as total_services
                FROM route_statistics
                WHERE on_time_percentage IS NOT NULL
            """
            result = conn.execute(query).fetchone()
            if result and result['on_time_rate']:
                return dict(result)
            
            return None
    
    def _calculate_adjusted_prediction(self, base_stats: Dict, 
                                      input_params: PredictionInput) -> PredictionResult:
        """Apply time and day adjustments to base statistics"""
        # Get adjustment factors
        time_factor = self._get_time_adjustment_factor(
            input_params.departure_datetime.time()
        )
        day_factor = self._get_day_adjustment_factor(
            input_params.departure_datetime.date()
        )
        
        # Combined adjustment
        combined_factor = time_factor * day_factor
        
        # Adjust probabilities (inverted for on-time)
        on_time_prob = min(1.0, base_stats['on_time_rate'] / combined_factor)
        delay_5_prob = min(1.0, base_stats['delay_5_rate'] * combined_factor)
        delay_10_prob = min(1.0, base_stats['delay_10_rate'] * combined_factor)
        delay_30_prob = min(1.0, base_stats['delay_30_rate'] * combined_factor)
        
        # Adjust expected delay
        expected_delay = base_stats['avg_delay_minutes'] * combined_factor
        
        # Determine confidence level
        sample_size = base_stats.get('total_services', 0)
        confidence = self._get_confidence_level(sample_size)
        
        return PredictionResult(
            on_time_probability=on_time_prob,
            delay_5_probability=delay_5_prob,
            delay_10_probability=delay_10_prob,
            delay_30_probability=delay_30_prob,
            expected_delay_minutes=expected_delay,
            confidence=confidence,
            sample_size=sample_size,
            time_adjustment_factor=time_factor,
            day_adjustment_factor=day_factor,
            is_degraded=False,
            origin=input_params.origin_crs,
            destination=input_params.destination_crs,
            departure_time=input_params.departure_datetime,
            toc=input_params.toc
        )
    
    def _degraded_prediction(self, input_params: PredictionInput) -> PredictionResult:
        """Fallback prediction when no data available"""
        # Use ORR industry averages
        return PredictionResult(
            on_time_probability=0.643,  # ~64.3% PPM industry average
            delay_5_probability=0.25,
            delay_10_probability=0.15,
            delay_30_probability=0.05,
            expected_delay_minutes=5.1,
            confidence=ConfidenceLevel.VERY_LOW,
            sample_size=0,
            time_adjustment_factor=1.0,
            day_adjustment_factor=1.0,
            is_degraded=True,
            degradation_reason="Using UK rail network average (no route-specific data)",
            origin=input_params.origin_crs,
            destination=input_params.destination_crs,
            departure_time=input_params.departure_datetime,
            toc=input_params.toc
        )
    
    def _get_time_adjustment_factor(self, departure_time: time) -> float:
        """Get adjustment factor based on time of day"""
        hour = departure_time.hour
        for (start, end), factor in self.TIME_FACTORS.items():
            if start <= hour < end:
                return factor
        return 1.0
    
    def _get_day_adjustment_factor(self, departure_date: date) -> float:
        """Get adjustment factor based on day of week"""
        # 0 = Monday, 6 = Sunday
        if departure_date.weekday() in [5, 6]:  # Weekend
            return self.WEEKEND_FACTOR
        return self.WEEKDAY_FACTOR
    
    def _get_confidence_level(self, sample_size: int) -> ConfidenceLevel:
        """Determine confidence level based on sample size"""
        if sample_size >= 100:
            return ConfidenceLevel.HIGH
        elif sample_size >= 30:
            return ConfidenceLevel.MEDIUM
        elif sample_size >= 10:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW


def predict_delay(db_path: str, origin: str, destination: str, 
                 departure_datetime: datetime, toc: Optional[str] = None) -> PredictionResult:
    """Convenience function for delay prediction"""
    predictor = DelayPredictor(db_path)
    input_params = PredictionInput(
        origin_crs=origin,
        destination_crs=destination,
        departure_datetime=departure_datetime,
        toc=toc
    )
    return predictor.predict(input_params)


def get_prediction_explanation(result: PredictionResult) -> str:
    """Generate user-friendly explanation of prediction"""
    explanation_parts = []
    
    # Main prediction
    if result.on_time_probability >= 0.75:
        explanation_parts.append(
            f"这趟列车有较大概率准点 (准点率 {result.on_time_probability:.1%})。"
        )
    elif result.on_time_probability >= 0.5:
        explanation_parts.append(
            f"这趟列车准点率中等 ({result.on_time_probability:.1%})。"
        )
    else:
        explanation_parts.append(
            f"这趟列车延误风险较高 (准点率仅 {result.on_time_probability:.1%})。"
        )
    
    # Expected delay
    if result.expected_delay_minutes >= 1:
        explanation_parts.append(
            f"预计平均延误 {result.expected_delay_minutes:.1f} 分钟。"
        )
    
    # Confidence
    if result.confidence == ConfidenceLevel.HIGH:
        explanation_parts.append(
            f"基于 {result.sample_size} 个历史班次的数据。"
        )
    elif result.confidence == ConfidenceLevel.MEDIUM:
        explanation_parts.append(
            f"基于 {result.sample_size} 个班次（置信度中等）。"
        )
    elif result.confidence == ConfidenceLevel.LOW:
        explanation_parts.append(
            f"基于 {result.sample_size} 个班次（数据有限）。"
        )
    else:
        explanation_parts.append("数据样本较少，预测仅供参考。")
    
    # Degradation warning
    if result.is_degraded:
        explanation_parts.append(f"⚠️ {result.degradation_reason}")
    
    return " ".join(explanation_parts)
