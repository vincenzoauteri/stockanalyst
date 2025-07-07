"""
Legacy Enhanced Configuration Module
This module provides backward compatibility by importing from unified_config
"""

# Import everything from unified_config for backward compatibility
from unified_config import (
    BaseConfig as EnhancedConfig,
    DevelopmentConfig as DevelopmentEnhancedConfig,
    ProductionConfig as ProductionEnhancedConfig,
    config,
    enhanced_config
)

# Legacy exports - maintain existing API
__all__ = [
    'EnhancedConfig',
    'DevelopmentEnhancedConfig',
    'ProductionEnhancedConfig', 
    'config',
    'enhanced_config'
]