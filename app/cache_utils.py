#!/usr/bin/env python3
"""
Cache Utilities for Stock Analyst Application
Provides caching functionality with Redis backend and fallback to simple memory cache
"""

import functools
import json
import logging
from typing import Any, Optional, Callable
from datetime import datetime, date
from flask_caching import Cache
from unified_config import get_config

# Try to import orjson for faster JSON processing
try:
    import orjson
    HAS_ORJSON = True
except ImportError:
    HAS_ORJSON = False

logger = logging.getLogger(__name__)

# Global cache instance
cache = None

def init_cache(app):
    """Initialize the cache with the Flask application"""
    global cache
    config = get_config()
    
    # Configure cache based on settings
    if config.REDIS_ENABLED:
        cache_config = {
            'CACHE_TYPE': 'redis',
            'CACHE_REDIS_HOST': config.REDIS_HOST,
            'CACHE_REDIS_PORT': config.REDIS_PORT,
            'CACHE_REDIS_DB': config.REDIS_DB,
            'CACHE_KEY_PREFIX': config.CACHE_KEY_PREFIX,
            'CACHE_DEFAULT_TIMEOUT': config.CACHE_DEFAULT_TIMEOUT,
        }
        
        if config.REDIS_PASSWORD:
            cache_config['CACHE_REDIS_PASSWORD'] = config.REDIS_PASSWORD
            
        logger.info(f"Initializing Redis cache at {config.REDIS_HOST}:{config.REDIS_PORT}")
    else:
        cache_config = {
            'CACHE_TYPE': 'simple',
            'CACHE_DEFAULT_TIMEOUT': config.CACHE_DEFAULT_TIMEOUT,
        }
        logger.info("Initializing simple memory cache")
    
    app.config.update(cache_config)
    cache = Cache(app)
    
    # Test cache connection
    try:
        cache.set('test_key', 'test_value', timeout=60)
        test_value = cache.get('test_key')
        if test_value == 'test_value':
            logger.info("Cache initialized successfully")
            cache.delete('test_key')
        else:
            logger.warning("Cache test failed - caching may not work properly")
    except Exception as e:
        logger.error(f"Cache initialization test failed: {e}")
        logger.warning("Falling back to no caching")

def get_cache():
    """Get the cache instance"""
    return cache

def cache_key(prefix: str, *args, **kwargs) -> str:
    """Generate a cache key from prefix and arguments"""
    key_parts = [prefix]
    
    # Add positional arguments
    for arg in args:
        if isinstance(arg, (str, int, float)):
            key_parts.append(str(arg))
        else:
            key_parts.append(str(hash(str(arg))))
    
    # Add keyword arguments (sorted for consistency)
    for key, value in sorted(kwargs.items()):
        key_parts.append(f"{key}:{value}")
    
    return ":".join(key_parts)

def serialize_for_cache(obj: Any) -> str:
    """Serialize object for cache storage"""
    if HAS_ORJSON:
        # orjson is faster and handles datetime objects natively
        try:
            # orjson returns bytes, so decode to string
            return orjson.dumps(obj, option=orjson.OPT_SORT_KEYS | orjson.OPT_PASSTHROUGH_DATETIME).decode('utf-8')
        except (TypeError, ValueError):
            # Fall back to standard json if orjson fails
            pass
    
    # Standard json fallback
    def date_serializer(o):
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        raise TypeError(f"Object of type {type(o)} is not JSON serializable")
    
    return json.dumps(obj, default=date_serializer, sort_keys=True)

def deserialize_from_cache(data: str) -> Any:
    """Deserialize object from cache storage"""
    if data is None:
        return None
    
    if HAS_ORJSON:
        try:
            # orjson is faster for deserialization
            return orjson.loads(data)
        except (TypeError, ValueError):
            # Fall back to standard json if orjson fails
            pass
    
    # Standard json fallback
    return json.loads(data)

def cached_function(timeout: Optional[int] = None, key_prefix: str = 'func'):
    """
    Decorator for caching function results
    
    Args:
        timeout: Cache timeout in seconds (uses config default if None)
        key_prefix: Prefix for cache keys
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not cache:
                # No cache available, execute function normally
                return func(*args, **kwargs)
            
            # Generate cache key
            cache_key_str = cache_key(key_prefix, func.__name__, *args, **kwargs)
            
            # Try to get from cache
            try:
                cached_result = cache.get(cache_key_str)
                if cached_result is not None:
                    result = deserialize_from_cache(cached_result)
                    logger.debug(f"Cache hit for {cache_key_str}")
                    return result
            except Exception as e:
                logger.warning(f"Cache get failed for {cache_key_str}: {e}")
            
            # Cache miss, execute function
            logger.debug(f"Cache miss for {cache_key_str}")
            result = func(*args, **kwargs)
            
            # Store in cache
            try:
                cache_timeout = timeout or get_config().CACHE_DEFAULT_TIMEOUT
                serialized_result = serialize_for_cache(result)
                cache.set(cache_key_str, serialized_result, timeout=cache_timeout)
                logger.debug(f"Cached result for {cache_key_str} (timeout: {cache_timeout}s)")
            except Exception as e:
                logger.warning(f"Cache set failed for {cache_key_str}: {e}")
            
            return result
        
        return wrapper
    return decorator

def invalidate_cache_pattern(pattern: str):
    """
    Invalidate cache entries matching a pattern
    
    Args:
        pattern: Pattern to match cache keys (Redis glob pattern)
    """
    if not cache:
        return
    
    try:
        if hasattr(cache.cache, 'delete_many'):
            # Redis backend
            redis_client = cache.cache._write_client
            keys = redis_client.keys(f"{get_config().CACHE_KEY_PREFIX}{pattern}")
            if keys:
                redis_client.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cache entries matching pattern: {pattern}")
        else:
            # Simple cache backend - clear all
            cache.clear()
            logger.info(f"Cleared all cache entries (pattern: {pattern})")
    except Exception as e:
        logger.error(f"Cache invalidation failed for pattern {pattern}: {e}")

def clear_cache():
    """Clear all cache entries"""
    if cache:
        try:
            cache.clear()
            logger.info("Cleared all cache entries")
        except Exception as e:
            logger.error(f"Cache clear failed: {e}")

def get_cache_stats():
    """Get cache statistics (Redis only)"""
    if not cache or not hasattr(cache.cache, 'info'):
        return None
    
    try:
        info = cache.cache.info()
        return {
            'connected_clients': info.get('connected_clients', 0),
            'used_memory': info.get('used_memory', 0),
            'used_memory_human': info.get('used_memory_human', '0B'),
            'keyspace_hits': info.get('keyspace_hits', 0),
            'keyspace_misses': info.get('keyspace_misses', 0),
            'total_commands_processed': info.get('total_commands_processed', 0),
        }
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        return None