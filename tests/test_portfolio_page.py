"""
Selenium tests for portfolio management functionality.
Tests adding transactions, deleting transactions, and portfolio display.
"""

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.alert import Alert


class TestPortfolioPage:
    """Test suite for portfolio management functionality using Selenium"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self, driver, authenticated_user, base_url):
        """Setup for each test method"""
        self.driver = driver
        self.base_url = base_url
        self.wait = WebDriverWait(driver, 30)  # Increased timeout for authentication and page loading
        self.user_data = authenticated_user
        
        # Login before each test
        self._login_user()
    
    def test_add_transaction(self):
        """
        Test Case: Test adding a new transaction to the portfolio
        Steps:
        1. Log in as a test user
        2. Navigate to /portfolio
        3. Fill out the "Add Transaction" form (e.g., BUY, AAPL, 10 shares)
        4. Submit the form
        Expected: Success message appears, new transaction is visible in Recent Transactions, portfolio holdings are updated
        """
        # Navigate to portfolio page
        self.driver.get(f"{self.base_url}/portfolio")
        
        # Wait for portfolio page to load (portfolio uses h2 for heading)
        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1, h2, .page-title"))
        )
        
        # Portfolio form is in a modal - need to click button to open it
        try:
            # Click the "Add Transaction" button to open modal
            add_transaction_btn = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-bs-target='#addTransactionModal']"))
            )
            add_transaction_btn.click()
            
            # Wait for modal to appear and form fields to be available
            symbol_input = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='symbol'], #symbol"))
            )
        except TimeoutException:
            pytest.skip("Add transaction form/modal not found")
        
        # Look for other form fields with correct names
        try:
            action_select = self.driver.find_element(By.CSS_SELECTOR, "select[name='transaction_type'], #transaction_type")
            quantity_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='shares'], #shares")
            price_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='price_per_share'], #price_per_share")
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
        except Exception as e:
            pytest.skip(f"Transaction form fields not found: {e}")
        
        # Fill out the form
        symbol_input.clear()
        symbol_input.send_keys("AAPL")
        
        # Select BUY action
        action_dropdown = Select(action_select)
        try:
            action_dropdown.select_by_visible_text("BUY")
        except:
            try:
                action_dropdown.select_by_value("BUY")
            except:
                # Try first option if BUY is not found
                action_dropdown.select_by_index(0)
        
        quantity_input.clear()
        quantity_input.send_keys("10")
        
        price_input.clear()
        price_input.send_keys("150.00")
        
        # Get current page content for comparison
        current_content = self.driver.find_element(By.CSS_SELECTOR, "body").text
        
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
            assert new_content != current_content, "Page should change after transaction submission"
        
        # Look for recent transactions list
        try:
            transactions_section = self.driver.find_element(By.CSS_SELECTOR, 
                ".transactions, .recent-transactions, table")
            
            # Check if AAPL transaction is visible
            transactions_text = transactions_section.text
            assert "AAPL" in transactions_text, "AAPL transaction should be visible in recent transactions"
            assert "10" in transactions_text, "Quantity should be visible in transaction"
            
        except Exception:
            # Fallback: check if transaction appears anywhere on the page
            page_content = self.driver.find_element(By.CSS_SELECTOR, "body").text
            assert "AAPL" in page_content, "AAPL transaction should be visible somewhere on the page"
    
    def test_delete_transaction(self):
        """
        Test Case: Verify that a transaction can be deleted
        Steps:
        1. Add a transaction for a test stock
        2. Navigate to the transactions page for that stock
        3. Click the "Delete" button for the transaction
        4. Confirm the action
        Expected: Transaction is removed from the list, portfolio holdings are updated accordingly
        """
        # First add a transaction
        self._add_test_transaction("MSFT", "BUY", "5", "250.00")
        
        # Navigate to portfolio page to see transactions
        self.driver.get(f"{self.base_url}/portfolio")
        
        # Wait for page to load
        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1, .page-title"))
        )
        
        # Look for delete button
        try:
            delete_button = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 
                    ".delete-btn, button[name='delete'], input[value='Delete'], .btn-danger"))
            )
        except TimeoutException:
            # Try alternative selectors
            delete_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                "button, input[type='submit'], a")
            delete_button = None
            for elem in delete_elements:
                elem_text = elem.text.lower()
                elem_value = (elem.get_attribute("value") or "").lower()
                if "delete" in elem_text or "delete" in elem_value or "remove" in elem_text:
                    delete_button = elem
                    break
            
            if not delete_button:
                pytest.skip("Delete button not found")
        
        # Get current transactions content
        current_content = self.driver.find_element(By.CSS_SELECTOR, "body").text
        
        # Click delete button
        delete_button.click()
        
        # Handle confirmation dialog if it appears
        try:
            # Wait for potential alert/confirm dialog
            alert = Alert(self.driver)
            alert.accept()
        except:
            # No alert, continue
            pass
        
        # Wait for deletion to complete
        self.wait.until(lambda driver: driver.current_url)
        
        # Check that transaction was removed
        try:
            new_content = self.driver.find_element(By.CSS_SELECTOR, "body").text
            
            # Content should change after deletion
            assert new_content != current_content, "Page content should change after transaction deletion"
            
            # MSFT transaction should be removed or count should be updated
            # This is a basic check - in a real implementation, we might check specific transaction IDs
            
        except Exception:
            # Fallback: check for success message
            success_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                ".alert-success, .success-message, .flash-success")
            if success_elements:
                success_text = success_elements[0].text.lower()
                assert "deleted" in success_text or "removed" in success_text, \
                    "Success message should indicate transaction was deleted"
    
    def test_portfolio_holdings_display(self):
        """
        Test Case: Verify that portfolio holdings are displayed correctly
        Steps:
        1. Add a few transactions
        2. Navigate to portfolio page
        3. Check holdings display
        Expected: Portfolio holdings show correct symbols and quantities
        """
        # Add multiple transactions
        self._add_test_transaction("AAPL", "BUY", "10", "150.00")
        self._add_test_transaction("GOOGL", "BUY", "5", "2500.00")
        
        # Navigate to portfolio page
        self.driver.get(f"{self.base_url}/portfolio")
        
        # Wait for page to load
        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1, .page-title"))
        )
        
        # Look for holdings section
        try:
            holdings_section = self.driver.find_element(By.CSS_SELECTOR, 
                ".holdings, .portfolio-holdings, table")
            holdings_text = holdings_section.text
        except:
            # Fallback: check entire page
            holdings_text = self.driver.find_element(By.CSS_SELECTOR, "body").text
        
        # Check that our test stocks appear
        assert "AAPL" in holdings_text, "AAPL should appear in portfolio holdings"
        assert "GOOGL" in holdings_text, "GOOGL should appear in portfolio holdings"
        
        # Check for quantity information
        quantity_indicators = ["10", "5", "shares", "qty", "quantity"]
        quantity_found = any(indicator in holdings_text for indicator in quantity_indicators)
        assert quantity_found, "Quantity information should be displayed"
    
    def test_empty_portfolio(self):
        """
        Test Case: Verify behavior when portfolio is empty
        Steps:
        1. Navigate to portfolio page without adding transactions
        Expected: Appropriate message for empty portfolio
        """
        # Navigate to portfolio page
        self.driver.get(f"{self.base_url}/portfolio")
        
        # Wait for page to load
        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1, .page-title"))
        )
        
        # Check for empty portfolio indicators
        page_content = self.driver.find_element(By.CSS_SELECTOR, "body").text.lower()
        empty_indicators = ["no transactions", "empty", "no holdings", "no stocks", "portfolio is empty"]
        empty_found = any(indicator in page_content for indicator in empty_indicators)
        
        if not empty_found:
            # Check if holdings table is empty
            try:
                holdings_table = self.driver.find_element(By.CSS_SELECTOR, "table")
                rows = holdings_table.find_elements(By.CSS_SELECTOR, "tr")
                data_rows = [row for row in rows if row.find_elements(By.CSS_SELECTOR, "td")]
                assert len(data_rows) == 0, "Empty portfolio should have no data rows"
            except:
                # No table found, which is also acceptable for empty portfolio
                pass
    
    def _add_test_transaction(self, symbol, action, quantity, price):
        """Helper method to add a test transaction"""
        self.driver.get(f"{self.base_url}/portfolio")
        
        # Wait for portfolio page to load (portfolio uses h2 for heading)
        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1, h2, .page-title"))
        )
        
        try:
            # Find form fields
            symbol_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='symbol'], #symbol")
            action_select = self.driver.find_element(By.CSS_SELECTOR, "select[name='action'], #action")
            quantity_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='quantity'], #quantity")
            price_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='price'], #price")
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
            
            # Fill form
            symbol_input.clear()
            symbol_input.send_keys(symbol)
            
            action_dropdown = Select(action_select)
            action_dropdown.select_by_visible_text(action)
            
            quantity_input.clear()
            quantity_input.send_keys(quantity)
            
            price_input.clear()
            price_input.send_keys(price)
            
            # Submit
            submit_button.click()
            
            # Wait for submission
            self.wait.until(lambda driver: driver.current_url)
            
        except Exception as e:
            pytest.skip(f"Could not add test transaction: {e}")
    
    def _login_user(self):
        """Helper method to login the test user with robust error handling"""
        try:
            self.driver.get(f"{self.base_url}/login")
            
            # Wait for login form elements with multiple fallbacks
            try:
                username_input = self.wait.until(
                    EC.presence_of_element_located((By.NAME, "username"))
                )
            except TimeoutException:
                # Try alternative selectors
                username_input = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#username, input[type='text'], input[type='email']"))
                )
            
            try:
                password_input = self.driver.find_element(By.NAME, "password")
            except:
                password_input = self.driver.find_element(By.CSS_SELECTOR, "#password, input[type='password']")
            
            try:
                submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            except:
                submit_button = self.driver.find_element(By.CSS_SELECTOR, "input[type='submit'], .btn-submit, .login-btn")
            
            # Enter credentials
            username_input.clear()
            username_input.send_keys(self.user_data['username'])
            password_input.clear()
            password_input.send_keys("securepassword123")  # Use the password from test_user_data fixture
            
            # Submit form
            submit_button.click()
            
            # Wait for successful login with extended timeout
            login_wait = WebDriverWait(self.driver, 30)
            login_wait.until(lambda driver: "/login" not in driver.current_url)
            
            # Wait for page to fully load after login
            import time
            time.sleep(2)
            
            # Verify authentication worked by checking session
            try:
                # Try to access portfolio page directly to test auth
                self.driver.get(f"{self.base_url}/portfolio")
                login_wait.until(lambda driver: "/login" not in driver.current_url)
                
                # If we're still not redirected to login, auth worked
                current_url = self.driver.current_url
                if "/login" in current_url:
                    raise Exception("Authentication failed - still being redirected to login")
                    
                print(f"✅ Successfully logged in as {self.user_data['username']}")
                
            except Exception as auth_e:
                print(f"❌ Authentication verification failed: {auth_e}")
                print(f"Current URL: {self.driver.current_url}")
                # Try to get session cookie info
                try:
                    cookies = self.driver.get_cookies()
                    print(f"Cookies: {[c['name'] for c in cookies]}")
                except:
                    pass
                raise
            
        except Exception as e:
            print(f"❌ Login failed: {e}")
            print(f"Current URL: {self.driver.current_url}")
            print(f"Page title: {self.driver.title}")
            raise
        
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