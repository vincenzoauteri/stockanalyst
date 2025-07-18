#!/usr/bin/env python3
"""
Stock Analyst Web Application - Refactored
Flask web app to display stock data and fundamentals
Uses separate data access layer for better separation of concerns
"""

import json
import os
import signal
import sys
import threading
from datetime import datetime, date
from sqlalchemy import text

# Try to import orjson for faster JSON processing
try:
    import orjson
    HAS_ORJSON = True
except ImportError:
    HAS_ORJSON = False

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from werkzeug.serving import make_server
from flask_assets import Environment, Bundle

from api_documentation import create_api_documentation
from api_routes import api_v2
from auth import login_required
from logging_config import setup_logging, get_logger
from services import (
    get_stock_service,
    get_fmp_client,
    get_undervaluation_analyzer,
    get_auth_manager,
    get_portfolio_manager
)
from unified_config import get_config
from cache_utils import init_cache

# Configure centralized logging
setup_logging(log_level="INFO", enable_file_logging=True, enable_console_logging=True)
logger = get_logger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')

# Check for default secret key in production environment
env = os.getenv('FLASK_ENV', os.getenv('ENV', 'production')).lower()
if env in ['production', 'prod']:
    default_secret_keys = [
        'your-secret-key-change-in-production',
        'change-me-in-production',
        'production-secret-key-change-me'
    ]
    if app.config['SECRET_KEY'] in default_secret_keys:
        logger.warning("SECURITY WARNING: Default SECRET_KEY detected in production environment. "
                      "Please set a secure SECRET_KEY environment variable.")

# Make config available in templates
@app.context_processor
def inject_config():
    """Inject configuration into template context"""
    return {'config': get_config()}

# Initialize cache
init_cache(app)

# Initialize Flask-Assets
assets = Environment(app)
assets.url = app.static_url_path
assets.directory = app.static_folder

# Define asset bundles for CSS and JS
css_bundle = Bundle(
    'css/style.css',
    filters='cssmin',
    output='gen/packed.css'
)
assets.register('css_all', css_bundle)

js_bundle = Bundle(
    'js/app.js',
    'js/chart.js',
    filters='jsmin',
    output='gen/packed.js'
)
assets.register('js_all', js_bundle)

# Register API blueprint
app.register_blueprint(api_v2)

# Initialize API documentation with Flask-RESTX
try:
    api_doc = create_api_documentation(app)
    logger.info("API documentation initialized successfully")
except ImportError:
    logger.warning("Flask-RESTX not available. API documentation disabled.")
except Exception as e:
    logger.error(f"Error initializing API documentation: {e}")

# Add JSON filter for templates with date serialization support
@app.template_filter('tojsonfilter')
def to_json_filter(obj):
    if HAS_ORJSON:
        try:
            # orjson handles datetime objects natively and is faster
            return orjson.dumps(obj, option=orjson.OPT_SERIALIZE_DATETIME).decode('utf-8')
        except (TypeError, ValueError):
            # Fall back to standard json if orjson fails
            pass
    
    # Standard json fallback
    def date_serializer(o):
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        raise TypeError(f"Object of type {type(o)} is not JSON serializable")

    return json.dumps(obj, default=date_serializer)


@app.route('/')
def index():
    """Main page showing list of S&P 500 stocks with pagination"""
    try:
        service = get_stock_service()

        # Get query parameters for pagination and filtering
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        sector = request.args.get('sector')
        min_score = request.args.get('min_score', type=float)
        max_score = request.args.get('max_score', type=float)
        search = request.args.get('search')
        sort_by = request.args.get('sort', 'symbol')
        sort_order = request.args.get('order', 'asc')
        
        # Validate parameters
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:  # Limit max per_page for frontend
            per_page = 50
        
        # Calculate offset
        offset = (page - 1) * per_page
        
        # Get total count
        total_count = service.get_stocks_count(
            sector=sector,
            min_score=min_score,
            max_score=max_score,
            search=search
        )
        
        # Get paginated stocks
        stocks_list = service.get_all_stocks_with_scores(
            sector=sector,
            min_score=min_score,
            max_score=max_score,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=per_page,
            offset=offset
        )

        # Get summary statistics (for all stocks, not just current page)
        all_stocks_sample = service.get_all_stocks_with_scores(limit=500)  # Get sample for stats
        stats = service.get_stock_summary_stats(all_stocks_sample)

        # Calculate pagination metadata
        total_pages = (total_count + per_page - 1) // per_page
        has_next = page < total_pages
        has_prev = page > 1
        
        pagination = {
            'total_count': total_count,
            'total_pages': total_pages,
            'current_page': page,
            'per_page': per_page,
            'has_next': has_next,
            'has_prev': has_prev
        }
        
        # Get available sectors for filter dropdown
        sectors = list(stats.get('sectors', []))
        
        filters = {
            'sector': sector,
            'min_score': min_score,
            'max_score': max_score,
            'search': search,
            'sort': sort_by,
            'order': sort_order
        }

        return render_template('index.html', 
                             stocks=stocks_list, 
                             stats=stats,
                             pagination=pagination,
                             filters=filters,
                             sectors=sectors)
    except AttributeError as e:
        logger.error(f"Service method not available in index route: {e}")
        return render_template('error.html', error='Service temporarily unavailable'), 503
    except ConnectionError as e:
        logger.error(f"Database connection error in index route: {e}")
        return render_template('error.html', error='Database connection error'), 503
    except FileNotFoundError as e:
        logger.error(f"Template not found in index route: {e}")
        return "Template error", 500
    except Exception as e:
        logger.error(f"Unexpected error in index route: {e}")
        return render_template('error.html', error='An unexpected error occurred'), 500

