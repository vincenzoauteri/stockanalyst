#!/usr/bin/env python3
"""
API Documentation for Stock Analyst Application
Provides comprehensive Swagger/OpenAPI documentation for all API endpoints
"""

from flask import Flask
from flask_restx import Api, Resource, fields, Namespace
from logging_config import get_logger

logger = get_logger(__name__)

def create_api_documentation(app: Flask) -> Api:
    """Create comprehensive API documentation using Flask-RESTX"""
    
    # Initialize Flask-RESTX API
    api = Api(
        app,
        version='2.0',
        title='Stock Analyst API',
        description='''
        A comprehensive stock analysis platform providing real-time financial data,
        undervaluation scoring, portfolio tracking, and investment analysis tools.
        
        ## Features
        - **Stock Data**: Access to S&P 500 company profiles and historical prices
        - **Undervaluation Analysis**: Advanced multi-factor scoring algorithm
        - **Portfolio Management**: Track investments and performance
        - **User Authentication**: Secure user accounts and personalization
        - **Sector Analysis**: Compare stocks within industry sectors
        
        ## Authentication
        Most endpoints require user authentication. Use the login endpoint to obtain
        a session token, then include it in subsequent requests.
        
        ## Rate Limits
        API calls to external services are rate-limited to respect provider quotas.
        Free tier users may experience reduced functionality during high usage periods.
        ''',
        doc='/api/docs/',
        prefix='/api/v2',
        contact='Stock Analyst Support',
        contact_email='support@stockanalyst.com'
    )
    
    # Define common models
    stock_model = api.model('Stock', {
        'symbol': fields.String(required=True, description='Stock ticker symbol'),
        'name': fields.String(description='Company name'),
        'sector': fields.String(description='Industry sector'),
        'price': fields.Float(description='Current stock price'),
        'market_cap': fields.Integer(description='Market capitalization'),
        'undervaluation_score': fields.Float(description='Undervaluation score (0-100)')
    })
    
    stock_detail_model = api.model('StockDetail', {
        'symbol': fields.String(required=True, description='Stock ticker symbol'),
        'company_name': fields.String(description='Company name'),
        'sector': fields.String(description='Industry sector'),
        'price': fields.Float(description='Current stock price'),
        'beta': fields.Float(description='Stock beta coefficient'),
        'market_cap': fields.Integer(description='Market capitalization'),
        'pe_ratio': fields.Float(description='Price-to-earnings ratio'),
        'pb_ratio': fields.Float(description='Price-to-book ratio'),
        'dividend_yield': fields.Float(description='Dividend yield percentage'),
        'undervaluation_score': fields.Float(description='Undervaluation score (0-100)'),
        'description': fields.String(description='Company description'),
        'website': fields.String(description='Company website'),
        'employees': fields.Integer(description='Number of employees')
    })
    
    sector_model = api.model('Sector', {
        'sector': fields.String(required=True, description='Sector name'),
        'stock_count': fields.Integer(description='Number of stocks in sector'),
        'avg_undervaluation_score': fields.Float(description='Average undervaluation score'),
        'avg_market_cap': fields.Float(description='Average market capitalization'),
        'best_stock': fields.String(description='Best performing stock symbol'),
        'worst_stock': fields.String(description='Worst performing stock symbol')
    })
    
    transaction_model = api.model('Transaction', {
        'id': fields.Integer(description='Transaction ID'),
        'symbol': fields.String(required=True, description='Stock ticker symbol'),
        'transaction_type': fields.String(required=True, description='BUY or SELL'),
        'shares': fields.Float(required=True, description='Number of shares'),
        'price_per_share': fields.Float(required=True, description='Price per share'),
        'transaction_date': fields.Date(required=True, description='Transaction date'),
        'fees': fields.Float(description='Transaction fees'),
        'notes': fields.String(description='Transaction notes'),
        'total_amount': fields.Float(description='Total transaction amount')
    })
    
    
    user_model = api.model('User', {
        'user_id': fields.Integer(description='User ID'),
        'username': fields.String(required=True, description='Username'),
        'email': fields.String(required=True, description='Email address'),
        'created_at': fields.DateTime(description='Account creation date'),
        'last_login': fields.DateTime(description='Last login time')
    })
    
    # Stock Data Namespace
    stocks_ns = Namespace('stocks', description='Stock data and analysis operations')
    
    @stocks_ns.route('/')
    class StocksList(Resource):
        @stocks_ns.doc('get_stocks')
        @stocks_ns.marshal_list_with(stock_model)
        @stocks_ns.param('sector', 'Filter by sector')
        @stocks_ns.param('min_score', 'Minimum undervaluation score')
        @stocks_ns.param('max_score', 'Maximum undervaluation score')
        @stocks_ns.param('sort', 'Sort field (symbol, score, price, market_cap)')
        @stocks_ns.param('order', 'Sort order (asc, desc)')
        @stocks_ns.param('limit', 'Number of results to return')
        def get(self):
            """Get list of all S&P 500 stocks with filtering and sorting options"""
            # Implementation would be in the main app
            pass
    
    @stocks_ns.route('/<string:symbol>')
    class StockDetail(Resource):
        @stocks_ns.doc('get_stock_detail')
        @stocks_ns.marshal_with(stock_detail_model)
        @stocks_ns.response(404, 'Stock not found')
        def get(self, symbol):
            """Get detailed information for a specific stock"""
            pass
    
    @stocks_ns.route('/<string:symbol>/history')
    class StockHistory(Resource):
        @stocks_ns.doc('get_stock_history')
        @stocks_ns.param('limit', 'Number of historical records to return')
        @stocks_ns.param('start_date', 'Start date (YYYY-MM-DD)')
        @stocks_ns.param('end_date', 'End date (YYYY-MM-DD)')
        def get(self, symbol):
            """Get historical price data for a stock"""
            pass
    
    # Sectors Namespace
    sectors_ns = Namespace('sectors', description='Sector analysis operations')
    
    @sectors_ns.route('/')
    class SectorsList(Resource):
        @sectors_ns.doc('get_sectors')
        @sectors_ns.marshal_list_with(sector_model)
        def get(self):
            """Get analysis data for all sectors"""
            pass
    
    @sectors_ns.route('/<string:sector_name>')
    class SectorDetail(Resource):
        @sectors_ns.doc('get_sector_detail')
        @sectors_ns.param('sort', 'Sort field for stocks in sector')
        @sectors_ns.param('limit', 'Number of stocks to return')
        def get(self, sector_name):
            """Get detailed analysis for a specific sector"""
            pass
    
    # Portfolio Namespace (Requires Authentication)
    portfolio_ns = Namespace('portfolio', description='Portfolio management operations (authentication required)')
    
    @portfolio_ns.route('/')
    class Portfolio(Resource):
        @portfolio_ns.doc('get_portfolio')
        @portfolio_ns.doc(security='sessionToken')
        def get(self):
            """Get user's complete portfolio with current values and performance"""
            pass
        
        @portfolio_ns.doc('add_transaction')
        @portfolio_ns.doc(security='sessionToken')
        @portfolio_ns.expect(transaction_model)
        def post(self):
            """Add a new portfolio transaction (buy or sell)"""
            pass
    
    @portfolio_ns.route('/transactions')
    class PortfolioTransactions(Resource):
        @portfolio_ns.doc('get_transactions')
        @portfolio_ns.doc(security='sessionToken')
        @portfolio_ns.marshal_list_with(transaction_model)
        @portfolio_ns.param('symbol', 'Filter transactions by stock symbol')
        @portfolio_ns.param('type', 'Filter by transaction type (BUY, SELL)')
        @portfolio_ns.param('limit', 'Number of transactions to return')
        def get(self):
            """Get user's transaction history"""
            pass
    
    @portfolio_ns.route('/transactions/<int:transaction_id>')
    class PortfolioTransaction(Resource):
        @portfolio_ns.doc('delete_transaction')
        @portfolio_ns.doc(security='sessionToken')
        @portfolio_ns.response(204, 'Transaction deleted')
        @portfolio_ns.response(404, 'Transaction not found')
        def delete(self, transaction_id):
            """Delete a portfolio transaction"""
            pass
    
    @portfolio_ns.route('/performance')
    class PortfolioPerformance(Resource):
        @portfolio_ns.doc('get_portfolio_performance')
        @portfolio_ns.doc(security='sessionToken')
        def get(self):
            """Get detailed portfolio performance analytics"""
            pass
    
    @portfolio_ns.route('/export')
    class PortfolioExport(Resource):
        @portfolio_ns.doc('export_portfolio')
        @portfolio_ns.doc(security='sessionToken')
        @portfolio_ns.param('format', 'Export format (csv, pdf)')
        @portfolio_ns.param('symbol', 'Filter by stock symbol')
        def get(self):
            """Export portfolio data in various formats"""
            pass
    
    # Watchlist Namespace (Requires Authentication)
    watchlist_ns = Namespace('watchlist', description='Watchlist management operations (authentication required)')
    
    @watchlist_ns.route('/')
    class Watchlist(Resource):
        @watchlist_ns.doc('get_watchlist')
        @watchlist_ns.doc(security='sessionToken')
        def get(self):
            """Get user's watchlist with stock details"""
            pass
        
        @watchlist_ns.doc('add_to_watchlist')
        @watchlist_ns.doc(security='sessionToken')
        @watchlist_ns.param('symbol', 'Stock symbol to add')
        @watchlist_ns.param('notes', 'Optional notes')
        def post(self):
            """Add a stock to watchlist"""
            pass
    
    @watchlist_ns.route('/<string:symbol>')
    class WatchlistItem(Resource):
        @watchlist_ns.doc('remove_from_watchlist')
        @watchlist_ns.doc(security='sessionToken')
        @watchlist_ns.response(204, 'Stock removed from watchlist')
        def delete(self, symbol):
            """Remove a stock from watchlist"""
            pass
        
        @watchlist_ns.doc('update_watchlist_notes')
        @watchlist_ns.doc(security='sessionToken')
        @watchlist_ns.param('notes', 'Updated notes')
        def put(self, symbol):
            """Update notes for a stock in watchlist"""
            pass
    
    # Analysis Namespace
    analysis_ns = Namespace('analysis', description='Stock analysis and scoring operations')
    
    @analysis_ns.route('/undervaluation')
    class UndervaluationAnalysis(Resource):
        @analysis_ns.doc('run_undervaluation_analysis')
        @analysis_ns.param('force_refresh', 'Force refresh of cached data')
        def post(self):
            """Trigger undervaluation analysis for all stocks"""
            pass
        
        @analysis_ns.doc('get_undervaluation_summary')
        def get(self):
            """Get summary of latest undervaluation analysis"""
            pass
    
    @analysis_ns.route('/undervaluation/<string:symbol>')
    class StockUndervaluationAnalysis(Resource):
        @analysis_ns.doc('get_stock_undervaluation')
        def get(self, symbol):
            """Get detailed undervaluation analysis for a specific stock"""
            pass
    
    # Authentication Namespace
    auth_ns = Namespace('auth', description='User authentication operations')
    
    @auth_ns.route('/register')
    class Register(Resource):
        @auth_ns.doc('register_user')
        @auth_ns.param('username', 'Username (minimum 3 characters)')
        @auth_ns.param('email', 'Email address')
        @auth_ns.param('password', 'Password (minimum 6 characters)')
        def post(self):
            """Register a new user account"""
            pass
    
    @auth_ns.route('/login')
    class Login(Resource):
        @auth_ns.doc('login_user')
        @auth_ns.param('username', 'Username')
        @auth_ns.param('password', 'Password')
        def post(self):
            """Authenticate user and create session"""
            pass
    
    @auth_ns.route('/logout')
    class Logout(Resource):
        @auth_ns.doc('logout_user')
        @auth_ns.doc(security='sessionToken')
        def post(self):
            """Logout user and invalidate session"""
            pass
    
    @auth_ns.route('/profile')
    class Profile(Resource):
        @auth_ns.doc('get_user_profile')
        @auth_ns.doc(security='sessionToken')
        @auth_ns.marshal_with(user_model)
        def get(self):
            """Get user profile information"""
            pass
        
        @auth_ns.doc('update_user_profile')
        @auth_ns.doc(security='sessionToken')
        def put(self):
            """Update user profile information"""
            pass
    
    # Add security definitions
    authorizations = {
        'sessionToken': {
            'type': 'apiKey',
            'in': 'cookie',
            'name': 'session',
            'description': 'Session token obtained from login endpoint'
        }
    }
    
    api.authorizations = authorizations
    
    # Add namespaces to API
    api.add_namespace(stocks_ns)
    api.add_namespace(sectors_ns)
    api.add_namespace(portfolio_ns)
    api.add_namespace(watchlist_ns)
    api.add_namespace(analysis_ns)
    api.add_namespace(auth_ns)
    
    logger.info("API documentation initialized with comprehensive endpoint descriptions")
    
    return api

