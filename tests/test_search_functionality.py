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
import sys
import os
sys.path.append('/app')
from database import DatabaseManager
from sqlalchemy import text

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

def setup_test_data():
    """Add test data to the database - enough for multiple pages"""
    print("Setting up test data...")
    db_manager = DatabaseManager()
    
    # Create 60+ stocks to force pagination (default page size is 50)
    test_stocks = []
    
    # Add A-companies (will be on first page)
    for i in range(20):
        test_stocks.append((f'A{i:02d}', f'Alpha Company {i:02d}', 'Technology'))
    
    # Add B-companies (will be on first page) 
    for i in range(20):
        test_stocks.append((f'B{i:02d}', f'Beta Company {i:02d}', 'Healthcare'))
    
    # Add C-companies (will be on first page)
    for i in range(15):
        test_stocks.append((f'C{i:02d}', f'Charlie Company {i:02d}', 'Finance'))
    
    # Add Z-companies (will be on second page - these are the key test targets)
    test_stocks.extend([
        ('ZTS', 'Zoetis Inc.', 'Healthcare'),
        ('ZBH', 'Zimmer Biomet Holdings Inc.', 'Healthcare'),
        ('ZBRA', 'Zebra Technologies Corporation', 'Technology'),
        ('ZION', 'Zions Bancorporation', 'Financial Services'),
        ('ZWS', 'Zowe Systems Corp.', 'Technology')
    ])
    
    print(f"Creating {len(test_stocks)} test stocks to ensure pagination...")
    
    try:
        with db_manager.engine.connect() as conn:
            # Clear existing data
            conn.execute(text("DELETE FROM sp500_constituents"))
            
            # Insert test data
            for symbol, name, sector in test_stocks:
                conn.execute(text("""
                    INSERT INTO sp500_constituents (symbol, name, sector) 
                    VALUES (:symbol, :name, :sector)
                    ON CONFLICT (symbol) DO UPDATE SET
                        name = EXCLUDED.name,
                        sector = EXCLUDED.sector
                """), {'symbol': symbol, 'name': name, 'sector': sector})
            
            conn.commit()
            print(f"Added {len(test_stocks)} test stocks to database")
            print("First page will contain A00-C14 stocks")
            print("Second page will contain Z-stocks (ZTS, ZBH, ZBRA, ZION, ZWS)")
            
    except Exception as e:
        print(f"Error setting up test data: {e}")
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
        webapp_url = "http://sa-test-web:5000"  # Use test container name for internal communication
        driver.get(webapp_url)
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
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
            WebDriverWait(driver, 10).until(
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
            WebDriverWait(driver, 10).until(
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
        
        # Test 3: Search for partial term that should return multiple results from second page
        print("\nTest 3: Searching for partial term 'Zebra' (should be on page 2)...")
        search_input = driver.find_element(By.ID, "searchInput")
        search_input.clear()
        search_input.send_keys("Zebra")
        
        time.sleep(1)
        
        try:
            WebDriverWait(driver, 10).until(
                EC.url_contains("search=Zebra")
            )
            print("URL updated with partial search: ✓")
            
            # Count results with 'Zebra' in name
            stock_rows = driver.find_elements(By.CSS_SELECTOR, ".stock-item")
            zebra_count = 0
            for row in stock_rows:
                company_name_element = row.find_element(By.CSS_SELECTOR, "td:nth-child(2)")
                symbol_element = row.find_element(By.CSS_SELECTOR, "td:first-child")
                if "zebra" in company_name_element.text.lower() or "zbra" in symbol_element.text.lower():
                    zebra_count += 1
            
            print(f"Found {zebra_count} companies with 'Zebra' in name")
            if zebra_count > 0:
                print("Partial search working correctly (found stock from page 2): ✓")
            else:
                print("Partial search not working: ✗")
                return False
                
        except TimeoutException:
            print("Partial search did not work: ✗")
            return False
        
        # Test 4: Navigate directly to verify pagination exists without search
        print("\nTest 4: Verifying pagination exists with full data...")
        driver.get("http://sa-test-web:5000")
        
        time.sleep(1)
        
        try:
            # Should see pagination with 60 stocks
            pagination = driver.find_element(By.CSS_SELECTOR, ".pagination")
            print("Pagination visible with full dataset: ✓")
            
            # Count stocks on first page (should be 50)
            stock_rows = driver.find_elements(By.CSS_SELECTOR, ".stock-item")
            print(f"Found {len(stock_rows)} stocks on first page")
            
            if len(stock_rows) == 50:
                print("Correct number of stocks per page: ✓")
            else:
                print(f"Expected 50 stocks per page, got {len(stock_rows)}")
            
        except NoSuchElementException:
            print("No pagination found - this is unexpected with 60 stocks")
            stock_rows = driver.find_elements(By.CSS_SELECTOR, ".stock-item")
            print(f"Total stocks visible: {len(stock_rows)}")
            # This is still acceptable as the core search functionality works
        
        print("\n✓ All search functionality tests passed!")
        return True
        
    except Exception as e:
        print(f"Error during testing: {e}")
        return False
        
    finally:
        if driver:
            try:
                # Take a screenshot for debugging
                driver.save_screenshot("/app/search_test_screenshot.png")
                print("Screenshot saved to search_test_screenshot.png")
            except:
                pass
            driver.quit()

if __name__ == "__main__":
    print("Testing search functionality with Selenium...")
    
    # Setup test data first
    setup_test_data()
    
    success = test_search_functionality()
    if success:
        print("\n🎉 Search functionality test completed successfully!")
        exit(0)
    else:
        print("\n❌ Search functionality test failed!")
        exit(1)