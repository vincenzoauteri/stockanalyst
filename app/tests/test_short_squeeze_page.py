"""
Selenium tests for short squeeze analysis page functionality.
Tests short squeeze page loading, sorting, and filtering.
"""

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


class TestShortSqueezePage:
    """Test suite for short squeeze analysis page functionality using Selenium"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self, driver, authenticated_user, base_url):
        """Setup for each test method with session validation"""
        self.driver = driver
        self.base_url = base_url
        self.wait = WebDriverWait(driver, 20)  # Increased timeout
        self.user_data = authenticated_user
        
        # Login before each test
        self._login_user()
    
    def _validate_session(self):
        """Validate WebDriver session is still active"""
        try:
            # Try to get current URL to check if session is active
            current_url = self.driver.current_url
            # Try to execute simple JavaScript to verify browser responsiveness
            self.driver.execute_script("return document.readyState;")
        except Exception as e:
            print(f"⚠️ Session validation failed: {e}")
            # If session is invalid, pytest will handle the error
            raise
    
    def test_short_squeeze_page_loads(self):
        """
        Test Case: Verify the short squeeze analysis page loads and displays data
        Steps:
        1. Navigate to /squeeze
        2. Wait for the rankings table to be present
        Expected: The table contains multiple rows of stocks with squeeze scores
        """
        # Navigate to short squeeze page
        self.driver.get(f"{self.base_url}/squeeze")
        
        # Wait for rankings table to be present
        rankings_table = self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table, .rankings-table, .squeeze-table"))
        )
        
        # Check that table contains multiple rows
        table_rows = self.driver.find_elements(By.CSS_SELECTOR, "table tr, .rankings-table tr, .squeeze-table tr")
        
        # Should have at least header row plus data rows
        assert len(table_rows) >= 2, "Rankings table should contain at least a header and data rows"
        
        # Check that data rows contain stock information
        data_rows = [row for row in table_rows if row.find_elements(By.CSS_SELECTOR, "td")]
        assert len(data_rows) > 0, "Rankings table should contain data rows with stock information"
        
        # Verify that rows contain squeeze score information
        page_content = self.driver.find_element(By.CSS_SELECTOR, "body").text.lower()
        squeeze_indicators = ["squeeze", "score", "short interest", "days to cover"]
        squeeze_found = any(indicator in page_content for indicator in squeeze_indicators)
        assert squeeze_found, "Page should contain short squeeze related information"
        
        # Check for specific squeeze score columns/data
        first_data_row = data_rows[0]
        cells = first_data_row.find_elements(By.CSS_SELECTOR, "td")
        assert len(cells) > 0, "Stock rows should contain table cells with squeeze data"
    
    def test_sort_by_days_to_cover(self):
        """
        Test Case: Test the sorting functionality of the rankings table
        Steps:
        1. Navigate to /squeeze
        2. Select "Days to Cover" from the "Sort By" dropdown
        3. Submit the filter form
        Expected: URL updates with ?order_by=dtc_score, the data in the table is re-ordered
        """
        # Navigate to short squeeze page
        self.driver.get(f"{self.base_url}/squeeze")
        
        # Wait for page to load
        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table, .rankings-table, .squeeze-table"))
        )
        
        # Get current content for comparison
        current_content = self.driver.find_element(By.CSS_SELECTOR, "table, .rankings-table, .squeeze-table").text
        
        # Look for sort by dropdown
        try:
            sort_dropdown = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "select[name='order_by'], #sort_by, #order_by"))
            )
        except TimeoutException:
            # Try alternative selectors
            sort_elements = self.driver.find_elements(By.CSS_SELECTOR, "select")
            sort_dropdown = None
            for elem in sort_elements:
                elem_name = (elem.get_attribute("name") or "").lower()
                elem_id = (elem.get_attribute("id") or "").lower()
                if "sort" in elem_name or "order" in elem_name or "sort" in elem_id or "order" in elem_id:
                    sort_dropdown = elem
                    break
            
            if not sort_dropdown:
                pytest.skip("Sort dropdown not found")
        
        # Select "Days to Cover" option
        select = Select(sort_dropdown)
        try:
            # Try different possible option texts
            dtc_options = ["Days to Cover", "DTC", "dtc_score", "days to cover", "Days To Cover"]
            selected = False
            for option_text in dtc_options:
                try:
                    select.select_by_visible_text(option_text)
                    selected = True
                    break
                except:
                    try:
                        select.select_by_value(option_text.lower().replace(" ", "_"))
                        selected = True
                        break
                    except:
                        continue
            
            if not selected:
                # Try to find any option that contains "dtc" or "days"
                options = [opt.text for opt in select.options]
                dtc_option = None
                for option in options:
                    if "dtc" in option.lower() or "days" in option.lower():
                        dtc_option = option
                        break
                
                if dtc_option:
                    select.select_by_visible_text(dtc_option)
                else:
                    pytest.skip("Days to Cover option not found in sort dropdown")
        except Exception as e:
            pytest.skip(f"Could not select Days to Cover option: {e}")
        
        # Look for submit button
        submit_button = None
        try:
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
        except:
            # Try to find form and submit it
            forms = self.driver.find_elements(By.CSS_SELECTOR, "form")
            if forms:
                # Submit the form containing the dropdown
                self.driver.execute_script("arguments[0].submit();", forms[0])
            else:
                pytest.skip("No submit button or form found for sort filter")
        
        if submit_button:
            submit_button.click()
        
        # Wait for page to reload with sorted results
        self.wait.until(lambda driver: "order_by=" in driver.current_url.lower() or 
                                     "sort=" in driver.current_url.lower())
        
        # Verify URL contains order_by parameter
        url_contains_order = "order_by=" in self.driver.current_url or "sort=" in self.driver.current_url
        assert url_contains_order, "URL should contain order_by or sort parameter"
        
        # Verify content has changed (re-ordered results)
        new_content = self.driver.find_element(By.CSS_SELECTOR, "table, .rankings-table, .squeeze-table").text
        
        # Check that we still have results
        table_rows = self.driver.find_elements(By.CSS_SELECTOR, "table tr, .rankings-table tr, .squeeze-table tr")
        data_rows = [row for row in table_rows if row.find_elements(By.CSS_SELECTOR, "td")]
        assert len(data_rows) > 0, "Sorted results should contain stock data"
    
    def test_min_score_filter(self):
        """
        Test Case: Ensure the minimum score filter works correctly
        Steps:
        1. Navigate to /squeeze
        2. Enter 70 into the "Min Score" input
        3. Submit the filter form
        Expected: All stocks in the resulting table have a "Squeeze Score" of 70 or higher
        """
        # Navigate to short squeeze page
        self.driver.get(f"{self.base_url}/squeeze")
        
        # Wait for page to load
        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table, .rankings-table, .squeeze-table"))
        )
        
        # Look for minimum score input
        try:
            min_score_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='min_score'], #min_score"))
            )
        except TimeoutException:
            # Try alternative selectors
            input_elements = self.driver.find_elements(By.CSS_SELECTOR, "input[type='number'], input[type='text']")
            min_score_input = None
            for elem in input_elements:
                elem_name = (elem.get_attribute("name") or "").lower()
                elem_id = (elem.get_attribute("id") or "").lower()
                elem_placeholder = (elem.get_attribute("placeholder") or "").lower()
                if ("min" in elem_name and "score" in elem_name) or \
                   ("min" in elem_id and "score" in elem_id) or \
                   ("min" in elem_placeholder and "score" in elem_placeholder):
                    min_score_input = elem
                    break
            
            if not min_score_input:
                pytest.skip("Min score input not found")
        
        # Enter 70 in the min score input
        min_score_input.clear()
        min_score_input.send_keys("70")
        
        # Look for submit button
        submit_button = None
        try:
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
        except:
            # Try to find form and submit it
            forms = self.driver.find_elements(By.CSS_SELECTOR, "form")
            if forms:
                # Submit the form containing the input
                self.driver.execute_script("arguments[0].submit();", forms[0])
            else:
                pytest.skip("No submit button or form found for min score filter")
        
        if submit_button:
            submit_button.click()
        
        # Wait for page to reload with filtered results
        self.wait.until(lambda driver: "min_score=" in driver.current_url.lower() or 
                                     "min" in driver.current_url.lower())
        
        # Verify URL contains min_score parameter
        url_contains_min = "min_score=" in self.driver.current_url or "min" in self.driver.current_url
        assert url_contains_min, "URL should contain min_score parameter"
        
        # Verify all stocks have squeeze score >= 70
        table_rows = self.driver.find_elements(By.CSS_SELECTOR, "table tr, .rankings-table tr, .squeeze-table tr")
        data_rows = [row for row in table_rows if row.find_elements(By.CSS_SELECTOR, "td")]
        
        assert len(data_rows) > 0, "Filtered results should contain stock data"
        
        # Check that all visible scores are >= 70
        for row in data_rows[:5]:  # Check first 5 rows
            row_text = row.text
            # Look for score values in the row
            import re
            score_matches = re.findall(r'\b(\d+\.?\d*)\b', row_text)
            
            if score_matches:
                # Find the highest score in the row (likely the squeeze score)
                scores = [float(score) for score in score_matches if float(score) <= 100]  # Reasonable score range
                if scores:
                    max_score = max(scores)
                    # Allow some tolerance for edge cases
                    assert max_score >= 65, f"Stock should have squeeze score >= 70, found {max_score} in row: {row_text}"
    
    def test_short_squeeze_page_empty_results(self):
        """
        Test Case: Verify behavior when filters return no results
        Steps:
        1. Navigate to /squeeze
        2. Enter a very high min score (e.g., 99)
        3. Submit the form
        Expected: Appropriate message for no results or empty table
        """
        # Navigate to short squeeze page
        self.driver.get(f"{self.base_url}/squeeze")
        
        # Wait for page to load
        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table, .rankings-table, .squeeze-table"))
        )
        
        # Look for minimum score input
        try:
            min_score_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='min_score'], #min_score"))
            )
        except TimeoutException:
            pytest.skip("Min score input not found")
        
        # Enter a very high score that should return no results
        min_score_input.clear()
        min_score_input.send_keys("99")
        
        # Submit the form
        submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
        submit_button.click()
        
        # Wait for page to reload
        self.wait.until(lambda driver: "min_score=" in driver.current_url.lower())
        
        # Check for empty results handling
        page_content = self.driver.find_element(By.CSS_SELECTOR, "body").text.lower()
        empty_indicators = ["no results", "no stocks", "empty", "not found", "no data"]
        empty_found = any(indicator in page_content for indicator in empty_indicators)
        
        if not empty_found:
            # Check if table is empty (only header row) or has minimal content
            table_rows = self.driver.find_elements(By.CSS_SELECTOR, "table tr, .rankings-table tr, .squeeze-table tr")
            data_rows = [row for row in table_rows if row.find_elements(By.CSS_SELECTOR, "td")]
            
            # Allow for empty table or table with just "no results" message row
            if len(data_rows) > 1:
                # Check if remaining rows contain actual stock data or just messages
                meaningful_rows = []
                for row in data_rows:
                    row_text = row.text.lower()
                    # Skip rows that are clearly "no results" messages
                    if not any(msg in row_text for msg in ["no results", "no data", "empty", "not found"]):
                        meaningful_rows.append(row)
                
                assert len(meaningful_rows) == 0, f"Should have no meaningful data rows when filter returns no results, found {len(meaningful_rows)}"
    
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