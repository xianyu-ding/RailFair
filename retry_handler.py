"""
Retry handler for HSP API calls with exponential backoff and jitter
"""
import time
import random
import logging
from typing import Callable, Any, Optional, Type
from functools import wraps

logger = logging.getLogger(__name__)


class RetryableError(Exception):
    """Base class for errors that should trigger a retry"""
    pass


class APIError(RetryableError):
    """API returned an error that might be temporary"""
    pass


class NetworkError(RetryableError):
    """Network connectivity issue"""
    pass


class RateLimitError(RetryableError):
    """API rate limit exceeded"""
    pass


class NonRetryableError(Exception):
    """Error that should not trigger a retry"""
    pass


class AuthenticationError(NonRetryableError):
    """Authentication failed - credentials invalid"""
    pass


class ValidationError(NonRetryableError):
    """Request validation failed - bad parameters"""
    pass


class RetryHandler:
    """
    Handle retries with exponential backoff and jitter
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for the given attempt number with exponential backoff
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff: delay = initial_delay * (base ^ attempt)
        delay = self.initial_delay * (self.exponential_base ** attempt)
        
        # Cap at max_delay
        delay = min(delay, self.max_delay)
        
        # Add jitter to avoid thundering herd
        if self.jitter:
            delay = delay * (0.5 + random.random())  # Random between 50% and 150%
        
        return delay
    
    def execute_with_retry(
        self,
        func: Callable,
        *args,
        retryable_exceptions: tuple = (RetryableError,),
        **kwargs
    ) -> Any:
        """
        Execute a function with retry logic
        
        Args:
            func: Function to execute
            *args: Positional arguments for func
            retryable_exceptions: Tuple of exception types to retry on
            **kwargs: Keyword arguments for func
            
        Returns:
            Result from func
            
        Raises:
            Last exception if all retries exhausted
        """
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                logger.debug(f"Attempt {attempt + 1}/{self.max_attempts} for {func.__name__}")
                result = func(*args, **kwargs)
                
                # Success - log if this was a retry
                if attempt > 0:
                    logger.info(f"Success on attempt {attempt + 1} for {func.__name__}")
                
                return result
                
            except retryable_exceptions as e:
                last_exception = e
                
                # Check if we should retry
                if attempt < self.max_attempts - 1:
                    delay = self.calculate_delay(attempt)
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.max_attempts} failed for {func.__name__}: "
                        f"{type(e).__name__}: {str(e)}. Retrying in {delay:.2f}s..."
                    )
                    
                    time.sleep(delay)
                else:
                    # Last attempt failed
                    logger.error(
                        f"All {self.max_attempts} attempts failed for {func.__name__}: "
                        f"{type(e).__name__}: {str(e)}"
                    )
            
            except NonRetryableError as e:
                # Don't retry these errors
                logger.error(
                    f"Non-retryable error in {func.__name__}: "
                    f"{type(e).__name__}: {str(e)}"
                )
                raise
            
            except Exception as e:
                # Unexpected error - don't retry
                logger.error(
                    f"Unexpected error in {func.__name__}: "
                    f"{type(e).__name__}: {str(e)}",
                    exc_info=True
                )
                raise
        
        # All retries exhausted
        raise last_exception


def with_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple = (RetryableError,)
):
    """
    Decorator to add retry logic to a function
    
    Usage:
        @with_retry(max_attempts=3, initial_delay=1.0)
        def my_api_call():
            # ... code that might fail ...
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            handler = RetryHandler(
                max_attempts=max_attempts,
                initial_delay=initial_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                jitter=jitter
            )
            return handler.execute_with_retry(
                func,
                *args,
                retryable_exceptions=retryable_exceptions,
                **kwargs
            )
        return wrapper
    return decorator


def classify_http_error(status_code: int, response_text: str = "") -> Exception:
    """
    Classify HTTP error and return appropriate exception
    
    Args:
        status_code: HTTP status code
        response_text: Response body text
        
    Returns:
        Appropriate exception instance
    """
    if status_code == 401 or status_code == 403:
        return AuthenticationError(f"Authentication failed: {status_code}")
    
    elif status_code == 400:
        return ValidationError(f"Invalid request: {response_text}")
    
    elif status_code == 429:
        return RateLimitError(f"Rate limit exceeded")
    
    elif 500 <= status_code < 600:
        return APIError(f"Server error: {status_code}")
    
    elif status_code == 408 or status_code == 504:
        return NetworkError(f"Timeout: {status_code}")
    
    else:
        return APIError(f"HTTP error: {status_code}")


# Example usage
if __name__ == "__main__":
    import requests
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example 1: Using decorator
    @with_retry(max_attempts=3, initial_delay=1.0)
    def fetch_data():
        logger.info("Fetching data...")
        # Simulate API call that might fail
        if random.random() < 0.7:
            raise APIError("Simulated API failure")
        return {"status": "success"}
    
    # Example 2: Using handler directly
    handler = RetryHandler(max_attempts=3, initial_delay=0.5)
    
    def another_api_call():
        logger.info("Another API call...")
        if random.random() < 0.5:
            raise NetworkError("Simulated network failure")
        return {"data": "result"}
    
    try:
        # Test decorator
        result1 = fetch_data()
        print(f"Result 1: {result1}")
        
        # Test handler
        result2 = handler.execute_with_retry(
            another_api_call,
            retryable_exceptions=(NetworkError, APIError)
        )
        print(f"Result 2: {result2}")
        
    except Exception as e:
        print(f"Failed: {e}")
