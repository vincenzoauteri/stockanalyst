#!/usr/bin/env python3
"""
API Routes for Stock Analyst Application
RESTful API endpoints for programmatic access to stock data and portfolio management
"""

from flask import Blueprint, request, jsonify, session
from data_access_layer import StockDataService
from fmp_client import FMPClient
from undervaluation_analyzer import UndervaluationAnalyzer
from auth import AuthenticationManager, login_required
from portfolio import PortfolioManager
from logging_config import get_logger
import pandas as pd
from datetime import datetime, date

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
def get_stock_service():
    """Get stock data service instance"""
    # This will be injected from the main app
    from app import get_stock_service as get_service
    return get_service()

def get_fmp_client():
    """Get FMP client instance"""
    from app import get_fmp_client as get_client
    return get_client()

def get_undervaluation_analyzer():
    """Get undervaluation analyzer instance"""
    from app import get_undervaluation_analyzer as get_analyzer
    return get_analyzer()

def get_auth_manager():
    """Get authentication manager instance"""
    from app import get_auth_manager as get_manager
    return get_manager()

def get_portfolio_manager():
    """Get portfolio manager instance"""
    from app import get_portfolio_manager as get_manager
    return get_manager()

# Stock Data Endpoints
@api_v2.route('/stocks', methods=['GET'])
def api_get_stocks():
    """Get list of all S&P 500 stocks with filtering and sorting"""
    try:
        service = get_stock_service()
        
        # Get query parameters
        sector = request.args.get('sector')
        min_score = request.args.get('min_score', type=float)
        max_score = request.args.get('max_score', type=float)
        sort_field = request.args.get('sort', 'symbol')
        sort_order = request.args.get('order', 'asc')
        limit = request.args.get('limit', type=int)
        
        # Get all stocks with scores
        stocks_list = service.get_all_stocks_with_scores()
        
        # Apply filters
        if sector:
            stocks_list = [s for s in stocks_list if s.get('sector', '').lower() == sector.lower()]
        
        if min_score is not None:
            stocks_list = [s for s in stocks_list if s.get('undervaluation_score', 0) >= min_score]
        
        if max_score is not None:
            stocks_list = [s for s in stocks_list if s.get('undervaluation_score', 0) <= max_score]
        
        # Apply sorting
        reverse_sort = sort_order.lower() == 'desc'
        if sort_field in ['symbol', 'price', 'market_cap', 'undervaluation_score']:
            stocks_list.sort(key=lambda x: x.get(sort_field, 0), reverse=reverse_sort)
        
        # Apply limit
        if limit:
            stocks_list = stocks_list[:limit]
        
        # Clean up response data
        response_data = []
        for stock in stocks_list:
            response_data.append({
                'symbol': stock.get('symbol'),
                'name': stock.get('name') or stock.get('company_name'),
                'sector': stock.get('sector'),
                'price': stock.get('price'),
                'market_cap': stock.get('mktcap'),
                'undervaluation_score': stock.get('undervaluation_score')
            })
        
        return jsonify({
            'success': True,
            'data': response_data,
            'total': len(response_data),
            'filters': {
                'sector': sector,
                'min_score': min_score,
                'max_score': max_score,
                'sort': sort_field,
                'order': sort_order,
                'limit': limit
            }
        })
        
    except Exception as e:
        logger.error(f"Error in api_get_stocks: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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

logger.info("API v2 routes initialized with comprehensive endpoints")