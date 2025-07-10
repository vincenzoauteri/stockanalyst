# Enhanced Logging for Stock Analyst Application

This document describes the enhanced logging system implemented to provide better context and monitoring for background tasks.

## New Logging Features

### Background Tasks Logger

A dedicated logger has been added for background tasks that writes to `logs/background_tasks.log`. This logger provides structured logging for all scheduled operations.

### Enhanced Context Logging

The new `log_background_task()` function provides structured logging with consistent format:

```python
from logging_config import log_background_task

log_background_task(
    task_name="Daily Update",
    status="COMPLETED", 
    duration=45.2,
    symbols_processed=500,
    details="Updated prices for all symbols"
)
```

### Log Format

Background task logs follow this structured format:
```
Task: {task_name} | Status: {status} | Duration: {duration}s | Symbols: {count} | Details: {details}
```

## Status Types

- **STARTED** - Task has begun execution
- **COMPLETED** - Task finished successfully
- **FAILED** - Task encountered an error
- **ERROR** - Critical error occurred

## Log Files

The application now creates the following log files:

1. **`logs/stock_analyst.log`** - Main application log
2. **`logs/errors.log`** - Error-only log
3. **`logs/api_requests.log`** - API request tracking
4. **`logs/background_tasks.log`** - Background task execution details

## Enhanced Scheduler Logging

The scheduler now provides detailed logging for:

### Daily Updates
- Start/completion timing
- Success/failure status
- Duration tracking
- Failure details

Example output:
```
Task: Daily Update | Status: STARTED
Task: Daily Update | Status: COMPLETED | Duration: 45.20s
```

### Health Checks
- Gap detection results
- Performance metrics
- Detailed breakdown of gap types

Example output:
```
Task: Health Check | Status: COMPLETED | Duration: 2.15s | Details: Found 15 gaps - price_data: 10, profile_data: 5
```

### Catchup Operations
- Symbols processed
- Success rates
- Performance metrics

## Usage in Code

### Basic Background Task Logging
```python
from logging_config import log_background_task
import time

start_time = time.time()
log_background_task("My Task", "STARTED")

try:
    # Do work
    symbols_processed = process_data()
    duration = time.time() - start_time
    log_background_task("My Task", "COMPLETED", 
                       duration=duration, 
                       symbols_processed=symbols_processed)
except Exception as e:
    duration = time.time() - start_time
    log_background_task("My Task", "FAILED", 
                       duration=duration, 
                       details=str(e))
```

### Getting Background Logger
```python
from logging_config import get_background_logger

bg_logger = get_background_logger()
bg_logger.info("Custom background task message")
```

## Benefits

1. **Structured Monitoring** - Consistent format for automated parsing
2. **Performance Tracking** - Duration and throughput metrics
3. **Failure Analysis** - Detailed error context
4. **Operational Visibility** - Clear task progression tracking
5. **Debugging Support** - Enhanced context for troubleshooting

## Future Enhancements

- Integration with monitoring systems (Prometheus, etc.)
- Alert thresholds based on task duration or failure rates
- Log aggregation and analysis tools
- Real-time dashboard for background task status