#!/usr/bin/env python3
"""
Debug script to understand form control styling issues
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

def debug_form_controls():
    # Setup driver
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Remote(
        command_executor='http://stockdev-selenium-chrome-1:4444/wd/hub',
        options=chrome_options
    )
    
    try:
        # Navigate to page
        driver.get("http://172.17.0.1:5000")
        time.sleep(2)
        
        # Activate dark mode
        toggle_button = driver.find_element(By.ID, "darkModeToggle")
        toggle_button.click()
        time.sleep(1)
        
        # Get CSS variables
        print("=== CSS Variables ===")
        html_element = driver.find_element(By.TAG_NAME, "html")
        theme = html_element.get_attribute("data-theme")
        print(f"Theme: {theme}")
        
        # Check CSS variables on root
        root_vars = driver.execute_script("""
            const root = document.documentElement;
            const styles = window.getComputedStyle(root);
            return {
                'light-bg': styles.getPropertyValue('--light-bg').trim(),
                'light-text': styles.getPropertyValue('--light-text').trim(),
                'light-border': styles.getPropertyValue('--light-border').trim(),
                'light-card-bg': styles.getPropertyValue('--light-card-bg').trim()
            };
        """)
        print("Root CSS Variables:", root_vars)
        
        # Find form controls and debug
        form_controls = driver.find_elements(By.CSS_SELECTOR, ".form-control, .form-select")
        print(f"\n=== Found {len(form_controls)} form controls ===")
        
        for i, control in enumerate(form_controls[:3]):  # Check first 3
            print(f"\nForm Control {i+1}:")
            print(f"  Tag: {control.tag_name}")
            print(f"  Classes: {control.get_attribute('class')}")
            
            # Get computed styles
            styles = driver.execute_script("""
                const elem = arguments[0];
                const computed = window.getComputedStyle(elem);
                return {
                    backgroundColor: computed.backgroundColor,
                    color: computed.color,
                    borderColor: computed.borderColor,
                    border: computed.border
                };
            """, control)
            
            print(f"  Computed Styles: {styles}")
            
            # Check if CSS rules are applied
            css_rules = driver.execute_script("""
                const elem = arguments[0];
                const sheets = Array.from(document.styleSheets);
                let rules = [];
                
                try {
                    for (let sheet of sheets) {
                        try {
                            for (let rule of sheet.cssRules || sheet.rules) {
                                if (rule.selectorText && rule.selectorText.includes('form-control')) {
                                    rules.push({
                                        selector: rule.selectorText,
                                        background: rule.style.backgroundColor,
                                        color: rule.style.color,
                                        border: rule.style.borderColor
                                    });
                                }
                            }
                        } catch (e) {
                            // Cross-origin or other access issues
                        }
                    }
                } catch (e) {
                    console.log('Error accessing stylesheets:', e);
                }
                
                return rules;
            """, control)
            
            print(f"  Matching CSS Rules: {css_rules}")
        
        # Test applying styles directly
        print("\n=== Testing Direct Style Application ===")
        if form_controls:
            test_control = form_controls[0]
            
            # Apply dark mode styles directly
            driver.execute_script("""
                const elem = arguments[0];
                elem.style.backgroundColor = '#343a40';
                elem.style.color = '#ffffff';
                elem.style.borderColor = '#495057';
            """, test_control)
            
            time.sleep(1)
            
            # Check if direct styles worked
            new_styles = driver.execute_script("""
                const elem = arguments[0];
                const computed = window.getComputedStyle(elem);
                return {
                    backgroundColor: computed.backgroundColor,
                    color: computed.color,
                    borderColor: computed.borderColor
                };
            """, test_control)
            
            print(f"After direct application: {new_styles}")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    debug_form_controls()