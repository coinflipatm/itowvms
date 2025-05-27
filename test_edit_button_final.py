#!/usr/bin/env python3
"""
Final test to verify edit button functionality
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import sys

def test_edit_button():
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--remote-debugging-port=9222')
    
    driver = None
    try:
        # Initialize the driver
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_window_size(1920, 1080)
        
        print("🧪 Testing Edit Button Functionality")
        print("=" * 50)
        
        # Load the page
        print("1. Loading application...")
        driver.get("http://localhost:5001")
        
        # Wait for the page to load completely
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "vehicleTableBody"))
        )
        print("✅ Application loaded successfully")
        
        # Wait for vehicles to load
        time.sleep(3)
        
        # Find the first edit button
        print("2. Looking for edit buttons...")
        edit_buttons = driver.find_elements(By.CSS_SELECTOR, "button[onclick*='openEditVehicleModal']")
        
        if not edit_buttons:
            print("❌ No edit buttons found")
            return False
            
        print(f"✅ Found {len(edit_buttons)} edit button(s)")
        
        # Get the first edit button and extract the call number
        first_edit_button = edit_buttons[0]
        onclick_attr = first_edit_button.get_attribute('onclick')
        print(f"3. First edit button onclick: {onclick_attr}")
        
        # Check for JavaScript errors before clicking
        logs = driver.get_log('browser')
        console_errors = [log for log in logs if log['level'] == 'SEVERE']
        if console_errors:
            print(f"⚠️  JavaScript errors before clicking:")
            for error in console_errors:
                print(f"   {error['message']}")
        else:
            print("✅ No JavaScript errors before clicking")
        
        # Click the edit button
        print("4. Clicking edit button...")
        driver.execute_script("arguments[0].click();", first_edit_button)
        
        # Wait a moment for the modal to appear
        time.sleep(2)
        
        # Check for JavaScript errors after clicking
        logs = driver.get_log('browser')
        new_console_errors = [log for log in logs if log['level'] == 'SEVERE']
        if len(new_console_errors) > len(console_errors):
            print(f"❌ New JavaScript errors after clicking:")
            for error in new_console_errors[len(console_errors):]:
                print(f"   {error['message']}")
            return False
        else:
            print("✅ No new JavaScript errors after clicking")
        
        # Check if edit modal appeared
        try:
            edit_modal = WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.ID, "editVehicleModal"))
            )
            print("✅ Edit modal opened successfully!")
            
            # Check if form fields are populated
            vin_field = driver.find_element(By.ID, "edit-vin")
            if vin_field.get_attribute('value'):
                print("✅ Form fields are populated with vehicle data")
            else:
                print("⚠️  Form fields appear empty")
            
            return True
            
        except Exception as e:
            print(f"❌ Edit modal did not appear: {str(e)}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        return False
        
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    success = test_edit_button()
    print("\n" + "=" * 50)
    if success:
        print("🎉 EDIT BUTTON TEST PASSED!")
        print("✅ Edit button opens modal without JavaScript errors")
        sys.exit(0)
    else:
        print("❌ EDIT BUTTON TEST FAILED!")
        sys.exit(1)
