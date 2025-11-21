"""
Load Testing Script for RailFair API
====================================

Uses Locust to simulate realistic user behavior and test API performance
under various load conditions.

Installation:
    pip install locust

Usage:
    # Run with web UI
    locust -f api/load_test.py --host=http://localhost:8000
    
    # Run headless
    locust -f api/load_test.py --host=http://localhost:8000 --headless -u 100 -r 10 -t 60s
    
    # Where:
    # -u: Number of users
    # -r: Spawn rate (users per second)
    # -t: Test duration
"""

from locust import HttpUser, task, between, events
import random
import json
from datetime import datetime, timedelta, date
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test data
STATIONS = [
    "EUS", "KGX", "PAD", "VIC", "WAT", "LBG", "CST", "LST", "STP", "MOG",
    "MAN", "BHM", "LDS", "NCL", "GLA", "EDI", "BRI", "CDF", "LIV", "NWP",
    "RDG", "OXF", "CBG", "NRW", "BRI", "PLY", "EXD", "SOU", "BRG", "YRK"
]

TOCS = [
    "VT", "GW", "EM", "LM", "SR", "SE", "SW", "XC", "TP", "NT",
    "GR", "AW", "CC", "CH", "CS", "GX", "HC", "HX", "IL", "LE"
]

POPULAR_ROUTES = [
    ("EUS", "MAN"), ("KGX", "EDI"), ("PAD", "RDG"), ("VIC", "BRG"),
    ("EUS", "BHM"), ("KGX", "YRK"), ("PAD", "BRI"), ("WAT", "SOU"),
    ("LBG", "BRG"), ("CST", "NCL"), ("LST", "NRW"), ("STP", "CBG"),
    ("MAN", "LDS"), ("BHM", "NCL"), ("GLA", "EDI"), ("LIV", "MAN")
]

