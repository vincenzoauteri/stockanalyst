#!/usr/bin/env python3
"""
Debug script to see what's actually on the page
"""

import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

def debug_page_content():
    # Setup driver
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Try multiple Selenium endpoints with fallback
    selenium_endpoints = [
        'http://stockdev-selenium-chrome-1:4444/wd/hub',
        'http://selenium-chrome:4444/wd/hub',
        'http://localhost:4444/wd/hub'
    ]
    
    driver = None
    for endpoint in selenium_endpoints:
        try:
            print(f"Attempting connection to {endpoint}...")
            driver = webdriver.Remote(
                command_executor=endpoint,
                options=chrome_options
            )
            print(f"Connected to Selenium Grid at {endpoint}")
            break
        except Exception as e:
            print(f"Failed to connect to {endpoint}: {e}")
            continue
    
    if not driver:
        print("Selenium Grid unavailable, using local Chrome driver...")
        chrome_options.add_argument("--headless")
        driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # Navigate to page
        webapp_url = os.getenv('WEBAPP_URL', 'http://webapp:5000')
        driver.get(webapp_url)
        time.sleep(3)  # Wait for page to fully load
        
        print("=== PAGE SOURCE SAMPLE ===")
        page_source = driver.page_source
        # Look for form-control in page source
        if 'form-control' in page_source:
            print("✓ 'form-control' found in page source")
            lines_with_form_control = [line.strip() for line in page_source.split('\n') if 'form-control' in line]
            for line in lines_with_form_control[:5]:
                print(f"  {line[:100]}...")
        else:
            print("✗ 'form-control' NOT found in page source")
        
        print("\n=== ALL INPUT ELEMENTS ===")
        all_inputs = driver.find_elements(By.TAG_NAME, "input")
        print(f"Found {len(all_inputs)} input elements")
        for i, inp in enumerate(all_inputs):
            classes = inp.get_attribute('class')
            visible = inp.is_displayed()
            print(f"  Input {i+1}: type={inp.get_attribute('type')}, class='{classes}', visible={visible}")
        
        print("\n=== ALL SELECT ELEMENTS ===")
        all_selects = driver.find_elements(By.TAG_NAME, "select")
        print(f"Found {len(all_selects)} select elements")
        for i, sel in enumerate(all_selects):
            classes = sel.get_attribute('class')
            visible = sel.is_displayed()
            print(f"  Select {i+1}: class='{classes}', visible={visible}")
        
        print("\n=== ELEMENTS WITH 'form' IN CLASS ===")
        form_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='form']")
        print(f"Found {len(form_elements)} elements with 'form' in class")
        for i, elem in enumerate(form_elements[:10]):
            classes = elem.get_attribute('class')
            visible = elem.is_displayed()
            print(f"  Element {i+1}: {elem.tag_name}, class='{classes}', visible={visible}")
        
        # Activate dark mode and check again
        print("\n=== ACTIVATING DARK MODE ===")
        toggle_button = driver.find_element(By.ID, "darkModeToggle")
        toggle_button.click()
        time.sleep(2)
        
        print("\n=== CHECKING SEARCH INPUT SPECIFICALLY ===")
        try:
            search_input = driver.find_element(By.ID, "searchInput")
            print("✓ Found searchInput element")
            print(f"  Tag: {search_input.tag_name}")
            print(f"  Classes: {search_input.get_attribute('class')}")
            print(f"  Visible: {search_input.is_displayed()}")
            
            # Get computed styles
            styles = driver.execute_script("""
                const elem = arguments[0];
                const computed = window.getComputedStyle(elem);
                return {
                    backgroundColor: computed.backgroundColor,
                    color: computed.color,
                    borderColor: computed.borderColor
                };
            """, search_input)
            print(f"  Computed styles: {styles}")
            
        except Exception as e:
            print(f"✗ Could not find searchInput: {e}")
        
        print("\n=== CHECKING SECTOR FILTER ===")
        try:
            sector_filter = driver.find_element(By.ID, "sectorFilter")
            print("✓ Found sectorFilter element")
            print(f"  Tag: {sector_filter.tag_name}")
            print(f"  Classes: {sector_filter.get_attribute('class')}")
            print(f"  Visible: {sector_filter.is_displayed()}")
            
            styles = driver.execute_script("""
                const elem = arguments[0];
                const computed = window.getComputedStyle(elem);
                return {
                    backgroundColor: computed.backgroundColor,
                    color: computed.color,
                    borderColor: computed.borderColor
                };
            """, sector_filter)
            print(f"  Computed styles: {styles}")
            
        except Exception as e:
            print(f"✗ Could not find sectorFilter: {e}")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    debug_page_content()