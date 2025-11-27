"""
Day 13: Optimized FastAPI Backend with Caching and Connection Pooling
=====================================================================

Major optimizations:
- Redis caching layer for predictions and fares
- Database connection pooling with SQLAlchemy
- Async query execution for parallel operations
- Performance monitoring and metrics
- Load testing ready

Performance targets:
- P95 response time: <40ms (with cache)
- Cache hit rate: >70%
- Concurrent users: 100+
- Requests/second: 50+
"""

from fastapi import FastAPI, HTTPException, Request, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date, time, timedelta
from enum import Enum
import hashlib
import time as time_module
import logging
import uuid
import asyncio
from collections import defaultdict
from threading import Lock
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

# Import optimization modules
from api.redis_cache import (
    get_cache, 
    cached, 
    CacheTTL,
    invalidate_prediction_cache,
    invalidate_fare_cache
)
from api.db_pool import (
    get_db_pool,
    OptimizedQueries,
    close_db_pool
)

# Import existing modules
from predictor import (
    predict_delay, 
    get_prediction_explanation,
    ConfidenceLevel,
    PredictionResult
)
from price_fetcher import (
    initialize_fares_system,
    FareComparator,
    FareComparison as FareComparisonData,
    TicketType
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize services
DB_PATH = os.getenv("RAILFAIR_DB_PATH", "data/railfair.db")
cache = get_cache()
db_pool = get_db_pool()
fare_engine: Optional[FareComparator] = None

# Performance monitoring
class PerformanceMonitor:
    """Track API performance metrics"""
    
    def __init__(self):
        self.request_times = []
        self.endpoint_times = defaultdict(list)
        self.lock = Lock()
    
    def record_request(self, endpoint: str, duration_ms: float):
        """Record request performance"""
        with self.lock:
            self.request_times.append(duration_ms)
            self.endpoint_times[endpoint].append(duration_ms)
            
            # Keep only last 1000 requests
            if len(self.request_times) > 1000:
                self.request_times = self.request_times[-1000:]
            
            for ep in self.endpoint_times:
                if len(self.endpoint_times[ep]) > 100:
                    self.endpoint_times[ep] = self.endpoint_times[ep][-100:]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        with self.lock:
            if not self.request_times:
                return {"message": "No requests recorded yet"}
            
            sorted_times = sorted(self.request_times)
            p50 = sorted_times[len(sorted_times) // 2]
            p95 = sorted_times[int(len(sorted_times) * 0.95)]
            p99 = sorted_times[int(len(sorted_times) * 0.99)]
            
            endpoint_stats = {}
            for endpoint, times in self.endpoint_times.items():
                if times:
                    endpoint_stats[endpoint] = {
                        "avg_ms": round(sum(times) / len(times), 2),
                        "min_ms": round(min(times), 2),
                        "max_ms": round(max(times), 2)
                    }
            
            return {
                "total_requests": len(self.request_times),
                "p50_ms": round(p50, 2),
                "p95_ms": round(p95, 2),
                "p99_ms": round(p99, 2),
                "avg_ms": round(sum(self.request_times) / len(self.request_times), 2),
                "endpoints": endpoint_stats
            }

performance_monitor = PerformanceMonitor()

# FastAPI app initialization
app = FastAPI(
    title="RailFair API - Optimized",
    description="UK Train Delay Prediction and Fare Comparison API with Redis Caching and Connection Pooling",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= Middleware =============

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header and record metrics"""
    start_time = time_module.time()
    response = await call_next(request)
    process_time_ms = (time_module.time() - start_time) * 1000
    
    # Record performance metrics
    performance_monitor.record_request(request.url.path, process_time_ms)
    
    # Add headers
    response.headers["X-Process-Time-Ms"] = str(round(process_time_ms, 2))
    response.headers["X-Cache-Status"] = getattr(request.state, 'cache_status', 'NONE')
    
    return response

# ============= Data Models =============

class PredictionRequest(BaseModel):
    """Request model for delay prediction"""
    origin: str = Field(..., min_length=3, max_length=3)
    destination: str = Field(..., min_length=3, max_length=3)
    departure_date: date = Field(...)
    departure_time: time = Field(...)
    include_fares: bool = Field(False)
    toc: Optional[str] = Field(None)
    use_cache: bool = Field(True, description="Enable caching")
    
    @validator('origin', 'destination')
    def uppercase_station(cls, v):
        return v.upper()

class BatchPredictionRequest(BaseModel):
    """Request model for batch predictions"""
    routes: List[PredictionRequest] = Field(..., max_items=10)
    parallel: bool = Field(True, description="Process routes in parallel")

# ============= Cached Functions =============

@cached("prediction", ttl=CacheTTL.PREDICTION)
def get_cached_prediction(origin: str, 
                         destination: str, 
                         departure_datetime: datetime,
                         toc: Optional[str] = None) -> Dict[str, Any]:
    """Get prediction with caching"""
    result = predict_delay(
        db_path=DB_PATH,
        origin=origin,
        destination=destination,
        departure_datetime=departure_datetime,
        toc=toc
    )
    return result.__dict__ if hasattr(result, '__dict__') else result

@cached("fare", ttl=CacheTTL.FARE)
def get_cached_fare(origin: str, 
                   destination: str,
                   departure_datetime: datetime) -> Optional[Dict[str, Any]]:
    """Get fare comparison with caching"""
    if not fare_engine:
        return None
    
    fare_data = fare_engine.compare_fares(
        origin,
        destination,
        departure_datetime
    )
    return fare_data.__dict__ if hasattr(fare_data, '__dict__') else fare_data

@cached("route_stats", ttl=CacheTTL.ROUTE_STATS)
def get_cached_route_stats(origin: str, destination: str) -> Dict[str, Any]:
    """Get route statistics with caching"""
    return OptimizedQueries.get_route_statistics(db_pool, origin, destination)

def get_timetables_for_date(origin: str, destination: str, departure_datetime: datetime) -> List[Dict[str, Any]]:
    """Get all services for a route on a specific date - with NRDP data and fallback"""
    timetables = []
    
    # First, try to load from NRDP timetable JSON cache  
    nrdp_timetable_path = Path(DB_PATH).parent / "timetable_parsed.json"
    if nrdp_timetable_path.exists():
        try:
            with open(nrdp_timetable_path, 'r', encoding='utf-8') as f:
                nrdp_data = json.load(f)
            
            # Filter services for this route
            matching_services = []
            
            # Minimum date threshold: only services valid after October 2025
            min_threshold_date = datetime(2025, 10, 1).date()
            
            for s in nrdp_data.get('services', []):
                if s.get('origin_location') != origin or s.get('destination_location') != destination:
                    continue
                
                # Check date validity - service must be valid after Oct 2025
                svc_start = s.get('start_date')
                svc_end = s.get('end_date')
                
                # Skip if service ends before October 2025
                if svc_end:
                    try:
                        svc_end_date = datetime.strptime(svc_end, '%Y-%m-%d').date()
                        if svc_end_date < min_threshold_date:
                            continue
                    except ValueError:
                        pass
                
                # Check if service is valid for the queried date
                if svc_start:
                    try:
                        svc_start_date = datetime.strptime(svc_start, '%Y-%m-%d').date()
                        if departure_datetime.date() < svc_start_date:
                            continue
                    except ValueError:
                        pass
                
                if svc_end:
                    try:
                        svc_end_date = datetime.strptime(svc_end, '%Y-%m-%d').date()
                        if departure_datetime.date() > svc_end_date:
                            continue
                    except ValueError:
                        pass
                
                # Check day of week
                days_run = s.get('days_run', [])
                if days_run:
                    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                    query_day = day_names[departure_datetime.weekday()]
                    if query_day not in days_run:
                        continue
                
                matching_services.append(s)
            
            if matching_services:
                logger.info(f"Found {len(matching_services)} services from NRDP timetable for {origin}->{destination}")
                
                # Convert NRDP services to our API format
                for nrdp_service in matching_services:
                    # Parse times
                    origin_time_str = nrdp_service.get('origin_time')
                    dest_time_str = nrdp_service.get('destination_time')
                    
                    if not origin_time_str or not dest_time_str:
                        continue
                    
                    # Parse time strings (HH:MM:SS format)
                    try:
                        parts = origin_time_str.split(':')
                        origin_time = time(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
                        
                        parts = dest_time_str.split(':')
                        dest_time = time(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
                    except (ValueError, IndexError):
                        continue
                    
                    # Construct full datetime
                    dep_dt = datetime.combine(departure_datetime.date(), origin_time)
                    arr_dt = datetime.combine(departure_datetime.date(), dest_time)
                    
                    # Handle crossing midnight
                    if arr_dt < dep_dt:
                        arr_dt += timedelta(days=1)
                    
                    # Calculate duration
                    duration = int((arr_dt - dep_dt).total_seconds() / 60)
                    
                    timetables.append({
                        "service_id": nrdp_service.get('train_uid', 'unknown'),
                        "origin": origin,
                        "destination": destination,
                        "scheduled_departure": dep_dt.isoformat(),
                        "scheduled_arrival": arr_dt.isoformat(),
                        "duration_minutes": duration,
                        "service_frequency": "",
                        "route_type": nrdp_service.get('train_category', 'unknown'),
                        "stats": {
                            "on_time_percentage": None,
                            "avg_delay_minutes": None
                        }
                    })
                
                if timetables:
                    return sorted(timetables, key=lambda x: x['scheduled_departure'])
        except Exception as e:
            logger.error(f"Error loading NRDP timetable data: {e}")
    
    # Fallback: generate realistic timetables from route metadata
    logger.info(f"No NRDP data for {origin}->{destination}, using fallback generator")
    try:
        query = """SELECT typical_duration_minutes, service_frequency, route_type 
                   FROM route_metadata WHERE origin_crs = :origin AND destination_crs = :destination"""
        results = db_pool.execute_query(query, {"origin": origin, "destination": destination})
        
        if not results:
            return []
        
        record = results[0]
        duration = int(record['typical_duration_minutes'] or 120)
        frequency_str = record['service_frequency'] or "Hourly"
        route_type = record['route_type'] or "intercity"
        
        # Determine interval
        interval_minutes = 60
        if "2-3" in frequency_str or "30" in frequency_str:
            interval_minutes = 30
        elif "2" in frequency_str or "half" in frequency_str:
            interval_minutes = 30
        elif "15" in frequency_str:
            interval_minutes = 15
        elif "hour" in frequency_str.lower():
            interval_minutes = 60
            
        # Generate services from 05:00 to 23:59
        current_time = departure_datetime.replace(hour=5, minute=0, second=0, microsecond=0)
        end_time = departure_datetime.replace(hour=23, minute=59, second=0, microsecond=0)
        
        service_id_counter = 1000
        while current_time <= end_time:
            variation = ((current_time.hour * 7 + current_time.minute // 10) * 3) % 7
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
                    "on_time_percentage": 85.0,
                    "avg_delay_minutes": 5.0
                }
            })
            
            service_id_counter += 1
            current_time += timedelta(minutes=interval_minutes)
    except Exception as e:
        logger.error(f"Error generating fallback timetables: {e}")
        
    return timetables


def _pence_to_pounds(value: Optional[Any]) -> Optional[float]:
    """Convert pence to pounds with 2 decimal precision"""
    if value is None:
        return None
    try:
        return round(float(value) / 100, 2)
    except (TypeError, ValueError):
        return None

def format_fare_response(fare_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Normalize fare payload for the frontend"""
    if not fare_data:
        return None
    
    cheapest_type = fare_data.get("cheapest_type")
    if hasattr(cheapest_type, "value"):
        cheapest_type = cheapest_type.value
    if isinstance(cheapest_type, str):
        cheapest_type = cheapest_type.upper()
    
    savings_percentage = fare_data.get("savings_percentage")
    if savings_percentage is not None:
        try:
            savings_percentage = round(float(savings_percentage), 1)
        except (TypeError, ValueError):
            savings_percentage = None
    
    cache_age_hours = fare_data.get("cache_age_hours")
    if cache_age_hours is not None:
        try:
            cache_age_hours = round(float(cache_age_hours), 2)
        except (TypeError, ValueError):
            cache_age_hours = None
    
    return {
        "advance": _pence_to_pounds(fare_data.get("advance_price")),
        "off_peak": _pence_to_pounds(fare_data.get("off_peak_price")),
        "anytime": _pence_to_pounds(fare_data.get("anytime_price")),
        "cheapest": {
            "type": cheapest_type,
            "price": _pence_to_pounds(fare_data.get("cheapest_price")),
            "savings_amount": _pence_to_pounds(fare_data.get("savings_amount")),
            "savings_percentage": savings_percentage
        },
        "meta": {
            "origin": fare_data.get("origin"),
            "destination": fare_data.get("destination"),
            "data_source": fare_data.get("data_source"),
            "cache_age_hours": cache_age_hours,
            "cached": fare_data.get("cached", True)
        }
    }

def build_timetable_payload(record: Optional[Dict[str, Any]], departure_datetime: datetime) -> Optional[Dict[str, Any]]:
    """Build timetable block from metadata"""
    if not record:
        return None
    
    duration = record.get("typical_duration_minutes")
    scheduled_arrival = None
    if duration is not None:
        try:
            duration_value = float(duration)
            scheduled_arrival = (departure_datetime + timedelta(minutes=duration_value)).isoformat()
        except (TypeError, ValueError):
            scheduled_arrival = None
    
    return {
        "origin": record.get("origin_crs"),
        "destination": record.get("destination_crs"),
        "scheduled_departure": departure_datetime.isoformat(),
        "scheduled_arrival": scheduled_arrival,
        "duration_minutes": duration,
        "service_frequency": record.get("service_frequency"),
        "route_type": record.get("route_type"),
        "priority_tier": record.get("priority_tier"),
        "notes": record.get("notes"),
        "data_source": "route_metadata",
        "metadata_updated_at": record.get("metadata_updated_at"),
        "stats": {
            "on_time_percentage": record.get("on_time_percentage"),
            "avg_delay_minutes": record.get("avg_delay_minutes"),
            "total_services": record.get("total_services"),
            "last_calculated_at": record.get("calculation_date")
        }
    }

@cached("popular_routes", ttl=CacheTTL.POPULAR_ROUTES)
def get_cached_popular_routes(limit: int = 10) -> List[Dict]:
    """Get popular routes with caching"""
    return OptimizedQueries.get_popular_routes(db_pool, limit)

# ============= API Endpoints =============

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global fare_engine
    
    # Initialize fare engine
    try:
        cache_obj, fare_engine = initialize_fares_system(DB_PATH)
        logger.info("✅ Fare engine initialized")
    except Exception as e:
        logger.warning(f"⚠️ Fare engine initialization failed: {e}")
    
    # Warm cache with popular routes
    try:
        popular_routes = OptimizedQueries.get_popular_routes(db_pool, limit=20)
        if popular_routes:
            cache.warm_cache(popular_routes)
    except Exception as e:
        logger.warning(f"Cache warming failed: {e}")
    
    # Log startup status
    logger.info("=" * 50)
    logger.info("RailFair API v2.0 - Optimized Edition")
    logger.info(f"Redis Cache: {'✅ Connected' if cache._is_available() else '❌ Not available'}")
    logger.info(f"Database Pool: {'✅ Healthy' if db_pool.health_check() else '❌ Unhealthy'}")
    logger.info(f"Fare Engine: {'✅ Ready' if fare_engine else '❌ Not available'}")
    logger.info("=" * 50)

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    close_db_pool()
    logger.info("Services shut down gracefully")

@app.get("/")
async def root():
    """Root endpoint with service status"""
    return {
        "service": "RailFair API v2.0",
        "status": "operational",
        "features": {
            "redis_cache": cache._is_available(),
            "db_pool": db_pool.health_check(),
            "fare_engine": fare_engine is not None
        },
        "documentation": "/docs"
    }

@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "api": "operational",
            "redis": "operational" if cache._is_available() else "degraded",
            "database": "operational" if db_pool.health_check() else "critical",
            "fare_engine": "operational" if fare_engine else "unavailable"
        }
    }
    
    # Determine overall status
    if not db_pool.health_check():
        health_status["status"] = "unhealthy"
    elif not cache._is_available():
        health_status["status"] = "degraded"
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    return JSONResponse(content=health_status, status_code=status_code)

@app.post("/api/predict")
async def predict_delay_endpoint(
    request: PredictionRequest,
    background_tasks: BackgroundTasks
):
    """
    Optimized prediction endpoint with caching and parallel queries
    
    Performance:
    - With cache hit: <10ms
    - With cache miss: <50ms
    - Parallel fare lookup
    """
    request_id = f"req_{uuid.uuid4().hex[:12]}"
    start_time = time_module.time()
    
    # Combine date and time
    departure_datetime = datetime.combine(
        request.departure_date,
        request.departure_time
    )
    
    # Determine cache status
    cache_key = cache._generate_key("prediction", {
        "origin": request.origin,
        "destination": request.destination,
        "departure_datetime": departure_datetime.isoformat(),
        "toc": request.toc
    })
    
    # Check cache first
    if request.use_cache:
        cached_result = cache.get(cache_key)
        if cached_result and not (isinstance(cached_result, dict) and cached_result.get("warming")):
            # Cache hit - return immediately
            return {
                "request_id": request_id,
                "cached": True,
                "data": cached_result,
                "metadata": {
                    "processing_time_ms": round((time_module.time() - start_time) * 1000, 2),
                    "cache_status": "HIT"
                }
            }
    
    # Parallel execution of prediction and fare queries
    tasks = []
    
    # Prediction task
    async def get_prediction():
        return await asyncio.get_event_loop().run_in_executor(
            None,
            get_cached_prediction,
            request.origin,
            request.destination,
            departure_datetime,
            request.toc
        )
    
    tasks.append(get_prediction())
    
    # Fare task (if requested)
    async def get_fares():
        if request.include_fares and fare_engine:
            return await asyncio.get_event_loop().run_in_executor(
                None,
                get_cached_fare,
                request.origin,
                request.destination,
                departure_datetime
            )
        return None
    
    if request.include_fares:
        tasks.append(get_fares())
    
    async def get_timetables():
        return await asyncio.get_event_loop().run_in_executor(
            None,
            get_timetables_for_date,
            request.origin,
            request.destination,
            departure_datetime
        )
    
    tasks.append(get_timetables())
    
    # Execute tasks in parallel
    results = await asyncio.gather(*tasks)
    prediction_result = results[0]
    if request.include_fares:
        fare_result = results[1]
        timetables_result = results[2]
    else:
        fare_result = None
        timetables_result = results[1]
    
    formatted_fares = format_fare_response(fare_result)
    
    # Build response
    response = {
        "request_id": request_id,
        "prediction": prediction_result,
        "fares": formatted_fares,
        "timetables": timetables_result,
        "cached": False,
        "metadata": {
            "processing_time_ms": round((time_module.time() - start_time) * 1000, 2),
            "timestamp": datetime.utcnow().isoformat(),
            "api_version": "2.0.0",
            "route": f"{request.origin}-{request.destination}",
            "cache_status": "MISS"
        }
    }
    
    # Cache the response for future requests
    if request.use_cache:
        cache.set(cache_key, response, ttl=CacheTTL.PREDICTION.value)
    
    return response

@app.post("/api/predict/batch")
async def batch_predict_endpoint(request: BatchPredictionRequest):
    """
    Batch prediction endpoint for multiple routes
    
    Processes up to 10 routes in parallel for optimal performance
    """
    start_time = time_module.time()
    
    async def process_single_route(route_request: PredictionRequest):
        """Process a single route prediction"""
        return await predict_delay_endpoint(route_request, BackgroundTasks())
    
    if request.parallel:
        # Process routes in parallel
        tasks = [process_single_route(route) for route in request.routes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    else:
        # Process routes sequentially
        results = []
        for route in request.routes:
            result = await process_single_route(route)
            results.append(result)
    
    # Filter out exceptions and format results
    successful_results = []
    failed_results = []
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            failed_results.append({
                "route_index": i,
                "error": str(result)
            })
        else:
            successful_results.append(result)
    
    return {
        "batch_id": f"batch_{uuid.uuid4().hex[:12]}",
        "total_routes": len(request.routes),
        "successful": len(successful_results),
        "failed": len(failed_results),
        "results": successful_results,
        "errors": failed_results if failed_results else None,
        "processing_time_ms": round((time_module.time() - start_time) * 1000, 2),
        "parallel_processing": request.parallel
    }

@app.get("/api/statistics")
async def get_statistics():
    """Get system statistics with caching metrics"""
    
    # Get cache metrics
    cache_metrics = cache.get_metrics()
    
    # Get database pool metrics
    db_metrics = db_pool.get_metrics()
    
    # Get performance metrics
    perf_metrics = performance_monitor.get_metrics()
    
    return {
        "cache": cache_metrics,
        "database": db_metrics,
        "performance": perf_metrics,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/routes/popular")
async def get_popular_routes_endpoint(limit: int = 10):
    """Get popular routes with caching"""
    routes = await asyncio.get_event_loop().run_in_executor(
        None,
        get_cached_popular_routes,
        limit
    )
    
    return {
        "count": len(routes),
        "routes": routes,
        "cached": True,
        "cache_ttl_seconds": CacheTTL.POPULAR_ROUTES.value
    }

@app.get("/api/routes/{origin}/{destination}/stats")
async def get_route_statistics_endpoint(origin: str, destination: str):
    """Get detailed route statistics with caching"""
    origin = origin.upper()
    destination = destination.upper()
    
    stats = await asyncio.get_event_loop().run_in_executor(
        None,
        get_cached_route_stats,
        origin,
        destination
    )
    
    if not stats or stats.get("total_services") == 0:
        raise HTTPException(status_code=404, detail="No data found for this route")
    
    return {
        "route": f"{origin}-{destination}",
        "statistics": stats,
        "cached": True,
        "cache_ttl_seconds": CacheTTL.ROUTE_STATS.value
    }

@app.get("/api/routes/{origin}/{destination}/stops")
async def get_route_stops_endpoint(origin: str, destination: str, departure_date: Optional[str] = None):
    """
    Get intermediate stops for a route from future timetable data
    
    Priority:
    1. NRDP Timetable (future scheduled services) - preferred
    2. Historical HSP data (fallback if timetable not available)
    """
    origin = origin.upper()
    destination = destination.upper()
    
    # Priority 1: Try to load from NRDP timetable parsed data
    timetable_file = Path(__file__).parent.parent / "data" / "timetable_parsed.json"
    
    if timetable_file.exists():
        try:
            import json
            with open(timetable_file, 'r', encoding='utf-8') as f:
                timetable_data = json.load(f)
            
            services = timetable_data.get('services', [])
            
            # Find services that match the route
            # Try exact match first
            matching_services = [
                s for s in services 
                if s.get('origin_location') == origin and s.get('destination_location') == destination
            ]
            
            # If no exact match, try to find services that pass through both stations
            if not matching_services:
                # This would require checking intermediate stops, which may not be in the parsed data
                pass
            
            if matching_services:
                # Filter by date if provided
                if departure_date:
                    try:
                        query_date = datetime.strptime(departure_date, '%Y-%m-%d').date()
                        matching_services = [
                            s for s in matching_services
                            if (not s.get('start_date') or s.get('start_date') <= query_date) and
                               (not s.get('end_date') or s.get('end_date') >= query_date)
                        ]
                    except ValueError:
                        pass
                
                if matching_services:
                    # Use the first matching service
                    service = matching_services[0]
                    
                    # Build stops list
                    stops = []
                    
                    # Add origin
                    if service.get('origin_location'):
                        origin_time = service.get('origin_time')
                        origin_time_str = None
                        if origin_time:
                            if isinstance(origin_time, str):
                                origin_time_str = origin_time
                            elif hasattr(origin_time, 'isoformat'):
                                origin_time_str = origin_time.isoformat()
                            else:
                                origin_time_str = str(origin_time)
                        
                        stops.append({
                            "location": service['origin_location'],
                            "location_name": service.get('origin_location'),
                            "scheduled_departure": origin_time_str,
                            "scheduled_arrival": None,
                            "is_origin": True,
                            "is_destination": False
                        })
                    
                    # Add intermediate stops (if available in parsed data)
                    intermediate_stops = service.get('intermediate_stops', [])
                    if intermediate_stops:
                        for stop in intermediate_stops:
                            dep_time = stop.get('departure') or stop.get('dep')
                            arr_time = stop.get('arrival') or stop.get('arr')
                            
                            dep_str = None
                            if dep_time:
                                if isinstance(dep_time, str):
                                    dep_str = dep_time
                                elif hasattr(dep_time, 'isoformat'):
                                    dep_str = dep_time.isoformat()
                                else:
                                    dep_str = str(dep_time)
                            
                            arr_str = None
                            if arr_time:
                                if isinstance(arr_time, str):
                                    arr_str = arr_time
                                elif hasattr(arr_time, 'isoformat'):
                                    arr_str = arr_time.isoformat()
                                else:
                                    arr_str = str(arr_time)
                            
                            stops.append({
                                "location": stop.get('location', ''),
                                "location_name": stop.get('location', ''),
                                "scheduled_departure": dep_str,
                                "scheduled_arrival": arr_str,
                                "platform": stop.get('platform', ''),
                                "is_origin": False,
                                "is_destination": False
                            })
                    
                    # Add destination
                    if service.get('destination_location'):
                        dest_time = service.get('destination_time')
                        dest_time_str = None
                        if dest_time:
                            if isinstance(dest_time, str):
                                dest_time_str = dest_time
                            elif hasattr(dest_time, 'isoformat'):
                                dest_time_str = dest_time.isoformat()
                            else:
                                dest_time_str = str(dest_time)
                        
                        stops.append({
                            "location": service['destination_location'],
                            "location_name": service.get('destination_location'),
                            "scheduled_departure": None,
                            "scheduled_arrival": dest_time_str,
                            "is_origin": False,
                            "is_destination": True
                        })
                    
                    return {
                        "route": f"{origin}-{destination}",
                        "train_uid": service.get('train_uid'),
                        "stops": stops,
                        "total_stops": len(stops),
                        "data_source": "nrdp_timetable",
                        "valid_from": str(service.get('start_date')) if service.get('start_date') else None,
                        "valid_to": str(service.get('end_date')) if service.get('end_date') else None,
                        "note": "Future timetable data" if stops else "Timetable data found but intermediate stops not available"
                    }
        except Exception as e:
            logger.warning(f"Failed to load timetable data: {e}")
    
    # Priority 2: Fallback to historical HSP data (for reference, but note it's historical)
    # This is less ideal but provides some data if timetable is not available
    query = """
        SELECT DISTINCT
            hsd.rid,
            hsd.location,
            hsd.location_name,
            hsd.scheduled_departure,
            hsd.scheduled_arrival,
            hsd.toc_code,
            hsd.toc_name
        FROM hsp_service_details hsd
        WHERE hsd.rid IN (
            SELECT DISTINCT rid
            FROM hsp_service_details
            WHERE location = :origin
        )
        AND hsd.rid IN (
            SELECT DISTINCT rid
            FROM hsp_service_details
            WHERE location = :destination
        )
        ORDER BY hsd.scheduled_departure
        LIMIT 1
    """
    
    route_rids = db_pool.execute_query(query, {"origin": origin, "destination": destination})
    
    if route_rids:
        rid = route_rids[0]["rid"]
        
        stops_query = """
            SELECT 
                location,
                location_name,
                scheduled_departure,
                scheduled_arrival,
                toc_code,
                toc_name
            FROM hsp_service_details
            WHERE rid = :rid
            ORDER BY scheduled_departure, scheduled_arrival
        """
        
        stops = db_pool.execute_query(stops_query, {"rid": rid})
        
        formatted_stops = []
        for stop in stops:
            formatted_stops.append({
                "location": stop.get("location"),
                "location_name": stop.get("location_name") or stop.get("location"),
                "scheduled_departure": stop.get("scheduled_departure"),
                "scheduled_arrival": stop.get("scheduled_arrival"),
                "toc_code": stop.get("toc_code"),
                "toc_name": stop.get("toc_name")
            })
        
        return {
            "route": f"{origin}-{destination}",
            "rid": rid,
            "stops": formatted_stops,
            "total_stops": len(formatted_stops),
            "data_source": "hsp_historical",
            "note": "⚠️ Historical data - may not reflect future schedules"
        }
    
    # No data available
    return {
        "route": f"{origin}-{destination}",
        "stops": [],
        "message": "No timetable data found for this route. Timetable data may need to be updated.",
        "data_source": None
    }

@app.post("/api/cache/invalidate")
async def invalidate_cache_endpoint(
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    cache_type: str = "prediction"
):
    """
    Invalidate cache entries
    
    Admin endpoint for cache management
    """
    if cache_type == "prediction":
        invalidate_prediction_cache(origin, destination)
    elif cache_type == "fare":
        invalidate_fare_cache()
    else:
        return {"error": "Invalid cache type"}
    
    return {
        "status": "success",
        "cache_type": cache_type,
        "origin": origin,
        "destination": destination
    }

@app.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus-compatible metrics endpoint
    
    Returns metrics in Prometheus text format
    """
    metrics = []
    
    # Cache metrics
    cache_stats = cache.get_metrics()
    metrics.append(f"# HELP cache_hits_total Total number of cache hits")
    metrics.append(f"# TYPE cache_hits_total counter")
    metrics.append(f"cache_hits_total {cache_stats['hits']}")
    
    metrics.append(f"# HELP cache_misses_total Total number of cache misses")
    metrics.append(f"# TYPE cache_misses_total counter")
    metrics.append(f"cache_misses_total {cache_stats['misses']}")
    
    metrics.append(f"# HELP cache_hit_rate Cache hit rate percentage")
    metrics.append(f"# TYPE cache_hit_rate gauge")
    metrics.append(f"cache_hit_rate {cache_stats['hit_rate'].rstrip('%')}")
    
    # Database metrics
    db_stats = db_pool.get_metrics()
    metrics.append(f"# HELP db_active_connections Active database connections")
    metrics.append(f"# TYPE db_active_connections gauge")
    metrics.append(f"db_active_connections {db_stats['active_connections']}")
    
    metrics.append(f"# HELP db_pool_usage Database pool usage percentage")
    metrics.append(f"# TYPE db_pool_usage gauge")
    metrics.append(f"db_pool_usage {db_stats['pool_usage_percent'].rstrip('%')}")
    
    # Performance metrics
    perf_stats = performance_monitor.get_metrics()
    if "p95_ms" in perf_stats:
        metrics.append(f"# HELP response_time_p95_ms 95th percentile response time")
        metrics.append(f"# TYPE response_time_p95_ms gauge")
        metrics.append(f"response_time_p95_ms {perf_stats['p95_ms']}")
    
    return "\n".join(metrics)

# ============= Main =============

if __name__ == "__main__":
    import uvicorn
    
    # Run with optimized settings
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        workers=1,  # Use 1 worker to share cache and pool
        loop="asyncio",
        log_level="info",
        access_log=True
    )
