"""
Retry utilities for handling API failures and network issues.
"""

import asyncio
import time
from typing import Callable, Any, Optional, Type, Union, Tuple
from functools import wraps
import logging


class RetryError(Exception):
    """Custom exception for retry failures."""
    pass


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    logger: Optional[logging.Logger] = None
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between attempts in seconds
        backoff_factor: Multiplier for delay after each failure
        exceptions: Tuple of exception types to catch and retry
        logger: Logger instance for logging retry attempts
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        # Last attempt failed
                        if logger:
                            logger.error(f"Function {func.__name__} failed after {max_attempts} attempts: {e}")
                        raise RetryError(f"Function {func.__name__} failed after {max_attempts} attempts") from e
                    
                    if logger:
                        logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {current_delay}s...")
                    
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff_factor
            
            # This should never be reached, but just in case
            raise RetryError(f"Function {func.__name__} failed after {max_attempts} attempts") from last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        # Last attempt failed
                        if logger:
                            logger.error(f"Function {func.__name__} failed after {max_attempts} attempts: {e}")
                        raise RetryError(f"Function {func.__name__} failed after {max_attempts} attempts") from e
                    
                    if logger:
                        logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {current_delay}s...")
                    
                    time.sleep(current_delay)
                    current_delay *= backoff_factor
            
            # This should never be reached, but just in case
            raise RetryError(f"Function {func.__name__} failed after {max_attempts} attempts") from last_exception
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class RetryManager:
    """Context manager for retry operations."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff_factor: float = 2.0,
        exceptions: Tuple[Type[Exception], ...] = (Exception,),
        logger: Optional[logging.Logger] = None
    ):
        self.max_attempts = max_attempts
        self.delay = delay
        self.backoff_factor = backoff_factor
        self.exceptions = exceptions
        self.logger = logger
        self.current_delay = delay
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic."""
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except self.exceptions as e:
                last_exception = e
                
                if attempt == self.max_attempts - 1:
                    if self.logger:
                        self.logger.error(f"Function {func.__name__} failed after {self.max_attempts} attempts: {e}")
                    raise RetryError(f"Function {func.__name__} failed after {self.max_attempts} attempts") from e
                
                if self.logger:
                    self.logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {self.current_delay}s...")
                
                if asyncio.iscoroutinefunction(func):
                    await asyncio.sleep(self.current_delay)
                else:
                    time.sleep(self.current_delay)
                
                self.current_delay *= self.backoff_factor
        
        raise RetryError(f"Function {func.__name__} failed after {self.max_attempts} attempts") from last_exception


def with_retry(
    func: Callable,
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    logger: Optional[logging.Logger] = None
) -> Callable:
    """
    Apply retry logic to a function without using decorator syntax.
    
    Returns a new function with retry logic applied.
    """
    retry_manager = RetryManager(max_attempts, delay, backoff_factor, exceptions, logger)
    
    async def async_wrapper(*args, **kwargs) -> Any:
        return await retry_manager.execute(func, *args, **kwargs)
    
    def sync_wrapper(*args, **kwargs) -> Any:
        return asyncio.run(retry_manager.execute(func, *args, **kwargs))
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper

