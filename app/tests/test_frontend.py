import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def test_login_page_title(driver, base_url):
    """
    Tests if the login page has the correct title.
    """
    driver.get(f"{base_url}/login")
    assert "Login" in driver.title

def test_successful_login(driver, authenticated_user, base_url):
    """
    Tests the full login flow with valid credentials.
    """
    driver.get(f"{base_url}/login")

    # Find form elements and fill them out
    # Note: You might need to adjust selectors based on your HTML
    driver.find_element(By.NAME, "username").send_keys(authenticated_user['username'])
    driver.find_element(By.NAME, "password").send_keys("securepassword123")
    driver.find_element(By.TAG_NAME, "form").submit()

    # Wait for the page to load and check for a welcome message
    # Using WebDriverWait is a best practice to handle page load times
    welcome_message = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CLASS_NAME, "alert-success"))
    )
    
    assert f'Welcome back, {authenticated_user["username"]}!' in welcome_message.text
    assert "/login" not in driver.current_url # Should be redirected
