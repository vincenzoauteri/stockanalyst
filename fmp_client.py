import requests
import pandas as pd
from typing import Dict, List, Optional, Union
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from datetime import datetime, date, timedelta
from collections import deque
import json
import time
from pathlib import Path
from logging_config import get_logger, log_function_call, log_api_request

load_dotenv()
logger = get_logger(__name__)


class APIUsageTracker:
    """
    Track API usage to ensure we stay within FMP free tier limits
    """
    
    def __init__(self, usage_file: str = 'api_usage.json', daily_limit: int = 250):
        self.usage_file = Path(usage_file)
        self.daily_limit = daily_limit
        self.usage_data = self._load_usage_data()
    
    def _load_usage_data(self) -> Dict:
        """Load usage data from file"""
        if self.usage_file.exists():
            try:
                with open(self.usage_file, 'r') as f:
                    data = json.load(f)
                return data
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not load usage data: {e}. Starting fresh.")
        
        return {
            'daily_usage': {},
            'total_requests': 0,
            'last_reset': str(date.today())
        }
    
    def _save_usage_data(self):
        """Save usage data to file"""
        try:
            with open(self.usage_file, 'w') as f:
                json.dump(self.usage_data, f, indent=2)
        except IOError as e:
            logger.error(f"Could not save usage data: {e}")
    
    def _get_today_key(self) -> str:
        """Get today's date as string key"""
        return str(date.today())
    
    def _reset_if_new_day(self):
        """Reset daily usage if it's a new day"""
        today = self._get_today_key()
        last_reset = self.usage_data.get('last_reset', today)
        
        if today != last_reset:
            logger.info(f"New day detected. Resetting daily usage counter.")
            self.usage_data['last_reset'] = today
            # Keep historical data but don't let it grow indefinitely
            daily_usage = self.usage_data.get('daily_usage', {})
            
            # Keep only last 30 days of usage data
            cutoff_date = datetime.now().replace(day=1)  # Keep current month
            filtered_usage = {
                date_str: usage for date_str, usage in daily_usage.items()
                if datetime.strptime(date_str, '%Y-%m-%d').date() >= cutoff_date.date()
            }
            
            self.usage_data['daily_usage'] = filtered_usage
            self._save_usage_data()
    
    def get_daily_usage(self, target_date: Optional[date] = None) -> int:
        """Get API usage for a specific date (default: today)"""
        if target_date is None:
            target_date = date.today()
        
        date_key = str(target_date)
        return self.usage_data.get('daily_usage', {}).get(date_key, 0)
    
    def get_remaining_budget(self) -> int:
        """Get remaining API requests for today"""
        self._reset_if_new_day()
        used_today = self.get_daily_usage()
        return max(0, self.daily_limit - used_today)
    
    def can_make_request(self, num_requests: int = 1) -> bool:
        """Check if we can make the requested number of API calls"""
        return self.get_remaining_budget() >= num_requests
    
    def record_request(self, num_requests: int = 1) -> bool:
        """
        Record API request usage
        Returns True if request was within limits, False if over limit
        """
        self._reset_if_new_day()
        
        today = self._get_today_key()
        current_usage = self.usage_data.get('daily_usage', {}).get(today, 0)
        new_usage = current_usage + num_requests
        
        # Update usage
        if 'daily_usage' not in self.usage_data:
            self.usage_data['daily_usage'] = {}
        
        self.usage_data['daily_usage'][today] = new_usage
        self.usage_data['total_requests'] = self.usage_data.get('total_requests', 0) + num_requests
        
        # Save to file
        self._save_usage_data()
        
        # Check if within limits
        within_limits = new_usage <= self.daily_limit
        
        if not within_limits:
            logger.warning(f"API usage exceeded daily limit! Used: {new_usage}/{self.daily_limit}")
        else:
            logger.debug(f"API usage recorded: {new_usage}/{self.daily_limit} requests today")
        
        return within_limits
    
    def get_usage_summary(self) -> Dict:
        """Get comprehensive usage summary"""
        self._reset_if_new_day()
        
        today_usage = self.get_daily_usage()
        remaining = self.get_remaining_budget()
        
        # Calculate weekly average
        weekly_usage = []
        for i in range(7):
            try:
                check_date = date.today().replace(day=date.today().day - i)
                usage = self.get_daily_usage(check_date)
                weekly_usage.append(usage)
            except Exception:
                continue
        
        avg_weekly = sum(weekly_usage) / len(weekly_usage) if weekly_usage else 0
        
        return {
            'date': str(date.today()),
            'daily_limit': self.daily_limit,
            'used_today': today_usage,
            'remaining_today': remaining,
            'percentage_used': (today_usage / self.daily_limit) * 100,
            'weekly_average': round(avg_weekly, 1),
            'total_requests': self.usage_data.get('total_requests', 0),
            'within_limits': today_usage <= self.daily_limit
        }
    
    def get_usage_recommendation(self) -> str:
        """Get recommendation based on current usage"""
        summary = self.get_usage_summary()
        used_pct = summary['percentage_used']
        
        if used_pct >= 90:
            return "CRITICAL: API budget nearly exhausted. Pause non-essential requests."
        elif used_pct >= 75:
            return "WARNING: High API usage. Prioritize only critical updates."
        elif used_pct >= 50:
            return "CAUTION: Moderate API usage. Monitor remaining budget carefully."
        else:
            return "OK: API usage within normal limits."

