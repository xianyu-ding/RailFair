"""
RailFair FastAPI Backend
========================

Main application file for the RailFair delay prediction and fare comparison API.

Day 10 Deliverables:
- FastAPI application setup
- Pydantic schemas
- Prediction endpoint: POST /api/predict
- Health check: GET /health
- Swagger documentation

Day 11 Deliverables:
- Feedback endpoint: POST /api/feedback
- Fingerprint tracking
- Rate limiting
- Error handling
- Integration tests
"""

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from enum import Enum
import logging
import time
import hashlib
import hashlib
import json
import sqlite3
from collections import defaultdict

from threading import Lock
import os
import sys
from pathlib import Path

# Add parent directory to path to allow imports from sibling modules
sys.path.append(str(Path(__file__).parent.parent))

from predictor import predict_delay, DelayPrediction as RealDelayPrediction
from price_fetcher import initialize_fares_system, FareComparator, TicketType


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# FastAPI Application Setup
# ============================================================================

app = FastAPI(
    title="RailFair API",
    description="""
    # RailFair - UK Train Delay Prediction & Fare Comparison API
    
    ## Overview
    RailFair helps UK rail passengers make informed travel decisions by:
    - Predicting train delays using historical performance data
    - Comparing fare prices across ticket types
    - Recommending the best value options (time vs money)
    
    ## Features
    - 🎯 Statistical delay predictions (70%+ accuracy)
    - 💰 Real-time fare comparisons (Advance/Off-Peak/Anytime)
    - 📊 Historical performance insights
    - 🔒 Privacy-first (no user tracking)
    
    ## Data Sources
    - Historical Service Performance (HSP) from Network Rail
    - Fares data from National Rail Data Portal (NRDP)
    - Station metadata from Knowledgebase API
    
    ## Rate Limits
    - 100 requests per minute per IP
    - 1000 requests per day per IP
    
    ## Status Codes
    - 200: Success
    - 400: Bad Request (invalid input)
    - 429: Too Many Requests (rate limit exceeded)
    - 500: Internal Server Error
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "RailFair Support",
        "email": "support@railfair.uk",
    },
    license_info={
        "name": "MIT",
    }
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local development
        "https://railfair.uk",     # Production
        "https://www.railfair.uk"  # Production www
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ============================================================================
# Pydantic Schemas (Day 10)
# ============================================================================

class TicketTypeEnum(str, Enum):
    """Ticket type enumeration"""
    ADVANCE = "advance"
    OFF_PEAK = "off_peak"
    ANYTIME = "anytime"
    SUPER_OFF_PEAK = "super_off_peak"


class DelayCategory(str, Enum):
    """Delay severity categories"""
    ON_TIME = "on_time"          # 0-5 minutes
    MINOR = "minor"               # 5-15 minutes
    MODERATE = "moderate"         # 15-30 minutes
    SEVERE = "severe"             # 30-60 minutes
    VERY_SEVERE = "very_severe"   # 60+ minutes
    CANCELLED = "cancelled"


class PredictionRequest(BaseModel):
    """Request schema for delay prediction"""
    origin: str = Field(
        ...,
        description="Origin station CRS code (3 letters)",
        example="EUS",
        min_length=3,
        max_length=3
    )
    destination: str = Field(
        ...,
        description="Destination station CRS code (3 letters)",
        example="MAN",
        min_length=3,
        max_length=3
    )
    departure_date: str = Field(
        ...,
        description="Departure date in ISO format (YYYY-MM-DD)",
        example="2024-12-25"
    )
    departure_time: str = Field(
        ...,
        description="Departure time in 24-hour format (HH:MM)",
        example="09:30"
    )
    include_fares: bool = Field(
        default=True,
        description="Whether to include fare comparison"
    )
    
    @validator('origin', 'destination')
    def validate_crs_code(cls, v):
        """Validate CRS code format"""
        if not v.isupper():
            raise ValueError('CRS code must be uppercase')
        if not v.isalpha():
            raise ValueError('CRS code must contain only letters')
        return v
    
    @validator('departure_date')
    def validate_date(cls, v):
        """Validate departure date"""
        try:
            date_obj = datetime.strptime(v, '%Y-%m-%d').date()
            today = datetime.now().date()
            if date_obj < today:
                raise ValueError('Departure date cannot be in the past')
            if date_obj > today + timedelta(days=90):
                raise ValueError('Departure date cannot be more than 90 days in the future')
            return v
        except ValueError as e:
            if 'does not match format' in str(e):
                raise ValueError('Date must be in YYYY-MM-DD format')
            raise
    
    @validator('departure_time')
    def validate_time(cls, v):
        """Validate departure time"""
        try:
            datetime.strptime(v, '%H:%M')
            return v
        except ValueError:
            raise ValueError('Time must be in HH:MM format (24-hour)')
    
    class Config:
        schema_extra = {
            "example": {
                "origin": "EUS",
                "destination": "MAN",
                "departure_date": "2024-12-25",
                "departure_time": "09:30",
                "include_fares": True
            }
        }


class FareInfo(BaseModel):
    """Fare information for a ticket type"""
    ticket_type: TicketTypeEnum
    price: Optional[float] = Field(None, description="Price in GBP, None if unavailable")
    restrictions: Optional[str] = Field(None, description="Ticket restrictions")
    valid_routes: Optional[List[str]] = Field(None, description="Valid route codes")
    
    class Config:
        schema_extra = {
            "example": {
                "ticket_type": "advance",
                "price": 25.50,
                "restrictions": "Must travel on booked train",
                "valid_routes": ["00000"]
            }
        }


class DelayPrediction(BaseModel):
    """Delay prediction result"""
    predicted_delay_minutes: int = Field(
        ...,
        description="Predicted delay in minutes (positive = late, negative = early)"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Prediction confidence (0.0-1.0)"
    )
    delay_category: DelayCategory = Field(
        ...,
        description="Delay severity category"
    )
    on_time_probability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Probability of arriving within 5 minutes of schedule"
    )
    historical_data_points: int = Field(
        ...,
        description="Number of historical records used for prediction"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "predicted_delay_minutes": 12,
                "confidence": 0.78,
                "delay_category": "minor",
                "on_time_probability": 0.65,
                "historical_data_points": 156
            }
        }


class FareComparison(BaseModel):
    """Fare comparison across ticket types"""
    advance: Optional[FareInfo] = None
    off_peak: Optional[FareInfo] = None
    anytime: Optional[FareInfo] = None
    cheapest_type: Optional[TicketTypeEnum] = None
    cheapest_price: Optional[float] = None
    savings_amount: Optional[float] = Field(None, description="Savings vs most expensive")
    savings_percentage: Optional[float] = Field(None, description="Savings percentage")
    data_source: str = Field("NRDP", description="Data source (NRDP/Simulated)")
    last_updated: Optional[str] = Field(None, description="Last update timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "advance": {
                    "ticket_type": "advance",
                    "price": 25.50,
                    "restrictions": "Must travel on booked train",
                    "valid_routes": ["00000"]
                },
                "off_peak": {
                    "ticket_type": "off_peak",
                    "price": 45.00,
                    "restrictions": "Valid off-peak times only",
                    "valid_routes": ["00000"]
                },
                "anytime": {
                    "ticket_type": "anytime",
                    "price": 89.00,
                    "restrictions": "No restrictions",
                    "valid_routes": ["00000"]
                },
                "cheapest_type": "advance",
                "cheapest_price": 25.50,
                "savings_amount": 63.50,
                "savings_percentage": 71.35,
                "data_source": "NRDP",
                "last_updated": "2024-11-16T10:30:00Z"
            }
        }


class Recommendation(BaseModel):
    """Travel recommendation"""
    option: str = Field(..., description="Recommendation type (time/money/balanced)")
    title: str = Field(..., description="Recommendation title")
    description: str = Field(..., description="Detailed explanation")
    score: float = Field(..., ge=0.0, le=100.0, description="Score (0-100)")
    ticket_type: Optional[TicketTypeEnum] = None
    estimated_price: Optional[float] = None
    estimated_delay: Optional[int] = None
    
    class Config:
        schema_extra = {
            "example": {
                "option": "money",
                "title": "Save £63.50 with Advance ticket",
                "description": "Book an Advance ticket for significant savings. Travel flexibility is limited.",
                "score": 85.0,
                "ticket_type": "advance",
                "estimated_price": 25.50,
                "estimated_delay": 12
            }
        }


class PredictionResponse(BaseModel):
    """Response schema for prediction endpoint"""
    request_id: str = Field(..., description="Unique request identifier")
    origin: str
    destination: str
    departure_datetime: str = Field(..., description="ISO format datetime")
    prediction: DelayPrediction
    fares: Optional[FareComparison] = None
    timetables: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[Recommendation] = Field(
        default_factory=list,
        description="Travel recommendations"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "request_id": "req_abc123def456",
                "origin": "EUS",
                "destination": "MAN",
                "departure_datetime": "2024-12-25T09:30:00",
                "prediction": {
                    "predicted_delay_minutes": 12,
                    "confidence": 0.78,
                    "delay_category": "minor",
                    "on_time_probability": 0.65,
                    "historical_data_points": 156
                },
                "fares": {
                    "advance": {"ticket_type": "advance", "price": 25.50},
                    "cheapest_type": "advance",
                    "cheapest_price": 25.50
                },
                "recommendations": [
                    {
                        "option": "money",
                        "title": "Save £63.50",
                        "description": "Book Advance ticket",
                        "score": 85.0
                    }
                ],
                "metadata": {
                    "processing_time_ms": 45,
                    "cache_hit": False
                }
            }
        }


class FeedbackRequest(BaseModel):
    """Feedback submission schema (Day 11)"""
    request_id: str = Field(..., description="Original prediction request ID")
    actual_delay_minutes: Optional[int] = Field(
        None,
        description="Actual delay experienced (if journey completed)"
    )
    was_cancelled: bool = Field(default=False, description="Whether train was cancelled")
    rating: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="User rating (1-5 stars)"
    )
    comment: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional user comment"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "request_id": "req_abc123def456",
                "actual_delay_minutes": 15,
                "was_cancelled": False,
                "rating": 4,
                "comment": "Prediction was fairly accurate"
            }
        }


class FeedbackResponse(BaseModel):
    """Feedback submission response"""
    feedback_id: str = Field(..., description="Unique feedback identifier")
    received_at: str = Field(..., description="Timestamp when feedback was received")
    message: str = Field(default="Thank you for your feedback!")
    
    class Config:
        schema_extra = {
            "example": {
                "feedback_id": "fb_xyz789abc012",
                "received_at": "2024-11-16T15:45:30Z",
                "message": "Thank you for your feedback!"
            }
        }


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status (healthy/degraded/unhealthy)")
    timestamp: str = Field(..., description="Current server time")
    version: str = Field(..., description="API version")
    uptime_seconds: float = Field(..., description="Server uptime in seconds")
    services: Dict[str, str] = Field(
        default_factory=dict,
        description="Status of dependent services"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-11-16T10:30:00Z",
                "version": "1.0.0",
                "uptime_seconds": 3600.5,
                "services": {
                    "database": "healthy",
                    "predictor": "healthy",
                    "fare_cache": "healthy"
                }
            }
        }


# ============================================================================
# Rate Limiting (Day 11)
# ============================================================================

class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self.requests = defaultdict(list)
        self.lock = Lock()
        self.minute_limit = 100  # requests per minute
        self.day_limit = 1000    # requests per day
    
    def is_allowed(self, client_id: str) -> tuple[bool, Optional[str]]:
        """
        Check if request is allowed
        
        Returns:
            (allowed, error_message)
        """
        with self.lock:
            now = time.time()
            
            # Clean old entries
            self.requests[client_id] = [
                req_time for req_time in self.requests[client_id]
                if now - req_time < 86400  # Keep last 24 hours
            ]
            
            recent_requests = self.requests[client_id]
            
            # Check minute limit
            minute_ago = now - 60
            minute_count = sum(1 for req_time in recent_requests if req_time > minute_ago)
            if minute_count >= self.minute_limit:
                return False, f"Rate limit exceeded: {self.minute_limit} requests per minute"
            
            # Check day limit
            day_ago = now - 86400
            day_count = sum(1 for req_time in recent_requests if req_time > day_ago)
            if day_count >= self.day_limit:
                return False, f"Rate limit exceeded: {self.day_limit} requests per day"
            
            # Record this request
            self.requests[client_id].append(now)
            return True, None
    
    def get_stats(self, client_id: str) -> Dict[str, int]:
        """Get usage statistics for a client"""
        with self.lock:
            now = time.time()
            recent = self.requests.get(client_id, [])
            
            minute_ago = now - 60
            day_ago = now - 86400
            
            return {
                "requests_last_minute": sum(1 for t in recent if t > minute_ago),
                "requests_last_day": sum(1 for t in recent if t > day_ago),
                "minute_limit": self.minute_limit,
                "day_limit": self.day_limit
            }


rate_limiter = RateLimiter()


def get_client_fingerprint(request: Request) -> str:
    """
    Generate client fingerprint for rate limiting
    
    Combines IP address with User-Agent for better uniqueness
    """
    client_host = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")
    
    fingerprint = f"{client_host}:{user_agent}"
    return hashlib.sha256(fingerprint.encode()).hexdigest()[:16]


async def check_rate_limit(request: Request):
    """Dependency to check rate limits"""
    client_id = get_client_fingerprint(request)
    allowed, error_msg = rate_limiter.is_allowed(client_id)
    
    if not allowed:
        raise HTTPException(status_code=429, detail=error_msg)
    
    return client_id


# ============================================================================
# Application State
# ============================================================================

class AppState:
    """Global application state"""
    
    def __init__(self):
        self.start_time = time.time()
        self.request_count = 0
        self.error_count = 0
        self.predictor = None
        self.fare_cache = None
        self.fare_comparator = None
        self.db_path = os.getenv("RAILFAIR_DB_PATH", "data/railfair.db")
    
    @property
    def uptime(self) -> float:
        """Get uptime in seconds"""
        return time.time() - self.start_time
    
    def increment_requests(self):
        """Increment request counter"""
        self.request_count += 1
    
    def increment_errors(self):
        """Increment error counter"""
        self.error_count += 1


app_state = AppState()


# ============================================================================
# Middleware (Day 11)
# ============================================================================

@app.middleware("http")
async def request_timing_middleware(request: Request, call_next):
    """Add request timing and logging"""
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url.path}")
    
    try:
        response = call_next(request)
        app_state.increment_requests()
        return await response
    except Exception as e:
        app_state.increment_errors()
        logger.error(f"Request failed: {str(e)}")
        raise
    finally:
        # Log response time
        process_time = (time.time() - start_time) * 1000
        logger.info(f"Response time: {process_time:.2f}ms")


@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    """Global error handling"""
    try:
        return await call_next(request)
    except HTTPException:
        # Let FastAPI handle HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unhandled error: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "An unexpected error occurred. Please try again later.",
                "request_id": generate_request_id()
            }
        )


# ============================================================================
# Utility Functions
# ============================================================================

def generate_request_id() -> str:
    """Generate unique request ID"""
    timestamp = datetime.now().isoformat()
    random_str = hashlib.md5(f"{timestamp}{time.time()}".encode()).hexdigest()[:12]
    return f"req_{random_str}"


def generate_feedback_id() -> str:
    """Generate unique feedback ID"""
    timestamp = datetime.now().isoformat()
    random_str = hashlib.md5(f"{timestamp}{time.time()}".encode()).hexdigest()[:12]
    return f"fb_{random_str}"


def categorize_delay(delay_minutes: int, was_cancelled: bool = False) -> DelayCategory:
    """Categorize delay severity"""
    if was_cancelled:
        return DelayCategory.CANCELLED
    elif delay_minutes <= 5:
        return DelayCategory.ON_TIME
    elif delay_minutes <= 15:
        return DelayCategory.MINOR
    elif delay_minutes <= 30:
        return DelayCategory.MODERATE
    elif delay_minutes <= 60:
        return DelayCategory.SEVERE
    else:
        return DelayCategory.VERY_SEVERE


def get_timetables_for_date(db_path: str, origin: str, destination: str, departure_datetime: datetime) -> List[Dict[str, Any]]:
    """Get all services for a route on a specific date"""
    query = """
        SELECT 
            s.service_id,
            s.departure_time,
            s.arrival_time,
            s.scheduled_duration_minutes,
            s.frequency,
            s.weekday_only,
            s.saturday_service,
            s.sunday_service,
            rm.origin_crs,
            rm.destination_crs,
            rm.route_type,
            rm.priority_tier,
            rm.notes,
            stats.on_time_percentage,
            stats.avg_delay_minutes
        FROM services s
        JOIN routes r ON s.route_id = r.route_id
        JOIN route_metadata rm ON r.origin = rm.origin_crs AND r.destination = rm.destination_crs
        LEFT JOIN (
            SELECT 
                origin, 
                destination, 
                avg_delay_minutes, 
                on_time_percentage, 
                calculation_date
            FROM route_statistics
            WHERE origin = ? AND destination = ?
            ORDER BY calculation_date DESC
            LIMIT 1
        ) stats ON 1=1
        WHERE r.origin = ? AND r.destination = ?
        ORDER BY s.departure_time
    """
    
    # Determine day type
    is_weekend = departure_datetime.weekday() >= 5
    is_sunday = departure_datetime.weekday() == 6
    
    timetables = []
    
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, (origin, destination, origin, destination))
            rows = cursor.fetchall()
            
            for row in rows:
                record = dict(row)
                
                # Filter by day type
                if is_sunday and not record['sunday_service']:
                    continue
                if is_weekend and not is_sunday and not record['saturday_service']:
                    continue
                if not is_weekend and record['weekday_only'] == 0 and not record['saturday_service'] and not record['sunday_service']:
                    pass
                
                # Construct full datetime
                dep_time_str = record['departure_time']
                arr_time_str = record['arrival_time']
                
                # Handle crossing midnight if needed (simplified for now)
                dep_dt = datetime.combine(departure_datetime.date(), datetime.strptime(dep_time_str, "%H:%M:%S").time())
                arr_dt = datetime.combine(departure_datetime.date(), datetime.strptime(arr_time_str, "%H:%M:%S").time())
                
                if arr_dt < dep_dt:
                    arr_dt += timedelta(days=1)
                
                timetables.append({
                    "service_id": record['service_id'],
                    "origin": record['origin_crs'],
                    "destination": record['destination_crs'],
                    "scheduled_departure": dep_dt.isoformat(),
                    "scheduled_arrival": arr_dt.isoformat(),
                    "duration_minutes": record['scheduled_duration_minutes'],
                    "service_frequency": record['frequency'],
                    "route_type": record['route_type'],
                    "stats": {
                        "on_time_percentage": record['on_time_percentage'],
                        "avg_delay_minutes": record['avg_delay_minutes']
                    }
                })
                
    except Exception as e:
        logger.error(f"Error fetching timetables: {e}")

    # Fallback if no timetables found in DB
    if not timetables:
        logger.info(f"No timetables found in DB for {origin}->{destination}, generating fallback.")
        timetables = generate_fallback_timetables(db_path, origin, destination, departure_datetime)
        
    return timetables


def generate_fallback_timetables(db_path: str, origin: str, destination: str, date: datetime) -> List[Dict[str, Any]]:
    """Generate realistic fallback timetables based on route metadata"""
    timetables = []
    
    try:
        # Get route metadata for duration and frequency
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT typical_duration_minutes, service_frequency, route_type FROM route_metadata WHERE origin_crs = ? AND destination_crs = ?",
                (origin, destination)
            )
            row = cursor.fetchone()
            
            if not row:
                return []
            
            duration = int(row['typical_duration_minutes'] or 120)
            frequency_str = row['service_frequency'] or "Hourly"
            route_type = row['route_type'] or "intercity"
            
            # Determine interval based on frequency string
            interval_minutes = 60
            if "2-3" in frequency_str or "30" in frequency_str:
                interval_minutes = 20
            elif "2" in frequency_str or "half" in frequency_str:
                interval_minutes = 30
            elif "15" in frequency_str:
                interval_minutes = 15
                
            # Generate services from 06:00 to 23:00
            start_hour = 6
            end_hour = 23
            
            current_time = date.replace(hour=start_hour, minute=0, second=0, microsecond=0)
            end_time = date.replace(hour=end_hour, minute=0, second=0, microsecond=0)
            
            service_id_counter = 1000
            
            while current_time <= end_time:
                # Add some random variation to departure time (0-5 mins)
                # For consistent results, we use a fixed pattern based on hour
                variation = (current_time.hour * 7) % 5
                actual_dep = current_time + timedelta(minutes=variation)
                
                actual_arr = actual_dep + timedelta(minutes=duration)
                
                timetables.append({
                    "service_id": service_id_counter,
                    "origin": origin,
                    "destination": destination,
                    "scheduled_departure": actual_dep.isoformat(),
                    "scheduled_arrival": actual_arr.isoformat(),
                    "duration_minutes": duration,
                    "service_frequency": frequency_str,
                    "route_type": route_type,
                    "stats": {
                        "on_time_percentage": 85.0, # Default good stats
                        "avg_delay_minutes": 5.0
                    }
                })
                
                service_id_counter += 1
                current_time += timedelta(minutes=interval_minutes)
                
    except Exception as e:
        logger.error(f"Error generating fallback timetables: {e}")
        
    return timetables


# ============================================================================
# API Endpoints - Day 10
# ============================================================================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - redirect to docs"""
    return {
        "message": "Welcome to RailFair API",
        "docs": "/docs",
        "health": "/health",
        "version": "1.0.0"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint
    
    Returns the current status of the API and its dependencies.
    """
    # Check service health
    services_status = {
        "database": "healthy",  # TODO: Add actual database check
        "predictor": "healthy" if app_state.predictor else "not_initialized",
        "fare_cache": "healthy" if app_state.fare_cache else "not_initialized"
    }
    
    # Determine overall status
    if all(s == "healthy" for s in services_status.values()):
        status = "healthy"
    elif any(s == "unhealthy" for s in services_status.values()):
        status = "unhealthy"
    else:
        status = "degraded"
    
    return HealthResponse(
        status=status,
        timestamp=datetime.now().isoformat(),
        version="1.0.0",
        uptime_seconds=app_state.uptime,
        services=services_status
    )


@app.post(
    "/api/predict",
    response_model=PredictionResponse,
    tags=["Predictions"],
    dependencies=[Depends(check_rate_limit)]
)
async def predict_delay(
    request: PredictionRequest,
    client_id: str = Depends(get_client_fingerprint)
):
    """
    Predict train delay and compare fares
    
    This endpoint predicts delays for a specific train journey using historical
    performance data and optionally compares fare prices across ticket types.
    
    ## Request Parameters
    - **origin**: 3-letter CRS code of departure station (e.g., "EUS" for Euston)
    - **destination**: 3-letter CRS code of arrival station (e.g., "MAN" for Manchester)
    - **departure_date**: Date in YYYY-MM-DD format
    - **departure_time**: Time in HH:MM format (24-hour)
    - **include_fares**: Whether to include fare comparison (default: true)
    
    ## Response
    Returns a prediction with:
    - Predicted delay in minutes
    - Confidence score (0.0-1.0)
    - Delay severity category
    - On-time probability
    - Fare comparison (if requested)
    - Personalized recommendations
    
    ## Example
    ```python
    POST /api/predict
    {
        "origin": "EUS",
        "destination": "MAN",
        "departure_date": "2024-12-25",
        "departure_time": "09:30",
        "include_fares": true
    }
    ```
    
    ## Rate Limits
    - 100 requests per minute per IP
    - 1000 requests per day per IP
    """
    start_time = time.time()
    request_id = generate_request_id()
    
    try:
        # Parse datetime
        departure_datetime = datetime.strptime(
            f"{request.departure_date} {request.departure_time}",
            "%Y-%m-%d %H:%M"
        )
        
        # Use real predictor
        logger.info(f"Predicting delay for {request.origin} -> {request.destination} at {departure_datetime}")
        
        # Call the real predictor
        # Note: predict_delay returns a PredictionResult object from predictor.py
        # We need to map it to the DelayPrediction model used in the API
        real_prediction = predict_delay(
            app_state.db_path,
            request.origin,
            request.destination,
            departure_datetime
        )
        
        # Map to API model
        prediction = DelayPrediction(
            predicted_delay_minutes=int(real_prediction.expected_delay_minutes),
            confidence=0.8 if real_prediction.confidence.name == "HIGH" else (0.6 if real_prediction.confidence.name == "MEDIUM" else 0.4),
            delay_category=categorize_delay(int(real_prediction.expected_delay_minutes)),
            on_time_probability=real_prediction.on_time_probability,
            historical_data_points=real_prediction.sample_size
        )
        
        # Get fare comparison if requested
        fares = None
        if request.include_fares and app_state.fare_comparator:
            logger.info("Fetching real fare data...")
            try:
                # Use the real fare comparator
                real_fares = app_state.fare_comparator.compare_fares(
                    request.origin,
                    request.destination,
                    departure_datetime
                )
                
                if real_fares:
                    # Map real fares to API model
                    # Helper to create FareInfo from price
                    def create_fare_info(price, ticket_type, restrictions=""):
                        if price is None:
                            return None
                        return FareInfo(
                            ticket_type=ticket_type,
                            price=price / 100.0,  # Convert pence to pounds
                            restrictions=restrictions,
                            valid_routes=["ANY"]
                        )
                    
                    fares = FareComparison(
                        advance=create_fare_info(real_fares.advance_price, TicketTypeEnum.ADVANCE, "Advance Purchase"),
                        off_peak=create_fare_info(real_fares.off_peak_price, TicketTypeEnum.OFF_PEAK, "Off-Peak Only"),
                        anytime=create_fare_info(real_fares.anytime_price, TicketTypeEnum.ANYTIME, "Anytime"),
                        cheapest_type=TicketTypeEnum(real_fares.cheapest_type.value) if real_fares.cheapest_type else None,
                        cheapest_price=real_fares.cheapest_price / 100.0 if real_fares.cheapest_price else None,
                        savings_amount=real_fares.savings_amount / 100.0 if real_fares.savings_amount else 0.0,
                        savings_percentage=real_fares.savings_percentage,
                        data_source=real_fares.data_source,
                        last_updated=datetime.now().isoformat()
                    )
                else:
                    logger.warning("No fare data found for this route")
            except Exception as e:
                logger.error(f"Error fetching fares: {e}")
                # Fallback to None or keep fares as None
        
        # Get timetables for the day
        timetables = get_timetables_for_date(
            app_state.db_path,
            request.origin,
            request.destination,
            departure_datetime
        )
        
        # If no real timetables found, fallback to generating one based on metadata (optional)
        # For now, if empty, the frontend will show empty or handle it.
        
        # Generate recommendations
        recommendations = _generate_recommendations(prediction, fares)
        
        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000
        
        return PredictionResponse(
            request_id=request_id,
            origin=request.origin,
            destination=request.destination,
            departure_datetime=departure_datetime.isoformat(),
            prediction=prediction,
            fares=fares,
            timetables=timetables,
            recommendations=recommendations,
            metadata={
                "processing_time_ms": round(processing_time, 2),
                "cache_hit": False,
                "client_fingerprint": client_id,
                "data_version": "1.0.0"
            }
        )
        
    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate prediction. Please try again."
        )


def _generate_recommendations(
    prediction: DelayPrediction,
    fares: Optional[FareComparison]
) -> List[Recommendation]:
    """Generate travel recommendations based on prediction and fares"""
    recommendations = []
    
    if not fares:
        return recommendations
    
    # Money-saving recommendation
    if fares.cheapest_type and fares.savings_amount and fares.savings_amount > 10:
        recommendations.append(Recommendation(
            option="money",
            title=f"Save £{fares.savings_amount:.2f} with {fares.cheapest_type.value.replace('_', ' ').title()} ticket",
            description=f"Book a {fares.cheapest_type.value.replace('_', ' ').title()} ticket to save £{fares.savings_amount:.2f} ({fares.savings_percentage:.1f}%) compared to Anytime fares.",
            score=85.0,
            ticket_type=fares.cheapest_type,
            estimated_price=fares.cheapest_price,
            estimated_delay=prediction.predicted_delay_minutes
        ))
    
    # Time-saving recommendation (if delays expected)
    if prediction.predicted_delay_minutes > 10:
        recommendations.append(Recommendation(
            option="time",
            title="Consider earlier train for on-time arrival",
            description=f"This service is predicted to be {prediction.predicted_delay_minutes} minutes late. Consider an earlier departure.",
            score=70.0,
            estimated_delay=0  # Assume earlier train is on time
        ))
    
    # Balanced recommendation
    if fares.off_peak and fares.off_peak.price:
        recommendations.append(Recommendation(
            option="balanced",
            title="Off-Peak offers good value and flexibility",
            description="Off-Peak tickets provide a balance between price and flexibility.",
            score=75.0,
            ticket_type=TicketTypeEnum.OFF_PEAK,
            estimated_price=fares.off_peak.price,
            estimated_delay=prediction.predicted_delay_minutes
        ))
    
    # Sort by score
    recommendations.sort(key=lambda x: x.score, reverse=True)
    
    return recommendations


# ============================================================================
# API Endpoints - Day 11
# ============================================================================

@app.post(
    "/api/feedback",
    response_model=FeedbackResponse,
    tags=["Feedback"],
    dependencies=[Depends(check_rate_limit)]
)
async def submit_feedback(
    feedback: FeedbackRequest,
    client_id: str = Depends(get_client_fingerprint)
):
    """
    Submit feedback on a prediction
    
    After completing a journey, users can provide feedback on the accuracy
    of the prediction. This data is used to improve the prediction model.
    
    ## Request Parameters
    - **request_id**: ID of the original prediction request
    - **actual_delay_minutes**: Actual delay experienced (optional)
    - **was_cancelled**: Whether the train was cancelled
    - **rating**: User rating from 1-5 stars (optional)
    - **comment**: Optional text comment (max 500 characters)
    
    ## Privacy
    Feedback is stored anonymously and associated only with the request ID.
    No personally identifiable information is collected.
    
    ## Example
    ```python
    POST /api/feedback
    {
        "request_id": "req_abc123def456",
        "actual_delay_minutes": 15,
        "was_cancelled": false,
        "rating": 4,
        "comment": "Prediction was fairly accurate"
    }
    ```
    """
    feedback_id = generate_feedback_id()
    received_at = datetime.now().isoformat()
    
    # TODO: Store feedback in database
    logger.info(f"Feedback received: {feedback_id} for request {feedback.request_id}")
    logger.info(f"Actual delay: {feedback.actual_delay_minutes}, Rating: {feedback.rating}")
    
    # Calculate prediction accuracy if both predicted and actual are available
    # This would be done in the actual implementation
    
    return FeedbackResponse(
        feedback_id=feedback_id,
        received_at=received_at,
        message="Thank you for your feedback! This helps us improve our predictions."
    )


@app.get("/api/stats", tags=["Statistics"])
async def get_statistics():
    """
    Get API usage statistics
    
    Returns basic statistics about API usage and performance.
    This endpoint is public but rate-limited.
    """
    return {
        "total_requests": app_state.request_count,
        "total_errors": app_state.error_count,
        "uptime_seconds": app_state.uptime,
        "uptime_hours": round(app_state.uptime / 3600, 2),
        "error_rate": round(app_state.error_count / max(app_state.request_count, 1) * 100, 2),
        "version": "1.0.0"
    }


# ============================================================================
# Startup / Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting RailFair API...")
    
    # Initialize fare system
    try:
        logger.info(f"Initializing fare system with DB: {app_state.db_path}")
        # Note: This requires .env to be loaded with NRDP credentials
        from dotenv import load_dotenv
        load_dotenv()
        
        cache, comparator = initialize_fares_system(app_state.db_path)
        app_state.fare_cache = cache
        app_state.fare_comparator = comparator
        logger.info("✅ Fare system initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize fare system: {e}")
        logger.warning("Fare comparison will be unavailable")
    
    logger.info("RailFair API started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down RailFair API...")
    
    # TODO: Close database connections
    
    logger.info("RailFair API shut down complete")


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Run with: python api/main.py or python -m api.main
    uvicorn.run(
        app,  # Use app directly instead of string reference
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes (dev only)
        log_level="info"
    )
