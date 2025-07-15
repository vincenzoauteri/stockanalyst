#!/usr/bin/env python3
"""
API Routes for Stock Analyst Application
RESTful API endpoints for programmatic access to stock data and portfolio management
"""

from datetime import datetime, date

from flask import Blueprint, request, jsonify, session

from auth import login_required
from logging_config import get_logger
from services import (
    get_stock_service,
    get_fmp_client,
    get_undervaluation_analyzer,
    get_portfolio_manager
)

logger = get_logger(__name__)

def serialize_dates_in_dict(obj):
    """
    Recursively convert date and datetime objects to ISO format strings for JSON serialization
    """
    if isinstance(obj, dict):
        return {key: serialize_dates_in_dict(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [serialize_dates_in_dict(item) for item in obj]
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    else:
        return obj

# Create API blueprint
api_v2 = Blueprint('api_v2', __name__, url_prefix='/api/v2')

# Initialize services (global instances will be used)

# Stock Data Endpoints
@api_v2.route('/stocks', methods=['GET'])
def api_get_stocks():
    """Get list of all S&P 500 stocks with filtering, sorting, and pagination"""
    try:
        service = get_stock_service()
        
        # Get query parameters with validation
        try:
            sector = request.args.get('sector')
            min_score = request.args.get('min_score', type=float)
            max_score = request.args.get('max_score', type=float)
            search = request.args.get('search')
            sort_field = request.args.get('sort', 'symbol')
            sort_order = request.args.get('order', 'asc')
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 50, type=int)
            
            # Validate pagination parameters
            if page < 1:
                page = 1
            if per_page < 1 or per_page > 500:  # Limit max per_page to prevent abuse
                per_page = 50
                
            # Calculate offset for pagination
            offset = (page - 1) * per_page
            
        except ValueError as e:
            logger.warning(f"Invalid query parameters in api_get_stocks: {e}")
            return jsonify({'success': False, 'error': 'Invalid query parameters'}), 400
        
        # Get total count for pagination
        total_count = service.get_stocks_count(
            sector=sector,
            min_score=min_score,
            max_score=max_score,
            search=search
        )
        
        # Get paginated stocks with database-level filtering and sorting
        stocks_list = service.get_all_stocks_with_scores(
            sector=sector,
            min_score=min_score,
            max_score=max_score,
            search=search,
            sort_by=sort_field,
            sort_order=sort_order,
            limit=per_page,
            offset=offset
        )
        
        # Clean up response data
        response_data = []
        for stock in stocks_list:
            try:
                response_data.append({
                    'symbol': stock.get('symbol'),
                    'name': stock.get('name') or stock.get('company_name'),
                    'sector': stock.get('sector'),
                    'price': stock.get('price'),
                    'market_cap': stock.get('market_cap'),
                    'undervaluation_score': stock.get('undervaluation_score')
                })
            except (AttributeError, KeyError) as e:
                logger.warning(f"Skipping malformed stock data: {e}")
                continue
        
        # Calculate pagination metadata
        total_pages = (total_count + per_page - 1) // per_page
        has_next = page < total_pages
        has_prev = page > 1
        
        return jsonify({
            'success': True,
            'data': response_data,
            'pagination': {
                'total_count': total_count,
                'total_pages': total_pages,
                'current_page': page,
                'per_page': per_page,
                'has_next': has_next,
                'has_prev': has_prev
            },
            'filters': {
                'sector': sector,
                'min_score': min_score,
                'max_score': max_score,
                'search': search,
                'sort': sort_field,
                'order': sort_order
            }
        })
        
    except AttributeError as e:
        logger.error(f"Service method not available in api_get_stocks: {e}")
        return jsonify({'success': False, 'error': 'Service temporarily unavailable'}), 503
    except ConnectionError as e:
        logger.error(f"Database connection error in api_get_stocks: {e}")
        return jsonify({'success': False, 'error': 'Database connection error'}), 503
    except Exception as e:
        logger.error(f"Unexpected error in api_get_stocks: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@api_v2.route('/stocks/<string:symbol>', methods=['GET'])
def api_get_stock_detail(symbol):
    """Get detailed information for a specific stock"""
    try:
        service = get_stock_service()
        
        # Get stock basic info
        basic_info = service.get_stock_basic_info(symbol.upper())
        if not basic_info:
            return jsonify({'success': False, 'error': 'Stock not found'}), 404
        
        # Get company profile
        profile = service.get_stock_company_profile(symbol.upper())
        
        # Get undervaluation score
        undervaluation_score = service.get_stock_undervaluation_score(symbol.upper())
        
        # Combine data
        stock_detail = {
            'symbol': basic_info.get('symbol'),
            'company_name': profile.get('companyname') if profile else basic_info.get('name'),
            'sector': basic_info.get('sector'),
            'price': profile.get('price') if profile else None,
            'beta': profile.get('beta') if profile else None,
            'market_cap': profile.get('mktcap') if profile else None,
            'description': profile.get('description') if profile else None,
            'website': profile.get('website') if profile else None,
            'employees': profile.get('fulltimeemployees') if profile else None,
            'undervaluation_score': undervaluation_score.get('undervaluation_score') if undervaluation_score else None
        }
        
        return jsonify({
            'success': True,
            'data': stock_detail
        })
        
    except Exception as e:
        logger.error(f"Error in api_get_stock_detail: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_v2.route('/stocks/<string:symbol>/history', methods=['GET'])
def api_get_stock_history(symbol):
    """Get historical price data for a stock"""
    try:
        service = get_stock_service()
        
        # Get query parameters
        limit = request.args.get('limit', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Get historical data
        history = service.get_stock_historical_prices(symbol.upper(), limit=limit)
        
        if not history:
            return jsonify({'success': False, 'error': 'No historical data found'}), 404
        
        # Filter by date range if specified
        if start_date or end_date:
            filtered_history = []
            for record in history:
                record_date = record.get('date')
                if record_date:
                    if start_date and record_date < start_date:
                        continue
                    if end_date and record_date > end_date:
                        continue
                    filtered_history.append(record)
            history = filtered_history
        
        # Serialize dates in the history data
        history = serialize_dates_in_dict(history)
        
        return jsonify({
            'success': True,
            'data': history,
            'total': len(history),
            'symbol': symbol.upper()
        })
        
    except Exception as e:
        logger.error(f"Error in api_get_stock_history: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Sectors Endpoints
@api_v2.route('/sectors', methods=['GET'])
def api_get_sectors():
    """Get analysis data for all sectors"""
    try:
        service = get_stock_service()
        
        # Get all stocks with scores
        stocks_list = service.get_all_stocks_with_scores()
        
        # Group by sector
        sectors = {}
        for stock in stocks_list:
            sector = stock.get('sector', 'Other')
            if sector not in sectors:
                sectors[sector] = {
                    'sector': sector,
                    'stocks': [],
                    'total_market_cap': 0,
                    'total_score': 0,
                    'stock_count': 0
                }
            
            sectors[sector]['stocks'].append(stock)
            sectors[sector]['stock_count'] += 1
            sectors[sector]['total_market_cap'] += stock.get('mktcap', 0)
            sectors[sector]['total_score'] += stock.get('undervaluation_score', 0)
        
        # Calculate averages and find best/worst
        sector_data = []
        for sector_info in sectors.values():
            count = sector_info['stock_count']
            if count > 0:
                avg_score = sector_info['total_score'] / count
                avg_market_cap = sector_info['total_market_cap'] / count
                
                # Find best and worst stocks
                stocks = sector_info['stocks']
                best_stock = max(stocks, key=lambda x: x.get('undervaluation_score', 0))
                worst_stock = min(stocks, key=lambda x: x.get('undervaluation_score', 0))
                
                sector_data.append({
                    'sector': sector_info['sector'],
                    'stock_count': count,
                    'avg_undervaluation_score': round(avg_score, 2),
                    'avg_market_cap': round(avg_market_cap, 0),
                    'best_stock': best_stock.get('symbol'),
                    'worst_stock': worst_stock.get('symbol')
                })
        
        # Sort by average score descending
        sector_data.sort(key=lambda x: x['avg_undervaluation_score'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': sector_data,
            'total': len(sector_data)
        })
        
    except Exception as e:
        logger.error(f"Error in api_get_sectors: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Portfolio Endpoints (Authentication Required)
@api_v2.route('/portfolio', methods=['GET'])
@login_required
def api_get_portfolio():
    """Get user's complete portfolio"""
    try:
        portfolio_mgr = get_portfolio_manager()
        
        portfolio_data = portfolio_mgr.get_user_portfolio(session['user_id'])
        
        return jsonify({
            'success': True,
            'data': portfolio_data
        })
        
    except Exception as e:
        logger.error(f"Error in api_get_portfolio: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_v2.route('/portfolio/transactions', methods=['GET'])
@login_required
def api_get_portfolio_transactions():
    """Get user's transaction history"""
    try:
        portfolio_mgr = get_portfolio_manager()
        
        # Get query parameters
        symbol = request.args.get('symbol')
        transaction_type = request.args.get('type')
        limit = request.args.get('limit', type=int)
        
        transactions = portfolio_mgr.get_user_transactions(session['user_id'], symbol=symbol, limit=limit)
        
        # Filter by transaction type if specified
        if transaction_type:
            transactions = [t for t in transactions if t['transaction_type'] == transaction_type.upper()]
        
        # Convert dates to strings for JSON serialization
        for transaction in transactions:
            if transaction.get('transaction_date'):
                transaction['transaction_date'] = transaction['transaction_date'].isoformat()
            if transaction.get('created_at'):
                transaction['created_at'] = transaction['created_at'].isoformat()
        
        return jsonify({
            'success': True,
            'data': transactions,
            'total': len(transactions)
        })
        
    except Exception as e:
        logger.error(f"Error in api_get_portfolio_transactions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_v2.route('/portfolio/performance', methods=['GET'])
@login_required
def api_get_portfolio_performance():
    """Get detailed portfolio performance analytics"""
    try:
        portfolio_mgr = get_portfolio_manager()
        
        performance = portfolio_mgr.get_portfolio_performance(session['user_id'])
        
        return jsonify({
            'success': True,
            'data': performance
        })
        
    except Exception as e:
        logger.error(f"Error in api_get_portfolio_performance: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Analysis Endpoints
@api_v2.route('/analysis/undervaluation', methods=['GET'])
def api_get_undervaluation_summary():
    """Get summary of latest undervaluation analysis"""
    try:
        analyzer = get_undervaluation_analyzer()
        
        # Get cache stats
        cache_stats = analyzer.get_cache_stats()
        
        # Get summary data
        service = get_stock_service()
        stocks_list = service.get_all_stocks_with_scores()
        
        # Calculate summary statistics
        scores = [s.get('undervaluation_score', 0) for s in stocks_list if s.get('undervaluation_score')]
        
        if scores:
            summary = {
                'total_stocks': len(stocks_list),
                'stocks_with_scores': len(scores),
                'avg_score': sum(scores) / len(scores),
                'min_score': min(scores),
                'max_score': max(scores),
                'highly_undervalued': len([s for s in scores if s >= 80]),
                'moderately_undervalued': len([s for s in scores if 60 <= s < 80]),
                'fairly_valued': len([s for s in scores if 40 <= s < 60]),
                'overvalued': len([s for s in scores if s < 40])
            }
        else:
            summary = {
                'total_stocks': len(stocks_list),
                'stocks_with_scores': 0,
                'message': 'No undervaluation scores available'
            }
        
        return jsonify({
            'success': True,
            'data': summary,
            'cache_stats': cache_stats
        })
        
    except Exception as e:
        logger.error(f"Error in api_get_undervaluation_summary: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_v2.route('/analysis/undervaluation/<string:symbol>', methods=['GET'])
def api_get_stock_undervaluation(symbol):
    """Get detailed undervaluation analysis for a specific stock"""
    try:
        service = get_stock_service()
        
        # Get undervaluation score details
        undervaluation_data = service.get_stock_undervaluation_score(symbol.upper())
        
        if not undervaluation_data:
            return jsonify({'success': False, 'error': 'No undervaluation data found for this stock'}), 404
        
        return jsonify({
            'success': True,
            'data': undervaluation_data
        })
        
    except Exception as e:
        logger.error(f"Error in api_get_stock_undervaluation: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Authentication status endpoint
@api_v2.route('/auth/status', methods=['GET'])
def api_auth_status():
    """Get current authentication status"""
    try:
        if 'user_id' in session:
            return jsonify({
                'success': True,
                'authenticated': True,
                'user': {
                    'user_id': session['user_id'],
                    'username': session.get('username'),
                    'email': session.get('email')
                }
            })
        else:
            return jsonify({
                'success': True,
                'authenticated': False,
                'message': 'Not authenticated'
            })
            
    except Exception as e:
        logger.error(f"Error in api_auth_status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# API Health Check
@api_v2.route('/health', methods=['GET'])
def api_health_check():
    """API health check endpoint"""
    try:
        # Check database connectivity
        service = get_stock_service()
        stock_count = len(service.get_all_stocks_with_scores())
        
        # Check FMP client
        client = get_fmp_client()
        remaining_requests = client.get_remaining_requests()
        
        return jsonify({
            'success': True,
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': {
                'connected': True,
                'stock_count': stock_count
            },
            'api_client': {
                'remaining_requests': remaining_requests
            }
        })
        
    except Exception as e:
        logger.error(f"Error in api_health_check: {e}")
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e)
        }), 500

# New Financial Data Endpoints

@api_v2.route('/stocks/<symbol>/corporate-actions', methods=['GET'])
def api_get_corporate_actions(symbol):
    """Get corporate actions for a specific symbol"""
    try:
        limit = request.args.get('limit', 50, type=int)
        service = get_stock_service()
        actions = service.get_corporate_actions(symbol.upper(), limit=limit)
        
        # Serialize dates in the actions data
        actions = serialize_dates_in_dict(actions)
        
        return jsonify({
            'success': True,
            'symbol': symbol.upper(),
            'corporate_actions': actions,
            'count': len(actions)
        })
        
    except Exception as e:
        logger.error(f"Error in api_get_corporate_actions for {symbol}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_v2.route('/corporate-actions', methods=['GET'])
def api_get_all_corporate_actions():
    """Get recent corporate actions across all symbols"""
    try:
        limit = request.args.get('limit', 100, type=int)
        service = get_stock_service()
        actions = service.get_all_corporate_actions(limit=limit)
        
        # Serialize dates in the actions data
        actions = serialize_dates_in_dict(actions)
        
        return jsonify({
            'success': True,
            'corporate_actions': actions,
            'count': len(actions)
        })
        
    except Exception as e:
        logger.error(f"Error in api_get_all_corporate_actions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_v2.route('/stocks/<symbol>/financial-statements', methods=['GET'])
def api_get_financial_statements(symbol):
    """Get financial statements for a specific symbol"""
    try:
        limit = request.args.get('limit', 5, type=int)
        service = get_stock_service()
        
        financial_statements = {
            'symbol': symbol.upper(),
            'income_statements': service.get_income_statements(symbol.upper(), limit=limit),
            'balance_sheets': service.get_balance_sheets(symbol.upper(), limit=limit),
            'cash_flow_statements': service.get_cash_flow_statements(symbol.upper(), limit=limit)
        }
        
        # Serialize dates in the financial statements data
        financial_statements = serialize_dates_in_dict(financial_statements)
        
        return jsonify({
            'success': True,
            'data': financial_statements
        })
        
    except Exception as e:
        logger.error(f"Error in api_get_financial_statements for {symbol}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_v2.route('/stocks/<symbol>/income-statements', methods=['GET'])
def api_get_income_statements(symbol):
    """Get income statements for a specific symbol"""
    try:
        limit = request.args.get('limit', 5, type=int)
        service = get_stock_service()
        statements = service.get_income_statements(symbol.upper(), limit=limit)
        
        # Serialize dates in the statements data
        statements = serialize_dates_in_dict(statements)
        
        return jsonify({
            'success': True,
            'symbol': symbol.upper(),
            'income_statements': statements,
            'count': len(statements)
        })
        
    except Exception as e:
        logger.error(f"Error in api_get_income_statements for {symbol}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_v2.route('/stocks/<symbol>/balance-sheets', methods=['GET'])
def api_get_balance_sheets(symbol):
    """Get balance sheets for a specific symbol"""
    try:
        limit = request.args.get('limit', 5, type=int)
        service = get_stock_service()
        statements = service.get_balance_sheets(symbol.upper(), limit=limit)
        
        # Serialize dates in the statements data
        statements = serialize_dates_in_dict(statements)
        
        return jsonify({
            'success': True,
            'symbol': symbol.upper(),
            'balance_sheets': statements,
            'count': len(statements)
        })
        
    except Exception as e:
        logger.error(f"Error in api_get_balance_sheets for {symbol}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_v2.route('/stocks/<symbol>/cash-flow-statements', methods=['GET'])
def api_get_cash_flow_statements(symbol):
    """Get cash flow statements for a specific symbol"""
    try:
        limit = request.args.get('limit', 5, type=int)
        service = get_stock_service()
        statements = service.get_cash_flow_statements(symbol.upper(), limit=limit)
        
        # Serialize dates in the statements data
        statements = serialize_dates_in_dict(statements)
        
        return jsonify({
            'success': True,
            'symbol': symbol.upper(),
            'cash_flow_statements': statements,
            'count': len(statements)
        })
        
    except Exception as e:
        logger.error(f"Error in api_get_cash_flow_statements for {symbol}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_v2.route('/stocks/<symbol>/analyst-recommendations', methods=['GET'])
def api_get_analyst_recommendations(symbol):
    """Get analyst recommendations for a specific symbol"""
    try:
        service = get_stock_service()
        recommendations = service.get_analyst_recommendations(symbol.upper())
        
        # Serialize dates in the recommendations data
        recommendations = serialize_dates_in_dict(recommendations)
        
        return jsonify({
            'success': True,
            'symbol': symbol.upper(),
            'analyst_recommendations': recommendations,
            'count': len(recommendations)
        })
        
    except Exception as e:
        logger.error(f"Error in api_get_analyst_recommendations for {symbol}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_v2.route('/stocks/<symbol>/financial-summary', methods=['GET'])
def api_get_financial_summary(symbol):
    """Get comprehensive financial summary for a symbol"""
    try:
        service = get_stock_service()
        summary = service.get_financial_summary(symbol.upper())
        
        # Serialize dates in the summary data
        summary = serialize_dates_in_dict(summary)
        
        return jsonify({
            'success': True,
            'data': summary
        })
        
    except Exception as e:
        logger.error(f"Error in api_get_financial_summary for {symbol}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Error handlers for API
@api_v2.errorhandler(404)
def api_not_found(error):
    """API 404 error handler"""
    return jsonify({
        'success': False,
        'error': 'Endpoint not found',
        'message': 'The requested API endpoint does not exist'
    }), 404

@api_v2.errorhandler(500)
def api_internal_error(error):
    """API 500 error handler"""
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500

@api_v2.route('/symbols', methods=['GET'])
def get_symbols():
    """
    Get all available S&P 500 stock symbols for autocomplete/selection
    
    Returns:
        JSON: List of all S&P 500 stock symbols
    """
    try:
        service = get_stock_service()
        symbols = service.db_manager.get_sp500_symbols()
        
        return jsonify({
            'success': True,
            'data': symbols,
            'count': len(symbols)
        })
        
    except Exception as e:
        logger.error(f"Error retrieving symbols: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': 'Failed to retrieve stock symbols'
        }), 500

@api_v2.route('/compare')
def compare_stocks():
    """
    Compare multiple stocks side-by-side
    Query parameters:
    - symbols: Comma-separated list of stock symbols (e.g., AAPL,MSFT,GOOGL)
    - format: Response format ('json' or 'table', default: 'json')
    """
    try:
        # Get symbols parameter
        symbols_param = request.args.get('symbols', '')
        if not symbols_param:
            return jsonify({
                'error': 'symbols parameter is required',
                'message': 'Provide comma-separated list of symbols (e.g., ?symbols=AAPL,MSFT,GOOGL)'
            }), 400
        
        # Parse and validate symbols
        symbols = [s.strip().upper() for s in symbols_param.split(',')]
        symbols = [s for s in symbols if s]  # Remove empty strings
        
        if len(symbols) < 2:
            return jsonify({
                'error': 'At least 2 symbols required for comparison',
                'message': 'Provide at least 2 comma-separated symbols'
            }), 400
        
        if len(symbols) > 5:
            return jsonify({
                'error': 'Maximum 5 symbols allowed for comparison',
                'message': 'Provide at most 5 comma-separated symbols'
            }), 400
        
        # Get comparison data
        service = get_stock_service()
        comparison_data = service.get_stock_comparison(symbols)
        
        if not comparison_data:
            return jsonify({
                'error': 'No data found for comparison',
                'message': 'None of the provided symbols have sufficient data'
            }), 404
        
        # Check requested format
        format_type = request.args.get('format', 'json').lower()
        
        if format_type == 'table':
            # Return table-friendly format
            table_data = {
                'headers': ['Metric'] + [stock['symbol'] for stock in comparison_data],
                'rows': []
            }
            
            # Define metrics to compare
            metrics = [
                ('Symbol', 'symbol'),
                ('Company Name', 'company_name'),
                ('Price', 'price'),
                ('Market Cap', 'market_cap'),
                ('Sector', 'sector'),
                ('Industry', 'industry'),
                ('Undervaluation Score', 'undervaluation_score'),
                ('Valuation Score', 'valuation_score'),
                ('Quality Score', 'quality_score'),
                ('PE Ratio', 'pe_ratio'),
                ('PB Ratio', 'pb_ratio'),
                ('PS Ratio', 'ps_ratio'),
                ('ROE', 'roe'),
                ('ROA', 'roa'),
                ('Beta', 'beta'),
                ('Data Quality', 'data_quality')
            ]
            
            for metric_name, metric_key in metrics:
                row = [metric_name]
                for stock in comparison_data:
                    value = stock.get(metric_key)
                    if value is None:
                        row.append('N/A')
                    elif isinstance(value, (int, float)):
                        if metric_key in ['price', 'market_cap']:
                            row.append(f"${value:,.2f}" if value < 1000000 else f"${value/1000000:,.1f}M")
                        elif metric_key in ['pe_ratio', 'pb_ratio', 'ps_ratio', 'roe', 'roa', 'beta']:
                            row.append(f"{value:.2f}")
                        else:
                            row.append(f"{value:.1f}")
                    else:
                        row.append(str(value))
                table_data['rows'].append(row)
            
            return jsonify({
                'comparison': table_data,
                'symbols': symbols,
                'total_compared': len(comparison_data)
            })
        else:
            # Return standard JSON format
            return jsonify({
                'comparison': comparison_data,
                'symbols': symbols,
                'total_compared': len(comparison_data)
            })
    
    except Exception as e:
        logger.error(f"Error in stock comparison: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# Advanced User Alerts System API Endpoints

@api_v2.route('/alerts', methods=['GET'])
@login_required
def api_get_user_alerts():
    """Get all alerts for the current user"""
    try:
        from alerts_service import AlertsService
        alerts_service = AlertsService()
        
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        alerts = alerts_service.get_user_alerts(session['user_id'], active_only=active_only)
        
        return jsonify({
            'success': True,
            'data': alerts,
            'total': len(alerts)
        })
        
    except Exception as e:
        logger.error(f"Error in api_get_user_alerts: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_v2.route('/alerts', methods=['POST'])
@login_required
def api_create_alert():
    """Create a new alert for the current user"""
    try:
        from alerts_service import AlertsService
        alerts_service = AlertsService()
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['symbol', 'alert_type', 'condition_type']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Validate alert_type
        valid_alert_types = ['price', 'volume', 'score', 'event']
        if data['alert_type'] not in valid_alert_types:
            return jsonify({'success': False, 'error': f'Invalid alert_type. Must be one of: {valid_alert_types}'}), 400
        
        # Validate condition_type
        valid_condition_types = ['above', 'below', 'range', 'change_percent']
        if data['condition_type'] not in valid_condition_types:
            return jsonify({'success': False, 'error': f'Invalid condition_type. Must be one of: {valid_condition_types}'}), 400
        
        # Create alert
        alert_id = alerts_service.create_alert(
            user_id=session['user_id'],
            symbol=data['symbol'],
            alert_type=data['alert_type'],
            condition_type=data['condition_type'],
            target_value=data.get('target_value'),
            upper_threshold=data.get('upper_threshold'),
            lower_threshold=data.get('lower_threshold')
        )
        
        if alert_id:
            return jsonify({
                'success': True,
                'alert_id': alert_id,
                'message': 'Alert created successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to create alert'}), 500
        
    except Exception as e:
        logger.error(f"Error in api_create_alert: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_v2.route('/alerts/<int:alert_id>', methods=['DELETE'])
@login_required
def api_delete_alert(alert_id):
    """Delete an alert"""
    try:
        from alerts_service import AlertsService
        alerts_service = AlertsService()
        
        success = alerts_service.delete_alert(alert_id, session['user_id'])
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Alert deleted successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Alert not found or access denied'}), 404
        
    except Exception as e:
        logger.error(f"Error in api_delete_alert: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_v2.route('/alerts/<int:alert_id>/toggle', methods=['POST'])
@login_required
def api_toggle_alert(alert_id):
    """Toggle alert active status"""
    try:
        from alerts_service import AlertsService
        alerts_service = AlertsService()
        
        success = alerts_service.toggle_alert(alert_id, session['user_id'])
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Alert status toggled successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Alert not found or access denied'}), 404
        
    except Exception as e:
        logger.error(f"Error in api_toggle_alert: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_v2.route('/notifications', methods=['GET'])
@login_required
def api_get_notifications():
    """Get notifications for the current user"""
    try:
        from alerts_service import AlertsService
        alerts_service = AlertsService()
        
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        limit = request.args.get('limit', 50, type=int)
        
        notifications = alerts_service.get_user_notifications(
            session['user_id'], 
            unread_only=unread_only, 
            limit=limit
        )
        
        return jsonify({
            'success': True,
            'data': notifications,
            'total': len(notifications)
        })
        
    except Exception as e:
        logger.error(f"Error in api_get_notifications: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_v2.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def api_mark_notification_read(notification_id):
    """Mark a notification as read"""
    try:
        from alerts_service import AlertsService
        alerts_service = AlertsService()
        
        success = alerts_service.mark_notification_read(notification_id, session['user_id'])
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Notification marked as read'
            })
        else:
            return jsonify({'success': False, 'error': 'Notification not found or access denied'}), 404
        
    except Exception as e:
        logger.error(f"Error in api_mark_notification_read: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_v2.route('/notifications/read-all', methods=['POST'])
@login_required
def api_mark_all_notifications_read():
    """Mark all notifications as read for the current user"""
    try:
        from alerts_service import AlertsService
        alerts_service = AlertsService()
        
        success = alerts_service.mark_all_notifications_read(session['user_id'])
        
        if success:
            return jsonify({
                'success': True,
                'message': 'All notifications marked as read'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to mark notifications as read'}), 500
        
    except Exception as e:
        logger.error(f"Error in api_mark_all_notifications_read: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_v2.route('/notifications/unread-count', methods=['GET'])
@login_required
def api_get_unread_count():
    """Get unread notification count for the current user"""
    try:
        from alerts_service import AlertsService
        alerts_service = AlertsService()
        
        count = alerts_service.get_unread_count(session['user_id'])
        
        return jsonify({
            'success': True,
            'unread_count': count
        })
        
    except Exception as e:
        logger.error(f"Error in api_get_unread_count: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Short Squeeze Analysis Endpoints

@api_v2.route('/squeeze/rankings', methods=['GET'])
def api_get_squeeze_rankings():
    """Get ranked list of short squeeze candidates"""
    try:
        service = get_stock_service()
        
        # Get query parameters with validation
        try:
            limit = request.args.get('limit', 50, type=int)
            order_by = request.args.get('order_by', 'squeeze_score')
            min_score = request.args.get('min_score', type=float)
            min_data_quality = request.args.get('min_data_quality')
            
            # Validate parameters
            if limit < 1 or limit > 500:
                limit = 50
            
            valid_order_fields = ['squeeze_score', 'si_score', 'dtc_score', 'float_score', 'momentum_score']
            if order_by not in valid_order_fields:
                order_by = 'squeeze_score'
            
            valid_quality_levels = ['high', 'medium', 'low']
            if min_data_quality and min_data_quality not in valid_quality_levels:
                min_data_quality = None
                
        except ValueError as e:
            logger.warning(f"Invalid query parameters in api_get_squeeze_rankings: {e}")
            return jsonify({'success': False, 'error': 'Invalid query parameters'}), 400
        
        # Get rankings from service
        rankings = service.get_short_squeeze_rankings(
            limit=limit,
            order_by=order_by,
            min_score=min_score,
            min_data_quality=min_data_quality
        )
        
        # Serialize dates
        rankings = serialize_dates_in_dict(rankings)
        
        return jsonify({
            'success': True,
            'data': rankings,
            'count': len(rankings),
            'filters': {
                'limit': limit,
                'order_by': order_by,
                'min_score': min_score,
                'min_data_quality': min_data_quality
            }
        })
        
    except Exception as e:
        logger.error(f"Error in api_get_squeeze_rankings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_v2.route('/squeeze/stats', methods=['GET'])
def api_get_squeeze_stats():
    """Get summary statistics for short squeeze analysis"""
    try:
        service = get_stock_service()
        stats = service.get_short_squeeze_summary_stats()
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        logger.error(f"Error in api_get_squeeze_stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_v2.route('/squeeze/short-interest', methods=['GET'])
def api_get_all_short_interest():
    """Get recent short interest data across all symbols"""
    try:
        service = get_stock_service()
        
        # Get query parameters
        limit = request.args.get('limit', 100, type=int)
        if limit < 1 or limit > 500:
            limit = 100
        
        short_interest_data = service.get_all_short_interest_data(limit=limit)
        
        # Serialize dates
        short_interest_data = serialize_dates_in_dict(short_interest_data)
        
        return jsonify({
            'success': True,
            'data': short_interest_data,
            'count': len(short_interest_data),
            'limit': limit
        })
        
    except Exception as e:
        logger.error(f"Error in api_get_all_short_interest: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_v2.route('/stocks/<string:symbol>/squeeze', methods=['GET'])
def api_get_stock_squeeze_analysis(symbol):
    """Get comprehensive short squeeze analysis for a specific stock"""
    try:
        service = get_stock_service()
        
        # Get comprehensive squeeze data
        squeeze_data = service.get_comprehensive_short_squeeze_data(symbol.upper())
        
        if not squeeze_data or 'error' in squeeze_data:
            return jsonify({'success': False, 'error': 'Stock not found'}), 404
        
        # Serialize dates
        squeeze_data = serialize_dates_in_dict(squeeze_data)
        
        return jsonify({
            'success': True,
            'data': squeeze_data
        })
        
    except Exception as e:
        logger.error(f"Error in api_get_stock_squeeze_analysis for {symbol}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_v2.route('/stocks/<string:symbol>/short-interest', methods=['GET'])
def api_get_stock_short_interest(symbol):
    """Get short interest data for a specific stock"""
    try:
        service = get_stock_service()
        
        short_interest = service.get_short_interest_data(symbol.upper())
        
        if not short_interest:
            return jsonify({'success': False, 'error': 'No short interest data found'}), 404
        
        # Serialize dates
        short_interest = serialize_dates_in_dict(short_interest)
        
        return jsonify({
            'success': True,
            'symbol': symbol.upper(),
            'data': short_interest
        })
        
    except Exception as e:
        logger.error(f"Error in api_get_stock_short_interest for {symbol}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_v2.route('/stocks/<string:symbol>/squeeze-score', methods=['GET'])
def api_get_stock_squeeze_score(symbol):
    """Get short squeeze score for a specific stock"""
    try:
        service = get_stock_service()
        
        squeeze_score = service.get_short_squeeze_score(symbol.upper())
        
        if not squeeze_score:
            return jsonify({'success': False, 'error': 'No squeeze score found'}), 404
        
        # Serialize dates
        squeeze_score = serialize_dates_in_dict(squeeze_score)
        
        return jsonify({
            'success': True,
            'symbol': symbol.upper(),
            'data': squeeze_score
        })
        
    except Exception as e:
        logger.error(f"Error in api_get_stock_squeeze_score for {symbol}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

logger.info("API v2 routes initialized with comprehensive endpoints including alerts system and short squeeze analysis")