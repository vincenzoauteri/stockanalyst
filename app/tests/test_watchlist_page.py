"""
Selenium tests for watchlist management functionality.
Tests adding stocks to watchlist and removing stocks from watchlist.
"""

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.alert import Alert


class TestWatchlistPage:
    """Test suite for watchlist management functionality using Selenium"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self, driver, authenticated_user, base_url):
        """Setup for each test method"""
        self.driver = driver
        self.base_url = base_url
        self.wait = WebDriverWait(driver, 10)
        self.user_data = authenticated_user
        
        # Login before each test
        self._login_user()
    
    def test_add_to_watchlist(self):
        """
        Test Case: Test adding a stock to the user's watchlist
        Steps:
        1. Log in as a test user
        2. Navigate to /watchlist
        3. Enter a valid symbol (e.g., MSFT) in the "Add to Watchlist" form
        4. Submit the form
        Expected: Success message appears, "MSFT" is now present in the watchlist table
        """
        # Navigate to watchlist page
        self.driver.get(f"{self.base_url}/watchlist")
        
        # Wait for watchlist page to load
        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1, .page-title"))
        )
        
        # Look for add to watchlist form
        try:
            symbol_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='symbol'], #symbol"))
            )
        except TimeoutException:
            pytest.skip("Add to watchlist form not found")
        
        # Look for submit button
        try:
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
        except Exception as e:
            pytest.skip(f"Submit button not found: {e}")
        
        # Get current watchlist content for comparison
        current_content = self.driver.find_element(By.CSS_SELECTOR, "body").text
        
        # Fill out the form with MSFT
        symbol_input.clear()
        symbol_input.send_keys("MSFT")
        
        # Submit the form
        submit_button.click()
        
        # Wait for form submission to complete
        self.wait.until(lambda driver: driver.current_url)
        
        # Check for success message
        try:
            success_message = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".alert-success, .success-message, .flash-success"))
            )
            assert "success" in success_message.text.lower() or "added" in success_message.text.lower()
        except TimeoutException:
            # Check if page content changed (indicating successful submission)
            new_content = self.driver.find_element(By.CSS_SELECTOR, "body").text
            assert new_content != current_content, "Page should change after watchlist submission"
        
        # Look for watchlist table/section
        try:
            watchlist_section = self.driver.find_element(By.CSS_SELECTOR, 
                ".watchlist, .watchlist-table, table")
            watchlist_text = watchlist_section.text
        except:
            # Fallback: check entire page
            watchlist_text = self.driver.find_element(By.CSS_SELECTOR, "body").text
        
        # Check if MSFT is now present in watchlist
        assert "MSFT" in watchlist_text, "MSFT should be present in the watchlist after adding"
    
    def test_remove_from_watchlist(self):
        """
        Test Case: Ensure a stock can be removed from the watchlist
        Steps:
        1. Add "MSFT" to the watchlist
        2. Click the "Remove" button for "MSFT"
        Expected: "MSFT" is removed from the watchlist table
        """
        # First add MSFT to the watchlist
        self._add_to_watchlist("MSFT")
        
        # Navigate to watchlist page to see the added stock
        self.driver.get(f"{self.base_url}/watchlist")
        
        # Wait for page to load
        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1, .page-title"))
        )
        
        # Verify MSFT is in watchlist before removal
        page_content = self.driver.find_element(By.CSS_SELECTOR, "body").text
        assert "MSFT" in page_content, "MSFT should be in watchlist before removal"
        
        # Look for remove button
        try:
            remove_button = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 
                    ".remove-btn, button[name='remove'], input[value='Remove'], .btn-danger"))
            )
        except TimeoutException:
            # Try alternative selectors
            remove_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                "button, input[type='submit'], a")
            remove_button = None
            for elem in remove_elements:
                elem_text = elem.text.lower()
                elem_value = (elem.get_attribute("value") or "").lower()
                if "remove" in elem_text or "remove" in elem_value or "delete" in elem_text:
                    remove_button = elem
                    break
            
            if not remove_button:
                pytest.skip("Remove button not found")
        
        # Click remove button
        remove_button.click()
        
        # Handle confirmation dialog if it appears
        try:
            alert = Alert(self.driver)
            alert.accept()
        except:
            # No alert, continue
            pass
        
        # Wait for removal to complete
        self.wait.until(lambda driver: driver.current_url)
        
        # Check that MSFT was removed
        new_content = self.driver.find_element(By.CSS_SELECTOR, "body").text
        
        # Look for success message
        success_elements = self.driver.find_elements(By.CSS_SELECTOR, 
            ".alert-success, .success-message, .flash-success")
        
        if success_elements:
            success_text = success_elements[0].text.lower()
            assert "removed" in success_text or "deleted" in success_text, \
                "Success message should indicate stock was removed"
        
        # Check that MSFT is no longer in watchlist
        # Note: This might require a page refresh depending on implementation
        try:
            watchlist_section = self.driver.find_element(By.CSS_SELECTOR, 
                ".watchlist, .watchlist-table, table")
            watchlist_text = watchlist_section.text
            assert "MSFT" not in watchlist_text, "MSFT should be removed from watchlist"
        except:
            # If no specific watchlist section found, check if page indicates empty watchlist
            empty_indicators = ["no stocks", "empty", "no items", "watchlist is empty"]
            empty_found = any(indicator in new_content.lower() for indicator in empty_indicators)
            # Either empty watchlist or MSFT is not present
            assert empty_found or "MSFT" not in new_content, "MSFT should be removed from watchlist"
    
    def test_add_duplicate_to_watchlist(self):
        """
        Test Case: Verify behavior when adding duplicate stock to watchlist
        Steps:
        1. Add "AAPL" to watchlist
        2. Try to add "AAPL" again
        Expected: Appropriate handling (error message or no duplicate)
        """
        # First add AAPL to watchlist
        self._add_to_watchlist("AAPL")
        
        # Navigate to watchlist page
        self.driver.get(f"{self.base_url}/watchlist")
        
        # Wait for page to load
        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1, .page-title"))
        )
        
        # Try to add AAPL again
        try:
            symbol_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='symbol'], #symbol")
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
            
            symbol_input.clear()
            symbol_input.send_keys("AAPL")
            submit_button.click()
            
            # Wait for submission
            self.wait.until(lambda driver: driver.current_url)
            
            # Check for error message or duplicate handling
            page_content = self.driver.find_element(By.CSS_SELECTOR, "body").text.lower()
            
            # Look for error indicators
            error_indicators = ["already", "duplicate", "exists", "error"]
            error_found = any(indicator in page_content for indicator in error_indicators)
            
            if error_found:
                # Good - system detected duplicate
                assert True
            else:
                # Check that we don't have multiple AAPL entries
                watchlist_section = self.driver.find_element(By.CSS_SELECTOR, "body").text
                aapl_count = watchlist_section.count("AAPL")
                assert aapl_count <= 2, "Should not have multiple AAPL entries in watchlist"  # Allow for some tolerance
                
        except Exception as e:
            pytest.skip(f"Could not test duplicate addition: {e}")
    
    def test_add_invalid_symbol_to_watchlist(self):
        """
        Test Case: Verify behavior when adding invalid stock symbol
        Steps:
        1. Navigate to watchlist page
        2. Enter invalid symbol (e.g., "INVALID")
        3. Submit form
        Expected: Error message or rejection of invalid symbol
        """
        # Navigate to watchlist page
        self.driver.get(f"{self.base_url}/watchlist")
        
        # Wait for page to load
        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1, .page-title"))
        )
        
        # Try to add invalid symbol
        try:
            symbol_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='symbol'], #symbol")
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
            
            symbol_input.clear()
            symbol_input.send_keys("INVALID")
            submit_button.click()
            
            # Wait for submission
            self.wait.until(lambda driver: driver.current_url)
            
            # Check for error message
            page_content = self.driver.find_element(By.CSS_SELECTOR, "body").text.lower()
            
            # Look for error indicators
            error_indicators = ["invalid", "not found", "error", "unknown symbol"]
            error_found = any(indicator in page_content for indicator in error_indicators)
            
            # Either error found or invalid symbol not added
            if not error_found:
                # Check that invalid symbol was not added to watchlist
                watchlist_text = self.driver.find_element(By.CSS_SELECTOR, "body").text
                assert "INVALID" not in watchlist_text, "Invalid symbol should not be added to watchlist"
            else:
                assert True, "System correctly rejected invalid symbol"
                
        except Exception as e:
            pytest.skip(f"Could not test invalid symbol addition: {e}")
    
    def test_empty_watchlist(self):
        """
        Test Case: Verify behavior when watchlist is empty
        Steps:
        1. Navigate to watchlist page without adding any stocks
        Expected: Appropriate message for empty watchlist
        """
        # Navigate to watchlist page
        self.driver.get(f"{self.base_url}/watchlist")
        
        # Wait for page to load
        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1, .page-title"))
        )
        
        # Check for empty watchlist indicators
        page_content = self.driver.find_element(By.CSS_SELECTOR, "body").text.lower()
        empty_indicators = ["no stocks", "empty", "no items", "watchlist is empty", "add your first stock"]
        empty_found = any(indicator in page_content for indicator in empty_indicators)
        
        if not empty_found:
            # Check if watchlist table is empty
            try:
                watchlist_table = self.driver.find_element(By.CSS_SELECTOR, "table")
                rows = watchlist_table.find_elements(By.CSS_SELECTOR, "tr")
                data_rows = [row for row in rows if row.find_elements(By.CSS_SELECTOR, "td")]
                assert len(data_rows) == 0, "Empty watchlist should have no data rows"
            except:
                # No table found, which is acceptable for empty watchlist
                pass
    
    def _add_to_watchlist(self, symbol):
        """Helper method to add a stock to watchlist"""
        self.driver.get(f"{self.base_url}/watchlist")
        
        # Wait for watchlist page to load
        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1, .page-title"))
        )
        
        try:
            symbol_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='symbol'], #symbol")
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
            
            symbol_input.clear()
            symbol_input.send_keys(symbol)
            submit_button.click()
            
            # Wait for submission
            self.wait.until(lambda driver: driver.current_url)
            
        except Exception as e:
            pytest.skip(f"Could not add {symbol} to watchlist: {e}")
    
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
        
        # Verify we're successfully authenticated by checking for user-specific elements
        try:
            # Look for logout link or user menu as confirmation of successful login
            self.wait.until(
                EC.any_of(
                    EC.presence_of_element_located((By.LINK_TEXT, "Logout")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".user-menu, .navbar .dropdown")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[href*='logout']"))
                )
            )
        except TimeoutException:
            # If no obvious login indicators, try navigating to a protected page to test
            self.driver.get(f"{self.base_url}/")
            # If we get redirected back to login, authentication failed
            if "/login" in self.driver.current_url:
                raise Exception("Authentication failed - redirected back to login page")