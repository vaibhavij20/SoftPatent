"""
Caching utilities for performance optimization.

This module provides a simple caching mechanism to store and retrieve
function results based on their input parameters.
"""
import functools
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple, TypeVar, cast

# Type variable for generic function typing
F = TypeVar('F', bound=Callable[..., Any])

class CacheManager:
    """
    A simple disk-based cache manager for function results.
    
    This class provides methods to cache function results on disk and retrieve them
    based on function arguments. It uses a hash of the function name and arguments
    as the cache key.
    """
    
    def __init__(self, cache_dir: str = ".cache"):
        """
        Initialize the cache manager.
        
        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_key(self, func_name: str, *args, **kwargs) -> str:
        """
        Generate a cache key from function name and arguments.
        
        Args:
            func_name: Name of the function being cached
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            A string representing the cache key
        """
        # Convert args and kwargs to a stable string representation
        args_str = json.dumps(args, sort_keys=True, default=str)
        kwargs_str = json.dumps(kwargs, sort_keys=True, default=str)
        key_str = f"{func_name}:{args_str}:{kwargs_str}"
        
        # Create a hash of the key string
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def get(self, key: str) -> Any:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        cache_file = self.cache_dir / f"{key}.json"
        if not cache_file.exists():
            return None
            
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
    
    def set(self, key: str, value: Any) -> None:
        """
        Store a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
        """
        cache_file = self.cache_dir / f"{key}.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(value, f)
        except (TypeError, OSError) as e:
            print(f"Warning: Failed to cache value: {e}")
    
    def clear(self) -> None:
        """Clear all cached values."""
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
            except OSError:
                pass

def cached(cache_manager: Optional[CacheManager] = None) -> Callable[[F], F]:
    """
    Decorator to cache function results.
    
    Example:
        @cached()
        def expensive_function(x, y):
            # ... expensive computation ...
            return result
    
    Args:
        cache_manager: Optional CacheManager instance. If None, a default one will be used.
        
    Returns:
        A decorator that caches function results
    """
    if cache_manager is None:
        cache_manager = CacheManager()
    
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            key = cache_manager._get_cache_key(
                f"{func.__module__}.{func.__name__}",
                *args,
                **{k: v for k, v in kwargs.items() if k != 'use_cache'}
            )
            
            # Check if we should use cache (default: True)
            use_cache = kwargs.pop('use_cache', True)
            
            # Try to get from cache
            if use_cache:
                cached_result = cache_manager.get(key)
                if cached_result is not None:
                    return cached_result
            
            # Call the function
            result = func(*args, **kwargs)
            
            # Cache the result
            if use_cache and result is not None:
                try:
                    cache_manager.set(key, result)
                except Exception as e:
                    print(f"Warning: Failed to cache result for {func.__name__}: {e}")
            
            return result
        
        return cast(F, wrapper)
    
    return decorator

def get_default_cache() -> CacheManager:
    """
    Get the default cache manager instance.
    
    Returns:
        A CacheManager instance with default settings
    """
    if not hasattr(get_default_cache, '_instance'):
        get_default_cache._instance = CacheManager()  # type: ignore
    return get_default_cache._instance  # type: ignore