# Performance tracking
class PerformanceTracker:
    """Track performance metrics across all users"""
    
    def __init__(self):
        self.response_times = []
        self.cache_hits = 0
        self.cache_misses = 0
        self.errors = 0
        self.start_time = None
    
    def record_response(self, response_time_ms: float, cache_hit: bool):
        """Record response metrics"""
        self.response_times.append(response_time_ms)
        if cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
    
    def record_error(self):
        """Record error"""
        self.errors += 1
    
    def get_summary(self):
        """Get performance summary"""
        if not self.response_times:
            return {"message": "No data collected yet"}
        
        sorted_times = sorted(self.response_times)
        return {
            "total_requests": len(self.response_times),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": round(self.cache_hits / len(self.response_times) * 100, 1) if self.response_times else 0,
            "errors": self.errors,
            "error_rate": round(self.errors / (len(self.response_times) + self.errors) * 100, 1) if self.response_times else 0,
            "response_times": {
                "min_ms": round(min(sorted_times), 2),
                "p50_ms": round(sorted_times[len(sorted_times) // 2], 2),
                "p95_ms": round(sorted_times[int(len(sorted_times) * 0.95)], 2),
                "p99_ms": round(sorted_times[int(len(sorted_times) * 0.99)], 2),
                "max_ms": round(max(sorted_times), 2),
                "avg_ms": round(sum(sorted_times) / len(sorted_times), 2)
            }
        }

performance_tracker = PerformanceTracker()

# Event handlers for test lifecycle
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Initialize test"""
    performance_tracker.start_time = time.time()
    logger.info("🚀 Load test started")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print test summary"""
    duration = time.time() - performance_tracker.start_time if performance_tracker.start_time else 0
    summary = performance_tracker.get_summary()
    
    logger.info("=" * 60)
    logger.info("📊 LOAD TEST SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Test Duration: {duration:.1f} seconds")
    logger.info(f"Total Requests: {summary.get('total_requests', 0)}")
    logger.info(f"Cache Hit Rate: {summary.get('cache_hit_rate', 0)}%")
    logger.info(f"Error Rate: {summary.get('error_rate', 0)}%")
    
    if "response_times" in summary:
        rt = summary["response_times"]
        logger.info(f"\nResponse Times:")
        logger.info(f"  Min: {rt['min_ms']}ms")
        logger.info(f"  P50: {rt['p50_ms']}ms")
        logger.info(f"  P95: {rt['p95_ms']}ms")
        logger.info(f"  P99: {rt['p99_ms']}ms")
        logger.info(f"  Max: {rt['max_ms']}ms")
        logger.info(f"  Avg: {rt['avg_ms']}ms")
    
    # Performance assessment
    if summary.get('total_requests', 0) > 0:
        p95 = summary.get('response_times', {}).get('p95_ms', 0)
        hit_rate = summary.get('cache_hit_rate', 0)
        
        logger.info("\n🎯 Performance Goals:")
        logger.info(f"  P95 < 40ms: {'✅ PASS' if p95 < 40 else '❌ FAIL'} ({p95}ms)")
        logger.info(f"  Cache Hit Rate > 70%: {'✅ PASS' if hit_rate > 70 else '❌ FAIL'} ({hit_rate}%)")
        logger.info(f"  Error Rate < 1%: {'✅ PASS' if summary.get('error_rate', 0) < 1 else '❌ FAIL'} ({summary.get('error_rate', 0)}%)")
    
    logger.info("=" * 60)


class RailFairUser(HttpUser):
    """Simulated RailFair API user"""
    
    # Wait between requests (simulating real user behavior)
    wait_time = between(1, 3)
    
    def on_start(self):
        """Initialize user session"""
        self.popular_routes = POPULAR_ROUTES
        self.query_count = 0
        self.use_cache = True  # Start with cache enabled
    
    def get_random_route(self):
        """Get a random route (80% popular, 20% random)"""
        if random.random() < 0.8 and self.popular_routes:
            # Use popular route
            return random.choice(self.popular_routes)
        else:
            # Random route
            origin = random.choice(STATIONS)
            destination = random.choice([s for s in STATIONS if s != origin])
            return (origin, destination)
    
    def get_random_datetime(self):
        """Get random future datetime"""
        days_ahead = random.randint(1, 30)
        departure_date = date.today() + timedelta(days=days_ahead)
        hour = random.randint(6, 22)
        minute = random.choice([0, 15, 30, 45])
        departure_time = f"{hour:02d}:{minute:02d}"
        return departure_date.isoformat(), departure_time
    
    @task(10)
    def predict_single_route(self):
        """Test single route prediction (most common)"""
        origin, destination = self.get_random_route()
        departure_date, departure_time = self.get_random_datetime()
        
        # Randomly include fare comparison (30% of requests)
        include_fares = random.random() < 0.3
        
        # Randomly specify TOC (20% of requests)
        toc = random.choice(TOCS) if random.random() < 0.2 else None
        
        # Disable cache for 10% of requests to test cache miss performance
        use_cache = False if random.random() < 0.1 else True
        
        payload = {
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "departure_time": departure_time,
            "include_fares": include_fares,
            "use_cache": use_cache
        }
        
        if toc:
            payload["toc"] = toc
        
        with self.client.post(
            "/api/predict",
            json=payload,
            catch_response=True
        ) as response:
            try:
                if response.status_code == 200:
                    data = response.json()
                    
                    # Extract performance metrics
                    processing_time = data.get("metadata", {}).get("processing_time_ms", 0)
                    cache_status = data.get("metadata", {}).get("cache_status", "UNKNOWN")
                    
                    # Record metrics
                    performance_tracker.record_response(
                        processing_time,
                        cache_status == "HIT"
                    )
                    
                    # Validate response structure
                    if "prediction" not in data:
                        response.failure("Missing prediction in response")
                    elif processing_time > 100:
                        response.failure(f"Slow response: {processing_time}ms")
                    else:
                        response.success()
                else:
                    response.failure(f"Status code: {response.status_code}")
                    performance_tracker.record_error()
                    
            except Exception as e:
                response.failure(str(e))
                performance_tracker.record_error()
    
    @task(2)
    def predict_batch_routes(self):
        """Test batch prediction (less common)"""
        num_routes = random.randint(2, 5)
        routes = []
        
        for _ in range(num_routes):
            origin, destination = self.get_random_route()
            departure_date, departure_time = self.get_random_datetime()
            
            routes.append({
                "origin": origin,
                "destination": destination,
                "departure_date": departure_date,
                "departure_time": departure_time,
                "include_fares": random.random() < 0.3
            })
        
        payload = {
            "routes": routes,
            "parallel": True
        }
        
        with self.client.post(
            "/api/predict/batch",
            json=payload,
            catch_response=True
        ) as response:
            try:
                if response.status_code == 200:
                    data = response.json()
                    processing_time = data.get("processing_time_ms", 0)
                    
                    # Batch should complete within reasonable time
                    if processing_time > 500:
                        response.failure(f"Slow batch response: {processing_time}ms")
                    else:
                        response.success()
                else:
                    response.failure(f"Status code: {response.status_code}")
                    
            except Exception as e:
                response.failure(str(e))
    
    @task(3)
    def get_popular_routes(self):
        """Test popular routes endpoint"""
        with self.client.get(
            "/api/routes/popular",
            params={"limit": random.choice([5, 10, 15])},
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")
    
    @task(3)
    def get_route_statistics(self):
        """Test route statistics endpoint"""
        origin, destination = self.get_random_route()
        
        with self.client.get(
            f"/api/routes/{origin}/{destination}/stats",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                # No data for route is acceptable
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")
    
    @task(1)
    def get_system_statistics(self):
        """Test system statistics endpoint"""
        with self.client.get(
            "/api/statistics",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                
                # Log cache hit rate periodically
                if self.query_count % 10 == 0:
                    cache_stats = data.get("cache", {})
                    logger.info(f"Cache Hit Rate: {cache_stats.get('hit_rate', 'N/A')}")
                
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")
        
        self.query_count += 1
    
    @task(1)
    def health_check(self):
        """Test health check endpoint"""
        with self.client.get(
            "/health",
            catch_response=True
        ) as response:
            if response.status_code in [200, 503]:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")


class AdminUser(HttpUser):
    """Simulated admin user for cache management"""
    
    wait_time = between(30, 60)  # Less frequent admin operations
    weight = 1  # Only 1 admin for every 10 regular users
    
    @task
    def invalidate_cache(self):
        """Periodically invalidate cache to test cache rebuilding"""
        # Randomly invalidate specific route or all
        if random.random() < 0.5:
            # Invalidate specific route
            origin, destination = random.choice(POPULAR_ROUTES)
            payload = {
                "origin": origin,
                "destination": destination,
                "cache_type": "prediction"
            }
        else:
            # Invalidate all predictions
            payload = {
                "cache_type": "prediction"
            }
        
        with self.client.post(
            "/api/cache/invalidate",
            json=payload,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                logger.info(f"Cache invalidated: {payload}")
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")


# Custom test scenarios
class SpikeTestUser(RailFairUser):
    """User for spike testing - simulates sudden traffic surge"""
    wait_time = between(0.1, 0.5)  # Much faster requests


class SoakTestUser(RailFairUser):
    """User for soak testing - sustained load over time"""
    wait_time = between(2, 5)  # Moderate pace for long-duration tests


if __name__ == "__main__":
    # Can also run directly with Python
    import sys
    from locust import main
    
    # Default arguments for standalone execution
    if len(sys.argv) == 1:
        sys.argv.extend([
            "--host=http://localhost:8000",
            "--users=50",
            "--spawn-rate=5",
            "--time=60s",
            "--headless",
            "--only-summary"
        ])
    
    main.main()
