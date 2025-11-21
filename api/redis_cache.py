"""
Redis Cache Manager for RailFair API
====================================

Provides intelligent caching for predictions, fares, and route statistics
with automatic fallback to database on cache failures.

Features:
- Connection pooling
- Automatic serialization/deserialization
- TTL management per data type
- Circuit breaker pattern
- Metrics collection
"""

import redis
import json
import hashlib
import logging
from typing import Optional, Any, Dict, Callable
from datetime import datetime, timedelta
from functools import wraps
import time
from enum import Enum
from dataclasses import dataclass, asdict
import os

# Configure logging
logger = logging.getLogger(__name__)

# Cache configuration from environment
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_POOL_SIZE = int(os.getenv("REDIS_POOL_SIZE", 20))
REDIS_TIMEOUT = int(os.getenv("REDIS_TIMEOUT", 5))

# TTL configurations (in seconds)
class CacheTTL(Enum):
    """Cache TTL configurations for different data types"""
    PREDICTION = 3600  # 1 hour for predictions
    FARE = 86400  # 24 hours for fares (matches update cycle)
    ROUTE_STATS = 21600  # 6 hours for route statistics  
    POPULAR_ROUTES = 1800  # 30 minutes for popular routes
    SYSTEM_STATS = 300  # 5 minutes for system statistics
    DEFAULT = 1800  # 30 minutes default


@dataclass
class CacheMetrics:
    """Cache performance metrics"""
    hits: int = 0
    misses: int = 0
    errors: int = 0
    total_hit_time_ms: float = 0
    total_miss_time_ms: float = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0
    
    @property
    def avg_hit_time_ms(self) -> float:
        """Average time for cache hits"""
        return self.total_hit_time_ms / self.hits if self.hits > 0 else 0
    
    @property
    def avg_miss_time_ms(self) -> float:
        """Average time for cache misses"""
        return self.total_miss_time_ms / self.misses if self.misses > 0 else 0


