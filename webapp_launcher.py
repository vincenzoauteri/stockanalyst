#!/usr/bin/env python3
"""
Unified Stock Analyst Web Application Launcher
Configurable entry point for both development and production environments
"""

import os
import sys
import logging
import signal
import argparse
from app import app

class WebAppLauncher:
    """
    Unified launcher for Stock Analyst web application.
    This class is responsible for configuring and running the Flask app.
    The scheduler is now an independent service.
    """
    
    def __init__(self):
        self.logger = self._configure_logging()
        
    def _configure_logging(self):
        """Configure logging based on environment"""
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        level = getattr(logging, log_level, logging.INFO)
        
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        return logging.getLogger(__name__)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info(f"Received signal {signum}. Shutting down web application gracefully...")
        sys.exit(0)
        
    def _check_environment(self):
        """Check and report on the application environment"""
        self.logger.info("🔧 Environment Check:")
        
        db_path = os.getenv('DATABASE_PATH', 'stock_analysis.db')
        if os.path.exists(db_path):
            self.logger.info(f"   ✅ Database found at {db_path}")
        else:
            self.logger.warning(f"   ⚠️ Database not found at {db_path}")
            
        api_key = os.getenv('FMP_API_KEY')
        if api_key:
            self.logger.info("   ✅ FMP API key configured")
        else:
            self.logger.warning("   ⚠️ FMP API key not configured (limited functionality)")
            
        self.logger.info("   💻 Running in local environment")
            
        return True
        
    def _configure_app(self, environment='development'):
        """Configure Flask app based on environment"""
        if environment == 'production':
            app.config.update(
                DEBUG=False,
                TESTING=False,
                SECRET_KEY=os.getenv('SECRET_KEY', 'production-secret-key-change-me'),
            )
        else:
            app.config.update(
                DEBUG=True,
                SECRET_KEY=os.getenv('SECRET_KEY', 'dev-secret-key'),
            )
            
    def _print_development_info(self, host, port):
        """Print development information and tips"""
        print()
        print("📊 Features available:")
        print("   • S&P 500 stock listing with search & filtering")
        print("   • Individual stock detail pages with fundamentals")
        print("   • Sector-based analysis and grouping")
        print("   • Real-time API endpoints for data access")
        print("   • Responsive design for mobile & desktop")
        print()
        print("🌐 Web Interface:")
        print(f"   • Main page: http://{host}:{port}/")
        print()
        print("🔗 API Endpoints:")
        print(f"   • All stocks: http://{host}:{port}/api/stocks")
        print()
        
    def run_development(self, host='localhost', port=5000):
        """Run the application in development mode"""
        self.logger.info("🚀 Starting Stock Analyst Web Application (Development Mode)...")
        self._check_environment()
        self._configure_app('development')
        self._print_development_info(host, port)
        
        try:
            print(f"Starting development server on http://{host}:{port}...")
            print("Press Ctrl+C to stop the server")
            print("=" * 50)
            
            app.run(
                debug=True,
                host=host,
                port=port,
                use_reloader=False
            )
            
        except KeyboardInterrupt:
            print("\n👋 Shutting down Stock Analyst Web Application...")
        except Exception as e:
            print(f"\n❌ Error starting web application: {e}")
            sys.exit(1)
            
    def run_production(self, host='0.0.0.0', port=5000):
        """Run the application in production mode"""
        self.logger.info("🐳 Starting Stock Analyst Web Application (Production Mode)...")
        
        if not self._check_environment():
            self.logger.error("❌ Failed to initialize application")
            sys.exit(1)
            
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        self._configure_app('production')
        
        self.logger.info(f"🌐 Starting production server on {host}:{port}")
        
        try:
            app.run(
                host=host,
                port=port,
                debug=False,
                use_reloader=False,
                threaded=True
            )
        except Exception as e:
            self.logger.error(f"❌ Failed to start server: {e}")
            sys.exit(1)

def main():
    """Main entry point with command line argument parsing"""
    parser = argparse.ArgumentParser(description='Stock Analyst Web Application Launcher')
    parser.add_argument('--mode', choices=['development', 'production'], 
                       default='development', help='Run mode (default: development)')
    parser.add_argument('--host', default=None, help='Host to bind to')
    parser.add_argument('--port', type=int, default=None, help='Port to bind to')
    
    args = parser.parse_args()
    
    if args.mode == 'production':
        host = args.host or os.getenv('FLASK_HOST', '0.0.0.0')
        port = args.port or int(os.getenv('FLASK_PORT', '5000'))
    else:
        host = args.host or os.getenv('FLASK_HOST', 'localhost')
        port = args.port or int(os.getenv('FLASK_PORT', '5000'))
    
    launcher = WebAppLauncher()
    
    if args.mode == 'production':
        launcher.run_production(host=host, port=port)
    else:
        launcher.run_development(host=host, port=port)

if __name__ == '__main__':
    main()
