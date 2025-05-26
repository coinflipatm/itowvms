#!/usr/bin/env python3
"""
Test Chrome WebDriver initialization with minimal configuration
"""

import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

def test_chrome_minimal():
    """Test Chrome WebDriver with minimal configuration"""
    
    chrome_options = Options()
    
    # Minimal set of options for containers
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-web-security')
    chrome_options.add_argument('--disable-features=VizDisplayCompositor,NetworkService')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.7103.113 Safari/537.36')

    try:
        print("Testing Chrome WebDriver with minimal configuration...")
        
        chromedriver_path = os.path.join(os.path.dirname(__file__), 'chromedriver')
        service = Service(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        print("✓ ChromeDriver initialized successfully!")
        
        # Test navigation
        print("Testing navigation...")
        driver.get("https://httpbin.org/headers")
        print(f"✓ Successfully navigated to: {driver.current_url}")
        
        # Clean up
        driver.quit()
        print("✓ Driver closed successfully")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return False

def test_chrome_medium():
    """Test Chrome WebDriver with medium configuration"""
    
    chrome_options = Options()
    
    # Medium set of options
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-web-security')
    chrome_options.add_argument('--disable-features=VizDisplayCompositor')
    chrome_options.add_argument('--disable-background-timer-throttling')
    chrome_options.add_argument('--disable-renderer-backgrounding')
    chrome_options.add_argument('--disable-backgrounding-occluded-windows')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.7103.113 Safari/537.36')

    try:
        print("Testing Chrome WebDriver with medium configuration...")
        
        chromedriver_path = os.path.join(os.path.dirname(__file__), 'chromedriver')
        service = Service(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        print("✓ ChromeDriver initialized successfully!")
        
        # Test navigation
        print("Testing navigation...")
        driver.get("https://httpbin.org/headers")
        print(f"✓ Successfully navigated to: {driver.current_url}")
        
        # Clean up
        driver.quit()
        print("✓ Driver closed successfully")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing different Chrome configurations...\n")
    
    success_minimal = test_chrome_minimal()
    print()
    
    if success_minimal:
        success_medium = test_chrome_medium()
        print()
        if success_medium:
            print("✓ Both minimal and medium configurations work!")
        else:
            print("✓ Minimal works, medium fails - use minimal config")
    else:
        print("✗ Both configurations failed")
    
    sys.exit(0 if success_minimal else 1)