def add_api_examples():
    """Add comprehensive examples and additional documentation"""
    return {
        'example_responses': {
            'stock_list': [
                {
                    'symbol': 'AAPL',
                    'name': 'Apple Inc.',
                    'sector': 'Technology',
                    'price': 175.25,
                    'market_cap': 2800000000000,
                    'undervaluation_score': 65.8
                },
                {
                    'symbol': 'MSFT',
                    'name': 'Microsoft Corporation',
                    'sector': 'Technology',
                    'price': 330.50,
                    'market_cap': 2450000000000,
                    'undervaluation_score': 72.3
                }
            ],
            'portfolio_summary': {
                'total_holdings': 5,
                'total_value': 25000.00,
                'total_cost': 22000.00,
                'total_gain_loss': 3000.00,
                'total_gain_loss_pct': 13.64
            }
        },
        'authentication_flow': """
        1. Register: POST /api/v2/auth/register with username, email, password
        2. Login: POST /api/v2/auth/login with username, password
        3. Use session token from login response for authenticated endpoints
        4. Logout: POST /api/v2/auth/logout to invalidate session
        """,
        'rate_limits': """
        - External API calls: 250 requests per day (free tier)
        - Database queries: No specific limit
        - Authentication attempts: 5 failed attempts = 15 minute lockout
        """
    }