class RedisCache:
    """Redis cache manager with connection pooling and circuit breaker"""
    
    def __init__(self, max_retries: int = 3, circuit_breaker_threshold: int = 5):
        """
        Initialize Redis cache manager
        
        Args:
            max_retries: Maximum number of retry attempts
            circuit_breaker_threshold: Number of failures before opening circuit
        """
        self.max_retries = max_retries
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.failure_count = 0
        self.circuit_open = False
        self.circuit_open_time = None
        self.metrics = CacheMetrics()
        
        # Initialize connection pool
        self.pool = self._create_pool()
        self.redis_client = None
        self._connect()
    
    def _create_pool(self) -> redis.ConnectionPool:
        """Create Redis connection pool"""
        return redis.ConnectionPool(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            max_connections=REDIS_POOL_SIZE,
            socket_connect_timeout=REDIS_TIMEOUT,
            socket_timeout=REDIS_TIMEOUT,
            decode_responses=True
        )
    
    def _connect(self) -> None:
        """Establish Redis connection"""
        try:
            self.redis_client = redis.Redis(connection_pool=self.pool)
            self.redis_client.ping()
            logger.info(f"✅ Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
            self.failure_count = 0
            self.circuit_open = False
        except redis.ConnectionError as e:
            logger.warning(f"⚠️ Failed to connect to Redis: {e}")
            self.failure_count += 1
            self._check_circuit_breaker()
    
    def _check_circuit_breaker(self) -> None:
        """Check and manage circuit breaker state"""
        if self.failure_count >= self.circuit_breaker_threshold:
            self.circuit_open = True
            self.circuit_open_time = datetime.now()
            logger.error(f"🔴 Circuit breaker OPEN after {self.failure_count} failures")
        
        # Auto-reset circuit after 60 seconds
        if self.circuit_open and self.circuit_open_time:
            if (datetime.now() - self.circuit_open_time).seconds > 60:
                logger.info("🔄 Attempting to reset circuit breaker...")
                self.circuit_open = False
                self.failure_count = 0
                self._connect()
    
    def _is_available(self) -> bool:
        """Check if cache is available"""
        if self.circuit_open:
            self._check_circuit_breaker()
            return False
        return self.redis_client is not None
    
    def _generate_key(self, prefix: str, params: Dict[str, Any]) -> str:
        """
        Generate cache key from prefix and parameters
        
        Args:
            prefix: Cache key prefix
            params: Parameters to include in key
            
        Returns:
            Hashed cache key
        """
        # Sort params for consistent key generation
        sorted_params = sorted(params.items())
        param_str = json.dumps(sorted_params, sort_keys=True, default=str)
        hash_digest = hashlib.md5(param_str.encode()).hexdigest()[:8]
        return f"{prefix}:{hash_digest}"
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        if not self._is_available():
            self.metrics.errors += 1
            return None
        
        try:
            start_time = time.time()
            value = self.redis_client.get(key)
            elapsed_ms = (time.time() - start_time) * 1000
            
            if value:
                self.metrics.hits += 1
                self.metrics.total_hit_time_ms += elapsed_ms
                # Parse JSON if it looks like JSON
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            else:
                self.metrics.misses += 1
                self.metrics.total_miss_time_ms += elapsed_ms
                return None
                
        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            self.metrics.errors += 1
            self.failure_count += 1
            self._check_circuit_breaker()
            return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self._is_available():
            return False
        
        try:
            # Serialize complex objects
            if isinstance(value, (dict, list)):
                value = json.dumps(value, default=str)
            elif hasattr(value, '__dict__'):
                value = json.dumps(value.__dict__, default=str)
            
            # Set with TTL if provided
            if ttl:
                self.redis_client.setex(key, ttl, value)
            else:
                self.redis_client.set(key, value)
            
            return True
            
        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            self.failure_count += 1
            self._check_circuit_breaker()
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete value from cache
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False otherwise
        """
        if not self._is_available():
            return False
        
        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching pattern
        
        Args:
            pattern: Key pattern (e.g., "prediction:*")
            
        Returns:
            Number of keys deleted
        """
        if not self._is_available():
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Cache invalidation error for pattern {pattern}: {e}")
            return 0
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get cache metrics"""
        return {
            "hits": self.metrics.hits,
            "misses": self.metrics.misses,
            "errors": self.metrics.errors,
            "hit_rate": f"{self.metrics.hit_rate:.1f}%",
            "avg_hit_time_ms": round(self.metrics.avg_hit_time_ms, 2),
            "avg_miss_time_ms": round(self.metrics.avg_miss_time_ms, 2),
            "circuit_breaker_open": self.circuit_open,
            "failure_count": self.failure_count
        }
    
    def warm_cache(self, routes: list) -> None:
        """
        Pre-warm cache with popular routes
        
        Args:
            routes: List of route dictionaries with origin/destination
        """
        logger.info(f"🔥 Warming cache with {len(routes)} popular routes...")
        warmed = 0
        
        for route in routes:
            # Create cache keys for common queries
            prediction_key = self._generate_key("prediction", {
                "origin": route["origin"],
                "destination": route["destination"],
                "date": datetime.now().date().isoformat()
            })
            
            # Mark as warming (will be replaced with real data on first request)
            if self.set(prediction_key, {"warming": True}, ttl=300):
                warmed += 1
        
        logger.info(f"✅ Cache warmed with {warmed}/{len(routes)} routes")


# Singleton cache instance
_cache_instance: Optional[RedisCache] = None

def get_cache() -> RedisCache:
    """Get or create cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache()
    return _cache_instance


def cache_key_generator(prefix: str, **kwargs) -> str:
    """
    Generate cache key from prefix and keyword arguments
    
    Args:
        prefix: Cache key prefix
        **kwargs: Key parameters
        
    Returns:
        Cache key string
    """
    cache = get_cache()
    return cache._generate_key(prefix, kwargs)


def cached(prefix: str, ttl: CacheTTL = CacheTTL.DEFAULT):
    """
    Decorator for caching function results
    
    Args:
        prefix: Cache key prefix
        ttl: Time to live enum
        
    Example:
        @cached("prediction", ttl=CacheTTL.PREDICTION)
        def get_prediction(origin, destination):
            # expensive operation
            return result
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key from function arguments
            cache = get_cache()
            cache_key = cache._generate_key(prefix, kwargs)
            
            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value and not (isinstance(cached_value, dict) and cached_value.get("warming")):
                logger.debug(f"Cache HIT for {cache_key}")
                return cached_value
            
            # Execute function and cache result
            logger.debug(f"Cache MISS for {cache_key}")
            result = await func(*args, **kwargs)
            
            # Cache the result
            if result is not None:
                cache.set(cache_key, result, ttl=ttl.value)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Generate cache key from function arguments
            cache = get_cache()
            cache_key = cache._generate_key(prefix, kwargs)
            
            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value and not (isinstance(cached_value, dict) and cached_value.get("warming")):
                logger.debug(f"Cache HIT for {cache_key}")
                return cached_value
            
            # Execute function and cache result
            logger.debug(f"Cache MISS for {cache_key}")
            result = func(*args, **kwargs)
            
            # Cache the result
            if result is not None:
                cache.set(cache_key, result, ttl=ttl.value)
            
            return result
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Cache invalidation helpers
def invalidate_prediction_cache(origin: str = None, destination: str = None):
    """Invalidate prediction cache entries"""
    cache = get_cache()
    if origin and destination:
        pattern = f"prediction:*{origin}*{destination}*"
    elif origin:
        pattern = f"prediction:*{origin}*"
    elif destination:
        pattern = f"prediction:*{destination}*"
    else:
        pattern = "prediction:*"
    
    count = cache.invalidate_pattern(pattern)
    logger.info(f"Invalidated {count} prediction cache entries")


def invalidate_fare_cache():
    """Invalidate all fare cache entries"""
    cache = get_cache()
    count = cache.invalidate_pattern("fare:*")
    logger.info(f"Invalidated {count} fare cache entries")


def invalidate_all_cache():
    """Invalidate all cache entries"""
    cache = get_cache()
    try:
        cache.redis_client.flushdb()
        logger.info("Invalidated ALL cache entries")
    except Exception as e:
        logger.error(f"Failed to flush cache: {e}")


# Export public interface
__all__ = [
    'RedisCache',
    'get_cache',
    'cached',
    'CacheTTL',
    'cache_key_generator',
    'invalidate_prediction_cache',
    'invalidate_fare_cache',
    'invalidate_all_cache',
    'CacheMetrics'
]
