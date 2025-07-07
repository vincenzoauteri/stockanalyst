import pytest
import os
import sqlite3
from datetime import datetime, timedelta
from auth import AuthenticationManager

# Use a temporary database file for testing
@pytest.fixture
def auth_manager():
    import tempfile
    temp_db = tempfile.NamedTemporaryFile(delete=False)
    db_path = temp_db.name
    temp_db.close()
    
    manager = AuthenticationManager(db_path=db_path)
    yield manager
    
    # Clean up temp database
    import os
    try:
        os.unlink(db_path)
    except OSError:
        pass

@pytest.fixture
def setup_user(auth_manager):
    # Register a test user
    username = "testuser"
    email = "test@example.com"
    password = "password123"
    result = auth_manager.register_user(username, email, password)
    assert result["success"]
    return username, password, result["user_id"]

def test_create_auth_tables(auth_manager):
    # Tables should be created during initialization
    conn = sqlite3.connect(auth_manager.db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
    users_table = cursor.fetchone()
    assert users_table is not None
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_sessions';")
    sessions_table = cursor.fetchone()
    assert sessions_table is not None

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_watchlists';")
    watchlists_table = cursor.fetchone()
    assert watchlists_table is not None

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_portfolios';")
    portfolios_table = cursor.fetchone()
    assert portfolios_table is not None

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='portfolio_transactions';")
    transactions_table = cursor.fetchone()
    assert transactions_table is not None
    
    conn.close()

def test_generate_password_hash(auth_manager):
    password = "securepassword"
    password_hash, salt = auth_manager.generate_password_hash(password)
    assert isinstance(password_hash, str)
    assert isinstance(salt, str)
    assert len(password_hash) > 0
    assert len(salt) > 0

def test_verify_password(auth_manager):
    password = "securepassword"
    password_hash, salt = auth_manager.generate_password_hash(password)
    assert auth_manager.verify_password(password, password_hash, salt)
    assert not auth_manager.verify_password("wrongpassword", password_hash, salt)

def test_register_user_success(auth_manager):
    result = auth_manager.register_user("newuser", "new@example.com", "newpassword")
    assert result["success"]
    assert "user_id" in result

def test_register_user_duplicate_username(auth_manager, setup_user):
    username, _, _ = setup_user
    result = auth_manager.register_user(username, "another@example.com", "password123")
    assert not result["success"]
    assert "Username or email already exists" in result["error"]

def test_register_user_duplicate_email(auth_manager, setup_user):
    _, _, user_id = setup_user
    conn = sqlite3.connect(auth_manager.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM users WHERE id = ?", (user_id,))
    email = cursor.fetchone()[0]
    conn.close()

    result = auth_manager.register_user("anotheruser", email, "password123")
    assert not result["success"]
    assert "Username or email already exists" in result["error"]

def test_register_user_invalid_input(auth_manager):
    result = auth_manager.register_user("", "a@b.com", "pass")
    assert not result["success"]
    assert "Username must be at least 3 characters long" in result["error"]

    result = auth_manager.register_user("user", "invalid-email", "password123")
    assert not result["success"]
    assert "Valid email address is required" in result["error"]

    result = auth_manager.register_user("user", "a@b.com", "short")
    assert not result["success"]
    assert "Password must be at least 6 characters long" in result["error"]

def test_authenticate_user_success(auth_manager, setup_user):
    username, password, user_id = setup_user
    result = auth_manager.authenticate_user(username, password, "127.0.0.1", "test-agent")
    assert result["success"]
    assert result["user_id"] == user_id
    assert "session_token" in result

def test_authenticate_user_invalid_password(auth_manager, setup_user):
    username, _, _ = setup_user
    result = auth_manager.authenticate_user(username, "wrongpassword", "127.0.0.1", "test-agent")
    assert not result["success"]
    assert "Invalid username or password" in result["error"]

def test_authenticate_user_not_found(auth_manager):
    result = auth_manager.authenticate_user("nonexistent", "password123", "127.0.0.1", "test-agent")
    assert not result["success"]
    assert "Invalid username or password" in result["error"]

def test_authenticate_user_account_locked(auth_manager, setup_user):
    username, password, user_id = setup_user
    conn = sqlite3.connect(auth_manager.db_path)
    cursor = conn.cursor()
    
    # Simulate 5 failed attempts and lock the account
    cursor.execute("UPDATE users SET failed_login_attempts = 5, locked_until = ? WHERE id = ?", 
                   [(datetime.now() + timedelta(minutes=15)).isoformat(), user_id])
    conn.commit()
    conn.close()

    result = auth_manager.authenticate_user(username, password, "127.0.0.1", "test-agent")
    assert not result["success"]
    assert "Account is temporarily locked" in result["error"]

def test_validate_session_success(auth_manager, setup_user):
    username, password, user_id = setup_user
    auth_result = auth_manager.authenticate_user(username, password, "127.0.0.1", "test-agent")
    session_token = auth_result["session_token"]

    validation_result = auth_manager.validate_session(session_token)
    assert validation_result["success"]
    assert validation_result["user_id"] == user_id
    assert validation_result["username"] == username

def test_validate_session_invalid_token(auth_manager):
    result = auth_manager.validate_session("invalid_token")
    assert not result["success"]
    assert "Invalid session" in result["error"]

def test_validate_session_expired(auth_manager, setup_user):
    username, password, user_id = setup_user
    auth_result = auth_manager.authenticate_user(username, password, "127.0.0.1", "test-agent")
    session_token = auth_result["session_token"]

    conn = sqlite3.connect(auth_manager.db_path)
    cursor = conn.cursor()
    # Set session to expire in the past
    cursor.execute("UPDATE user_sessions SET expires_at = ? WHERE session_token = ?", 
                   [(datetime.now() - timedelta(minutes=1)).isoformat(), session_token])
    conn.commit()
    conn.close()

    result = auth_manager.validate_session(session_token)
    assert not result["success"]
    assert "Session expired" in result["error"]

def test_logout_user(auth_manager, setup_user):
    username, password, user_id = setup_user
    auth_result = auth_manager.authenticate_user(username, password, "127.0.0.1", "test-agent")
    session_token = auth_result["session_token"]

    logout_success = auth_manager.logout_user(session_token)
    assert logout_success

    # Verify session is no longer active
    validation_result = auth_manager.validate_session(session_token)
    assert not validation_result["success"]
    assert "Invalid session" in validation_result["error"]

def test_cleanup_expired_sessions(auth_manager, setup_user):
    username, password, user_id = setup_user
    auth_result = auth_manager.authenticate_user(username, password, "127.0.0.1", "test-agent")
    session_token_active = auth_result["session_token"]

    # Create an expired session
    conn = sqlite3.connect(auth_manager.db_path)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO user_sessions (user_id, session_token, expires_at, is_active) VALUES (?, ?, ?, ?)",
                   (user_id, "expired_token_123", (datetime.now() - timedelta(hours=2)).isoformat(), 1))
    conn.commit()
    conn.close()

    # Before cleanup, both should be present (one active, one expired but still in DB)
    conn = sqlite3.connect(auth_manager.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM user_sessions WHERE is_active = 1")
    active_count_before = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM user_sessions WHERE is_active = 0")
    inactive_count_before = cursor.fetchone()[0]
    conn.close()

    # We expect at least one active session, but there might be others from fixture setup
    assert active_count_before >= 1
    assert inactive_count_before == 0 # Expired session is still active=1 until cleanup

    auth_manager.cleanup_expired_sessions()

    # After cleanup, expired session should be marked inactive
    conn = sqlite3.connect(auth_manager.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM user_sessions WHERE is_active = 1")
    active_count_after = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM user_sessions WHERE is_active = 0")
    inactive_count_after = cursor.fetchone()[0]
    conn.close()

    assert active_count_after == 1
    assert inactive_count_after == 1

    # Validate the active session still works
    validation_result = auth_manager.validate_session(session_token_active)
    assert validation_result["success"]

    # Validate the expired session is now inactive
    validation_result_expired = auth_manager.validate_session("expired_token_123")
    assert not validation_result_expired["success"]
    assert "Invalid session" in validation_result_expired["error"]
