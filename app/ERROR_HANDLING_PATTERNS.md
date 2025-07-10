# Error Handling Patterns for Stock Analyst Application

This document outlines the improved error handling patterns implemented to replace generic `except Exception` handlers with specific exception handling.

## Common Exception Types

### API Endpoints (api_routes.py)
1. **ValueError** - Invalid query parameters or data conversion errors
2. **AttributeError** - Service methods not available or object attribute errors
3. **KeyError** - Missing dictionary keys in data structures
4. **TypeError** - Type incompatibility in operations (e.g., sorting)
5. **ConnectionError** - Database or external API connection issues

### Web Routes (app.py)
1. **AttributeError** - Service methods not available
2. **ConnectionError** - Database connection issues
3. **FileNotFoundError** - Template files missing
4. **ValueError** - Invalid data format or parameters

### Data Processing
1. **pandas.errors.EmptyDataError** - Empty dataframes
2. **sqlalchemy.exc.SQLAlchemyError** - Database operation errors
3. **requests.exceptions.RequestException** - External API call failures

## Recommended Error Handling Pattern

```python
try:
    # Main business logic
    pass
    
except ValueError as e:
    logger.warning(f"Invalid input in {function_name}: {e}")
    return error_response("Invalid input parameters", 400)
    
except AttributeError as e:
    logger.error(f"Service method not available in {function_name}: {e}")
    return error_response("Service temporarily unavailable", 503)
    
except ConnectionError as e:
    logger.error(f"Database connection error in {function_name}: {e}")
    return error_response("Database connection error", 503)
    
except Exception as e:
    logger.error(f"Unexpected error in {function_name}: {e}")
    return error_response("Internal server error", 500)
```

## HTTP Status Codes

- **400 Bad Request** - Invalid input parameters or malformed requests
- **404 Not Found** - Resource not found
- **500 Internal Server Error** - Unexpected application errors
- **503 Service Unavailable** - Database or service connectivity issues

## Examples Implemented

### API Endpoint (api_routes.py)
The `/api/v2/stocks` endpoint now includes:
- Parameter validation with ValueError handling
- Type error handling for sorting operations
- Malformed data handling for individual stock records
- Specific error responses for different failure scenarios

### Web Route (app.py)
The index route now includes:
- Service availability checks
- Database connection error handling
- Template error handling
- Specific HTTP status codes for different errors

## Remaining Work

As of version 0.0.10, there are approximately 535 generic `except Exception` handlers remaining in the codebase. These should be gradually replaced following the patterns established in this document.

Priority areas for improvement:
1. Critical API endpoints
2. Main web routes
3. Database operations
4. External API calls
5. Background processes

## Benefits

1. **Better Debugging** - Specific error types provide clearer insight into failure causes
2. **Improved User Experience** - Appropriate HTTP status codes and error messages
3. **Enhanced Monitoring** - Different log levels and messages for different error types
4. **Graceful Degradation** - Fallback behavior for specific error scenarios