#!/usr/bin/env python3
"""
Selenium test for search functionality
Tests that search works across all tickers, not just the first page
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def create_driver():
    """Create Chrome driver with appropriate options"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    
    # Connect to Chrome in the selenium container
    chrome_options.add_argument('--remote-debugging-address=0.0.0.0')
    chrome_options.add_argument('--remote-debugging-port=9222')
    
    try:
        driver = webdriver.Remote(
            command_executor='http://selenium-chrome:4444/wd/hub',
            options=chrome_options
        )
        return driver
    except Exception as e:
        print(f"Failed to connect to remote Chrome: {e}")
        # Fallback to local Chrome
        try:
            driver = webdriver.Chrome(options=chrome_options)
            return driver
        except Exception as e2:
            print(f"Failed to create local Chrome driver: {e2}")
            raise

def test_search_functionality():
    """Test that search functionality works across all tickers"""
    driver = None
    try:
        print("Creating Chrome driver...")
        driver = create_driver()
        driver.implicitly_wait(10)
        
        # Navigate to the main page
        print("Navigating to webapp...")
        webapp_url = "http://sa-web:5000"  # Use container name for internal communication
        driver.get(webapp_url)
        
        # Wait for page to load
        WebDriverWait(driver, 10).wait(
            EC.presence_of_element_located((By.ID, "searchInput"))
        )
        print("Page loaded successfully")
        
        # Test 1: Search for a ticker that should be at the end of the alphabet (ZTS)
        print("\nTest 1: Searching for ZTS (should be at end of list)...")
        search_input = driver.find_element(By.ID, "searchInput")
        search_input.clear()
        search_input.send_keys("ZTS")
        
        # Wait for search to complete (debounced by 500ms)
        time.sleep(1)
        
        # Check if ZTS appears in results
        try:
            # Wait for the page to reload with search results
            WebDriverWait(driver, 10).wait(
                EC.url_contains("search=ZTS")
            )
            print("URL updated with search parameter: ✓")
            
            # Look for ZTS in the results
            stock_rows = driver.find_elements(By.CSS_SELECTOR, ".stock-item")
            zts_found = False
            for row in stock_rows:
                symbol_element = row.find_element(By.CSS_SELECTOR, "td:first-child")
                if "ZTS" in symbol_element.text:
                    zts_found = True
                    print("ZTS found in search results: ✓")
                    break
            
            if not zts_found:
                print("ZTS not found in search results: ✗")
                return False
                
        except TimeoutException:
            print("Search did not update URL with search parameter: ✗")
            return False
        
        # Test 2: Search for company name (Zoetis)
        print("\nTest 2: Searching for company name 'Zoetis'...")
        search_input = driver.find_element(By.ID, "searchInput")
        search_input.clear()
        search_input.send_keys("Zoetis")
        
        time.sleep(1)
        
        try:
            WebDriverWait(driver, 10).wait(
                EC.url_contains("search=Zoetis")
            )
            print("URL updated with company name search: ✓")
            
            # Look for Zoetis/ZTS in the results
            stock_rows = driver.find_elements(By.CSS_SELECTOR, ".stock-item")
            zoetis_found = False
            for row in stock_rows:
                company_name_element = row.find_element(By.CSS_SELECTOR, "td:nth-child(2)")
                symbol_element = row.find_element(By.CSS_SELECTOR, "td:first-child")
                if "Zoetis" in company_name_element.text or "ZTS" in symbol_element.text:
                    zoetis_found = True
                    print("Zoetis found in search results: ✓")
                    break
            
            if not zoetis_found:
                print("Zoetis not found in search results: ✗")
                return False
                
        except TimeoutException:
            print("Company name search did not work: ✗")
            return False
        
        # Test 3: Search for partial term that should return multiple results
        print("\nTest 3: Searching for partial term 'tech'...")
        search_input = driver.find_element(By.ID, "searchInput")
        search_input.clear()
        search_input.send_keys("tech")
        
        time.sleep(1)
        
        try:
            WebDriverWait(driver, 10).wait(
                EC.url_contains("search=tech")
            )
            print("URL updated with partial search: ✓")
            
            # Count results with 'tech' in name
            stock_rows = driver.find_elements(By.CSS_SELECTOR, ".stock-item")
            tech_count = 0
            for row in stock_rows:
                company_name_element = row.find_element(By.CSS_SELECTOR, "td:nth-child(2)")
                if "tech" in company_name_element.text.lower():
                    tech_count += 1
            
            print(f"Found {tech_count} companies with 'tech' in name")
            if tech_count > 0:
                print("Partial search working correctly: ✓")
            else:
                print("Partial search not working: ✗")
                return False
                
        except TimeoutException:
            print("Partial search did not work: ✗")
            return False
        
        # Test 4: Clear search and verify all stocks return
        print("\nTest 4: Clearing search...")
        search_input = driver.find_element(By.ID, "searchInput")
        search_input.clear()
        
        time.sleep(1)
        
        try:
            WebDriverWait(driver, 10).wait_until(
                lambda driver: "search=" not in driver.current_url
            )
            print("Search parameter cleared from URL: ✓")
            
            # Should see pagination again (more than 50 results)
            try:
                pagination = driver.find_element(By.CSS_SELECTOR, ".pagination")
                print("Pagination visible after clearing search: ✓")
            except NoSuchElementException:
                print("No pagination visible - this might be expected if < 50 total stocks")
            
        except TimeoutException:
            print("Search not properly cleared: ✗")
            return False
        
        print("\n✓ All search functionality tests passed!")
        return True
        
    except Exception as e:
        print(f"Error during testing: {e}")
        return False
        
    finally:
        if driver:
            try:
                # Take a screenshot for debugging
                driver.save_screenshot("/workspace/stockdev/search_test_screenshot.png")
                print("Screenshot saved to search_test_screenshot.png")
            except:
                pass
            driver.quit()

if __name__ == "__main__":
    print("Testing search functionality with Selenium...")
    success = test_search_functionality()
    if success:
        print("\n🎉 Search functionality test completed successfully!")
        exit(0)
    else:
        print("\n❌ Search functionality test failed!")
        exit(1)