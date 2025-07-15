#!/usr/bin/env python3
"""
Selenium test for dark mode functionality verification
Tests tables, modals, and form controls in both light and dark modes
"""

import time
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class DarkModeSeleniumTest:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.driver = None
        
    def setup_driver(self):
        """Setup Chrome driver with Selenium Grid and fallback options"""
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Try multiple Selenium Grid endpoints
        selenium_endpoints = [
            'http://stockdev-selenium-chrome-1:4444/wd/hub',
            'http://selenium-chrome:4444/wd/hub',
            'http://localhost:4444/wd/hub'
        ]
        
        for endpoint in selenium_endpoints:
            try:
                print(f"Attempting to connect to Selenium Grid at {endpoint}...")
                self.driver = webdriver.Remote(
                    command_executor=endpoint,
                    options=chrome_options
                )
                print(f"✓ Chrome driver connected to Selenium Grid at {endpoint} successfully")
                return True
            except Exception as e:
                print(f"✗ Failed to connect to {endpoint}: {e}")
                continue
        
        # Fallback: Try local Chrome driver
        try:
            print("Attempting to use local Chrome driver as fallback...")
            chrome_options.add_argument("--headless")  # Run headless for CI environments
            self.driver = webdriver.Chrome(options=chrome_options)
            print("✓ Local Chrome driver initialized successfully")
            return True
        except Exception as e:
            print(f"✗ Failed to initialize local Chrome driver: {e}")
        
        print("✗ All Selenium driver options failed")
        return False
    
    def wait_for_element(self, by, value, timeout=10):
        """Wait for element to be present and return it"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            print(f"✗ Element not found: {by}={value}")
            return None
    
    def get_computed_style(self, element, property_name):
        """Get computed CSS property value"""
        try:
            return self.driver.execute_script(
                f"return window.getComputedStyle(arguments[0]).getPropertyValue('{property_name}');",
                element
            )
        except Exception as e:
            print(f"✗ Error getting computed style: {e}")
            return None
    
    def test_dark_mode_toggle(self):
        """Test dark mode toggle functionality"""
        print("\n🌙 Testing Dark Mode Toggle...")
        
        # Navigate to home page
        self.driver.get(self.base_url)
        time.sleep(2)
        
        # Check initial theme (should be light)
        html_element = self.driver.find_element(By.TAG_NAME, "html")
        initial_theme = html_element.get_attribute("data-theme")
        print(f"Initial theme: {initial_theme or 'light'}")
        
        # Find and click dark mode toggle
        toggle_button = self.wait_for_element(By.ID, "darkModeToggle")
        if not toggle_button:
            print("✗ Dark mode toggle button not found")
            return False
        
        print("✓ Dark mode toggle button found")
        toggle_button.click()
        time.sleep(1)
        
        # Check if theme changed to dark
        new_theme = html_element.get_attribute("data-theme")
        if new_theme == "dark":
            print("✓ Dark mode activated successfully")
            return True
        else:
            print(f"✗ Dark mode not activated. Theme: {new_theme}")
            return False
    
    def test_table_dark_mode_styling(self):
        """Test table styling in dark mode"""
        print("\n📊 Testing Table Dark Mode Styling...")
        
        # Find stock table
        table = self.wait_for_element(By.CSS_SELECTOR, "#stockList table, .table")
        if not table:
            print("✗ Stock table not found")
            return False
        
        print("✓ Stock table found")
        
        # Test table header styling
        table_header = self.driver.find_element(By.CSS_SELECTOR, "thead th")
        if table_header:
            bg_color = self.get_computed_style(table_header, "background-color")
            text_color = self.get_computed_style(table_header, "color")
            print(f"Table header - Background: {bg_color}, Text: {text_color}")
            
            # In dark mode, should have dark background
            if "rgb(52, 58, 64)" in bg_color or "343a40" in bg_color:
                print("✓ Table header has dark mode styling")
                header_ok = True
            else:
                print("✗ Table header does not have dark mode styling")
                header_ok = False
        else:
            print("✗ Table header not found")
            header_ok = False
        
        # Test table row hover (simulate hover)
        table_rows = self.driver.find_elements(By.CSS_SELECTOR, "tbody tr")
        if table_rows:
            # Move to first row to trigger hover
            self.driver.execute_script("arguments[0].dispatchEvent(new Event('mouseenter'));", table_rows[0])
            time.sleep(0.5)
            
            row_bg = self.get_computed_style(table_rows[0], "background-color")
            print(f"Table row hover - Background: {row_bg}")
            
            # Check if hover has blue tint (rgba(52, 152, 219, 0.2))
            if "rgba(52, 152, 219" in row_bg or "rgb(52, 152, 219)" in row_bg:
                print("✓ Table row has dark mode hover styling")
                row_ok = True
            else:
                print("✗ Table row does not have dark mode hover styling")
                row_ok = False
        else:
            print("✗ Table rows not found")
            row_ok = False
        
        return header_ok and row_ok
    
    def test_modal_dark_mode_styling(self):
        """Test modal styling in dark mode"""
        print("\n🪟 Testing Modal Dark Mode Styling...")
        
        # Try to find and trigger a modal
        modal_triggers = self.driver.find_elements(By.CSS_SELECTOR, "[data-bs-toggle='modal'], .btn[onclick*='modal']")
        
        if not modal_triggers:
            print("ℹ️ No modal triggers found on current page, checking stock detail page...")
            
            # Navigate to a stock detail page to find modals
            try:
                stock_link = self.driver.find_element(By.CSS_SELECTOR, "tbody tr")
                if stock_link:
                    stock_link.click()
                    time.sleep(2)
                    
                    # Look for squeeze analysis button or similar
                    squeeze_btn = self.driver.find_elements(By.CSS_SELECTOR, "[data-bs-target*='Modal'], .btn[onclick*='squeeze']")
                    if squeeze_btn:
                        squeeze_btn[0].click()
                        time.sleep(1)
                    else:
                        print("ℹ️ No modal trigger found on stock detail page")
                        return None
            except:
                print("ℹ️ Could not navigate to stock detail page")
                return None
        else:
            # Click first modal trigger
            modal_triggers[0].click()
            time.sleep(1)
        
        # Check if modal is visible
        modal = self.wait_for_element(By.CSS_SELECTOR, ".modal.show, .modal", timeout=5)
        if not modal:
            print("ℹ️ No modal opened")
            return None
        
        print("✓ Modal found")
        
        # Test modal content styling
        modal_content = self.driver.find_element(By.CSS_SELECTOR, ".modal-content")
        if modal_content:
            bg_color = self.get_computed_style(modal_content, "background-color")
            text_color = self.get_computed_style(modal_content, "color")
            border_color = self.get_computed_style(modal_content, "border-color")
            
            print(f"Modal content - Background: {bg_color}, Text: {text_color}, Border: {border_color}")
            
            # In dark mode, should have dark background
            if "rgb(52, 58, 64)" in bg_color or "343a40" in bg_color:
                print("✓ Modal has dark mode styling")
                return True
            else:
                print("✗ Modal does not have dark mode styling")
                return False
        else:
            print("✗ Modal content not found")
            return False
    
    def test_form_controls_dark_mode(self):
        """Test form controls styling in dark mode"""
        print("\n📝 Testing Form Controls Dark Mode Styling...")
        
        # Wait a bit more for page to load completely
        time.sleep(2)
        
        # Test specific form controls we know exist
        test_results = []
        
        # Test search input
        try:
            search_input = self.driver.find_element(By.ID, "searchInput")
            print("✓ Found search input")
            
            bg_color = self.get_computed_style(search_input, "background-color")
            text_color = self.get_computed_style(search_input, "color")
            border_color = self.get_computed_style(search_input, "border-color")
            
            print(f"  Search Input - Background: {bg_color}, Text: {text_color}, Border: {border_color}")
            
            # Check for dark mode styling
            dark_bg = "rgb(33, 37, 41)" in bg_color
            light_text = "rgb(255, 255, 255)" in text_color
            dark_border = "rgb(73, 80, 87)" in border_color
            
            if dark_bg and light_text and dark_border:
                print("  ✓ Search input has correct dark mode styling")
                test_results.append(True)
            else:
                print("  ✗ Search input does not have correct dark mode styling")
                test_results.append(False)
                
        except Exception as e:
            print(f"  ✗ Could not test search input: {e}")
            test_results.append(False)
        
        # Test sector filter
        try:
            sector_filter = self.driver.find_element(By.ID, "sectorFilter")
            print("✓ Found sector filter")
            
            bg_color = self.get_computed_style(sector_filter, "background-color")
            text_color = self.get_computed_style(sector_filter, "color")
            border_color = self.get_computed_style(sector_filter, "border-color")
            
            print(f"  Sector Filter - Background: {bg_color}, Text: {text_color}, Border: {border_color}")
            
            # Check for dark mode styling
            dark_bg = "rgb(33, 37, 41)" in bg_color
            light_text = "rgb(255, 255, 255)" in text_color
            dark_border = "rgb(73, 80, 87)" in border_color
            
            if dark_bg and light_text and dark_border:
                print("  ✓ Sector filter has correct dark mode styling")
                test_results.append(True)
            else:
                print("  ✗ Sector filter does not have correct dark mode styling")
                test_results.append(False)
                
        except Exception as e:
            print(f"  ✗ Could not test sector filter: {e}")
            test_results.append(False)
        
        # Overall result
        if all(test_results) and test_results:
            print("\n✓ All form controls have dark mode styling")
            return True
        else:
            print("\n✗ Some form controls do not have dark mode styling")
            return False
    
    def test_overall_theme(self):
        """Test overall page theme"""
        print("\n🎨 Testing Overall Page Theme...")
        
        # Check body background
        body = self.driver.find_element(By.TAG_NAME, "body")
        body_bg = self.get_computed_style(body, "background-color")
        body_color = self.get_computed_style(body, "color")
        
        print(f"Body - Background: {body_bg}, Text: {body_color}")
        
        # Check navbar
        navbar = self.driver.find_element(By.CSS_SELECTOR, ".navbar, nav")
        if navbar:
            navbar_bg = self.get_computed_style(navbar, "background-color")
            print(f"Navbar - Background: {navbar_bg}")
        
        # In dark mode, body should have dark background
        if "rgb(33, 37, 41)" in body_bg or "212529" in body_bg:
            print("✓ Overall theme is dark")
            return True
        else:
            print("✗ Overall theme is not dark")
            return False
    
    def run_all_tests(self):
        """Run all dark mode tests"""
        print("🧪 Starting Dark Mode Selenium Tests")
        print("=" * 50)
        
        if not self.setup_driver():
            return False
        
        try:
            results = {}
            
            # Test dark mode toggle
            results['toggle'] = self.test_dark_mode_toggle()
            
            if results['toggle']:
                # Run tests in dark mode
                results['overall_theme'] = self.test_overall_theme()
                results['table_styling'] = self.test_table_dark_mode_styling()
                results['modal_styling'] = self.test_modal_dark_mode_styling()
                results['form_controls'] = self.test_form_controls_dark_mode()
            else:
                print("⚠️ Dark mode toggle failed, skipping other tests")
                return False
            
            # Print results summary
            print("\n" + "=" * 50)
            print("📋 TEST RESULTS SUMMARY")
            print("=" * 50)
            
            for test_name, result in results.items():
                if result is True:
                    status = "✓ PASS"
                elif result is False:
                    status = "✗ FAIL"
                else:
                    status = "⚠️ SKIP"
                print(f"{test_name.replace('_', ' ').title()}: {status}")
            
            # Overall assessment
            passed_tests = sum(1 for r in results.values() if r is True)
            total_tests = len([r for r in results.values() if r is not None])
            
            print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
            
            if passed_tests == total_tests and total_tests > 0:
                print("🎉 All dark mode tests PASSED!")
                return True
            else:
                print("⚠️ Some dark mode tests FAILED!")
                return False
                
        except Exception as e:
            print(f"✗ Test execution error: {e}")
            return False
        finally:
            if self.driver:
                self.driver.quit()
                print("\n🔚 Browser closed")


def main():
    """Main test execution"""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        # Use container name for webapp
        base_url = "http://sa-web-dev:5000"
    
    print(f"Testing dark mode at: {base_url}")
    
    test = DarkModeSeleniumTest(base_url)
    success = test.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()