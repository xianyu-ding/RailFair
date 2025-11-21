"""
Database Connection Pool Manager
================================

Provides connection pooling for SQLite/PostgreSQL with SQLAlchemy
for optimal database connection management.

Features:
- Connection pooling with configurable size
- Query optimization and monitoring
- Automatic connection recycling
- Graceful degradation
- Performance metrics
"""

import os
import time
import logging
from typing import Optional, Dict, Any, List, Tuple
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from sqlalchemy import create_engine, event, pool, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool, NullPool, StaticPool
import sqlite3

# Configure logging
logger = logging.getLogger(__name__)

# Database configuration from environment
DB_URL = os.getenv("DATABASE_URL", "sqlite:///data/railfair.db")
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", 20))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", 10))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", 30))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", 3600))
DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"


@dataclass
class ConnectionPoolMetrics:
    """Database connection pool metrics"""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    overflow_connections: int = 0
    total_queries: int = 0
    slow_queries: int = 0
    query_errors: int = 0
    total_query_time_ms: float = 0
    
    @property
    def avg_query_time_ms(self) -> float:
        """Calculate average query time"""
        return self.total_query_time_ms / self.total_queries if self.total_queries > 0 else 0
    
    @property
    def pool_usage_percent(self) -> float:
        """Calculate pool usage percentage"""
        if self.total_connections > 0:
            return (self.active_connections / self.total_connections) * 100
        return 0


