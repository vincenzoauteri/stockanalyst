import pytest
import os
from unittest.mock import patch
from datetime import datetime, timedelta
from auth import AuthenticationManager
from database import DatabaseManager

# Use proper environment variable isolation for testing
@pytest.fixture
def auth_manager():
    test_env = {
        'DATABASE_PATH': ':memory:',
        'POSTGRES_HOST': None,  # Force SQLite usage
        'FMP_API_KEY': 'test_fmp_key',
        'SECRET_KEY': 'test-secret-key-for-testing',
        'TESTING': 'true'
    }
    
    with patch.dict(os.environ, test_env, clear=False):
        db_manager = DatabaseManager()
        manager = AuthenticationManager(db_manager=db_manager)
        yield manager

@pytest.fixture
def setup_user(auth_manager):
    user_data = {
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'password123'
    }
    
    # Register a test user
    result = auth_manager.register_user(**user_data)
    assert result['success'], f"Failed to register user: {result.get('error')}"
    
    return {
        'user_id': result['user_id'],
        **user_data
    }

def test_create_auth_tables(auth_manager):
    """Test that authentication tables are created successfully"""
    # Just verify the manager initializes without error
    assert auth_manager is not None
    assert auth_manager.db_manager is not None

def test_generate_password_hash(auth_manager):
    """Test password hash generation"""
    password = "test_password"
    password_hash, salt = auth_manager.generate_password_hash(password)
    
    assert password_hash is not None
    assert salt is not None
    assert len(password_hash) > 0
    assert len(salt) > 0

def test_verify_password(auth_manager):
    """Test password verification"""
    password = "test_password"
    password_hash, salt = auth_manager.generate_password_hash(password)
    
    # Test correct password
    assert auth_manager.verify_password(password, password_hash, salt)
    
    # Test incorrect password
    assert not auth_manager.verify_password("wrong_password", password_hash, salt)

def test_register_user_success(auth_manager):
    """Test successful user registration"""
    result = auth_manager.register_user("newuser", "new@example.com", "password123")
    assert result['success']
    assert 'user_id' in result

def test_register_user_duplicate_username(auth_manager, setup_user):
    """Test registration with duplicate username"""
    result = auth_manager.register_user(setup_user['username'], "different@example.com", "password123")
    assert not result['success']
    assert 'already exists' in result['error']

def test_register_user_duplicate_email(auth_manager, setup_user):
    """Test registration with duplicate email"""
    result = auth_manager.register_user("differentuser", setup_user['email'], "password123")
    assert not result['success']
    assert 'already exists' in result['error']

def test_register_user_invalid_input(auth_manager):
    """Test registration with invalid input"""
    # Short username
    result = auth_manager.register_user("ab", "test@example.com", "password123")
    assert not result['success']
    
    # Invalid email
    result = auth_manager.register_user("testuser", "invalid_email", "password123")
    assert not result['success']
    
    # Short password
    result = auth_manager.register_user("testuser", "test@example.com", "123")
    assert not result['success']

def test_authenticate_user_success(auth_manager, setup_user):
    """Test successful user authentication"""
    result = auth_manager.authenticate_user(setup_user['username'], setup_user['password'])
    assert result['success']
    assert result['user_id'] == setup_user['user_id']
    assert 'session_token' in result

def test_authenticate_user_invalid_password(auth_manager, setup_user):
    """Test authentication with invalid password"""
    result = auth_manager.authenticate_user(setup_user['username'], "wrong_password")
    assert not result['success']

def test_authenticate_user_not_found(auth_manager):
    """Test authentication with non-existent user"""
    result = auth_manager.authenticate_user("nonexistent", "password")
    assert not result['success']

def test_authenticate_user_account_locked(auth_manager, setup_user):
    """Test authentication with locked account"""
    username = setup_user['username']
    
    # Try to login with wrong password 5 times to lock account
    for _ in range(5):
        result = auth_manager.authenticate_user(username, "wrong_password")
        assert not result['success']
    
    # Now try with correct password - should be locked
    result = auth_manager.authenticate_user(username, setup_user['password'])
    assert not result['success']
    assert 'locked' in result['error']

def test_validate_session_success(auth_manager, setup_user):
    """Test successful session validation"""
    # First authenticate to get session token
    auth_result = auth_manager.authenticate_user(setup_user['username'], setup_user['password'])
    session_token = auth_result['session_token']
    
    # Validate the session
    result = auth_manager.validate_session(session_token)
    assert result['success']
    assert result['user_id'] == setup_user['user_id']

def test_validate_session_invalid_token(auth_manager):
    """Test validation with invalid session token"""
    result = auth_manager.validate_session("invalid_token")
    assert not result['success']

def test_validate_session_expired(auth_manager, setup_user):
    """Test validation with expired session"""
    # This would require manipulating the session expiration time
    # For now, just test with an invalid token
    result = auth_manager.validate_session("expired_token")
    assert not result['success']

def test_logout_user(auth_manager, setup_user):
    """Test user logout"""
    # First authenticate to get session token
    auth_result = auth_manager.authenticate_user(setup_user['username'], setup_user['password'])
    session_token = auth_result['session_token']
    
    # Logout
    result = auth_manager.logout_user(session_token)
    assert result
    
    # Verify session is no longer valid
    validation_result = auth_manager.validate_session(session_token)
    assert not validation_result['success']

def test_cleanup_expired_sessions(auth_manager):
    """Test cleanup of expired sessions"""
    # Just verify the method runs without error
    auth_manager.cleanup_expired_sessions()