"""
Legacy Configuration Module
This module provides backward compatibility by importing from unified_config
"""

# Import everything from unified_config for backward compatibility
from unified_config import (
    BaseConfig as Config,
    DevelopmentConfig,
    ProductionConfig,
    TestConfig,
    config,
    get_config
)

# Legacy exports - maintain existing API
__all__ = [
    'Config',
    'DevelopmentConfig', 
    'ProductionConfig',
    'TestConfig',
    'config'
]