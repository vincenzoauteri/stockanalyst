#!/usr/bin/env python3
"""
Centralized logging configuration for Stock Analyst Application
"""

import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path

def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    enable_file_logging: bool = True,
    enable_console_logging: bool = True,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
):
    """
    Set up centralized logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory to store log files
        enable_file_logging: Whether to log to files
        enable_console_logging: Whether to log to console
        max_file_size: Maximum size of each log file in bytes
        backup_count: Number of backup log files to keep
    """
    
    # Create logs directory if it doesn't exist
    if enable_file_logging:
        Path(log_dir).mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    if enable_console_logging:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handlers
    if enable_file_logging:
        # Main application log
        main_log_file = os.path.join(log_dir, 'stock_analyst.log')
        main_handler = logging.handlers.RotatingFileHandler(
            main_log_file,
            maxBytes=max_file_size,
            backupCount=backup_count
        )
        main_handler.setLevel(getattr(logging, log_level.upper()))
        main_handler.setFormatter(formatter)
        root_logger.addHandler(main_handler)
        
        # Error-only log
        error_log_file = os.path.join(log_dir, 'errors.log')
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=max_file_size,
            backupCount=backup_count
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        root_logger.addHandler(error_handler)
        
        # API requests log
        api_log_file = os.path.join(log_dir, 'api_requests.log')
        api_handler = logging.handlers.RotatingFileHandler(
            api_log_file,
            maxBytes=max_file_size,
            backupCount=backup_count
        )
        api_handler.setLevel(logging.INFO)
        api_handler.setFormatter(formatter)
        
        # Create API logger
        api_logger = logging.getLogger('api_requests')
        api_logger.addHandler(api_handler)
        api_logger.setLevel(logging.INFO)
        api_logger.propagate = False  # Don't propagate to root logger
    
    # Set specific logger levels for third-party libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    
    # Log the configuration
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Level: {log_level}, File logging: {enable_file_logging}, Console: {enable_console_logging}")
    
    return root_logger

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)

def log_function_call(func):
    """
    Decorator to log function calls with parameters and execution time
    """
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        func_name = f"{func.__module__}.{func.__name__}"
        
        # Log function entry
        logger.debug(f"Entering {func_name} with args={args}, kwargs={kwargs}")
        
        start_time = datetime.now()
        try:
            result = func(*args, **kwargs)
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.debug(f"Completed {func_name} in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Error in {func_name} after {execution_time:.3f}s: {e}")
            raise
    
    return wrapper

def log_api_request(endpoint: str, symbol: str = None, status: str = "SUCCESS", 
                   response_time: float = None, error: str = None):
    """
    Log API request details
    
    Args:
        endpoint: API endpoint called
        symbol: Stock symbol (if applicable)
        status: Request status (SUCCESS, ERROR, etc.)
        response_time: Response time in seconds
        error: Error message (if any)
    """
    api_logger = logging.getLogger('api_requests')
    
    if status == "SUCCESS":
        api_logger.info(f"API Request: {endpoint} {symbol or ''} - {status} ({response_time:.3f}s)")
    else:
        api_logger.error(f"API Request: {endpoint} {symbol or ''} - {status} - {error}")