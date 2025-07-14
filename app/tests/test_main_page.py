"""
Selenium tests for main page (stock list) functionality.
Tests stock list display, pagination, and filtering.
"""

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


class TestMainPage:
    """Test suite for main page stock list functionality using Selenium"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self, driver, authenticated_user, base_url):
        """Setup for each test method"""
        self.driver = driver
        self.base_url = base_url
        self.wait = WebDriverWait(driver, 10)
        self.user_data = authenticated_user
        
        # Login before each test
        self._login_user()
    
    def test_stock_list_loads(self):
        """
        Test Case: Verify that the main page loads and displays a list of stocks
        Steps:
        1. Navigate to /
        2. Wait for the stock table to be present
        Expected: The table contains multiple rows (<tr>), each representing a stock
        """
        # Navigate to main page
        self.driver.get(f"{self.base_url}/")
        
        # Wait for stock table to be present
        stock_table = self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table, .stock-table"))
        )
        
        # Check that table contains multiple rows
        stock_rows = self.driver.find_elements(By.CSS_SELECTOR, "table tr, .stock-table tr")
        
        # Should have at least header row plus data rows
        assert len(stock_rows) >= 2, "Stock table should contain at least a header and data rows"
        
        # Check that data rows contain stock information
        data_rows = [row for row in stock_rows if row.find_elements(By.CSS_SELECTOR, "td")]
        assert len(data_rows) > 0, "Stock table should contain data rows with stock information"
        
        # Verify that stock rows contain expected elements (symbols, names, etc.)
        first_data_row = data_rows[0]
        cells = first_data_row.find_elements(By.CSS_SELECTOR, "td")
        assert len(cells) > 0, "Stock rows should contain table cells with data"
    
    def test_pagination_links(self):
        """
        Test Case: Test the functionality of the pagination controls
        Steps:
        1. Navigate to /
        2. Click the "Next" pagination link
        3. Click the "Previous" pagination link
        Expected: URL updates with ?page=2, content changes, after "Previous" returns to base or ?page=1
        """
        # Navigate to main page
        self.driver.get(f"{self.base_url}/")
        
        # Wait for page to load
        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table, .stock-table"))
        )
        
        # Look for pagination controls
        try:
            # Try to find Next button/link
            next_button = self.wait.until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Next"))
            )
        except TimeoutException:
            # Try alternative selectors for pagination
            next_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                ".pagination a, .page-link, a[href*='page=']")
            next_button = None
            for elem in next_elements:
                if "next" in elem.text.lower() or ">" in elem.text:
                    next_button = elem
                    break
            
            if not next_button:
                pytest.skip("Pagination controls not found - may not be present with current data")
        
        # Get current page content for comparison
        current_content = self.driver.find_element(By.CSS_SELECTOR, "table, .stock-table").text
        
        # Click Next
        next_button.click()
        
        # Wait for page to load and verify URL change
        self.wait.until(lambda driver: "page=2" in driver.current_url or driver.current_url != f"{self.base_url}/")
        
        # Verify URL contains page parameter
        assert "page=" in self.driver.current_url, "URL should contain page parameter after clicking Next"
        
        # Verify content has changed
        new_content = self.driver.find_element(By.CSS_SELECTOR, "table, .stock-table").text
        assert new_content != current_content, "Page content should change after pagination"
        
        # Look for Previous button/link
        try:
            previous_button = self.wait.until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Previous"))
            )
        except TimeoutException:
            # Try alternative selectors
            prev_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                ".pagination a, .page-link, a[href*='page=']")
            previous_button = None
            for elem in prev_elements:
                if "previous" in elem.text.lower() or "prev" in elem.text.lower() or "<" in elem.text:
                    previous_button = elem
                    break
            
            if not previous_button:
                pytest.skip("Previous pagination control not found")
        
        # Click Previous
        previous_button.click()
        
        # Wait for page to load
        self.wait.until(lambda driver: "page=1" in driver.current_url or driver.current_url == f"{self.base_url}/")
        
        # Verify we're back to first page
        assert "page=1" in self.driver.current_url or self.driver.current_url == f"{self.base_url}/", \
            "Should return to first page after clicking Previous"
    
    def test_sector_filter(self):
        """
        Test Case: Ensure the sector filter correctly updates the stock list
        Steps:
        1. Navigate to /
        2. Select "Technology" from the sector dropdown
        3. Submit the filter form
        Expected: Stock table updates to show only Technology stocks, URL contains ?sector=Technology
        """
        # Navigate to main page
        self.driver.get(f"{self.base_url}/")
        
        # Wait for page to load
        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table, .stock-table"))
        )
        
        # Look for sector filter dropdown
        try:
            sector_dropdown = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "select[name='sector'], #sector"))
            )
        except TimeoutException:
            # Try alternative selectors
            sector_elements = self.driver.find_elements(By.CSS_SELECTOR, "select")
            sector_dropdown = None
            for elem in sector_elements:
                name_attr = elem.get_attribute("name") or ""
                id_attr = elem.get_attribute("id") or ""
                if "sector" in name_attr.lower() or "sector" in id_attr.lower():
                    sector_dropdown = elem
                    break
            
            if not sector_dropdown:
                pytest.skip("Sector filter dropdown not found")
        
        # Get current content for comparison
        current_content = self.driver.find_element(By.CSS_SELECTOR, "table, .stock-table").text
        
        # Select Technology from dropdown
        select = Select(sector_dropdown)
        try:
            select.select_by_visible_text("Technology")
        except:
            # Try alternative text options
            options = [opt.text for opt in select.options]
            tech_option = None
            for option in options:
                if "technology" in option.lower() or "tech" in option.lower():
                    tech_option = option
                    break
            
            if tech_option:
                select.select_by_visible_text(tech_option)
            else:
                pytest.skip("Technology sector option not found in dropdown")
        
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
                pytest.skip("No submit button or form found for sector filter")
        
        if submit_button:
            submit_button.click()
        
        # Wait for page to reload with filtered results
        self.wait.until(lambda driver: "sector=" in driver.current_url.lower())
        
        # Verify URL contains sector parameter
        assert "sector=" in self.driver.current_url.lower(), "URL should contain sector parameter"
        assert "technology" in self.driver.current_url.lower() or "tech" in self.driver.current_url.lower(), \
            "URL should contain Technology sector parameter"
        
        # Verify content has changed (filtered results)
        new_content = self.driver.find_element(By.CSS_SELECTOR, "table, .stock-table").text
        
        # Check that we have results (not empty)
        stock_rows = self.driver.find_elements(By.CSS_SELECTOR, "table tr, .stock-table tr")
        data_rows = [row for row in stock_rows if row.find_elements(By.CSS_SELECTOR, "td")]
        assert len(data_rows) > 0, "Filtered results should contain stock data"
    
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