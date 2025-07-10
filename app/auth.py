#!/usr/bin/env python3
"""
User Authentication System for Stock Analyst Application
Provides registration, login, logout, and session management functionality
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import session, redirect, url_for, flash, request
from sqlalchemy import text
from database import DatabaseManager
from logging_config import get_logger, log_function_call

logger = get_logger(__name__)

class AuthenticationManager:
    """Handles user authentication and session management"""
    
    def __init__(self):
        """Initialize authentication manager"""
        self.db_manager = DatabaseManager()
        logger.info("Initializing AuthenticationManager with centralized DatabaseManager")
        self.create_auth_tables()
        
    @log_function_call
    def create_auth_tables(self):
        """Create authentication-related database tables"""
        logger.debug("Creating authentication tables...")
        try:
            with self.db_manager.engine.connect() as conn:
                # Users table - PostgreSQL only (containerized environment)
                conn.execute(text('''
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        salt TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT true,
                        last_login TIMESTAMP,
                        failed_login_attempts INTEGER DEFAULT 0,
                        locked_until TIMESTAMP
                    )
                '''))
            
                # User sessions table
                conn.execute(text('''
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        session_token TEXT UNIQUE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP NOT NULL,
                        ip_address TEXT,
                        user_agent TEXT,
                        is_active BOOLEAN DEFAULT true,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                '''))
            
                # User watchlists table
                conn.execute(text('''
                    CREATE TABLE IF NOT EXISTS user_watchlists (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        symbol TEXT NOT NULL,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        notes TEXT,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                        UNIQUE(user_id, symbol)
                    )
                '''))
            
                # User portfolios table
                conn.execute(text('''
                    CREATE TABLE IF NOT EXISTS user_portfolios (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        symbol TEXT NOT NULL,
                        shares REAL NOT NULL,
                        purchase_price REAL NOT NULL,
                        purchase_date DATE NOT NULL,
                        purchase_notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                        UNIQUE(user_id, symbol)
                    )
                '''))
            
                # Portfolio transactions table (for detailed tracking)
                conn.execute(text('''
                    CREATE TABLE IF NOT EXISTS portfolio_transactions (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        symbol TEXT NOT NULL,
                        transaction_type TEXT NOT NULL CHECK (transaction_type IN ('BUY', 'SELL')),
                        shares REAL NOT NULL,
                        price_per_share REAL NOT NULL,
                        transaction_date DATE NOT NULL,
                        fees REAL DEFAULT 0,
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                '''))
            
                conn.commit()
                logger.debug("Authentication tables created successfully")
                
        except Exception as e:
            logger.error(f"Error creating authentication tables: {e}")
            raise
    
    @log_function_call
    def generate_password_hash(self, password: str) -> tuple:
        """Generate password hash with salt"""
        logger.debug("Generating password hash")
        try:
            salt = secrets.token_hex(16)
            password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return password_hash.hex(), salt
        except Exception as e:
            logger.error(f"Error generating password hash: {e}")
            raise
    
    @log_function_call
    def verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """Verify password against hash"""
        logger.debug("Verifying password")
        try:
            expected_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return expected_hash.hex() == password_hash
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False
    
    @log_function_call
    def register_user(self, username: str, email: str, password: str) -> dict:
        """Register a new user"""
        logger.info(f"Registering new user: {username} ({email})")
        
        # Validate inputs
        if not username or len(username) < 3:
            return {'success': False, 'error': 'Username must be at least 3 characters long'}
        
        if not email or '@' not in email:
            return {'success': False, 'error': 'Valid email address is required'}
        
        if not password or len(password) < 6:
            return {'success': False, 'error': 'Password must be at least 6 characters long'}
        
        try:
            with self.db_manager.engine.connect() as conn:
                # Check if user already exists
                result = conn.execute(text('SELECT id FROM users WHERE username = :username OR email = :email'), 
                                    {'username': username, 'email': email})
                if result.fetchone():
                    return {'success': False, 'error': 'Username or email already exists'}
                
                # Generate password hash
                password_hash, salt = self.generate_password_hash(password)
                
                # Insert new user - PostgreSQL only (containerized environment)
                result = conn.execute(text('''
                    INSERT INTO users (username, email, password_hash, salt)
                    VALUES (:username, :email, :password_hash, :salt)
                    RETURNING id
                '''), {'username': username, 'email': email, 'password_hash': password_hash, 'salt': salt})
                user_id = result.fetchone()[0]
                conn.commit()
                
                logger.info(f"User {username} registered successfully with ID: {user_id}")
                return {'success': True, 'user_id': user_id}
                
        except Exception as e:
            logger.error(f"Error registering user {username}: {e}")
            return {'success': False, 'error': 'Registration failed. Please try again.'}
    
    @log_function_call
    def authenticate_user(self, username: str, password: str, ip_address: str = None, user_agent: str = None) -> dict:
        """Authenticate user and create session"""
        logger.info(f"Authenticating user: {username}")
        
        try:
            with self.db_manager.engine.connect() as conn:
                # Get user data
                result = conn.execute(text('''
                    SELECT id, username, email, password_hash, salt, is_active, 
                           failed_login_attempts, locked_until
                    FROM users WHERE username = :username
                '''), {'username': username})
                
                user_data = result.fetchone()
                if not user_data:
                    logger.warning(f"Authentication failed for {username}: user not found")
                    return {'success': False, 'error': 'Invalid username or password'}
                
                user_id, username, email, password_hash, salt, is_active, failed_attempts, locked_until = user_data
                
                # Check if account is locked
                if locked_until:
                    locked_until_dt = datetime.fromisoformat(locked_until.replace('Z', '+00:00'))
                    if datetime.now() < locked_until_dt:
                        logger.warning(f"Authentication failed for {username}: account locked until {locked_until}")
                        return {'success': False, 'error': 'Account is temporarily locked due to failed login attempts'}
                
                # Check if account is active
                if not is_active:
                    logger.warning(f"Authentication failed for {username}: account inactive")
                    return {'success': False, 'error': 'Account is inactive'}
                
                # Verify password
                if not self.verify_password(password, password_hash, salt):
                    # Increment failed attempts
                    failed_attempts += 1
                    if failed_attempts >= 5:
                        # Lock account for 15 minutes
                        locked_until = datetime.now() + timedelta(minutes=15)
                        conn.execute(text('''
                            UPDATE users SET failed_login_attempts = :failed_attempts, locked_until = :locked_until
                            WHERE id = :user_id
                        '''), {'failed_attempts': failed_attempts, 'locked_until': locked_until.isoformat(), 'user_id': user_id})
                        logger.warning(f"Account {username} locked after {failed_attempts} failed attempts")
                    else:
                        conn.execute(text('''
                            UPDATE users SET failed_login_attempts = :failed_attempts WHERE id = :user_id
                        '''), {'failed_attempts': failed_attempts, 'user_id': user_id})
                    
                    conn.commit()
                    logger.warning(f"Authentication failed for {username}: invalid password")
                    return {'success': False, 'error': 'Invalid username or password'}
                
                # Reset failed attempts and update last login
                conn.execute(text('''
                    UPDATE users SET failed_login_attempts = 0, locked_until = NULL,
                                    last_login = CURRENT_TIMESTAMP
                    WHERE id = :user_id
                '''), {'user_id': user_id})
                
                # Create session token
                session_token = secrets.token_urlsafe(32)
                expires_at = datetime.now() + timedelta(hours=24)
                
                conn.execute(text('''
                    INSERT INTO user_sessions (user_id, session_token, expires_at, ip_address, user_agent)
                    VALUES (:user_id, :session_token, :expires_at, :ip_address, :user_agent)
                '''), {'user_id': user_id, 'session_token': session_token, 'expires_at': expires_at.isoformat(), 
                      'ip_address': ip_address, 'user_agent': user_agent})
                
                conn.commit()
                
                logger.info(f"User {username} authenticated successfully")
                return {
                    'success': True,
                    'user_id': user_id,
                    'username': username,
                    'email': email,
                    'session_token': session_token
                }
            
        except Exception as e:
            logger.error(f"Error authenticating user {username}: {e}")
            return {'success': False, 'error': 'Authentication failed. Please try again.'}
    
    @log_function_call
    def validate_session(self, session_token: str) -> dict:
        """Validate session token and return user data"""
        logger.debug("Validating session token")
        
        try:
            with self.db_manager.engine.connect() as conn:
                result = conn.execute(text('''
                    SELECT us.user_id, us.expires_at, u.username, u.email, u.is_active
                    FROM user_sessions us
                    JOIN users u ON us.user_id = u.id
                    WHERE us.session_token = :session_token AND us.is_active = true
                '''), {'session_token': session_token})
                
                session_data = result.fetchone()
                if not session_data:
                    logger.debug("Session validation failed: session not found")
                    return {'success': False, 'error': 'Invalid session'}
                
                user_id, expires_at, username, email, is_active = session_data
                
                # Check if session has expired
                expires_at_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                if datetime.now() > expires_at_dt:
                    logger.debug("Session validation failed: session expired")
                    # Deactivate expired session
                    conn.execute(text('UPDATE user_sessions SET is_active = false WHERE session_token = :session_token'), 
                            {'session_token': session_token})
                    conn.commit()
                    return {'success': False, 'error': 'Session expired'}
            
            # Check if user is still active
            if not is_active:
                logger.debug("Session validation failed: user inactive")
                return {'success': False, 'error': 'User account is inactive'}
            
            logger.debug(f"Session validated successfully for user: {username}")
            return {
                'success': True,
                'user_id': user_id,
                'username': username,
                'email': email
            }
            
        except Exception as e:
            logger.error(f"Error validating session: {e}")
            return {'success': False, 'error': 'Session validation failed'}
    
    @log_function_call
    def logout_user(self, session_token: str) -> bool:
        """Logout user by deactivating session"""
        logger.info("Logging out user")
        
        try:
            with self.db_manager.engine.connect() as conn:
                conn.execute(text('UPDATE user_sessions SET is_active = false WHERE session_token = :session_token'), 
                           {'session_token': session_token})
                conn.commit()
                
                logger.info("User logged out successfully")
                return True
                
        except Exception as e:
            logger.error(f"Error logging out user: {e}")
            return False
    
    @log_function_call
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        logger.debug("Cleaning up expired sessions")
        
        try:
            with self.db_manager.engine.connect() as conn:
                result = conn.execute(text('''
                    UPDATE user_sessions SET is_active = false 
                    WHERE expires_at < :now AND is_active = true
                '''), {'now': datetime.now().isoformat()})
                
                deleted_count = result.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} expired sessions")
                
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")

# Flask decorators for authentication
def login_required(f):
    """Decorator to require authentication for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin privileges for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        
        # Add admin check logic here if needed
        # For now, all logged-in users have access
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Get current user data from session"""
    if 'user_id' in session:
        return {
            'user_id': session['user_id'],
            'username': session.get('username'),
            'email': session.get('email')
        }
    return None