#!/usr/bin/env python3
"""
Service Registry for Stock Analyst Application
Centralized service management to avoid circular imports and duplication
"""

from auth import AuthenticationManager
from data_access_layer import StockDataService
from fmp_client import FMPClient
from logging_config import get_logger
from portfolio import PortfolioManager
from undervaluation_analyzer import UndervaluationAnalyzer

logger = get_logger(__name__)

class ServiceRegistry:
    """Centralized service registry using singleton pattern"""
    
    _instance = None
    _services = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_stock_service(self):
        """Get stock data service, initializing if needed"""
        if 'stock_service' not in self._services:
            self._services['stock_service'] = StockDataService()
            logger.debug("Initialized StockDataService")
        return self._services['stock_service']
    
    def get_fmp_client(self):
        """Get FMP client, initializing if needed"""
        if 'fmp_client' not in self._services:
            self._services['fmp_client'] = FMPClient()
            logger.debug("Initialized FMPClient")
        return self._services['fmp_client']
    
    def get_undervaluation_analyzer(self):
        """Get undervaluation analyzer, initializing if needed"""
        if 'undervaluation_analyzer' not in self._services:
            self._services['undervaluation_analyzer'] = UndervaluationAnalyzer()
            logger.debug("Initialized UndervaluationAnalyzer")
        return self._services['undervaluation_analyzer']
    
    def get_auth_manager(self):
        """Get authentication manager, initializing if needed"""
        if 'auth_manager' not in self._services:
            self._services['auth_manager'] = AuthenticationManager()
            logger.debug("Initialized AuthenticationManager")
        return self._services['auth_manager']
    
    def get_portfolio_manager(self):
        """Get portfolio manager, initializing if needed"""
        if 'portfolio_manager' not in self._services:
            self._services['portfolio_manager'] = PortfolioManager()
            logger.debug("Initialized PortfolioManager")
        return self._services['portfolio_manager']

# Global service registry instance
_registry = ServiceRegistry()

# Convenience functions for easy access
def get_stock_service():
    """Get stock data service instance"""
    return _registry.get_stock_service()

def get_fmp_client():
    """Get FMP client instance"""
    return _registry.get_fmp_client()

def get_undervaluation_analyzer():
    """Get undervaluation analyzer instance"""
    return _registry.get_undervaluation_analyzer()

def get_auth_manager():
    """Get authentication manager instance"""
    return _registry.get_auth_manager()

def get_portfolio_manager():
    """Get portfolio manager instance"""
    return _registry.get_portfolio_manager()