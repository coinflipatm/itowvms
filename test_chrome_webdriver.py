#!/usr/bin/env python3
"""
Test Chrome WebDriver initialization with our configuration
"""

import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

def test_chrome_webdriver():
    """Test Chrome WebDriver initialization"""
    
    chrome_options = Options()
    
    # Essential options for containerized environments
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-background-timer-throttling')
    chrome_options.add_argument('--disable-renderer-backgrounding')
    chrome_options.add_argument('--disable-backgrounding-occluded-windows')
    chrome_options.add_argument('--disable-ipc-flooding-protection')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--remote-debugging-port=9222')
    chrome_options.add_argument('--disable-web-security')
    chrome_options.add_argument('--disable-features=VizDisplayCompositor')
    chrome_options.add_argument('--single-process')
    chrome_options.add_argument('--no-zygote')
    chrome_options.add_argument('--disable-setuid-sandbox')
    chrome_options.add_argument('--disable-software-rasterizer')
    chrome_options.add_argument('--disable-background-networking')
    chrome_options.add_argument('--disable-default-apps')
    chrome_options.add_argument('--disable-sync')
    chrome_options.add_argument('--disable-logging')
    chrome_options.add_argument('--disable-in-process-stack-traces')
    chrome_options.add_argument('--disable-crash-reporter')
    chrome_options.add_argument('--disable-component-update')
    chrome_options.add_argument('--memory-pressure-off')
    chrome_options.add_argument('--max_old_space_size=4096')
    chrome_options.add_argument('--headless=new')
    
    # User agent
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.7103.113 Safari/537.36')

    try:
        print("Testing Chrome WebDriver initialization...")
        
        # Use the local ChromeDriver
        chromedriver_path = os.path.join(os.path.dirname(__file__), 'chromedriver')
        print(f"Using ChromeDriver at: {chromedriver_path}")
        
        if not os.path.exists(chromedriver_path):
            print(f"ERROR: ChromeDriver not found at {chromedriver_path}")
            return False
            
        service = Service(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        print("✓ ChromeDriver initialized successfully!")
        
        # Test navigation to a simple page
        print("Testing navigation to Google...")
        driver.get("https://www.google.com")
        print(f"✓ Successfully navigated to: {driver.current_url}")
        print(f"✓ Page title: {driver.title}")
        
        # Clean up
        driver.quit()
        print("✓ Driver closed successfully")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_chrome_webdriver()
    sys.exit(0 if success else 1)
