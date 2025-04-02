import logging
import sqlite3
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from geopy.geocoders import Nominatim

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TowBookScraper:
    def __init__(self, username, password, database='vehicles.db'):
        self.username = username
        self.password = password
        self.database = database
        self.driver = None
        self.wait = None
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

    def _init_driver(self):
        if self.driver:
            return self.driver
            
        chrome_options = Options()
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--window-size=1920,1080')
        # chrome_options.add_argument('--headless')  # Uncomment for production
        
        try:
            self.driver = webdriver.Chrome(service=Service(), options=chrome_options)
            self.wait = WebDriverWait(self.driver, 30)  # Longer timeout
            logging.info("WebDriver initialized")
            return self.driver
        except Exception as e:
            logging.error(f"Failed to initialize WebDriver: {str(e)}")
            self.progress['error'] = f"Browser initialization failed: {str(e)}"
            raise

    def get_progress(self):
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

    def get_jurisdiction(self, address):
        if not address or address.strip() == "":
            return ""
        try:
            address_clean = address.strip()
            if address_clean in self.geocode_cache:
                return self.geocode_cache[address_clean]
            location = self.geolocator.geocode(f"{address_clean}, Genesee County, MI", exactly_one=True, timeout=5, addressdetails=True)
            if location and 'address' in location.raw:
                addr = location.raw['address']
                if 'Genesee' not in addr.get('county', '').lower():
                    return ""
                jurisdiction = addr.get('township', addr.get('city', addr.get('municipality', '')))
                if jurisdiction:
                    jurisdiction = jurisdiction.replace(" Charter Township", " Township")
                    self.geocode_cache[address_clean] = jurisdiction
                    return jurisdiction
            return ""
        except Exception as e:
            logging.error(f"Geocoding error: {str(e)}")
            return ""

    def login(self):
        try:
            self.progress['status'] = "Logging in to TowBook"
            self._init_driver()
            self.driver.get('https://app.towbook.com/Security/Login.aspx')
            self.wait.until(EC.presence_of_element_located((By.NAME, 'Username'))).send_keys(self.username)
            self.driver.find_element(By.NAME, 'Password').send_keys(self.password)
            self.driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()
            self.wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(text(), 'Reports')]")))
            logging.info("Login successful")
            return True
        except Exception as e:
            logging.error(f"Login failed: {str(e)}")
            self.progress['error'] = f"Login failed: {str(e)}"
            return False

    def navigate_to_call_analysis(self):
        try:
            self.progress['status'] = "Navigating to Reports"
            # Click on Reports
            self.driver.find_element(By.XPATH, "//a[contains(text(), 'Reports')]").click()
            time.sleep(2)  # Wait for menu to load
            
            # Try to handle welcome modal
            try:
                not_now_button = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Not right now')]"))
                )
                not_now_button.click()
                logging.info("Closed welcome dialog")
                time.sleep(1)
            except:
                logging.info("No welcome dialog detected")
            
            self.progress['status'] = "Navigating to Dispatching Reports"
            # Click on Dispatching Reports
            dispatching_link = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//a[contains(text(), 'Dispatching Reports')]")
            ))
            dispatching_link.click()
            time.sleep(2)  # Wait for submenu to load
            
            self.progress['status'] = "Navigating to Call Analysis"
            # Click on Call Analysis
            call_analysis_link = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//a[contains(text(), 'Call Analysis')]")
            ))
            call_analysis_link.click()
            
            # Wait for the page to load
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input.ui-combobox-input")))
            logging.info("Navigated to Call Analysis successfully")
            return True
        except Exception as e:
            logging.error(f"Navigation failed: {str(e)}")
            self.progress['error'] = f"Navigation failed: {str(e)}"
            return False

    def select_ppi_account(self):
        try:
            self.progress['status'] = "Selecting .PPI account"
            # Click the account dropdown
            dropdown = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input.ui-combobox-input")))
            dropdown.click()
            time.sleep(2)  # Wait for dropdown to populate
            
            # Find and click the .PPI checkbox
            ppi_xpath = "//li[contains(@class, 'towbook-combobox-item')]//label[contains(text(), '.PPI')]"
            ppi_label = self.wait.until(EC.element_to_be_clickable((By.XPATH, ppi_xpath)))
            ppi_checkbox = ppi_label.find_element(By.TAG_NAME, 'input')
            if not ppi_checkbox.is_selected():
                ppi_label.click()
                logging.info("Selected .PPI account")
            else:
                logging.info(".PPI account already selected")
            
            # Wait for dropdown to close
            time.sleep(2)
            return True
        except Exception as e:
            logging.error(f"PPI account selection failed: {str(e)}")
            self.progress['error'] = f"PPI account selection failed: {str(e)}"
            return False

    def set_date_range(self, start_date_str, end_date_str):
        try:
            self.progress['status'] = f"Setting date range: {start_date_str} to {end_date_str}"
            # Format dates if they're in ISO format
            if '-' in start_date_str:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                start_date_str = start_date.strftime('%m/%d/%Y')
            if '-' in end_date_str:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                end_date_str = end_date.strftime('%m/%d/%Y')
                
            # Set date range
            start_input = self.driver.find_element(By.ID, "dpStartDate")
            end_input = self.driver.find_element(By.ID, "dpEndDate")
            
            # Clear existing values and set new ones
            start_input.clear()
            start_input.send_keys(start_date_str)
            end_input.clear()
            end_input.send_keys(end_date_str)
            
            logging.info(f"Set date range: {start_date_str} to {end_date_str}")
            return True
        except Exception as e:
            logging.error(f"Date range setting failed: {str(e)}")
            self.progress['error'] = f"Date range setting failed: {str(e)}"
            return False

    def click_update_button(self):
        try:
            self.progress['status'] = "Clicking update button"
            update_button = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//input[@value='Update']")
            ))
            update_button.click()
            
            # Handle possible alert
            try:
                alert = WebDriverWait(self.driver, 5).until(EC.alert_is_present())
                alert_text = alert.text
                logging.info(f"Alert: {alert_text}")
                alert.accept()
                if "didn't return any results" in alert_text:
                    self.progress['error'] = "No results found for date range"
                    return False
            except TimeoutException:
                pass  # No alert is good
            
            # Wait for loading to complete
            try:
                self.wait.until(EC.invisibility_of_element_located((By.CLASS_NAME, "loading-indicator")))
            except:
                pass  # Loading indicator might not be present
                
            time.sleep(3)  # Give additional time for page to update
            logging.info("Clicked update button")
            return True
        except Exception as e:
            logging.error(f"Update button click failed: {str(e)}")
            self.progress['error'] = f"Update button failed: {str(e)}"
            return False

    def get_ppi_data(self):
        try:
            self.progress['status'] = "Finding vehicle entries"
            # Find all call links
            call_links = self.wait.until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "a[id^='callEditorLink_']")
            ))
            
            self.progress['total'] = len(call_links)
            self.progress['processed'] = 0
            
            logging.info(f"Found {self.progress['total']} calls to process")
            
            if self.progress['total'] == 0:
                self.progress['error'] = "No vehicles found in date range"
                return []
            
            vehicles = []
            for index, call_link in enumerate(call_links, 1):
                try:
                    self.progress['status'] = f"Processing vehicle {index}/{self.progress['total']}"
                    call_number = call_link.text.strip()
                    logging.info(f"Processing call {call_number}")
                    
                    # Click to open the modal
                    call_link.click()
                    time.sleep(1)
                    
                    # Wait for modal to open
                    self.wait.until(EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, ".modal-content, div.modal, #callEditor")
                    ))
                    
                    # Extract vehicle data
                    vehicle_data = {
                        'towbook_call_number': call_number,
                        'tow_date': self.get_element_value("#x-impound-date-date"),
                        'tow_time': self.get_element_value("#x-impound-date-time"),
                        'location': self.get_element_value("input#towFrom"),
                        'requestor': 'PROPERTY OWNER',
                        'vin': self.get_element_value("input[id*='vin']"),
                        'year': self.get_select_value("select[id*='year']"),
                        'make': self.get_element_value("input[id*='make']"),
                        'model': self.get_element_value("input[id*='model']"),
                        'color': self.get_select_value("select[id*='color']"),
                        'plate': self.get_element_value("input[id*='plate']"),
                        'state': self.get_select_value("select[id*='state']")
                    }
                    
                    # Determine jurisdiction if location exists
                    if vehicle_data['location']:
                        vehicle_data['jurisdiction'] = self.get_jurisdiction(vehicle_data['location'])
                    
                    # Close the modal
                    cancel_button = self.driver.find_element(By.CSS_SELECTOR, "input[value='Cancel']")
                    cancel_button.click()
                    
                    # Handle possible alert
                    try:
                        alert = WebDriverWait(self.driver, 2).until(EC.alert_is_present())
                        alert.accept()
                    except:
                        pass
                    
                    # Wait for modal to close
                    time.sleep(1)
                    
                    vehicles.append(vehicle_data)
                    self.progress['processed'] = index
                    
                except Exception as e:
                    logging.error(f"Error processing vehicle {index}: {str(e)}")
                    try:
                        # Try to close modal if still open
                        cancel_buttons = self.driver.find_elements(By.CSS_SELECTOR, "input[value='Cancel']")
                        if cancel_buttons:
                            cancel_buttons[0].click()
                            time.sleep(1)
                    except:
                        pass
                    self.progress['processed'] = index
            
            return vehicles
        except Exception as e:
            logging.error(f"Error in get_ppi_data: {str(e)}")
            self.progress['error'] = f"Data extraction failed: {str(e)}"
            return []

    def get_element_value(self, selector):
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, selector)
            return element.get_attribute("value") or ""
        except:
            return ""

    def get_select_value(self, selector):
        try:
            select = self.driver.find_element(By.CSS_SELECTOR, selector)
            selected = select.find_element(By.CSS_SELECTOR, "option:checked")
            return selected.text
        except:
            return ""

    def store_vehicles(self, vehicles):
        try:
            self.progress['status'] = "Storing vehicle data"
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            
            # Create vehicles table if it doesn't exist
            cursor.execute("CREATE TABLE IF NOT EXISTS vehicles (towbook_call_number TEXT PRIMARY KEY)")
            
            # Get existing columns
            cursor.execute("PRAGMA table_info(vehicles)")
            existing_columns = [col[1] for col in cursor.fetchall()]
            
            # Add any missing columns
            for vehicle in vehicles:
                for field in vehicle.keys():
                    if field not in existing_columns:
                        cursor.execute(f"ALTER TABLE vehicles ADD COLUMN {field} TEXT")
                        existing_columns.append(field)
                        logging.info(f"Added column {field}")
            
            # Insert vehicles
            for vehicle in vehicles:
                fields = list(vehicle.keys())
                placeholders = ','.join(['?'] * len(fields))
                values = [vehicle[field] for field in fields]
                
                # Check if this vehicle already exists
                cursor.execute("SELECT COUNT(*) FROM vehicles WHERE towbook_call_number = ?", 
                              (vehicle['towbook_call_number'],))
                exists = cursor.fetchone()[0] > 0
                
                # Set default status for new vehicles
                if 'status' not in vehicle:
                    fields.append('status')
                    placeholders += ',?'
                    values.append('New')
                
                # Set last_updated timestamp
                if 'last_updated' not in fields:
                    fields.append('last_updated')
                    placeholders += ',?'
                    values.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                
                if exists:
                    # Update existing vehicle
                    set_clause = ', '.join([f"{f} = ?" for f in fields])
                    cursor.execute(f"UPDATE vehicles SET {set_clause} WHERE towbook_call_number = ?", 
                                 values + [vehicle['towbook_call_number']])
                else:
                    # Insert new vehicle
                    cursor.execute(f"INSERT INTO vehicles ({','.join(fields)}) VALUES ({placeholders})", values)
            
            conn.commit()
            conn.close()
            logging.info(f"Stored {len(vehicles)} vehicles")
            return True
        except Exception as e:
            logging.error(f"Error storing vehicles: {str(e)}")
            self.progress['error'] = f"Storage failed: {str(e)}"
            return False

    def start_scraping_with_date_range(self, start_date_str, end_date_str):
        self.progress = {
            'percentage': 0,
            'is_running': True,
            'processed': 0,
            'total': 0,
            'status': f"Starting scraping for {start_date_str} to {end_date_str}",
            'error': None
        }
        
        try:
            # Login
            if not self.login():
                raise Exception("Login failed")
            
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