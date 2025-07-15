import pytest
from auth import AuthenticationManager

def test_create_auth_tables(auth_manager):
    """Test that authentication tables are created successfully"""
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

def test_register_user_duplicate_username(authenticated_user):
    """Test registration with duplicate username"""
    auth_manager = authenticated_user['auth_manager']
    result = auth_manager.register_user(authenticated_user['username'], "different@example.com", "password123")
    assert not result['success']
    assert 'already exists' in result['error']

def test_register_user_duplicate_email(authenticated_user):
    """Test registration with duplicate email"""
    auth_manager = authenticated_user['auth_manager']
    result = auth_manager.register_user("differentuser", authenticated_user['email'], "password123")
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

def test_authenticate_user_success(authenticated_user, test_user_data):
    """Test successful user authentication"""
    auth_manager = authenticated_user['auth_manager']
    result = auth_manager.authenticate_user(test_user_data['username'], test_user_data['password'])
    assert result['success']
    assert result['user_id'] == authenticated_user['user_id']
    assert 'session_token' in result

def test_authenticate_user_invalid_password(authenticated_user, test_user_data):
    """Test authentication with invalid password"""
    auth_manager = authenticated_user['auth_manager']
    result = auth_manager.authenticate_user(test_user_data['username'], "wrong_password")
    assert not result['success']

def test_authenticate_user_not_found(auth_manager):
    """Test authentication with non-existent user"""
    result = auth_manager.authenticate_user("nonexistent", "password")
    assert not result['success']

def test_validate_session_success(authenticated_user):
    """Test successful session validation"""
    auth_manager = authenticated_user['auth_manager']
    session_token = authenticated_user['session_token']
    
    # Validate the session
    result = auth_manager.validate_session(session_token)
    assert result['success']
    assert result['user_id'] == authenticated_user['user_id']

def test_validate_session_invalid_token(auth_manager):
    """Test validation with invalid session token"""
    result = auth_manager.validate_session("invalid_token")
    assert not result['success']

def test_logout_user(authenticated_user):
    """Test user logout"""
    auth_manager = authenticated_user['auth_manager']
    session_token = authenticated_user['session_token']
    
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