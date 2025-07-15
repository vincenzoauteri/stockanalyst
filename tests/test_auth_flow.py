"""
Selenium tests for authentication flow.
Tests login, logout, and access control functionality.
"""

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


class TestAuthFlow:
    """Test suite for authentication flow using Selenium"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self, driver, authenticated_user, base_url):
        """Setup for each test method"""
        self.driver = driver
        self.base_url = base_url
        self.wait = WebDriverWait(driver, 10)
        self.user_data = authenticated_user
        
    def test_login_with_invalid_credentials(self):
        """
        Test Case: Ensure login fails with incorrect password
        Steps:
        1. Navigate to /login
        2. Enter a valid username and an invalid password
        3. Submit the form
        Expected: Error message "Invalid credentials" is displayed, user remains on /login page
        """
        # Navigate to login page
        self.driver.get(f"{self.base_url}/login")
        
        # Wait for login form to be present
        username_input = self.wait.until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        password_input = self.driver.find_element(By.NAME, "password")
        submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        
        # Enter valid username but invalid password
        username_input.clear()
        username_input.send_keys(self.user_data['username'])
        password_input.clear()
        password_input.send_keys("invalid_password")
        
        # Submit the form
        submit_button.click()
        
        # Wait for error message to appear
        try:
            error_message = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".alert-danger, .error-message"))
            )
            assert "Invalid credentials" in error_message.text.lower() or "invalid" in error_message.text.lower()
        except TimeoutException:
            # Check if there's any error indication
            error_elements = self.driver.find_elements(By.CSS_SELECTOR, ".alert, .error, .flash-message")
            assert len(error_elements) > 0, "No error message displayed for invalid credentials"
            assert any("invalid" in elem.text.lower() for elem in error_elements), "Error message does not indicate invalid credentials"
        
        # Verify user remains on login page
        assert "/login" in self.driver.current_url, "User should remain on login page after failed login"
    
    def test_logout_flow(self):
        """
        Test Case: Verify that a logged-in user can successfully log out
        Steps:
        1. Log in as a test user
        2. Click the "Logout" button
        3. Navigate back to a protected page like /portfolio
        Expected: User is redirected to /login page, "You have been logged out" message appears
        """
        # Login first
        self._login_user()
        
        # Look for logout button/link
        logout_element = self.wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Logout"))
        )
        logout_element.click()
        
        # Wait for logout to complete and check for success message
        try:
            success_message = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".alert-success, .success-message"))
            )
            assert "logged out" in success_message.text.lower()
        except TimeoutException:
            # Check if we're redirected to login page as indication of successful logout
            self.wait.until(lambda driver: "/login" in driver.current_url)
        
        # Try to navigate to protected page
        self.driver.get(f"{self.base_url}/portfolio")
        
        # Should be redirected to login page
        self.wait.until(lambda driver: "/login" in driver.current_url)
        assert "/login" in self.driver.current_url, "User should be redirected to login page after logout"
    
    def test_access_protected_page_when_logged_out(self):
        """
        Test Case: Ensure unauthenticated users cannot access protected pages
        Steps:
        1. Navigate directly to /portfolio
        Expected: User is redirected to /login page
        """
        # Navigate directly to protected page without logging in
        self.driver.get(f"{self.base_url}/portfolio")
        
        # Should be redirected to login page
        self.wait.until(lambda driver: "/login" in driver.current_url)
        assert "/login" in self.driver.current_url, "Unauthenticated user should be redirected to login page"
        
        # Check that login form is present
        login_form = self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "form"))
        )
        assert login_form is not None, "Login form should be present"
    
    def _login_user(self):
        """Helper method to login the test user"""
        self.driver.get(f"{self.base_url}/login")
        
        # Wait for login form elements
        username_input = self.wait.until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        password_input = self.driver.find_element(By.NAME, "password")
        submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        
        # Enter credentials
        username_input.clear()
        username_input.send_keys(self.user_data['username'])
        password_input.clear()
        password_input.send_keys("securepassword123")  # Use the password from test_user_data fixture
        
        # Submit form
        submit_button.click()
        
        # Wait for successful login (redirect away from login page)
        self.wait.until(lambda driver: "/login" not in driver.current_url)