class FMPClient:
    def __init__(self):
        self.api_key = os.getenv('FMP_API_KEY')
        self.base_url = 'https://financialmodelingprep.com/api/v3'
        self.log_file = 'fmp_api_requests.log'
        self.max_log_entries = 1000
        self.usage_tracker = APIUsageTracker()
        
        # Rate limiting cache for 429 errors
        self.rate_limit_cache = {}
        self.rate_limit_cooldown = timedelta(hours=1)  # 1 hour cooldown
        
        # Initialize Yahoo Finance fallback client
        try:
            from yahoo_finance_client import YahooFinanceClient
            self.yahoo_client = YahooFinanceClient()
            self.fallback_available = True
            logger.info("Yahoo Finance fallback client initialized")
        except ImportError as e:
            logger.warning(f"Yahoo Finance fallback not available: {e}")
            self.yahoo_client = None
            self.fallback_available = False
        
        # API key is only required for profile and historical data, not for S&P 500 list
        if not self.api_key:
            logger.warning("FMP_API_KEY not found. Company profiles and historical data will not be available.")
            if self.fallback_available:
                logger.info("Yahoo Finance fallback will be used when needed.")
    
    def _log_api_request(self, endpoint: str, symbol: str = None, status: str = "SUCCESS", response_size: int = 0, error: str = None):
        """Log API request details to rolling log file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_entry = {
            'timestamp': timestamp,
            'endpoint': endpoint,
            'symbol': symbol,
            'status': status,
            'response_size': response_size,
            'error': error
        }
        
        # Read existing log entries
        log_entries = []
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            log_entries.append(json.loads(line.strip()))
            except (json.JSONDecodeError, IOError):
                log_entries = []
        
        # Add new entry
        log_entries.append(log_entry)
        
        # Keep only last 1000 entries
        if len(log_entries) > self.max_log_entries:
            log_entries = log_entries[-self.max_log_entries:]
        
        # Write back to file
        try:
            with open(self.log_file, 'w') as f:
                for entry in log_entries:
                    f.write(json.dumps(entry) + '\n')
        except IOError as e:
            logger.warning(f"Could not write to log file: {e}")
    
    def get_api_request_log(self) -> List[str]:
        """Get formatted API request log entries"""
        if not os.path.exists(self.log_file):
            return ["No API requests logged yet."]
        
        formatted_entries = []
        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    if line.strip():
                        entry = json.loads(line.strip())
                        symbol_part = f" [{entry['symbol']}]" if entry['symbol'] else ""
                        error_part = f" ERROR: {entry['error']}" if entry['error'] else ""
                        size_part = f" ({entry['response_size']} bytes)" if entry['response_size'] > 0 else ""
                        
                        formatted_line = f"{entry['timestamp']} - {entry['endpoint']}{symbol_part} - {entry['status']}{size_part}{error_part}"
                        formatted_entries.append(formatted_line)
        except (json.JSONDecodeError, IOError):
            return ["Error reading log file."]
        
        return formatted_entries
    
    def _is_rate_limited(self) -> bool:
        """
        Check if API is currently rate limited based on recent 429 errors
        """
        if not self.rate_limit_cache:
            return False
        
        current_time = datetime.now()
        
        # Clean up expired entries
        expired_keys = [
            key for key, timestamp in self.rate_limit_cache.items()
            if current_time - timestamp > self.rate_limit_cooldown
        ]
        
        for key in expired_keys:
            del self.rate_limit_cache[key]
        
        # Check if we have any active rate limits
        return len(self.rate_limit_cache) > 0
    
    def _record_rate_limit(self, endpoint: str, symbol: str = None):
        """
        Record a rate limit (429 error) for the cooldown period
        """
        current_time = datetime.now()
        cache_key = f"{endpoint}:{symbol}" if symbol else endpoint
        
        self.rate_limit_cache[cache_key] = current_time
        
        # Clean up old entries to prevent memory buildup
        if len(self.rate_limit_cache) > 100:
            # Keep only the most recent 50 entries
            sorted_items = sorted(self.rate_limit_cache.items(), key=lambda x: x[1], reverse=True)
            self.rate_limit_cache = dict(sorted_items[:50])
        
        cooldown_end = current_time + self.rate_limit_cooldown
        logger.warning(f"Rate limit recorded for {cache_key}. FMP API calls paused until {cooldown_end.strftime('%Y-%m-%d %H:%M:%S')}")
    
    def _get_rate_limit_status(self) -> Dict:
        """
        Get current rate limit status information
        """
        if not self.rate_limit_cache:
            return {
                "is_rate_limited": False,
                "active_limits": 0,
                "next_available": None
            }
        
        current_time = datetime.now()
        active_limits = []
        
        for key, timestamp in self.rate_limit_cache.items():
            expires_at = timestamp + self.rate_limit_cooldown
            if expires_at > current_time:
                active_limits.append({
                    "endpoint": key,
                    "expires_at": expires_at,
                    "remaining_seconds": (expires_at - current_time).total_seconds()
                })
        
        next_available = min([limit["expires_at"] for limit in active_limits]) if active_limits else None
        
        return {
            "is_rate_limited": len(active_limits) > 0,
            "active_limits": len(active_limits),
            "next_available": next_available,
            "details": active_limits
        }
    
    def _make_api_request(self, endpoint: str, symbol: str = None, params: Dict = None, require_api_key: bool = True) -> Union[Dict, List, None]:
        """
        Centralized method for making API requests with error handling and logging
        
        Args:
            endpoint: API endpoint path (e.g., 'profile', 'historical-price-full')
            symbol: Stock symbol (optional)
            params: Additional query parameters (optional)
            require_api_key: Whether this endpoint requires an API key
        
        Returns:
            JSON response data or None if request failed
        """
        start_time = time.time()
        
        if require_api_key and not self.api_key:
            logger.error(f"Cannot access {endpoint} for {symbol or 'endpoint'}: FMP_API_KEY not found")
            self._log_api_request(endpoint, symbol, "FAILED", 0, "FMP_API_KEY not found")
            log_api_request(endpoint, symbol, "FAILED", 0, "FMP_API_KEY not found")
            return None
        
        # Check rate limiting before making request
        if require_api_key and self._is_rate_limited():
            rate_limit_status = self._get_rate_limit_status()
            next_available = rate_limit_status.get("next_available")
            if next_available:
                remaining_time = (next_available - datetime.now()).total_seconds()
                logger.info(f"API request skipped due to rate limiting: {endpoint} for {symbol or 'endpoint'}. "
                           f"Rate limit expires in {remaining_time:.0f} seconds")
            else:
                logger.info(f"API request skipped due to rate limiting: {endpoint} for {symbol or 'endpoint'}")
            
            self._log_api_request(endpoint, symbol, "RATE_LIMITED", 0, "Skipped due to recent 429 errors")
            log_api_request(endpoint, symbol, "RATE_LIMITED", 0, "Skipped due to recent 429 errors")
            return None
        
        # Check usage limits before making request (only for API key endpoints)
        if require_api_key and not self.usage_tracker.can_make_request():
            logger.error(f"API request blocked: Daily limit reached. {self.usage_tracker.get_usage_recommendation()}")
            self._log_api_request(endpoint, symbol, "BLOCKED", 0, "Daily API limit reached")
            log_api_request(endpoint, symbol, "BLOCKED", 0, "Daily API limit reached")
            return None
        
        # Construct URL
        if symbol:
            url = f"{self.base_url}/{endpoint}/{symbol}"
        else:
            url = f"{self.base_url}/{endpoint}"
        
        # Add API key to params if required
        if require_api_key:
            if params is None:
                params = {}
            params['apikey'] = self.api_key
        
        logger.debug(f"Making API request to {endpoint} for {symbol or 'general'}")
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            response_size = len(response.content)
            response_time = time.time() - start_time
            
            self._log_api_request(endpoint, symbol, "SUCCESS", response_size)
            log_api_request(endpoint, symbol, "SUCCESS", response_time)
            
            logger.debug(f"API request successful: {endpoint} {symbol or ''} ({response_time:.3f}s, {response_size} bytes)")
            
            # Record usage for API key endpoints
            if require_api_key:
                self.usage_tracker.record_request()
            
            return data
            
        except requests.exceptions.RequestException as e:
            response_time = time.time() - start_time
            logger.error(f"Error fetching {endpoint} for {symbol or 'endpoint'}: {e}")
            
            # Check if this is a 429 error and record it for rate limiting
            if "429" in str(e) or "Too Many Requests" in str(e):
                self._record_rate_limit(endpoint, symbol)
                self._log_api_request(endpoint, symbol, "RATE_LIMITED", 0, str(e))
                log_api_request(endpoint, symbol, "RATE_LIMITED", response_time, str(e))
            else:
                self._log_api_request(endpoint, symbol, "FAILED", 0, str(e))
                log_api_request(endpoint, symbol, "FAILED", response_time, str(e))
            
            return None
        except json.JSONDecodeError as e:
            response_time = time.time() - start_time
            logger.error(f"Error parsing JSON response from {endpoint} for {symbol or 'endpoint'}: {e}")
            self._log_api_request(endpoint, symbol, "FAILED", 0, f"JSON decode error: {str(e)}")
            log_api_request(endpoint, symbol, "FAILED", response_time, f"JSON decode error: {str(e)}")
            return None
    
    def get_usage_summary(self) -> Dict:
        """Get comprehensive API usage summary"""
        return self.usage_tracker.get_usage_summary()
    
    def get_usage_recommendation(self) -> str:
        """Get recommendation based on current API usage"""
        return self.usage_tracker.get_usage_recommendation()
    
    def get_remaining_requests(self) -> int:
        """Get remaining API requests for today"""
        return self.usage_tracker.get_remaining_budget()
    
    def get_rate_limit_status(self) -> Dict:
        """Get current rate limit status"""
        return self._get_rate_limit_status()
    
    def is_available(self) -> bool:
        """
        Check if the FMP client is available for making requests
        Returns True if we have an API key and haven't exceeded usage limits
        """
        return self.api_key is not None and self.usage_tracker.can_make_request() and not self._is_rate_limited()
    
    def _should_use_fallback(self) -> bool:
        """
        Determine if we should use Yahoo Finance fallback
        """
        # Use fallback if no API key
        if not self.api_key:
            return True
        
        # Use fallback if we're currently rate limited
        if self._is_rate_limited():
            return True
        
        # Use fallback if we've exceeded usage limits
        if not self.usage_tracker.can_make_request():
            return True
        
        # Use fallback if usage is critically high (>90%)
        usage_summary = self.usage_tracker.get_usage_summary()
        if usage_summary.get('percentage_used', 0) > 90:
            return True
        
        return False
    
    def get_usage_info(self) -> Dict:
        """
        Get current API usage information including fallback status
        """
        usage_summary = self.usage_tracker.get_usage_summary()
        rate_limit_status = self._get_rate_limit_status()
        
        return {
            'fmp_requests_used': usage_summary.get('requests_today', 0),
            'fmp_daily_limit': self.usage_tracker.daily_limit,
            'remaining_requests': usage_summary.get('remaining_budget', 0),
            'percentage_used': usage_summary.get('percentage_used', 0),
            'fallback_available': self.fallback_available,
            'using_fallback': self._should_use_fallback(),
            'recommendation': self.usage_tracker.get_usage_recommendation(),
            'rate_limited': rate_limit_status.get('is_rate_limited', False),
            'active_rate_limits': rate_limit_status.get('active_limits', 0),
            'next_available': rate_limit_status.get('next_available')
        }
    
    def _fetch_external_url(self, url: str, description: str = "") -> str:
        """
        Centralized method for fetching external URLs (non-FMP API)
        """
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            response_size = len(response.content)
            self._log_api_request(f"external-{description}", None, "SUCCESS", response_size)
            
            return response.text
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {description} from {url}: {e}")
            self._log_api_request(f"external-{description}", None, "FAILED", 0, str(e))
            return None

    def get_sp500_constituents(self) -> pd.DataFrame:
        """
        Fetch S&P 500 constituents from Wikipedia
        """
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        
        try:
            content = self._fetch_external_url(url, "sp500-constituents")
            if content is None:
                return pd.DataFrame()
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find the main S&P 500 table (first table with id 'constituents')
            table = soup.find('table', {'id': 'constituents'})
            if not table:
                # Fallback: find the first table with class 'wikitable sortable'
                table = soup.find('table', {'class': 'wikitable sortable'})
            
            if not table:
                logger.error("Could not find S&P 500 constituents table")
                return pd.DataFrame()
            
            # Extract table data
            rows = table.find_all('tr')[1:]  # Skip header row
            data = []
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 4:  # Ensure we have enough columns
                    symbol = cells[0].get_text(strip=True)
                    name = cells[1].get_text(strip=True)
                    sector = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                    sub_sector = cells[3].get_text(strip=True) if len(cells) > 3 else ""
                    headquarters = cells[4].get_text(strip=True) if len(cells) > 4 else ""
                    
                    data.append({
                        'symbol': symbol,
                        'name': name,
                        'sector': sector,
                        'sub_sector': sub_sector,
                        'headquarters_location': headquarters
                    })
            
            df = pd.DataFrame(data)
            return df
            
        except Exception as e:
            logger.error(f"Error parsing S&P 500 data: {e}")
            return pd.DataFrame()
    
    def get_company_profile(self, symbol: str) -> Dict:
        """
        Get company profile for a given symbol with Yahoo Finance fallback
        """
        # Try FMP first if available and within limits
        if not self._should_use_fallback():
            data = self._make_api_request("profile", symbol)
            if data and len(data) > 0:
                return data[0]
        
        # Use Yahoo Finance fallback
        if self.fallback_available:
            logger.info(f"Using Yahoo Finance fallback for company profile: {symbol}")
            yahoo_profile = self.yahoo_client.get_company_profile(symbol)
            if yahoo_profile:
                return yahoo_profile
        
        logger.warning(f"No company profile data available for {symbol}")
        return {}
    
    def get_historical_prices(self, symbol: str, period: str = '1year') -> pd.DataFrame:
        """
        Get historical prices for a symbol
        """
        params = {
            'timeseries': 252 if period == '1year' else 50
        }
        
        data = self._make_api_request("historical-price-full", symbol, params)
        if data is None:
            return pd.DataFrame()
        
        if 'historical' in data:
            df = pd.DataFrame(data['historical'])
            df['date'] = pd.to_datetime(df['date'])
            return df.sort_values('date')
        
        return pd.DataFrame()
    
    def get_key_metrics(self, symbol: str, period: str = 'annual', limit: int = 5) -> pd.DataFrame:
        """
        Get key financial metrics for a symbol
        
        Args:
            symbol: Stock symbol
            period: 'annual' or 'quarter'
            limit: Number of periods to retrieve
        """
        params = {
            'period': period,
            'limit': limit
        }
        
        data = self._make_api_request("key-metrics", symbol, params)
        if data is None:
            return pd.DataFrame()
        
        if data:
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            return df.sort_values('date')
        
        return pd.DataFrame()
    
    def get_financial_ratios(self, symbol: str, period: str = 'annual', limit: int = 5) -> pd.DataFrame:
        """
        Get financial ratios for a symbol
        
        Args:
            symbol: Stock symbol
            period: 'annual' or 'quarter'
            limit: Number of periods to retrieve
        """
        params = {
            'period': period,
            'limit': limit
        }
        
        data = self._make_api_request("ratios", symbol, params)
        if data is None:
            return pd.DataFrame()
        
        if data:
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            return df.sort_values('date')
        
        return pd.DataFrame()
    
    def get_income_statement(self, symbol: str, period: str = 'annual', limit: int = 5) -> pd.DataFrame:
        """
        Get income statement for a symbol
        
        Args:
            symbol: Stock symbol
            period: 'annual' or 'quarter'
            limit: Number of periods to retrieve
        """
        params = {
            'period': period,
            'limit': limit
        }
        
        data = self._make_api_request("income-statement", symbol, params)
        if data is None:
            return pd.DataFrame()
        
        if data:
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            return df.sort_values('date')
        
        return pd.DataFrame()
    
    def get_fundamentals_summary(self, symbol: str) -> Dict:
        """
        Get a comprehensive fundamentals summary for a symbol with Yahoo Finance fallback
        Combines key metrics, ratios, and income statement data
        """
        # Try FMP first if available and within limits
        if not self._should_use_fallback():
            try:
                # Get latest data from each endpoint
                key_metrics = self.get_key_metrics(symbol, limit=1)
                ratios = self.get_financial_ratios(symbol, limit=1)
                income_stmt = self.get_income_statement(symbol, limit=1)
                
                summary = {'symbol': symbol}
                
                # Extract key metrics
                if not key_metrics.empty:
                    latest_metrics = key_metrics.iloc[-1]
                    summary.update({
                        'market_cap': latest_metrics.get('marketCap'),
                        'enterprise_value': latest_metrics.get('enterpriseValue'),
                        'pe_ratio': latest_metrics.get('peRatio'),
                        'pb_ratio': latest_metrics.get('pbRatio'),
                        'price_to_sales': latest_metrics.get('priceToSalesRatio'),
                        'dividend_yield': latest_metrics.get('dividendYield'),
                        'roe': latest_metrics.get('roe'),
                        'debt_to_equity': latest_metrics.get('debtToEquity'),
                        'current_ratio': latest_metrics.get('currentRatio'),
                        'free_cash_flow_yield': latest_metrics.get('freeCashFlowYield'),
                        'metrics_date': latest_metrics.get('date')
                    })
                
                # Extract financial ratios
                if not ratios.empty:
                    latest_ratios = ratios.iloc[-1]
                    summary.update({
                        'gross_profit_margin': latest_ratios.get('grossProfitMargin'),
                        'operating_profit_margin': latest_ratios.get('operatingProfitMargin'),
                        'net_profit_margin': latest_ratios.get('netProfitMargin'),
                        'return_on_assets': latest_ratios.get('returnOnAssets'),
                        'return_on_equity': latest_ratios.get('returnOnEquity'),
                        'debt_ratio': latest_ratios.get('debtRatio'),
                        'ratios_date': latest_ratios.get('date')
                    })
                
                # Extract income statement data
                if not income_stmt.empty:
                    latest_income = income_stmt.iloc[-1]
                    summary.update({
                        'revenue': latest_income.get('revenue'),
                        'gross_profit': latest_income.get('grossProfit'),
                        'operating_income': latest_income.get('operatingIncome'),
                        'net_income': latest_income.get('netIncome'),
                        'eps': latest_income.get('eps'),
                        'eps_diluted': latest_income.get('epsdiluted'),
                        'income_date': latest_income.get('date')
                    })
            
                self._log_api_request("fundamentals-summary", symbol, "SUCCESS", 0)
                return summary
                
            except Exception as e:
                logger.warning(f"Error with FMP fundamentals for {symbol}: {e}")
        
        # Use Yahoo Finance fallback
        if self.fallback_available:
            logger.info(f"Using Yahoo Finance fallback for fundamentals: {symbol}")
            yahoo_fundamentals = self.yahoo_client.get_fundamentals_summary(symbol)
            if yahoo_fundamentals:
                return yahoo_fundamentals
        
        logger.warning(f"No fundamentals data available for {symbol}")
        return {'symbol': symbol, 'error': 'No data available from FMP or Yahoo Finance'}
    
    def get_price_targets(self, symbol: str) -> List[Dict]:
        """
        Get analyst price targets for a symbol
        """
        data = self._make_api_request("price-target", symbol)
        if data is None:
            return []
        
        return data if data else []