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
    def __init__(self, username, password, database='vehicles.db'):
        self.username = username
        self.password = password
        self.database = database
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
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-dev-shm-usage')  # Prevent crashes in low-memory environments

        if headless:
            chrome_options.add_argument('--headless')

        try:
            self.driver = webdriver.Chrome(service=Service(), options=chrome_options)
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
        try:
            self.progress['status'] = "Logging in to TowBook"
            if not self.driver:
                self._init_driver()

            self.driver.get('https://app.towbook.com/Security/Login.aspx')

            username_field = self.wait.until(EC.element_to_be_clickable((By.NAME, 'Username')))
            username_field.clear()
            username_field.send_keys(self.username)
            time.sleep(1)

            password_field = self.driver.find_element(By.NAME, 'Password')
            password_field.clear()
            password_field.send_keys(self.password)
            time.sleep(1)

            submit_button = self.driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
            self.robust_click(submit_button)

            self.wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(text(), 'Reports')]")))
            logging.info("Login successful")
            return True
        except Exception as e:
            logging.error(f"Login failed: {str(e)}")
            self.progress['error'] = f"Login failed: {str(e)}"
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
                    
                    # Initialize vehicle with call number 
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
        """Store vehicle data in the database"""
        try:
            self.progress['status'] = "Storing vehicle data"
            conn = sqlite3.connect(self.database)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Create vehicles table if it doesn't exist
            cursor.execute("CREATE TABLE IF NOT EXISTS vehicles (towbook_call_number TEXT PRIMARY KEY)")
            
            # Get existing columns
            cursor.execute("PRAGMA table_info(vehicles)")
            existing_columns = [col[1] for col in cursor.fetchall()]
            
            # Add 'complaint_number', 'complaint_sequence', 'complaint_year' if they don't exist
            # These should exist based on the database schema, but this is a safeguard.
            complaint_cols = [
                ('complaint_number', 'TEXT'),
                ('complaint_sequence', 'INTEGER'),
                ('complaint_year', 'TEXT')
            ]
            for col_name, col_type in complaint_cols:
                if col_name not in existing_columns:
                    cursor.execute(f"ALTER TABLE vehicles ADD COLUMN {col_name} {col_type}")
                    existing_columns.append(col_name)
                    logging.info(f"Added column {col_name}")

            required_columns = [
                ('status', 'TEXT'),
                ('archived', 'INTEGER'),
                ('last_updated', 'TEXT'),
                ('top_form_sent_date', 'TEXT'),
                ('tr52_available_date', 'TEXT'),
                ('days_until_next_step', 'INTEGER'),
                ('days_until_auction', 'INTEGER'),
                ('auction_date', 'TEXT'),
                ('release_date', 'TEXT'),
                ('release_time', 'TEXT'),
                ('release_reason', 'TEXT'),
                ('decision', 'TEXT'),
                ('decision_date', 'TEXT'),
                ('estimated_date', 'TEXT'),
                ('vin', 'TEXT'),
                ('make', 'TEXT'),
                ('model', 'TEXT'),
                ('year', 'TEXT'),
                ('color', 'TEXT'),
                ('jurisdiction', 'TEXT'),
                ('location', 'TEXT'),
                ('plate', 'TEXT'),
                ('tow_date', 'TEXT'),
                ('tow_time', 'TEXT')
                # complaint_number is handled above or assumed to exist
            ]
            
            for col_name, col_type in required_columns:
                if col_name not in existing_columns:
                    cursor.execute(f"ALTER TABLE vehicles ADD COLUMN {col_name} {col_type}")
                    existing_columns.append(col_name)
                    logging.info(f"Added column {col_name}")
            
            # Check for any other columns from vehicle data
            for vehicle in vehicles:
                for field in vehicle.keys():
                    if field not in existing_columns:
                        cursor.execute(f"ALTER TABLE vehicles ADD COLUMN {field} TEXT")
                        existing_columns.append(field)
                        logging.info(f"Added dynamic column {field}")

            # Get existing vehicles to check for duplicates
            cursor.execute("SELECT towbook_call_number, status FROM vehicles")
            existing_vehicles = {row[0]: row[1] for row in cursor.fetchall()}
            
            new_count = 0
            updated_count = 0
            skipped_count = 0

            # Insert vehicles
            for vehicle in vehicles:
                # Generate and assign the ITXXXX-YY complaint number using the utility function
                # The utility function now directly queries the database, so no need to pass cursor or year
                complaint_full_number, complaint_seq, complaint_yr = generate_next_complaint_number(db_path=self.database)
                vehicle['complaint_number'] = complaint_full_number
                vehicle['complaint_sequence'] = complaint_seq
                vehicle['complaint_year'] = complaint_yr

                call_number = vehicle['towbook_call_number']
                if call_number:
                    fields = list(vehicle.keys())
                    placeholders = ','.join(['?'] * len(fields))
                    values = [vehicle[field] for field in fields]
                    
                    # Check if this vehicle already exists and has a non-New status
                    exists = call_number in existing_vehicles
                    existing_status = existing_vehicles.get(call_number, '')
                    
                    # Don't change the status if it's already been processed
                    if exists and existing_status and existing_status != 'New':
                        # Skip updating the status
                        if 'status' in fields:
                            status_index = fields.index('status')
                            values[status_index] = existing_status
                    
                    if exists:
                        # Update existing vehicle - only update non-null values
                        non_null_fields = []
                        non_null_values = []
                        
                        for i, field in enumerate(fields):
                            # Skip status field if already set to something other than New
                            if field == 'status' and existing_status and existing_status != 'New':
                                continue
                                
                            # Only update non-empty values
                            if values[i] is not None and values[i] != '':
                                non_null_fields.append(field)
                                non_null_values.append(values[i])
                        
                        if non_null_fields:
                            set_clause = ', '.join([f"{f} = ?" for f in non_null_fields])
                            cursor.execute(f"UPDATE vehicles SET {set_clause} WHERE towbook_call_number = ?", 
                                        non_null_values + [call_number])
                            updated_count += 1
                        else:
                            skipped_count += 1
                    else:
                        # Insert new vehicle
                        cursor.execute(f"INSERT INTO vehicles ({','.join(fields)}) VALUES ({placeholders})", values)
                        new_count += 1
                else:
                    skipped_count += 1
            
            conn.commit()
            conn.close()
            
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