@app.route('/stock/<symbol>')
def stock_detail(symbol):
    """Individual stock detail page"""
    try:
        logger.info(f"Starting stock_detail route for {symbol}")
        service = get_stock_service()
        client = get_fmp_client()
        
        # Get comprehensive stock data in optimized queries
        logger.info(f"Getting comprehensive stock data for {symbol}")
        stock_data = service.get_comprehensive_stock_data(symbol)
        
        if not stock_data:
            return render_template('error.html', error=f"Stock {symbol} not found")
        
        logger.info(f"Comprehensive stock data retrieved for {symbol}")
        
        # Get fundamentals from API if available
        if client.api_key:
            try:
                fundamentals = client.get_fundamentals_summary(symbol)
                if fundamentals and 'error' not in fundamentals:
                    # Serialize any date objects in fundamentals data
                    def serialize_dates(obj):
                        if isinstance(obj, dict):
                            return {key: serialize_dates(value) for key, value in obj.items()}
                        elif isinstance(obj, list):
                            return [serialize_dates(item) for item in obj]
                        elif hasattr(obj, 'isoformat'):  # Any date-like object
                            return obj.isoformat()
                        else:
                            return obj
                    stock_data['fundamentals'] = serialize_dates(fundamentals)
                
                # Get price targets
                price_targets = client.get_price_targets(symbol)
                if price_targets:
                    stock_data['price_targets'] = price_targets
                    
            except Exception as api_error:
                logger.warning(f"API error for {symbol}: {api_error}")
                stock_data['api_error'] = str(api_error)
        
        # Serialize dates for template compatibility (for JavaScript charts)
        def serialize_dates_for_template(obj):
            if isinstance(obj, dict):
                return {key: serialize_dates_for_template(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [serialize_dates_for_template(item) for item in obj]
            elif isinstance(obj, (datetime, date)):
                return obj.isoformat()
            elif hasattr(obj, 'isoformat'):  # Catch any other date-like objects
                return obj.isoformat()
            else:
                return obj
        
        stock_data = serialize_dates_for_template(stock_data)
        return render_template('stock_detail.html', stock=stock_data)
        
    except Exception as e:
        logger.error(f"Error in stock_detail route for {symbol}: {e}")
        return render_template('error.html', error=str(e))


@app.route('/compare')
def stock_comparison():
    """Stock comparison page"""
    try:
        # Get symbols from query parameters
        symbols_param = request.args.get('symbols', '')
        symbols = []
        comparison_data = []
        
        if symbols_param:
            symbols = [s.strip().upper() for s in symbols_param.split(',')]
            symbols = [s for s in symbols if s]  # Remove empty strings
            
            if len(symbols) >= 2 and len(symbols) <= 5:
                service = get_stock_service()
                comparison_data = service.get_stock_comparison(symbols)
        
        return render_template('stock_comparison.html', 
                             symbols=symbols, 
                             comparison_data=comparison_data)
        
    except Exception as e:
        logger.error(f"Error in stock comparison page: {e}")
        return render_template('error.html', error=str(e))

@app.route('/sectors')
def sectors_overview():
    """Sectors overview page with aggregated analysis"""
    try:
        service = get_stock_service()
        
        # Get sector analysis
        sector_analysis = service.get_sector_analysis()
        
        return render_template('sectors.html', sectors=sector_analysis)
        
    except Exception as e:
        logger.error(f"Error in sectors_overview route: {e}")
        return render_template('error.html', error=str(e))

@app.route('/api/stocks')
def api_stocks():
    """API endpoint to get stocks data as JSON"""
    try:
        service = get_stock_service()
        
        # Get query parameters
        sector = request.args.get('sector')
        search = request.args.get('search')
        limit = request.args.get('limit', 100, type=int)
        
        if search:
            stocks_list = service.search_stocks(search, limit=limit)
        elif sector:
            stocks_list = service.get_stocks_by_sector(sector)
        else:
            stocks_list = service.get_all_stocks_with_scores()
        
        # Convert to API-friendly format
        api_stocks = []
        for stock in stocks_list[:limit]:
            api_stocks.append({
                'symbol': stock['symbol'],
                'name': stock.get('company_name') or stock.get('name'),
                'sector': stock['sector'],
                'price': float(stock['price']) if stock.get('price') else None,
                'market_cap': float(stock.get('market_cap') or stock.get('mktcap')) if stock.get('market_cap') or stock.get('mktcap') else None,
                'undervaluation_score': float(stock['undervaluation_score']) if stock.get('undervaluation_score') else None,
                'data_quality': stock.get('data_quality')
            })
        
        return jsonify(api_stocks)
        
    except Exception as e:
        logger.error(f"Error in api_stocks route: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stock/<symbol>')
def api_stock_detail(symbol):
    """API endpoint to get individual stock data as JSON"""
    try:
        service = get_stock_service()
        
        # Get basic stock info
        basic_info = service.get_stock_basic_info(symbol)
        if not basic_info:
            return jsonify({'error': f'Stock {symbol} not found'}), 404
        
        # Get additional data
        profile = service.get_stock_company_profile(symbol)
        undervaluation_score = service.get_stock_undervaluation_score(symbol)
        price_history = service.get_stock_historical_prices(symbol, limit=30)
        
        stock_data = {
            'basic_info': basic_info,
            'profile': profile,
            'undervaluation': undervaluation_score,
            'recent_prices': price_history
        }
        
        # Serialize dates for JSON compatibility
        def serialize_dates(obj):
            if isinstance(obj, dict):
                return {key: serialize_dates(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [serialize_dates(item) for item in obj]
            elif isinstance(obj, (datetime, date)):
                return obj.isoformat()
            else:
                return obj
        
        stock_data = serialize_dates(stock_data)
        return jsonify(stock_data)
        
    except Exception as e:
        logger.error(f"Error in api_stock_detail route for {symbol}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sectors')
def api_sectors():
    """API endpoint to get sector analysis as JSON"""
    try:
        service = get_stock_service()
        
        sector_analysis = service.get_sector_analysis()
        
        return jsonify(sector_analysis)
        
    except Exception as e:
        logger.error(f"Error in api_sectors route: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/analysis/run', methods=['POST'])
def api_run_analysis():
    """API endpoint to trigger undervaluation analysis"""
    try:
        analyzer = get_undervaluation_analyzer()
        
        # Get request parameters
        force_refresh = request.json.get('force_refresh', False) if request.is_json else False
        
        # Run analysis
        summary = analyzer.analyze_undervaluation(use_cache=True, force_refresh=force_refresh)
        
        return jsonify({
            'success': True,
            'summary': summary,
            'cache_stats': analyzer.get_cache_stats()
        })
        
    except Exception as e:
        logger.error(f"Error in api_run_analysis route: {e}")
        return jsonify({'error': str(e)}), 500

# Authentication Routes

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Basic validation
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        auth_mgr = get_auth_manager()
        result = auth_mgr.register_user(username, email, password)
        
        if result['success']:
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash(result['error'], 'error')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        auth_mgr = get_auth_manager()
        result = auth_mgr.authenticate_user(
            username, 
            password, 
            request.remote_addr, 
            request.headers.get('User-Agent')
        )
        
        if result['success']:
            session['user_id'] = result['user_id']
            session['username'] = result['username']
            session['email'] = result['email']
            session['session_token'] = result['session_token']
            
            flash(f'Welcome back, {result["username"]}!', 'success')
            
            # Redirect to next page if specified
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash(result['error'], 'error')
            return render_template('login.html')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """User logout"""
    if 'session_token' in session:
        auth_mgr = get_auth_manager()
        auth_mgr.logout_user(session['session_token'])
    
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    """User profile page"""
    try:
        # Get user information using PostgreSQL
        auth_mgr = get_auth_manager()
        
        with auth_mgr.db_manager.engine.connect() as conn:
            # Get user details
            result = conn.execute(text('''
                SELECT created_at, last_login FROM users WHERE id = :user_id
            '''), {'user_id': session['user_id']})
            user_data = result.fetchone()
            
            # Get watchlist count
            result = conn.execute(text('''
                SELECT COUNT(*) FROM user_watchlists WHERE user_id = :user_id
            '''), {'user_id': session['user_id']})
            watchlist_count = result.fetchone()[0]
        
        user_info = {
            'created_at': user_data[0] if user_data and user_data[0] else None,
            'last_login': user_data[1] if user_data and user_data[1] else None
        }
        
        return render_template('profile.html', user_info=user_info, watchlist_count=watchlist_count)
        
    except Exception as e:
        logger.error(f"Error in profile route: {e}")
        flash('Error loading profile', 'error')
        return redirect(url_for('index'))

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_new_password = request.form.get('confirm_new_password', '')
    
    if new_password != confirm_new_password:
        flash('New passwords do not match', 'error')
        return redirect(url_for('profile'))
    
    try:
        auth_mgr = get_auth_manager()
        result = auth_mgr.change_password(session['user_id'], current_password, new_password)
        
        if result['success']:
            flash('Password changed successfully', 'success')
        else:
            flash(result['error'], 'error')
        
    except Exception as e:
        logger.error(f"Error changing password: {e}")
        flash('Error changing password', 'error')
    
    return redirect(url_for('profile'))

@app.route('/watchlist')
@login_required
def watchlist():
    """User's watchlist page"""
    try:
        auth_mgr = get_auth_manager()
        watchlist = auth_mgr.get_user_watchlist(session['user_id'])
        
        # Convert datetime strings for template rendering
        for stock in watchlist:
            if stock.get('added_at') and isinstance(stock['added_at'], str):
                stock['added_at'] = datetime.fromisoformat(stock['added_at'])
        
        return render_template('watchlist.html', watchlist=watchlist)
        
    except Exception as e:
        logger.error(f"Error in watchlist route: {e}")
        flash('Error loading watchlist', 'error')
        return redirect(url_for('index'))

@app.route('/add_to_watchlist', methods=['POST'])
@login_required
def add_to_watchlist():
    """Add stock to user's watchlist"""
    symbol = request.form.get('symbol', '').strip().upper()
    notes = request.form.get('notes', '').strip()
    
    if not symbol:
        flash('Stock symbol is required', 'error')
        return redirect(url_for('watchlist'))
    
    try:
        # Verify stock exists in S&P 500
        service = get_stock_service()
        stock_info = service.get_stock_basic_info(symbol)
        
        if not stock_info:
            flash(f'Stock symbol {symbol} not found in our database', 'error')
            return redirect(url_for('watchlist'))
        
        auth_mgr = get_auth_manager()
        result = auth_mgr.add_to_watchlist(session['user_id'], symbol, notes)
        
        if result['success']:
            flash(f'{symbol} added to your watchlist', 'success')
        else:
            flash(result['error'], 'error')
        
    except Exception as e:
        logger.error(f"Error adding to watchlist: {e}")
        flash('Error adding stock to watchlist', 'error')
    
    return redirect(url_for('watchlist'))

@app.route('/remove_from_watchlist', methods=['POST'])
@login_required
def remove_from_watchlist():
    """Remove stock from user's watchlist"""
    data = request.get_json()
    symbol = data.get('symbol', '').strip().upper()
    
    if not symbol:
        return jsonify({'success': False, 'error': 'Stock symbol is required'})
    
    try:
        auth_mgr = get_auth_manager()
        result = auth_mgr.remove_from_watchlist(session['user_id'], symbol)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error removing from watchlist: {e}")
        return jsonify({'success': False, 'error': 'Error removing stock from watchlist'})

@app.route('/update_watchlist_notes', methods=['POST'])
@login_required
def update_watchlist_notes():
    """Update notes for a stock in user's watchlist"""
    symbol = request.form.get('symbol', '').strip().upper()
    notes = request.form.get('notes', '').strip()
    
    if not symbol:
        flash('Stock symbol is required', 'error')
        return redirect(url_for('watchlist'))
    
    try:
        auth_mgr = get_auth_manager()
        result = auth_mgr.update_watchlist_notes(session['user_id'], symbol, notes)
        
        if result['success']:
            flash(f'Notes updated for {symbol}', 'success')
        else:
            flash(result['error'], 'error')
        
    except Exception as e:
        logger.error(f"Error updating watchlist notes: {e}")
        flash('Error updating notes', 'error')
    
    return redirect(url_for('watchlist'))

# Portfolio Routes

@app.route('/portfolio')
@login_required
def portfolio():
    """User's portfolio page"""
    try:
        portfolio_mgr = get_portfolio_manager()
        
        # Get portfolio data
        portfolio_data = portfolio_mgr.get_user_portfolio(session['user_id'])
        
        # Get recent transactions (last 5)
        recent_transactions = portfolio_mgr.get_user_transactions(session['user_id'], limit=5)
        
        return render_template('portfolio.html', 
                             portfolio=portfolio_data, 
                             recent_transactions=recent_transactions,
                             today=date.today().isoformat())
        
    except Exception as e:
        logger.error(f"Error in portfolio route: {e}")
        flash('Error loading portfolio', 'error')
        return redirect(url_for('index'))

@app.route('/add_portfolio_transaction', methods=['POST'])
@login_required
def add_portfolio_transaction():
    """Add a new portfolio transaction"""
    try:
        portfolio_mgr = get_portfolio_manager()
        
        # Get form data
        transaction_type = request.form.get('transaction_type', '').upper()
        symbol = request.form.get('symbol', '').strip().upper()
        shares = float(request.form.get('shares', 0))
        price_per_share = float(request.form.get('price_per_share', 0))
        transaction_date = request.form.get('transaction_date', '')
        fees = float(request.form.get('fees', 0))
        notes = request.form.get('notes', '').strip()
        
        # Verify stock exists in our database
        service = get_stock_service()
        stock_info = service.get_stock_basic_info(symbol)
        
        if not stock_info:
            flash(f'Stock symbol {symbol} not found in our database', 'error')
            return redirect(url_for('portfolio'))
        
        # Add transaction
        result = portfolio_mgr.add_transaction(
            user_id=session['user_id'],
            symbol=symbol,
            transaction_type=transaction_type,
            shares=shares,
            price_per_share=price_per_share,
            transaction_date=transaction_date,
            fees=fees,
            notes=notes
        )
        
        if result['success']:
            flash(f'{transaction_type} transaction for {symbol} added successfully', 'success')
        else:
            flash(result['error'], 'error')
            
    except Exception as e:
        logger.error(f"Error adding portfolio transaction: {e}")
        flash('Error adding transaction', 'error')
    
    return redirect(url_for('portfolio'))

@app.route('/portfolio/transactions')
@app.route('/portfolio/transactions/<symbol>')
@login_required
def portfolio_transactions(symbol=None):
    """Portfolio transactions page"""
    try:
        portfolio_mgr = get_portfolio_manager()
        
        # Get transactions
        transactions = portfolio_mgr.get_user_transactions(session['user_id'], symbol=symbol)
        
        return render_template('transactions.html', 
                             transactions=transactions, 
                             symbol=symbol)
        
    except Exception as e:
        logger.error(f"Error in portfolio_transactions route: {e}")
        flash('Error loading transactions', 'error')
        return redirect(url_for('portfolio'))

@app.route('/delete_portfolio_transaction', methods=['POST'])
@login_required
def delete_portfolio_transaction():
    """Delete a portfolio transaction"""
    try:
        data = request.get_json()
        transaction_id = data.get('transaction_id')
        
        if not transaction_id:
            return jsonify({'success': False, 'error': 'Transaction ID is required'})
        
        portfolio_mgr = get_portfolio_manager()
        result = portfolio_mgr.delete_transaction(session['user_id'], transaction_id)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error deleting portfolio transaction: {e}")
        return jsonify({'success': False, 'error': 'Error deleting transaction'})

@app.route('/portfolio/performance')
@login_required
def portfolio_performance():
    """Portfolio performance analysis page"""
    try:
        portfolio_mgr = get_portfolio_manager()
        
        # Get performance data
        performance = portfolio_mgr.get_portfolio_performance(session['user_id'])
        
        return jsonify(performance)
        
    except Exception as e:
        logger.error(f"Error in portfolio_performance route: {e}")
        return jsonify({'error': 'Failed to load performance data'})

@app.route('/export_transactions')
@app.route('/export_transactions/<symbol>')
@login_required
def export_transactions(symbol=None):
    """Export transactions to CSV or PDF"""
    try:
        format_type = request.args.get('format', 'csv').lower()
        
        portfolio_mgr = get_portfolio_manager()
        transactions = portfolio_mgr.get_user_transactions(session['user_id'], symbol=symbol)
        
        if format_type == 'csv':
            # Create CSV response
            import io
            import csv
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(['Date', 'Type', 'Symbol', 'Shares', 'Price per Share', 'Fees', 'Total Amount', 'Notes'])
            
            # Write data
            for transaction in transactions:
                writer.writerow([
                    transaction['transaction_date'].isoformat() if transaction['transaction_date'] else '',
                    transaction['transaction_type'],
                    transaction['symbol'],
                    transaction['shares'],
                    transaction['price_per_share'],
                    transaction['fees'],
                    transaction['total_amount'],
                    transaction['notes'] or ''
                ])
            
            output.seek(0)
            
            from flask import Response
            filename = f"transactions_{symbol}_{date.today().isoformat()}.csv" if symbol else f"transactions_{date.today().isoformat()}.csv"
            
            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename={filename}'
                }
            )
        
        else:
            # Unsupported format - default to CSV
            logger.warning(f"Unsupported export format requested: {format_type}, defaulting to CSV")
            return redirect(url_for('export_transactions', symbol=symbol, format='csv'))
            
    except Exception as e:
        logger.error(f"Error exporting transactions: {e}")
        flash('Error exporting transactions', 'error')
        return redirect(url_for('portfolio_transactions', symbol=symbol))

# New Financial Data Routes

@app.route('/corporate-actions')
def corporate_actions():
    """Corporate actions overview page"""
    try:
        service = get_stock_service()
        actions = service.get_all_corporate_actions(limit=200)
        
        # Get data availability status for corporate actions
        data_availability = {}
        
        # Calculate summary statistics
        dividend_count = len([a for a in actions if a['action_type'] == 'dividend'])
        split_count = len([a for a in actions if a['action_type'] == 'split'])
        
        # Count recent actions (last 30 days)
        from datetime import datetime, timedelta
        recent_cutoff = datetime.now() - timedelta(days=30)
        recent_count = len([a for a in actions if datetime.strptime(a['action_date'], '%Y-%m-%d') > recent_cutoff])
        
        return render_template('corporate_actions.html',
                             actions=actions,
                             dividend_count=dividend_count,
                             split_count=split_count,
                             recent_count=recent_count,
                             data_availability=data_availability)
        
    except Exception as e:
        logger.error(f"Error in corporate_actions route: {e}")
        flash('Error loading corporate actions data', 'error')
        return render_template('corporate_actions.html', 
                             actions=[], 
                             dividend_count=0, 
                             split_count=0, 
                             recent_count=0,
                             data_availability={'corporate_actions': 'Data Unavailable'})

@app.route('/analyst-recommendations')
def general_analyst_recommendations():
    """General analyst recommendations overview page"""
    try:
        service = get_stock_service()
        recommendations = service.get_all_analyst_recommendations(limit=200)
        
        # Get data availability status for analyst recommendations
        data_availability = {}
        
        # Calculate summary statistics
        symbols_with_data = len(set([r['symbol'] for r in recommendations]))
        
        # Group by recommendation type
        strong_buy_avg = sum([r.get('strong_buy', 0) for r in recommendations]) / len(recommendations) if recommendations else 0
        buy_avg = sum([r.get('buy', 0) for r in recommendations]) / len(recommendations) if recommendations else 0
        hold_avg = sum([r.get('hold', 0) for r in recommendations]) / len(recommendations) if recommendations else 0
        sell_avg = sum([r.get('sell', 0) for r in recommendations]) / len(recommendations) if recommendations else 0
        strong_sell_avg = sum([r.get('strong_sell', 0) for r in recommendations]) / len(recommendations) if recommendations else 0
        
        return render_template('analyst_recommendations.html',
                             recommendations=recommendations,
                             symbols_with_data=symbols_with_data,
                             strong_buy_avg=round(strong_buy_avg, 1),
                             buy_avg=round(buy_avg, 1),
                             hold_avg=round(hold_avg, 1),
                             sell_avg=round(sell_avg, 1),
                             strong_sell_avg=round(strong_sell_avg, 1),
                             data_availability=data_availability)
        
    except Exception as e:
        logger.error(f"Error in general_analyst_recommendations route: {e}")
        flash('Error loading analyst recommendations data', 'error')
        return render_template('analyst_recommendations.html', 
                             recommendations=[], 
                             symbols_with_data=0,
                             strong_buy_avg=0,
                             buy_avg=0,
                             hold_avg=0,
                             sell_avg=0,
                             strong_sell_avg=0,
                             data_availability={'analyst_recommendations': 'Data Unavailable'})

@app.route('/stock/<symbol>/financial-statements')
def financial_statements(symbol):
    """Financial statements page for a specific symbol"""
    try:
        service = get_stock_service()
        
        # Get financial statements
        income_statements = service.get_income_statements(symbol.upper(), limit=5)
        balance_sheets = service.get_balance_sheets(symbol.upper(), limit=5)
        cash_flow_statements = service.get_cash_flow_statements(symbol.upper(), limit=5)
        
        # Get data availability status for financial statements
        data_availability = service.get_data_availability_status(symbol.upper())
        
        return render_template('financial_statements.html',
                             symbol=symbol.upper(),
                             income_statements=income_statements,
                             balance_sheets=balance_sheets,
                             cash_flow_statements=cash_flow_statements,
                             data_availability=data_availability)
        
    except Exception as e:
        logger.error(f"Error in financial_statements route for {symbol}: {e}")
        flash('Error loading financial statements data', 'error')
        return render_template('financial_statements.html',
                             symbol=symbol.upper(),
                             income_statements=[],
                             balance_sheets=[],
                             cash_flow_statements=[],
                             data_availability={'financial_statements': 'Data Unavailable'})

@app.route('/stock/<symbol>/analyst-recommendations')
def analyst_recommendations(symbol):
    """Analyst recommendations page for a specific symbol"""
    try:
        service = get_stock_service()
        recommendations = service.get_analyst_recommendations(symbol.upper())
        
        # Get data availability status for analyst recommendations
        data_availability = service.get_data_availability_status(symbol.upper())
        
        return render_template('analyst_recommendations.html',
                             symbol=symbol.upper(),
                             recommendations=recommendations,
                             data_availability=data_availability)
        
    except Exception as e:
        logger.error(f"Error in analyst_recommendations route for {symbol}: {e}")
        flash('Error loading analyst recommendations', 'error')
        return render_template('analyst_recommendations.html',
                             symbol=symbol.upper(),
                             recommendations=[],
                             data_availability={'analyst_recommendations': 'Data Unavailable'})

# Add format_currency filter for templates
@app.route('/api/stock/<symbol>/chart')
def get_stock_chart_data(symbol):
    """API endpoint for historical price chart data"""
    try:
        service = get_stock_service()
        
        # Get period parameter (default to 1 year)
        period = request.args.get('period', '1y')
        
        # Map period to actual date range
        from datetime import datetime, timedelta
        end_date = datetime.now().date()
        
        if period == '1m':
            start_date = end_date - timedelta(days=30)
        elif period == '3m':
            start_date = end_date - timedelta(days=90)
        elif period == '6m':
            start_date = end_date - timedelta(days=180)
        elif period == '1y':
            start_date = end_date - timedelta(days=365)
        elif period == '2y':
            start_date = end_date - timedelta(days=730)
        elif period == '5y':
            start_date = end_date - timedelta(days=1825)
        else:
            start_date = end_date - timedelta(days=365)  # Default to 1 year
            
        # Get historical price data
        price_data = service.get_historical_prices(symbol.upper(), start_date, end_date)
        
        if not price_data:
            return jsonify({
                'error': 'No price data available',
                'symbol': symbol.upper(),
                'period': period
            }), 404
        
        # Format data for Chart.js
        chart_data = {
            'symbol': symbol.upper(),
            'period': period,
            'data': {
                'labels': [row['date'].strftime('%Y-%m-%d') for row in price_data],
                'datasets': [{
                    'label': f'{symbol.upper()} Price',
                    'data': [float(row['close']) for row in price_data],
                    'borderColor': 'rgb(54, 162, 235)',
                    'backgroundColor': 'rgba(54, 162, 235, 0.1)',
                    'fill': True,
                    'tension': 0.1
                }]
            },
            'volume_data': {
                'labels': [row['date'].strftime('%Y-%m-%d') for row in price_data],
                'datasets': [{
                    'label': 'Volume',
                    'data': [int(row['volume']) if row['volume'] else 0 for row in price_data],
                    'backgroundColor': 'rgba(75, 192, 192, 0.2)',
                    'borderColor': 'rgba(75, 192, 192, 1)',
                }]
            }
        }
        
        return jsonify(chart_data)
        
    except Exception as e:
        logger.error(f"Error getting chart data for {symbol}: {e}")
        return jsonify({
            'error': 'Failed to retrieve chart data',
            'symbol': symbol.upper(),
            'period': period,
            'message': str(e)
        }), 500

@app.template_filter('format_currency')
def format_currency(value):
    """Format currency values for display"""
    if value is None:
        return '-'
    
    try:
        value = float(value)
        if abs(value) >= 1e12:
            return f"${value/1e12:.2f}T"
        elif abs(value) >= 1e9:
            return f"${value/1e9:.2f}B"
        elif abs(value) >= 1e6:
            return f"${value/1e6:.2f}M"
        elif abs(value) >= 1e3:
            return f"${value/1e3:.2f}K"
        else:
            return f"${value:.2f}"
    except (ValueError, TypeError):
        return '-'

# Advanced User Alerts System Routes

@app.route('/alerts')
@login_required
def alerts():
    """User alerts management page"""
    try:
        from alerts_service import AlertsService
        alerts_service = AlertsService()
        
        # Get user alerts
        user_alerts = alerts_service.get_user_alerts(session['user_id'])
        
        # Get recent notifications
        recent_notifications = alerts_service.get_user_notifications(session['user_id'], limit=10)
        
        # Get unread count
        unread_count = alerts_service.get_unread_count(session['user_id'])
        
        return render_template('alerts.html',
                             alerts=user_alerts,
                             notifications=recent_notifications,
                             unread_count=unread_count)
        
    except Exception as e:
        logger.error(f"Error in alerts route: {e}")
        flash('Error loading alerts', 'error')
        return redirect(url_for('index'))

@app.route('/alerts/create', methods=['GET', 'POST'])
@login_required
def create_alert():
    """Create new alert page"""
    if request.method == 'POST':
        try:
            from alerts_service import AlertsService
            alerts_service = AlertsService()
            
            # Get form data
            symbol = request.form.get('symbol', '').strip().upper()
            alert_type = request.form.get('alert_type', '').strip()
            condition_type = request.form.get('condition_type', '').strip()
            target_value = request.form.get('target_value', '').strip()
            upper_threshold = request.form.get('upper_threshold', '').strip()
            lower_threshold = request.form.get('lower_threshold', '').strip()
            
            # Validate required fields
            if not symbol or not alert_type or not condition_type:
                flash('Symbol, alert type, and condition type are required', 'error')
                return redirect(url_for('create_alert'))
            
            # Verify stock exists
            service = get_stock_service()
            stock_info = service.get_stock_basic_info(symbol)
            if not stock_info:
                flash(f'Stock symbol {symbol} not found in our database', 'error')
                return redirect(url_for('create_alert'))
            
            # Parse numeric values
            target_val = float(target_value) if target_value else None
            upper_val = float(upper_threshold) if upper_threshold else None
            lower_val = float(lower_threshold) if lower_threshold else None
            
            # Create alert
            alert_id = alerts_service.create_alert(
                user_id=session['user_id'],
                symbol=symbol,
                alert_type=alert_type,
                condition_type=condition_type,
                target_value=target_val,
                upper_threshold=upper_val,
                lower_threshold=lower_val
            )
            
            if alert_id:
                flash(f'Alert created successfully for {symbol}', 'success')
                return redirect(url_for('alerts'))
            else:
                flash('Failed to create alert', 'error')
                return redirect(url_for('create_alert'))
                
        except ValueError as e:
            flash('Invalid numeric value provided', 'error')
            return redirect(url_for('create_alert'))
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            flash('Error creating alert', 'error')
            return redirect(url_for('create_alert'))
    
    # GET request - show create form
    return render_template('create_alert.html')

@app.route('/notifications')
@login_required
def notifications():
    """User notifications page"""
    try:
        from alerts_service import AlertsService
        alerts_service = AlertsService()
        
        # Get notifications
        limit = request.args.get('limit', 50, type=int)
        user_notifications = alerts_service.get_user_notifications(session['user_id'], limit=limit)
        
        # Get unread count
        unread_count = alerts_service.get_unread_count(session['user_id'])
        
        return render_template('notifications.html',
                             notifications=user_notifications,
                             unread_count=unread_count)
        
    except Exception as e:
        logger.error(f"Error in notifications route: {e}")
        flash('Error loading notifications', 'error')
        return redirect(url_for('index'))

@app.route('/squeeze')
def short_squeeze_analysis():
    """Short squeeze analysis dashboard"""
    try:
        service = get_stock_service()
        
        # Get query parameters for filtering
        limit = request.args.get('limit', 50, type=int)
        min_score = request.args.get('min_score', type=float)
        min_data_quality = request.args.get('min_data_quality')
        order_by = request.args.get('order_by', 'squeeze_score')
        
        # Validate parameters
        if limit < 1 or limit > 200:
            limit = 50
        
        valid_order_fields = ['squeeze_score', 'si_score', 'dtc_score', 'float_score', 'momentum_score']
        if order_by not in valid_order_fields:
            order_by = 'squeeze_score'
        
        # Get squeeze rankings
        rankings = service.get_short_squeeze_rankings(
            limit=limit,
            order_by=order_by,
            min_score=min_score,
            min_data_quality=min_data_quality
        )
        
        # Get summary statistics
        stats = service.get_short_squeeze_summary_stats()
        
        return render_template('short_squeeze.html', 
                             rankings=rankings,
                             stats=stats,
                             filters={
                                 'limit': limit,
                                 'min_score': min_score,
                                 'min_data_quality': min_data_quality,
                                 'order_by': order_by
                             })
        
    except Exception as e:
        logger.error(f"Error in short_squeeze_analysis route: {e}")
        flash('Error loading short squeeze analysis', 'error')
        return redirect(url_for('index'))

@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error="Internal server error"), 500


# Global server instance for graceful shutdown
server = None
shutdown_event = threading.Event()

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_event.set()
    if server:
        server.shutdown()
    sys.exit(0)

def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGHUP'):
        signal.signal(signal.SIGHUP, signal_handler)

def write_pid_file(pid_file_path="/tmp/stock_analyst_webapp.pid"):
    """Write process ID to file for external management"""
    try:
        with open(pid_file_path, 'w') as f:
            f.write(str(os.getpid()))
        logger.info(f"PID file written: {pid_file_path}")
    except Exception as e:
        logger.warning(f"Could not write PID file: {e}")

def remove_pid_file(pid_file_path="/tmp/stock_analyst_webapp.pid"):
    """Remove PID file on shutdown"""
    try:
        if os.path.exists(pid_file_path):
            os.remove(pid_file_path)
        logger.info("PID file removed")
    except Exception as e:
        logger.warning(f"Could not remove PID file: {e}")

def run_app():
    """Run the Flask application with graceful shutdown support"""
    global server
    
    # Setup signal handlers
    setup_signal_handlers()
    
    # Write PID file for process management
    write_pid_file()
    
    try:
        # Create server instance
        port = int(os.environ.get('PORT', 5000))
        server = make_server('0.0.0.0', port, app, threaded=True)
        logger.info(f"Stock Analyst Web Application starting on http://0.0.0.0:{port}")
        logger.info(f"Process ID: {os.getpid()}")
        
        # Start server
        server.serve_forever()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Error running server: {e}")
    finally:
        # Cleanup
        remove_pid_file()
        logger.info("Stock Analyst Web Application stopped")

if __name__ == '__main__':
    run_app()