class DatabasePool:
    """Database connection pool manager with SQLAlchemy"""
    
    def __init__(self, 
                 url: str = None,
                 pool_size: int = None,
                 max_overflow: int = None,
                 pool_timeout: int = None,
                 pool_recycle: int = None):
        """
        Initialize database connection pool
        
        Args:
            url: Database URL
            pool_size: Number of persistent connections
            max_overflow: Maximum overflow connections
            pool_timeout: Timeout for getting connection
            pool_recycle: Time to recycle connections
        """
        self.url = url or DB_URL
        self.pool_size = pool_size or DB_POOL_SIZE
        self.max_overflow = max_overflow or DB_MAX_OVERFLOW
        self.pool_timeout = pool_timeout or DB_POOL_TIMEOUT
        self.pool_recycle = pool_recycle or DB_POOL_RECYCLE
        self.metrics = ConnectionPoolMetrics()
        
        # Create engine with appropriate pool class
        self.engine = self._create_engine()
        
        # Set up event listeners
        self._setup_event_listeners()
        
        # Create indexes for optimization
        self._create_indexes()
        
        logger.info(f"✅ Database pool initialized with size={self.pool_size}, max_overflow={self.max_overflow}")
    
    def _create_engine(self) -> Engine:
        """Create SQLAlchemy engine with connection pool"""
        # Determine pool class based on database type
        if self.url.startswith("sqlite"):
            # SQLite specific configuration
            if ":memory:" in self.url or "mode=memory" in self.url:
                # Use StaticPool for in-memory SQLite
                poolclass = StaticPool
                pool_kwargs = {
                    "connect_args": {"check_same_thread": False}
                }
            else:
                # Use NullPool for file-based SQLite (no real pooling)
                poolclass = NullPool
                pool_kwargs = {
                    "connect_args": {"check_same_thread": False}
                }
        else:
            # Use QueuePool for PostgreSQL/MySQL
            poolclass = QueuePool
            pool_kwargs = {
                "pool_size": self.pool_size,
                "max_overflow": self.max_overflow,
                "timeout": self.pool_timeout,
                "pool_recycle": self.pool_recycle,
                "pool_pre_ping": True  # Verify connections before using
            }
        
        # Create engine
        engine = create_engine(
            self.url,
            poolclass=poolclass,
            echo=DB_ECHO,
            **pool_kwargs
        )
        
        return engine
    
    def _setup_event_listeners(self):
        """Set up SQLAlchemy event listeners for monitoring"""
        
        @event.listens_for(self.engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            """Handle new connection creation"""
            self.metrics.total_connections += 1
            logger.debug(f"New connection created, total: {self.metrics.total_connections}")
            
            # Enable SQLite optimizations
            if isinstance(dbapi_conn, sqlite3.Connection):
                dbapi_conn.execute("PRAGMA journal_mode=WAL")
                dbapi_conn.execute("PRAGMA synchronous=NORMAL")
                dbapi_conn.execute("PRAGMA cache_size=10000")
                dbapi_conn.execute("PRAGMA temp_store=MEMORY")
        
        @event.listens_for(self.engine, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            """Handle connection checkout from pool"""
            self.metrics.active_connections += 1
            self.metrics.idle_connections = max(0, self.metrics.idle_connections - 1)
        
        @event.listens_for(self.engine, "checkin")
        def receive_checkin(dbapi_conn, connection_record):
            """Handle connection return to pool"""
            self.metrics.active_connections = max(0, self.metrics.active_connections - 1)
            self.metrics.idle_connections += 1
    
    def _create_indexes(self):
        """Create database indexes for query optimization"""
        try:
            with self.get_connection() as conn:
                # Create indexes for existing tables
                indexes = [
                    # Indexes for HSP tables (actual table names)
                    "CREATE INDEX IF NOT EXISTS idx_hsp_metrics_route ON hsp_service_metrics(origin, destination)",
                    "CREATE INDEX IF NOT EXISTS idx_hsp_metrics_toc ON hsp_service_metrics(toc_code)",
                    "CREATE INDEX IF NOT EXISTS idx_hsp_details_rid ON hsp_service_details(rid)",
                    "CREATE INDEX IF NOT EXISTS idx_hsp_details_date ON hsp_service_details(date_of_service)",
                    
                    # Create indexes for fare_cache table (actual table name)
                    "CREATE INDEX IF NOT EXISTS idx_fare_cache_route ON fare_cache(origin, destination)",
                    "CREATE INDEX IF NOT EXISTS idx_fare_cache_ticket ON fare_cache(ticket_type)",
                    "CREATE INDEX IF NOT EXISTS idx_fare_cache_updated ON fare_cache(updated_at)",
                    
                    # Create indexes for stats tracking
                    "CREATE INDEX IF NOT EXISTS idx_route_stats ON route_statistics(origin, destination)",
                    "CREATE INDEX IF NOT EXISTS idx_route_stats_date ON route_statistics(calculation_date)"
                ]
                
                for idx_sql in indexes:
                    conn.execute(text(idx_sql))
                
                conn.commit()
                logger.info(f"✅ Created {len(indexes)} database indexes for optimization")
                
        except Exception as e:
            logger.warning(f"Failed to create indexes: {e}")
    
    @contextmanager
    def get_connection(self):
        """
        Get database connection from pool
        
        Yields:
            Database connection
        """
        conn = None
        start_time = time.time()
        
        try:
            conn = self.engine.connect()
            yield conn
            
            # Track successful query
            elapsed_ms = (time.time() - start_time) * 1000
            self.metrics.total_queries += 1
            self.metrics.total_query_time_ms += elapsed_ms
            
            # Track slow queries (>100ms)
            if elapsed_ms > 100:
                self.metrics.slow_queries += 1
                logger.warning(f"Slow query detected: {elapsed_ms:.1f}ms")
                
        except Exception as e:
            self.metrics.query_errors += 1
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, query: str, params: Dict = None) -> List[Dict]:
        """
        Execute SELECT query and return results
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of result dictionaries
        """
        with self.get_connection() as conn:
            result = conn.execute(text(query), params or {})
            
            # Convert to list of dicts
            if result.returns_rows:
                columns = result.keys()
                return [dict(zip(columns, row)) for row in result.fetchall()]
            return []
    
    def execute_update(self, query: str, params: Dict = None) -> int:
        """
        Execute UPDATE/INSERT/DELETE query
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Number of affected rows
        """
        with self.get_connection() as conn:
            result = conn.execute(text(query), params or {})
            conn.commit()
            return result.rowcount
    
    def execute_many(self, query: str, params_list: List[Dict]) -> int:
        """
        Execute bulk INSERT/UPDATE
        
        Args:
            query: SQL query string
            params_list: List of parameter dictionaries
            
        Returns:
            Total affected rows
        """
        total_affected = 0
        with self.get_connection() as conn:
            for params in params_list:
                result = conn.execute(text(query), params)
                total_affected += result.rowcount
            conn.commit()
        return total_affected
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get connection pool status"""
        pool = self.engine.pool
        
        # Update metrics based on pool type
        if hasattr(pool, 'size'):
            self.metrics.total_connections = pool.size()
        if hasattr(pool, 'checked_out'):
            self.metrics.active_connections = pool.checkedout()
        if hasattr(pool, 'overflow'):
            self.metrics.overflow_connections = pool.overflow()
        
        self.metrics.idle_connections = self.metrics.total_connections - self.metrics.active_connections
        
        return {
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "total_connections": self.metrics.total_connections,
            "active_connections": self.metrics.active_connections,
            "idle_connections": self.metrics.idle_connections,
            "overflow_connections": self.metrics.overflow_connections,
            "pool_usage_percent": f"{self.metrics.pool_usage_percent:.1f}%"
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get database metrics"""
        return {
            **self.get_pool_status(),
            "total_queries": self.metrics.total_queries,
            "slow_queries": self.metrics.slow_queries,
            "query_errors": self.metrics.query_errors,
            "avg_query_time_ms": round(self.metrics.avg_query_time_ms, 2),
            "total_query_time_ms": round(self.metrics.total_query_time_ms, 2)
        }
    
    def health_check(self) -> bool:
        """Check database health"""
        try:
            with self.get_connection() as conn:
                result = conn.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def close(self):
        """Close all connections in the pool"""
        self.engine.dispose()
        logger.info("Database pool closed")


# Optimized query functions
class OptimizedQueries:
    """Collection of optimized database queries"""
    
    @staticmethod
    def get_prediction_data(pool: DatabasePool, 
                           origin: str, 
                           destination: str, 
                           toc: str = None) -> Dict[str, Any]:
        """Get optimized prediction data from route_statistics"""
        # Use route_statistics table which contains pre-calculated statistics
            query = """
                SELECT 
                on_time_percentage / 100.0 as on_time_rate,
                avg_delay_minutes as avg_delay,
                total_services as sample_size,
                0.0 as delay_stddev
            FROM route_statistics
            WHERE origin = :origin 
            AND destination = :destination
            ORDER BY calculation_date DESC
            LIMIT 1
            """
            params = {"origin": origin, "destination": destination}
        
        results = pool.execute_query(query, params)
        return results[0] if results else {}
    
    @staticmethod
    def get_popular_routes(pool: DatabasePool, limit: int = 10) -> List[Dict]:
        """Get most popular routes from route_statistics"""
        query = """
            SELECT 
                origin,
                destination,
                total_services as query_count,
                avg_delay_minutes as avg_delay,
                on_time_percentage / 100.0 as on_time_rate
            FROM route_statistics
            WHERE calculation_date > date('now', '-30 days')
            ORDER BY total_services DESC
            LIMIT :limit
        """
        return pool.execute_query(query, {"limit": limit})
    
    @staticmethod
    def get_route_statistics(pool: DatabasePool, 
                            origin: str, 
                            destination: str) -> Dict[str, Any]:
        """Get detailed route statistics from route_statistics table"""
        query = """
            SELECT 
                total_services,
                avg_delay_minutes as avg_delay,
                max_delay_minutes as max_delay,
                median_delay_minutes as median_delay,
                on_time_percentage,
                time_to_5_percentage as delay_5_percentage,
                time_to_10_percentage as delay_10_percentage,
                time_to_30_percentage as delay_30_percentage,
                cancelled_percentage,
                reliability_score,
                reliability_grade,
                calculation_date
            FROM route_statistics
            WHERE origin = :origin 
            AND destination = :destination
            ORDER BY calculation_date DESC
            LIMIT 1
        """
        results = pool.execute_query(query, {"origin": origin, "destination": destination})
        return results[0] if results else {}


# Singleton pool instance
_pool_instance: Optional[DatabasePool] = None

def get_db_pool() -> DatabasePool:
    """Get or create database pool instance"""
    global _pool_instance
    if _pool_instance is None:
        _pool_instance = DatabasePool()
    return _pool_instance


def close_db_pool():
    """Close database pool"""
    global _pool_instance
    if _pool_instance:
        _pool_instance.close()
        _pool_instance = None


# Export public interface
__all__ = [
    'DatabasePool',
    'get_db_pool',
    'close_db_pool',
    'OptimizedQueries',
    'ConnectionPoolMetrics'
]
