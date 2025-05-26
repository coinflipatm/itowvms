import logging
import sqlite3
import time
import glob
import shutil
import json  # Add missing json import
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By  # <-- Ensure By is always imported at the top
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, StaleElementReferenceException,
    ElementClickInterceptedException, ElementNotInteractableException
)
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import re
import os
import uuid
from utils import generate_next_complaint_number # Import the centralized function

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TowBookScraper:
    def __init__(self, username, password, database='vehicles.db', test_mode=False):
        self.username = username
        self.password = password
        self.database = database
        self.test_mode = test_mode  # Add test mode flag
        self.driver = None
        self.wait = None
        self.short_wait = None
        self.geolocator = Nominatim(user_agent="itow_scraper")
        self.geocode_cache = {}
        self.progress = {
            'percentage': 0,
            'is_running': False,
            'processed': 0,
            'total': 0,
            'status': 'Not started',
            'error': None
        }

    def _init_driver(self, headless=True):
        """Initialize the WebDriver with configurable headless option"""
        if self.driver:
            return self.driver

        chrome_options = Options()
        
        # Stable options for containerized environments
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
        # User agent to avoid detection
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.7103.113 Safari/537.36')

        if headless:
            chrome_options.add_argument('--headless=new')  # Use new headless mode

        try:
            # Use the local ChromeDriver
            chromedriver_path = os.path.join(os.path.dirname(__file__), 'chromedriver')
            service = Service(executable_path=chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 30)
            self.short_wait = WebDriverWait(self.driver, 5)
            logging.info(f"WebDriver initialized (headless: {headless})")
            return self.driver
        except Exception as e:
            logging.error(f"Failed to initialize WebDriver: {str(e)}")
            self.progress['error'] = f"Browser initialization failed: {str(e)}"
            raise

    def login(self):
        """Login to TowBook"""
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                self.progress['status'] = f"Logging in to TowBook (attempt {attempt + 1})"
                if not self.driver:
                    self._init_driver()

                # Navigate to login page
                logging.info("Navigating to TowBook login page...")
                self.driver.get('https://app.towbook.com/Security/Login.aspx')
                
                # Wait for page to load
                time.sleep(2)
                
                # Check if login form is present
                try:
                    username_field = self.wait.until(EC.element_to_be_clickable((By.NAME, 'Username')))
                except TimeoutException:
                    logging.warning("Login form not found, trying alternative selectors...")
                    # Try alternative selectors
                    username_field = self.wait.until(EC.element_to_be_clickable((By.ID, 'Username')))
                
                username_field.clear()
                username_field.send_keys(self.username)
                time.sleep(1)

                password_field = self.driver.find_element(By.NAME, 'Password')
                password_field.clear()
                password_field.send_keys(self.password)
                time.sleep(1)

                submit_button = self.driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
                self.robust_click(submit_button)

                # Wait for either successful login or error message
                try:
                    # Check for successful login (Reports link appears)
                    self.wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(text(), 'Reports')]")))
                    logging.info("Login successful")
                    return True
                except TimeoutException:
                    # Check for error messages
                    error_elements = self.driver.find_elements(By.CSS_SELECTOR, ".error, .alert-danger, #ErrorLabel")
                    if error_elements:
                        error_text = error_elements[0].text
                        logging.error(f"Login error: {error_text}")
                        if "invalid" in error_text.lower() or "incorrect" in error_text.lower():
                            self.progress['error'] = f"Invalid credentials: {error_text}"
                            return False
                    
                    # If no specific error, continue to next attempt
                    logging.warning(f"Login attempt {attempt + 1} failed, retrying...")
                    time.sleep(2)
                    
            except Exception as e:
                logging.error(f"Login attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_attempts - 1:
                    self.progress['error'] = f"Login failed: {str(e)}"
                    return False
                time.sleep(2)
        
        logging.error("Login failed after multiple attempts")
        self.progress['error'] = "Login failed after multiple attempts"
        return False

    def navigate_to_call_analysis(self):
        """Navigate to Call Analysis report"""
        try:
            self.progress['status'] = "Navigating to Reports"
            reports_link = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Reports')]")))
            self.robust_click(reports_link)
            time.sleep(2)

            self.progress['status'] = "Navigating to Dispatching Reports"
            dispatching_link = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//a[contains(text(), 'Dispatching Reports')]")
            ))
            self.robust_click(dispatching_link)
            time.sleep(2)

            self.progress['status'] = "Navigating to Call Analysis"
            call_analysis_link = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//a[contains(text(), 'Call Analysis')]")
            ))
            self.robust_click(call_analysis_link)

            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input.ui-combobox-input")))
            logging.info("Navigated to Call Analysis successfully")
            return True
        except Exception as e:
            logging.error(f"Navigation failed: {str(e)}")
            self.progress['error'] = f"Navigation failed: {str(e)}"
            return False

    def select_ppi_account(self):
        """Select PPI account"""
        try:
            self.progress['status'] = "Selecting .PPI account"
            account_dropdown = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input.ui-combobox-input")))
            self.robust_click(account_dropdown)
            time.sleep(2)

            ppi_checkbox_label = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//li[contains(@class, 'towbook-combobox-item')]//label[contains(text(), '.PPI')]")
            ))
            ppi_checkbox = ppi_checkbox_label.find_element(By.TAG_NAME, 'input')

            if not ppi_checkbox.is_selected():
                self.robust_click(ppi_checkbox_label)
                logging.info("Selected .PPI account")
            else:
                logging.info(".PPI account already selected")

            time.sleep(2)
            return True
        except Exception as e:
            logging.error(f"PPI account selection failed: {str(e)}")
            self.progress['error'] = f"PPI account selection failed: {str(e)}"
            return False

    def set_date_range(self, start_date_str, end_date_str):
        """Set date range"""
        try:
            self.progress['status'] = f"Setting date range: {start_date_str} to {end_date_str}"
            if '-' in start_date_str:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                start_date_str = start_date.strftime('%m/%d/%Y')
            if '-' in end_date_str:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                end_date_str = end_date.strftime('%m/%d/%Y')

            self.driver.execute_script(f"document.getElementById('dpStartDate').value = '{start_date_str}';")
            self.driver.execute_script(f"document.getElementById('dpEndDate').value = '{end_date_str}';")

            logging.info(f"Set date range: {start_date_str} to {end_date_str}")
            return True
        except Exception as e:
            logging.error(f"Date range setting failed: {str(e)}")
            self.progress['error'] = f"Date range setting failed: {str(e)}"
            return False

    def get_ppi_data(self):
        try:
            self.progress['status'] = "Finding vehicle entries"
            # Find all call links
            call_links = self.wait.until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "a[id^='callEditorLink_']")
            ))
            
            if not call_links:
                call_links = self.driver.find_elements(By.XPATH, "//td/a[contains(@href, 'CallEditor')]")
            
            self.progress['total'] = len(call_links)
            self.progress['processed'] = 0
            
            logging.info(f"Found {self.progress['total']} calls to process")
            
            if self.progress['total'] == 0:
                self.progress['error'] = "No vehicles found in date range"
                return []
            
            vehicles = []
            for index, call_link in enumerate(call_links, 1):
                try:
                    # Get call number from link text or attribute
                    call_number = call_link.text.strip()
                    if not call_number:
                        # Try to extract from ID
                        call_id = call_link.get_attribute('id')
                        if call_id and 'callEditorLink_' in call_id:
                            call_number = call_id.replace('callEditorLink_', '')
                    
                    self.progress['status'] = f"Processing vehicle {index}/{self.progress['total']} (Call #: {call_number})"
                    logging.info(f"Processing call {index}/{self.progress['total']}: Call #: {call_number}")
                    
                    # Initialize vehicle with call number - using current field mapping
                    vehicle_data = {
                        'towbook_call_number': call_number,
                        'jurisdiction': "", 'tow_date': "", 'tow_time': "", 'location': "",
                        'requestor': "PROPERTY OWNER", 'vin': "", 'year': "", 'make': "", 'model': "", 'color': "",
                        'plate': "", 'state': "", 'status': 'New', 'archived': 0,
                        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    # Try to open the modal
                    try:
                        # Scroll to the link and click it
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", call_link)
                        time.sleep(0.5)
                        self.driver.execute_script("arguments[0].click();", call_link)
                        
                        # Wait for modal to open
                        modal_selectors = [".modal-content", "div.modal", "div[role='dialog']", "#callEditor", "form.edit-form"]
                        modal_opened = False
                        
                        for selector in modal_selectors:
                            try:
                                WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))
                                modal_opened = True
                                logging.info(f"Modal opened with {selector}")
                                break
                            except:
                                continue
                                
                        if not modal_opened:
                            logging.warning(f"Modal not opened for call {call_number}")
                            vehicles.append(vehicle_data)  # Add with basic info
                            self.progress['processed'] = index
                            continue
                            
                    except Exception as click_error:
                        logging.error(f"Error opening modal: {click_error}")
                        vehicles.append(vehicle_data)  # Add with basic info
                        self.progress['processed'] = index
                        continue
                    
                    # Extract date and time data
                    vehicle_data = self.extract_datetime_fields(vehicle_data)
                    
                    # Use the same field selectors from your working code
                    selectors_map = {
                        'location': ["input#towFrom", "input[id*='towFrom']", "input[placeholder*='Address']", "textarea[id*='towFrom']"],
                        'vin': ["input[id*='vin']", "input[placeholder*='VIN']"],
                        'year': ["select[id*='year']", "select.x-vehicle-year"],
                        'make': ["input[placeholder*='make']", "input[id*='make']", "input.x-vehicle-make"],
                        'model': ["input[placeholder*='model']", "input[id*='model']", "input.x-vehicle-model"],
                        'color': ["select[id*='color']", "select.x-vehicle-color"],
                        'plate': ["input.x-license-plate", "input[id*='plate']", "input[placeholder*='plate']"],
                        'state': ["select.x-license-state", "select[id*='state']"]
                    }
                    
                    for field, selectors in selectors_map.items():
                        for selector in selectors:
                            try:
                                value = self.get_select_value_by_css(selector) if field in ['year', 'color', 'state'] else self.get_element_value_by_css(selector)
                                if value:
                                    vehicle_data[field] = value
                                    logging.info(f"Found {field}: {value}")
                                    break
                            except:
                                continue
                    
                    # Determine jurisdiction if location exists
                    if vehicle_data['location']:
                        vehicle_data['jurisdiction'] = self.get_jurisdiction(vehicle_data['location'])
                        
                    # Close the modal
                    self.close_modal_safely()
                    
                    vehicles.append(vehicle_data)
                    self.progress['processed'] = index
                    
                    # Add a delay to avoid overloading TowBook
                    time.sleep(1)
                    
                except Exception as e:
                    logging.error(f"Error processing vehicle {index}: {str(e)}")
                    # Try to recover
                    if self.is_alert_present():
                        self.handle_alert()
                    try:
                        self.close_modal_safely()
                    except:
                        pass
                    self.progress['processed'] = index
                    time.sleep(1)
            
            return vehicles
        except Exception as e:
            logging.error(f"Error in get_ppi_data: {str(e)}")
            self.progress['error'] = f"Data extraction failed: {str(e)}"
            return []

    # Removed _get_initial_complaint_sequence method as it's replaced by utils.generate_next_complaint_number

    def store_vehicles(self, vehicles):
        """Store vehicle data in the database using the current database.py insert_vehicle function"""
        try:
            from database import insert_vehicle
            from utils import generate_next_complaint_number
            
            self.progress['status'] = "Storing vehicle data"
            
            new_count = 0
            updated_count = 0
            skipped_count = 0
            
            for vehicle in vehicles:
                try:
                    call_number = vehicle.get('towbook_call_number')
                    if not call_number:
                        skipped_count += 1
                        continue
                    
                    # Check if vehicle already exists
                    from database import get_vehicle_by_call_number
                    existing_vehicle = get_vehicle_by_call_number(call_number)
                    
                    if existing_vehicle:
                        # For scraped vehicles, always reset to 'New' status since this constitutes a new entry
                        # This ensures freshly scraped vehicles appear in the 'active' tab for management
                        vehicle['status'] = 'New'
                        
                        # Filter out empty values to avoid overwriting existing data
                        update_data = {k: v for k, v in vehicle.items() 
                                     if v is not None and v != '' and v != 'N/A'}
                        
                        from database import update_vehicle
                        success = update_vehicle(call_number, update_data)
                        if success:
                            updated_count += 1
                        else:
                            skipped_count += 1
                    else:
                        # Insert new vehicle - set status to 'New' for freshly scraped vehicles
                        vehicle['status'] = 'New'
                        
                        # Generate complaint number if not provided
                        if 'complaint_number' not in vehicle or not vehicle['complaint_number']:
                            vehicle['complaint_number'] = generate_next_complaint_number()
                        
                        vehicle_id = insert_vehicle(vehicle)
                        if vehicle_id:
                            new_count += 1
                        else:
                            skipped_count += 1
                            
                except Exception as e:
                    logging.error(f"Error storing vehicle {call_number}: {e}")
                    skipped_count += 1
            
            result_msg = f"Added {new_count} new vehicles, updated {updated_count} existing vehicles, skipped {skipped_count}"
            logging.info(result_msg)
            self.progress['status'] = result_msg
            return True
            
        except Exception as e:
            logging.error(f"Error storing vehicles: {e}")
            self.progress['error'] = f"Storage failed: {str(e)}"
            return False

    def start_scraping_with_date_range(self, start_date_str, end_date_str, headless=True):
        self.progress = {
            'percentage': 0,
            'is_running': True,
            'processed': 0,
            'total': 0,
            'status': f"Starting scraping for {start_date_str} to {end_date_str}",
            'error': None
        }

        try:
            # Initialize driver with headless option
            self._init_driver(headless)

            # Login - retry up to 3 times
            login_attempts = 0
            login_success = False

            while login_attempts < 3 and not login_success:
                login_success = self.login()
                if not login_success:
                    login_attempts += 1
                    time.sleep(2)  # Wait before retrying

            if not login_success:
                raise Exception("Login failed after multiple attempts")

            # Navigate to Call Analysis
            if not self.navigate_to_call_analysis():
                raise Exception("Failed to navigate to Call Analysis")

            # Select PPI account
            if not self.select_ppi_account():
                raise Exception("Failed to select PPI account")

            # Set date range
            if not self.set_date_range(start_date_str, end_date_str):
                raise Exception("Failed to set date range")

            # Click update
            if not self.click_update_button():
                raise Exception("Failed to click update button")

            # Get vehicle data
            vehicles = self.get_ppi_data()

            # Store vehicles
            if vehicles:
                if not self.store_vehicles(vehicles):
                    raise Exception("Failed to store vehicles")
                self.progress['status'] = f"Completed: Processed {len(vehicles)} vehicles"
            else:
                self.progress['status'] = "No vehicles found in date range"

        except Exception as e:
            logging.error(f"Scraping failed: {str(e)}")
            self.progress['error'] = str(e)
        finally:
            self.progress['is_running'] = False
            if self.driver:
                self.driver.quit()
                self.driver = None

    def get_progress(self):
        if not self.progress['is_running']:
            return {
                "percentage": 0,
                "is_running": False,
                "processed": 0,
                "total": 0,
                "status": "Not currently scraping.",
                "error": None
            }

        if self.progress['total'] == 0:
            percentage = 0
        else:
            percentage = min(100, int((self.progress['processed'] / self.progress['total']) * 100))

        return {
            "percentage": percentage,
            "is_running": self.progress['is_running'],
            "processed": self.progress['processed'],
            "total": self.progress['total'],
            "status": self.progress['status'],
            "error": self.progress['error']
        }

    def robust_click(self, element, retries=3, delay=1):
        """Click an element with retries for common issues"""
        for attempt in range(retries):
            try:
                element.click()
                return True
            except (ElementClickInterceptedException, ElementNotInteractableException, StaleElementReferenceException) as e:
                logging.warning(f"Click failed: {str(e)}, retrying in {delay}s (Attempt {attempt + 1})")
                time.sleep(delay)

        # If all attempts failed, try JavaScript click
        try:
            self.driver.execute_script("arguments[0].click();", element)
            return True
        except Exception as e:
            logging.error(f"JavaScript click failed: {str(e)}")
            return False

    def click_update_button(self):
        """Click the update button on the Call Analysis page"""
        try:
            self.progress['status'] = "Clicking update button"
            update_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@value='Update']")))
            self.driver.execute_script("arguments[0].scrollIntoView(true); arguments[0].click();", update_button)

            # Handle potential alert
            try:
                alert = self.short_wait.until(EC.alert_is_present())
                alert_text = alert.text
                logging.info(f"Alert detected: {alert_text}")
                alert.accept()
                if "didn't return any results" in alert_text:
                    self.progress['error'] = "No results found for the selected date range"
                    return False
            except TimeoutException:
                pass  # No alert is good

            # Wait for loading to complete
            try:
                self.wait.until(EC.invisibility_of_element_located((By.CLASS_NAME, "loading-indicator")))
            except:
                pass  # Loading indicator might not be present

            time.sleep(5)  # Additional wait for page updates
            logging.info("Clicked update button successfully")
            return True
        except Exception as e:
            logging.error(f"Failed to click update button: {str(e)}")
            self.progress['error'] = f"Update button click failed: {str(e)}"
            return False

    def extract_datetime_fields(self, vehicle_data):
        """Extract date and time with multiple fallback methods"""
        # Define various selectors for different field types
        date_selectors = ["input#x-impound-date-date", "input[id*='impound'][id*='date']", "input.datepicker", "input[name*='date']", "#serviceDate"]
        time_selectors = ["input#x-impound-date-time", "input[id*='impound'][id*='time']", "input.timepicker", "input[name*='time']", "#serviceTime"]
        po_selectors = ["input#poNumber", "input[id*='poNumber']", "input[name*='poNumber']", "input[placeholder*='PO']", "input[placeholder*='po']"]

        # Get tow date
        date_value = ""
        for selector in date_selectors:
            date_value = self.get_element_value_by_css(selector)
            if date_value:
                logging.info(f"Found date: {date_value} with {selector}")
                break

        # Get tow time - improved to ensure we get this value
        time_value = ""
        for selector in time_selectors:
            time_value = self.get_element_value_by_css(selector)
            if time_value:
                logging.info(f"Found time: {time_value} with {selector}")
                break
        
        # Try additional time selectors if not found
        if not time_value:
            # Try JavaScript approach to find time input
            try:
                time_value = self.driver.execute_script("""
                    return Array.from(document.querySelectorAll('input')).find(i => 
                        (i.placeholder && i.placeholder.toLowerCase().includes('time')) || 
                        (i.id && i.id.toLowerCase().includes('time')) ||
                        (i.name && i.name.toLowerCase().includes('time'))
                    )?.value || '';
                """)
                if time_value:
                    logging.info(f"Found time using JavaScript: {time_value}")
            except Exception as e:
                logging.warning(f"JavaScript time extraction error: {e}")
        
        # If still no time value, use current time as fallback
        if not time_value:
            time_value = datetime.now().strftime('%H:%M')
            logging.info(f"Using current time as fallback: {time_value}")
        
        # Get PO number for complaint number
        po_value = ""
        for selector in po_selectors:
            po_value = self.get_element_value_by_css(selector)
            if po_value:
                logging.info(f"Found PO#: {po_value} with {selector}")
                break
        
        # Try additional PO selectors if not found
        if not po_value:
            try:
                # Try JavaScript approach to find PO input
                po_value = self.driver.execute_script("""
                    return Array.from(document.querySelectorAll('input')).find(i => 
                        (i.placeholder && i.placeholder.toLowerCase().includes('po')) || 
                        (i.id && i.id.toLowerCase().includes('po')) ||
                        (i.name && i.name.toLowerCase().includes('po'))
                    )?.value || '';
                """)
                if po_value:
                    logging.info(f"Found PO# using JavaScript: {po_value}")
                    
                # If still not found, try to look for a field with 'reference' or 'ref' in its attributes
                if not po_value:
                    po_value = self.driver.execute_script("""
                        return Array.from(document.querySelectorAll('input')).find(i => 
                            (i.placeholder && (i.placeholder.toLowerCase().includes('reference') || i.placeholder.toLowerCase().includes('ref'))) || 
                            (i.id && (i.id.toLowerCase().includes('reference') || i.id.toLowerCase().includes('ref'))) ||
                            (i.name && (i.name.toLowerCase().includes('reference') || i.name.toLowerCase().includes('ref')))
                        )?.value || '';
                    """)
                    if po_value:
                        logging.info(f"Found PO# as reference number using JavaScript: {po_value}")
            except Exception as e:
                logging.warning(f"JavaScript PO extraction error: {e}")

        # Update vehicle data
        if date_value:
            vehicle_data['tow_date'] = date_value
            
            # Format the date properly if found
            try:
                if '/' in date_value:
                    # MM/DD/YYYY format
                    tow_date = datetime.strptime(date_value, '%m/%d/%Y')
                    vehicle_data['tow_date'] = tow_date.strftime('%Y-%m-%d')
                else:
                    # Try another common format
                    tow_date = datetime.strptime(date_value, '%Y-%m-%d')
                    # Already in the right format
            except Exception as e:
                logging.warning(f"Date format conversion error: {e}")
                # If we can't parse it, leave it as is
                
        if time_value:
            vehicle_data['tow_time'] = time_value
        
        if po_value:
            vehicle_data['complaint_number'] = po_value
        
        return vehicle_data

    def get_element_value_by_css(self, css_selector):
        """Get the value of an input/textarea element using a CSS selector"""
        try:
            element = self.short_wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, css_selector)))
            # Try getting 'value' attribute using JavaScript first, then Selenium's get_attribute
            value = self.driver.execute_script("return arguments[0].value;", element)
            if value is None: # If JS returns null, try Selenium's method
                 value = element.get_attribute("value")
            return value.strip() if value else ""
        except (TimeoutException, NoSuchElementException):
            logging.debug(f"Element not found for selector {css_selector}")
            return ""
        except Exception as e:
            logging.debug(f"Failed to get value for selector {css_selector}: {str(e)}")
            return ""

    def get_select_value_by_css(self, css_selector):
        """Get selected option text"""
        try:
            select = WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.CSS_SELECTOR, css_selector)))
            value = self.driver.execute_script("return arguments[0].options[arguments[0].selectedIndex]?.text || '';", select)
            value = value.strip() # Strip the value first
            if value == "0":      # If the stripped value is "0"
                return ""         # Return empty string (meaning not found or not specified)
            return value          # Otherwise, return the stripped value
        except:
            return ""

    def get_element_text_by_css(self, css_selector):
        """Get the text content of an element using a CSS selector"""
        try:
            element = self.short_wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, css_selector)))
            # Use textContent for potentially hidden elements, fallback to .text
            text = element.get_attribute("textContent") or element.text
            return text.strip() if text else ""
        except (TimeoutException, NoSuchElementException):
            logging.debug(f"Element not found for selector {css_selector}")
            return ""
        except Exception as e:
            logging.debug(f"Failed to get text for selector {css_selector}: {str(e)}")
            return ""

    def close_modal_safely(self):
        """Reliably close the modal with proper alert handling"""
        try:
            logging.info("Attempting to close modal safely")
            
            # Look for cancel button and click it
            close_selectors = [
                "input.standard-button[value='Cancel']",
                "button.close", 
                ".modal-header .close",
                "button[aria-label='Close']",
                "a.modal-close",
                ".modal-footer button:not(.btn-primary)"
            ]
            
            # Try each selector
            button_clicked = False
            for selector in close_selectors:
                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if buttons:
                        self.driver.execute_script("arguments[0].click();", buttons[0])
                        button_clicked = True
                        logging.info(f"Modal close button clicked using selector: {selector}")
                        break  # Found and clicked a button, stop trying other selectors
                except:
                    continue
            
            # If no close button was clicked, try JavaScript approach
            if not button_clicked:
                self.driver.execute_script("""
                    var modalElements = document.querySelectorAll('.modal, .modal-backdrop, [role="dialog"]');
                    modalElements.forEach(function(el) { if(el.parentNode) el.parentNode.removeChild(el); });
                    document.body.classList.remove('modal-open');
                """)
                logging.info("Modal removed via JavaScript")
            
            # Handle the "abandon changes" alert if it appears
            try:
                WebDriverWait(self.driver, 3).until(EC.alert_is_present())
                alert = self.driver.switch_to.alert
                alert_text = alert.text
                logging.info(f"Found alert after closing modal: {alert_text}")
                alert.accept()
                logging.info("Accepted alert")
            except:
                pass
            
            # Add a delay to ensure everything settles
            time.sleep(1.5)
            
            # Double-check for any lingering alerts
            if self.is_alert_present():
                self.driver.switch_to.alert.accept()
                time.sleep(0.5)
                
            return True
        except Exception as e:
            logging.error(f"Error in close_modal_safely: {e}")
            
            # Final safety check for alerts
            try:
                if self.is_alert_present():
                    self.driver.switch_to.alert.accept()
            except:
                pass
                
            return False

    def get_jurisdiction(self, address):
        """Determine jurisdiction based on address"""
        if not address or not isinstance(address, str) or address.strip() == "" or address.strip().lower() == 'n/a':
            logging.debug("Address is empty or invalid, cannot determine jurisdiction.")
            return ""
        try:
            # Basic cleaning: remove content in parentheses, strip whitespace
            address_clean = re.sub(r'\s*\(.*\)', '', address).strip()
            if not address_clean:
                 logging.debug("Cleaned address is empty.")
                 return ""

            # Check cache first
            if address_clean in self.geocode_cache:
                logging.debug(f"Using cached jurisdiction for '{address_clean}': {self.geocode_cache[address_clean]}")
                return self.geocode_cache[address_clean]

            logging.info(f"Geocoding address: '{address_clean}, Genesee County, MI'")
            # Geocode with timeout and address details
            location = self.geolocator.geocode(f"{address_clean}, Genesee County, MI", exactly_one=True, timeout=10, addressdetails=True) # Increased timeout

            if location and location.raw and 'address' in location.raw:
                addr = location.raw['address']
                logging.debug(f"Geocoding result address details: {addr}")

                # Check if it's in Genesee County (case-insensitive)
                county = addr.get('county', '')
                if not county or 'genesee county' not in county.lower():
                    logging.warning(f"Address '{address_clean}' resolved outside Genesee County: {county}. Setting jurisdiction empty.")
                    self.geocode_cache[address_clean] = "" # Cache empty result for non-Genesee
                    return ""

                # Prioritize township, then city, then municipality
                jurisdiction = addr.get('township', addr.get('city', addr.get('municipality', '')))

                if jurisdiction:
                    # Standardize "Charter Township" to "Township"
                    jurisdiction = jurisdiction.replace(" Charter Township", " Township")
                    logging.info(f"Determined jurisdiction: {jurisdiction}")
                    self.geocode_cache[address_clean] = jurisdiction # Cache successful result
                    return jurisdiction
                else:
                    logging.warning(f"Could not determine specific jurisdiction (township/city) within Genesee County for '{address_clean}'. Address details: {addr}")
                    self.geocode_cache[address_clean] = "" # Cache empty result if no specific jurisdiction found
                    return ""
            else:
                logging.warning(f"Geocoding failed or returned no address details for '{address_clean}'.")
                self.geocode_cache[address_clean] = "" # Cache failure
                return ""
        except GeocoderTimedOut:
             logging.error(f"Geocoding timed out for address: '{address_clean}'")
             # Don't cache timeouts, maybe it works next time
             return ""
        except Exception as e:
            logging.error(f"Geocoding error for address '{address_clean}': {str(e)}")
            self.geocode_cache[address_clean] = "" # Cache other errors
            return ""

    def scrape_data(self, start_date, end_date):
        """Main scraping method called by API routes - wrapper for start_scraping_with_date_range"""
        try:
            if self.test_mode:
                return self._run_test_mode(start_date, end_date)
            
            self.start_scraping_with_date_range(start_date, end_date, headless=True)
            
            # Check if scraping completed successfully
            if self.progress['error']:
                return False, self.progress['error']
            elif self.progress['status'] and 'Completed' in self.progress['status']:
                return True, self.progress['status']
            else:
                return False, "Scraping completed but with unknown status"
                
        except Exception as e:
            logging.error(f"Error in scrape_data: {str(e)}")
            return False, f"Scraping failed: {str(e)}"
    
    def _run_test_mode(self, start_date, end_date):
        """Run scraper in test mode with simulated data"""
        logging.info("Running scraper in test mode...")
        
        self.progress['is_running'] = True
        self.progress['status'] = "Running in test mode"
        self.progress['total'] = 5
        
        # Import database functions
        from database import insert_vehicle, get_vehicle_by_call_number, update_vehicle
        
        # Create test vehicles
        test_vehicles = [
            {
                'towbook_call_number': 'TEST001',
                'jurisdiction': 'Burton',
                'tow_date': '2024-01-15',
                'tow_time': '14:30',
                'location': '123 Test Street',
                'requestor': 'PROPERTY OWNER',
                'vin': 'TEST1234567890001',
                'year': '2020',  # Use correct database field name
                'make': 'Honda',
                'model': 'Civic',
                'color': 'Blue',
                'plate': 'TEST123',
                'state': 'MI',
                'status': 'New',
                'archived': 0,
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            {
                'towbook_call_number': 'TEST002',
                'jurisdiction': 'Flint',
                'tow_date': '2024-01-16',
                'tow_time': '09:15',
                'location': '456 Demo Avenue',
                'requestor': 'POLICE',
                'vin': 'TEST1234567890002',
                'year': '2019',  # Use correct database field name
                'make': 'Toyota',
                'model': 'Camry',
                'color': 'Red',
                'plate': 'TEST456',
                'state': 'MI',
                'status': 'New',
                'archived': 0,
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        ]
        
        # Process test vehicles
        for i, vehicle in enumerate(test_vehicles):
            self.progress['processed'] = i + 1
            self.progress['percentage'] = int((i + 1) / len(test_vehicles) * 100)
            self.progress['status'] = f"Processing test vehicle {i + 1} of {len(test_vehicles)}"
            
            # Check for existing vehicle
            existing = get_vehicle_by_call_number(vehicle['towbook_call_number'])
            if existing:
                # Preserve original status unless it's archived
                if existing.get('archived', 0) == 0:
                    vehicle['status'] = existing.get('status', 'New')
                    vehicle['complaint_number'] = existing.get('complaint_number', '')
                
                update_vehicle(vehicle['towbook_call_number'], vehicle)
                logging.info(f"Updated test vehicle: {vehicle['towbook_call_number']}")
            else:
                # Generate complaint number for new vehicles
                vehicle['complaint_number'] = generate_next_complaint_number()
                insert_vehicle(vehicle)
                logging.info(f"Inserted test vehicle: {vehicle['towbook_call_number']}")
            
            time.sleep(0.5)  # Simulate processing time
        
        self.progress['is_running'] = False
        self.progress['status'] = "Test mode completed"
        self.progress['percentage'] = 100
        
        logging.info("Test mode completed successfully")
        return True, "Test mode completed successfully"
    
    def is_running(self):
        """Check if scraper is currently running"""
        return self.progress.get('is_running', False)
    
    def is_alert_present(self):
        """Check if an alert is present"""
        try:
            self.driver.switch_to.alert
            return True
        except:
            return False
    
    def handle_alert(self):
        """Handle any present alert"""
        try:
            if self.is_alert_present():
                alert = self.driver.switch_to.alert
                alert_text = alert.text
                logging.info(f"Handling alert: {alert_text}")
                alert.accept()
                return True
        except Exception as e:
            logging.warning(f"Error handling alert: {e}")
        return False