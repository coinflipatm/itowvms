#scraper.py

import logging
import sqlite3
import csv
import time
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.alert import Alert
from selenium.common.exceptions import (
    UnexpectedAlertPresentException, NoAlertPresentException, TimeoutException,
    ElementClickInterceptedException, ElementNotInteractableException, NoSuchElementException,
    StaleElementReferenceException
)
from geopy.geocoders import Nominatim

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TowBookScraper:
    def __init__(self, username, password, database='vehicles.db', csv_file='vehicles.csv'):
        self.username = username
        self.password = password
        self.database = database
        self.csv_file = csv_file
        self.driver = None
        self.wait = None
        self.geolocator = Nominatim(user_agent="ppi_scraper")
        self.geocode_cache = {}
        
        # Progress tracking
        self.total_entries = 0
        self.processed_entries = 0
        self.current_status = "Not started"
        self.is_running = False
        self.error_message = None
        
        # Date filtering
        self.start_date = None
        self.end_date = None
        self.date_filtering_enabled = False

    def _init_driver(self):
        if self.driver is not None:
            return self.driver
        chrome_options = Options()
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--headless')
        service = Service()
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 60)
        return self.driver

    def get_progress(self):
        """Return the current progress as a percentage and status message"""
        percentage = 0 if self.total_entries == 0 else min(100, int((self.processed_entries / self.total_entries) * 100))
        return {
            "percentage": percentage,
            "status": self.current_status,
            "is_running": self.is_running,
            "processed": self.processed_entries,
            "total": self.total_entries,
            "error": self.error_message
        }

    def robust_click(self, element, retries=3, delay=2):
        """Click an element with retries for common issues"""
        for attempt in range(retries):
            try:
                element.click()
                return True
            except (ElementClickInterceptedException, ElementNotInteractableException, StaleElementReferenceException) as e:
                logging.warning(f"Click failed: {str(e)}, retrying in {delay}s (Attempt {attempt + 1})")
                time.sleep(delay)
        logging.error("Failed to click element after retries")
        return False

    def get_jurisdiction(self, address):
        """Determine jurisdiction using geocoding"""
        if not address or address.strip() == "":
            return ""
        try:
            address_clean = re.sub(r'\s*\(.*?\)', '', address).strip()
            if address_clean in self.geocode_cache:
                return self.geocode_cache[address_clean]
            location = self.geolocator.geocode(f"{address_clean}, Genesee County, MI", exactly_one=True, timeout=10, addressdetails=True)
            if location and 'address' in location.raw:
                addr = location.raw['address']
                county = addr.get('county', '')
                if 'Genesee' not in county and 'genesee' not in county.lower():
                    logging.warning(f"Address not in Genesee County: {county}")
                    return ""
                jurisdiction = addr.get('township', addr.get('city', addr.get('municipality', addr.get('town', addr.get('village', '')))))
                if jurisdiction:
                    jurisdiction = jurisdiction.replace(" Charter Township", " Township")
                    self.geocode_cache[address_clean] = jurisdiction
                    return jurisdiction
            logging.warning(f"No jurisdiction found for: {address_clean}")
            return ""
        except Exception as e:
            logging.error(f"Error determining jurisdiction: {str(e)}")
            return ""

    def login(self):
        try:
            self.current_status = "Logging in to TowBook"
            logging.info("Navigating to login page...")
            self._init_driver()
            self.driver.get('https://app.towbook.com/Security/Login.aspx')
            username_field = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='Username']")))
            username_field.send_keys(self.username)
            password_field = self.driver.find_element(By.CSS_SELECTOR, "input[name='Password']")
            password_field.send_keys(self.password)
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
            self.robust_click(submit_button)
            self.wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/Reports/') and contains(text(), 'Reports')]")))
            logging.info("Login successful")
            return True
        except Exception as e:
            logging.exception(f"Login failed: {str(e)}")
            self.error_message = f"Login failed: {str(e)}"
            return False

    def navigate_to_reports(self):
        try:
            self.current_status = "Navigating to Reports"
            reports_link = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/Reports/') and contains(text(), 'Reports')]")))
            self.robust_click(reports_link)
            self.wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'Dispatching/') and contains(text(), 'Dispatching Reports')]")))
            logging.info("Navigated to Reports")
            return True
        except Exception as e:
            logging.exception(f"Navigation failed: {str(e)}")
            self.error_message = f"Navigation to Reports failed: {str(e)}"
            return False

    def close_welcome_modal(self):
        try:
            self.current_status = "Handling welcome dialog"
            try:
                not_now_button = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//button[text()='Not right now']")))
                self.robust_click(not_now_button)
                self.wait.until(EC.invisibility_of_element_located((By.XPATH, "//button[text()='Not right now']")))
                logging.info("Closed welcome modal")
            except TimeoutException:
                logging.warning("No welcome modal found")
            return True
        except Exception as e:
            logging.exception(f"Error closing modal: {str(e)}")
            return True

    def navigate_to_dispatching_reports(self):
        try:
            self.current_status = "Navigating to Dispatching Reports"
            dispatching_link = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'Dispatching/') and contains(text(), 'Dispatching Reports')]")))
            self.robust_click(dispatching_link)
            self.wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '../CallAnalysis/') and contains(text(), 'Call Analysis')]")))
            logging.info("Navigated to Dispatching Reports")
            return True
        except Exception as e:
            logging.exception(f"Navigation failed: {str(e)}")
            self.error_message = f"Navigation to Dispatching Reports failed: {str(e)}"
            return False

    def navigate_to_call_analysis(self):
        try:
            self.current_status = "Navigating to Call Analysis"
            call_analysis_link = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '../CallAnalysis/') and contains(text(), 'Call Analysis')]")))
            self.robust_click(call_analysis_link)
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input.ui-combobox-input")))
            logging.info("Navigated to Call Analysis")
            return True
        except Exception as e:
            logging.exception(f"Navigation failed: {str(e)}")
            self.error_message = f"Navigation to Call Analysis failed: {str(e)}"
            return False

    def select_ppi_account(self):
        try:
            self.current_status = "Selecting .PPI account"
            account_dropdown = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input.ui-combobox-input")))
            self.robust_click(account_dropdown)
            ppi_checkbox_label = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//li[contains(@class, 'towbook-combobox-item')]//label[contains(text(), '.PPI')]")))
            ppi_checkbox = ppi_checkbox_label.find_element(By.TAG_NAME, 'input')
            if not ppi_checkbox.is_selected():
                self.robust_click(ppi_checkbox_label)
                logging.info("Selected .PPI account")
            else:
                logging.info(".PPI already selected")
            self.wait.until(EC.staleness_of(ppi_checkbox_label))
            return True
        except Exception as e:
            logging.exception(f"Account selection failed: {str(e)}")
            self.error_message = f"Failed to select .PPI account: {str(e)}"
            return False

    def click_update_button(self):
        try:
            self.current_status = "Updating data view"
            update_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@class='standard-button' and @value='Update']")))
            self.driver.execute_script("arguments[0].scrollIntoView(true); arguments[0].click();", update_button)
            try:
                WebDriverWait(self.driver, 10).until(lambda d: EC.alert_is_present()(d) or EC.invisibility_of_element_located((By.CLASS_NAME, "loading-indicator"))(d))
            except TimeoutException:
                logging.warning("No alert or loading indicator detected")
            if self.is_alert_present():
                alert = self.driver.switch_to.alert
                alert_text = alert.text
                alert.accept()
                if "no results" in alert_text.lower():
                    logging.info("No results found")
                    self.error_message = "No results found"
                    return False
            self.wait.until(EC.invisibility_of_element_located((By.CLASS_NAME, "loading-indicator")))
            logging.info("Update completed")
            return True
        except Exception as e:
            logging.exception(f"Update failed: {str(e)}")
            self.error_message = f"Failed to update data view: {str(e)}"
            return False

    def get_ppi_data(self, days_back=None):
        """Extract vehicle data from all calls in the Call Analysis report"""
        try:
            vehicles = []
            self.current_status = "Locating call entries"
            
            # Find call number links - look specifically for the Call # column's links
            call_links = self.driver.find_elements(By.CSS_SELECTOR, "td a[id^='callEditorLink_']")
            if not call_links:
                call_links = self.driver.find_elements(By.XPATH, "//td/a[contains(@href, 'CallEditor')]")
            
            self.total_entries = len(call_links)
            self.processed_entries = 0
            logging.info(f"Found {self.total_entries} calls to process")

            if self.total_entries == 0:
                logging.warning("No call links found in the report table")
                return vehicles

            # Process each call link
            for index, call_link in enumerate(call_links, 1):
                try:
                    # Get the call number text - this is what appears in the UI
                    call_number = call_link.text.strip()
                    
                    # If text is empty, try to get it from the href or id
                    if not call_number:
                        href = call_link.get_attribute('href')
                        id_match = re.search(r'callId=(\d+)', href)
                        if id_match:
                            call_number = id_match.group(1)
                        else:
                            link_id = call_link.get_attribute('id')
                            if link_id and 'callEditorLink_' in link_id:
                                call_number = link_id.replace('callEditorLink_', '')
                    
                    self.current_status = f"Processing call {index}/{self.total_entries} (Call #: {call_number})"
                    logging.info(f"Processing call {index}/{self.total_entries}: Call #: {call_number}")

                    # Create vehicle data structure with call number
                    vehicle_data = {
                        'towbook_call_number': call_number,
                        'jurisdiction': "", 'tow_date': "", 'tow_time': "", 'location': "",
                        'requestor': "PROPERTY OWNER", 'vin': "", 'year': "", 'make': "", 'model': "", 'color': "",
                        'plate': "", 'state': "", 'case_number': "", 'officer_name': "", 'reference_number': ""
                    }
                    
                    # Use JavaScript to click the link (more reliable than Selenium click)
                    try:
                        # Scroll the link into view first
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", call_link)
                        time.sleep(0.5)  # Give the page time to scroll
                        
                        # Then click it
                        self.driver.execute_script("arguments[0].click();", call_link)
                        logging.info(f"Clicked on call link for {call_number}")
                    except Exception as click_error:
                        logging.error(f"Error clicking call link: {click_error}")
                        vehicles.append(vehicle_data)  # Add with basic info
                        self.processed_entries = index
                        continue
                    
                    # Wait for the modal to appear
                    modal_opened = False
                    try:
                        # Look for dialog elements
                        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".modal-content, div.modal, div[role='dialog'], #callEditor, form.edit-form")))
                        modal_opened = True
                        logging.info(f"Modal opened for call {call_number}")
                    except Exception as modal_error:
                        logging.warning(f"Modal wait error: {modal_error}")
                    
                    if not modal_opened:
                        logging.warning(f"Could not open modal for Call #: {call_number}")
                        vehicles.append(vehicle_data)  # Add with basic info
                        self.processed_entries = index
                        continue

                    # Now extract data exactly as we did before
                    vehicle_data = self.extract_datetime_fields(vehicle_data)
                    
                    # Extract other vehicle data using the same field selectors that worked before
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
                                    break
                            except:
                                continue

                    # Determine jurisdiction if location was found
                    if vehicle_data['location']:
                        vehicle_data['jurisdiction'] = self.get_jurisdiction(vehicle_data['location'])
                        
                    vehicles.append(vehicle_data)
                    
                    # Make sure to close the modal before continuing
                    self.close_modal_safely()
                    self.processed_entries = index
                    
                    # Add a small delay between calls
                    time.sleep(1)

                except Exception as e:
                    logging.error(f"Error processing call {index}: {str(e)}")
                    if self.is_alert_present():
                        self.handle_alert()
                    try:
                        self.close_modal_safely()
                    except:
                        pass
                    self.processed_entries = index
                    time.sleep(1)
                    continue

            return vehicles
        except Exception as e:
            logging.error(f"Error in get_ppi_data: {str(e)}")
            self.error_message = f"Failed to extract data: {str(e)}"
            return []

    def extract_datetime_fields(self, vehicle_data):
        """Extract date and time with multiple fallback methods"""
        date_selectors = ["input#x-impound-date-date", "input[id*='impound'][id*='date']", "input.datepicker", "input[name*='date']", "#serviceDate"]
        time_selectors = ["input#x-impound-date-time", "input[id*='impound'][id*='time']", "input.timepicker", "input[name*='time']", "#serviceTime"]

        date_value = ""
        for selector in date_selectors:
            try:
                date_value = self.get_element_value_by_css(selector)
                if date_value:
                    logging.info(f"Found date: {date_value} with {selector}")
                    break
            except:
                continue

        time_value = ""
        for selector in time_selectors:
            try:
                time_value = self.get_element_value_by_css(selector)
                if time_value:
                    logging.info(f"Found time: {time_value} with {selector}")
                    break
            except:
                continue

        if date_value:
            vehicle_data['tow_date'] = date_value
        if time_value:
            vehicle_data['tow_time'] = time_value
        
        # Check if this vehicle falls within our date range if date filtering is enabled
        if self.date_filtering_enabled and date_value:
            try:
                # Handle multiple date formats
                tow_date = None
                if '/' in date_value:
                    # MM/DD/YYYY format
                    parts = date_value.split('/')
                    if len(parts) == 3:
                        month, day, year = parts
                        tow_date = datetime(int(year), int(month), int(day))
                else:
                    # Try YYYY-MM-DD format
                    tow_date = datetime.strptime(date_value, '%Y-%m-%d')
                
                if tow_date and (tow_date < self.start_date or tow_date >= self.end_date):
                    logging.info(f"Skipping vehicle outside date range: {date_value}")
                    vehicle_data['skip_due_to_date_filter'] = True
            except Exception as e:
                logging.warning(f"Error parsing date for filtering: {e}")
        
        return vehicle_data

    def try_open_modal(self, call_link, call_id):
        """Open modal with robust handling"""
        try:
            if self.is_alert_present():
                self.handle_alert()
            self.driver.execute_script("arguments[0].scrollIntoView(true); arguments[0].click();", call_link)
            modal_selectors = [".modal-content", "div.modal", "div[role='dialog']", "#callEditor", "form.edit-form"]
            for selector in modal_selectors:
                try:
                    WebDriverWait(self.driver, 3).until(EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))
                    logging.info(f"Modal opened with {selector}")
                    return True
                except:
                    continue
            logging.warning(f"Modal not detected for Call ID {call_id}")
            return False
        except Exception as e:
            logging.error(f"Error opening modal for {call_id}: {str(e)}")
            return False

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
                    button = WebDriverWait(self.driver, 1).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    self.driver.execute_script("arguments[0].click();", button)
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
            
            # Now critically wait for and handle the "abandon changes" alert
            # Wait explicitly for alert to appear
            try:
                WebDriverWait(self.driver, 3).until(EC.alert_is_present())
                alert = self.driver.switch_to.alert
                alert_text = alert.text
                logging.info(f"Found alert after closing modal: {alert_text}")
                
                if "abandon" in alert_text.lower() or "changes" in alert_text.lower():
                    alert.accept()
                    logging.info("Accepted 'abandon changes' alert")
                else:
                    alert.accept() 
                    logging.info(f"Accepted unknown alert: {alert_text}")
            except:
                logging.info("No alert appeared after closing modal")
            
            # Add a delay to ensure everything settles
            time.sleep(1.5)
            
            # Double-check for any lingering alerts
            if self.is_alert_present():
                alert = self.driver.switch_to.alert
                logging.info(f"Found lingering alert: {alert.text}")
                alert.accept()
                time.sleep(0.5)  # Another short pause
                
            return True
        except Exception as e:
            logging.error(f"Error in close_modal_safely: {e}")
            
            # Final safety check for alerts
            try:
                if self.is_alert_present():
                    self.driver.switch_to.alert.accept()
                    logging.info("Accepted alert during error recovery")
            except:
                pass
                
            return False

    def get_element_value_by_css(self, css_selector):
        """Get element value with fallback"""
        try:
            element = WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.CSS_SELECTOR, css_selector)))
            value = self.driver.execute_script("return arguments[0].value;", element) or element.get_attribute("value")
            return value.strip() if value else ""
        except Exception as e:
            logging.warning(f"Error getting value for {css_selector}: {str(e)}")
            return ""

    def get_select_value_by_css(self, css_selector):
        """Get selected option text"""
        try:
            select = WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.CSS_SELECTOR, css_selector)))
            value = self.driver.execute_script("return arguments[0].options[arguments[0].selectedIndex]?.text || '';", select)
            return value.strip() if value else ""
        except Exception as e:
            logging.warning(f"Error getting select value for {css_selector}: {str(e)}")
            return ""

    def store_vehicles(self, vehicles):
        """Store vehicles dynamically with default values, preventing duplicates"""
        try:
            self.current_status = "Storing vehicle data"
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS vehicles (towbook_call_number TEXT PRIMARY KEY)")
            cursor.execute("PRAGMA table_info(vehicles)")
            existing_columns = [row[1] for row in cursor.fetchall()]

            # Add missing columns
            for vehicle in vehicles:
                for field in vehicle.keys():
                    if field not in existing_columns:
                        cursor.execute(f"ALTER TABLE vehicles ADD COLUMN {field} TEXT")
                        existing_columns.append(field)

            # Ensure required columns exist
            required_columns = ['status', 'archived', 'last_updated']
            for col in required_columns:
                if col not in existing_columns:
                    cursor.execute(f"ALTER TABLE vehicles ADD COLUMN {col} TEXT")
                    existing_columns.append(col)

            # Check for existing vehicles to prevent duplicates
            new_vehicles = []
            skipped_vehicles = 0
            
            for vehicle in vehicles:
                call_number = vehicle.get('towbook_call_number')
                if not call_number:
                    continue  # Skip vehicles without call numbers
                    
                # Check if vehicle already exists
                cursor.execute("SELECT * FROM vehicles WHERE towbook_call_number = ?", (call_number,))
                existing_vehicle = cursor.fetchone()
                
                if existing_vehicle:
                    # Skip this vehicle to prevent overwriting existing data
                    skipped_vehicles += 1
                    continue
                    
                # Add default values
                vehicle_with_defaults = vehicle.copy()
                vehicle_with_defaults['status'] = vehicle_with_defaults.get('status', 'New')
                vehicle_with_defaults['archived'] = vehicle_with_defaults.get('archived', 0)
                vehicle_with_defaults['last_updated'] = vehicle_with_defaults.get('last_updated', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

                columns = [k for k in vehicle_with_defaults.keys() if k in existing_columns]
                values = [vehicle_with_defaults.get(k) for k in columns]
                placeholders = ','.join(['?' for _ in columns])
                cursor.execute(f"INSERT INTO vehicles ({','.join(columns)}) VALUES ({placeholders})", values)
                
                new_vehicles.append(vehicle)

            conn.commit()
            conn.close()

            logging.info(f"Added {len(new_vehicles)} new vehicles, skipped {skipped_vehicles} duplicate vehicles")
            self.current_status = f"Added {len(new_vehicles)} new vehicles, skipped {skipped_vehicles} duplicates"
            return True
        except Exception as e:
            logging.error(f"Error storing vehicles: {str(e)}")
            self.error_message = f"Failed to store vehicles: {str(e)}"
            return False

    def start_scraping(self, days_back=1):
        """Execute the scraping process"""
        try:
            self.is_running = True
            self.error_message = None
            self.current_status = "Starting scraping process"
            self.date_filtering_enabled = False  # Disable date filtering
            
            if (self.login() and self.navigate_to_reports() and self.close_welcome_modal() and
                self.navigate_to_dispatching_reports() and self.navigate_to_call_analysis() and
                self.select_ppi_account() and self.click_update_button()):
                vehicles = self.get_ppi_data(days_back)
                if vehicles:
                    self.store_vehicles(vehicles)
                    self.current_status = "Completed successfully"
                    logging.info("Scraping completed")
                else:
                    self.current_status = "No vehicles found"
                    logging.warning("No vehicles to store")
        except Exception as e:
            logging.error(f"Scraping error: {str(e)}")
            self.error_message = f"Scraping failed: {str(e)}"
            self.current_status = "Failed"
        finally:
            self.is_running = False
            self.cleanup()
            
    def start_scraping_with_date_range(self, start_date_str, end_date_str):
        """Execute scraping for a date range using TowBook's jQuery UI datepicker"""
        try:
            self.is_running = True
            self.error_message = None
            self.current_status = f"Starting scraping for date range: {start_date_str} to {end_date_str}"
            
            # Parse the input dates
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                
                # Format as MM/DD/YYYY which is what the UI datepicker expects
                formatted_start_date = start_date.strftime('%m/%d/%Y')
                formatted_end_date = end_date.strftime('%m/%d/%Y')
            except ValueError as e:
                self.error_message = f"Invalid date format: {e}"
                self.is_running = False
                return
                
            if self.login() and self.navigate_to_reports() and self.close_welcome_modal() and self.navigate_to_dispatching_reports() and self.navigate_to_call_analysis():
                # Select PPI account
                if not self.select_ppi_account():
                    self.is_running = False
                    return
                    
                # Now set the date range in the jQuery UI datepicker
                try:
                    # Target the specific datepicker input fields by ID
                    start_date_input = self.driver.find_element(By.ID, "dpStartDate")
                    end_date_input = self.driver.find_element(By.ID, "dpEndDate")
                    
                    # Clear the fields
                    self.driver.execute_script("arguments[0].value = '';", start_date_input)
                    self.driver.execute_script("arguments[0].value = '';", end_date_input)
                    
                    # Set the start date value using jQuery UI datepicker
                    self.driver.execute_script(f"arguments[0].value = '{formatted_start_date}';", start_date_input)
                    self.driver.execute_script("$(arguments[0]).change().blur();", start_date_input)
                    
                    # Allow a moment for the first date to register
                    time.sleep(1)
                    
                    # Set the end date value
                    self.driver.execute_script(f"arguments[0].value = '{formatted_end_date}';", end_date_input)
                    self.driver.execute_script("$(arguments[0]).change().blur();", end_date_input)
                    
                    logging.info(f"Set date range from {formatted_start_date} to {formatted_end_date}")
                    
                    # Allow time for date changes to process
                    time.sleep(1)
                    
                except Exception as e:
                    logging.error(f"Error setting datepicker: {str(e)}")
                    self.error_message = f"Failed to set date range: {str(e)}"
                
                # Click the Update button to apply the filters and fetch results
                if self.click_update_button():
                    # Wait longer for the table to fully load after date filter
                    time.sleep(3)
                    
                    # Take a debug screenshot
                    try:
                        debug_path = f"debug_table_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
                        self.driver.save_screenshot(debug_path)
                        logging.info(f"Saved table screenshot to {debug_path}")
                    except Exception as ss_error:
                        logging.warning(f"Error saving screenshot: {ss_error}")
                    
                    # *** IMPORTANT: Use the same approach as the working get_ppi_data method ***
                    # Find call numbers in the table - looking for the actual call numbers in the first column
                    # First, try to get all table rows that might contain calls
                    rows = self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
                    if not rows:
                        rows = self.driver.find_elements(By.XPATH, "//table//tr[position() > 1]")  # Skip header row
                    
                    call_numbers = []
                    for row in rows:
                        try:
                            # Get the call number from the first cell or a link in the first cell
                            cells = row.find_elements(By.TAG_NAME, "td")
                            if cells and len(cells) > 0:
                                # Try to get the call number directly from text
                                call_cell = cells[0]
                                call_text = call_cell.text.strip()
                                
                                # If empty, try to find a link with the call number
                                if not call_text:
                                    links = call_cell.find_elements(By.TAG_NAME, "a")
                                    if links and len(links) > 0:
                                        call_text = links[0].text.strip()
                                
                                if call_text and call_text.isdigit():
                                    call_numbers.append(call_text)
                        except Exception as row_error:
                            logging.warning(f"Error extracting call number from row: {row_error}")
                    
                    self.total_entries = len(call_numbers)
                    self.processed_entries = 0
                    logging.info(f"Found {self.total_entries} calls to process")
                    
                    # If no call numbers found, try to find call number links
                    if self.total_entries == 0:
                        # Fall back to call editor links
                        call_links = self.driver.find_elements(By.CSS_SELECTOR, "a[id^='callEditorLink_']")
                        if not call_links:
                            call_links = self.driver.find_elements(By.XPATH, "//td/a[contains(@href, 'CallEditor')]")
                        
                        self.total_entries = len(call_links)
                        logging.info(f"Found {self.total_entries} call links to process")
                        
                        if self.total_entries > 0:
                            vehicles = []
                            # Process each call link
                            for index, call_link in enumerate(call_links, 1):
                                try:
                                    # Extract call number from link text or attribute
                                    call_number = call_link.text.strip()
                                    if not call_number:
                                        # Try to extract from ID
                                        call_id = call_link.get_attribute('id')
                                        if call_id and 'callEditorLink_' in call_id:
                                            call_number = call_id.replace('callEditorLink_', '')
                                    
                                    self.current_status = f"Processing call {index}/{self.total_entries} (Call #: {call_number})"
                                    logging.info(f"Processing call {index}/{self.total_entries}: Call #: {call_number}")
                                    
                                    # Initialize with the call number
                                    vehicle_data = {
                                        'towbook_call_number': call_number,
                                        'jurisdiction': "", 'tow_date': "", 'tow_time': "", 'location': "",
                                        'requestor': "PROPERTY OWNER", 'vin': "", 'year': "", 'make': "", 'model': "", 'color': "",
                                        'plate': "", 'state': "", 'case_number': "", 'officer_name': "", 'reference_number': ""
                                    }
                                    
                                    # Open the modal
                                    modal_opened = self.try_open_modal(call_link, call_number)
                                    if not modal_opened:
                                        logging.warning(f"Could not open modal for Call #: {call_number}")
                                        vehicles.append(vehicle_data)
                                        self.processed_entries = index
                                        continue
                                    
                                    # Extract data from modal
                                    vehicle_data = self.extract_datetime_fields(vehicle_data)
                                    
                                    # Extract other fields using the field selectors
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
                                                    break
                                            except:
                                                continue
                                    
                                    if vehicle_data['location']:
                                        vehicle_data['jurisdiction'] = self.get_jurisdiction(vehicle_data['location'])
                                    
                                    vehicles.append(vehicle_data)
                                    self.close_modal_safely()
                                    self.processed_entries = index
                                    
                                    # Add a small delay to avoid overloading the server
                                    time.sleep(1)
                                    
                                except Exception as e:
                                    logging.error(f"Error processing call {index}: {str(e)}")
                                    if self.is_alert_present():
                                        self.handle_alert()
                                    try:
                                        self.close_modal_safely()
                                    except:
                                        pass
                                    self.processed_entries = index
                                    time.sleep(1)
                                    continue
                            
                            # Store the vehicles we found
                            if vehicles:
                                self.store_vehicles(vehicles)
                                self.current_status = f"Completed scraping for date range: {start_date_str} to {end_date_str}"
                            else:
                                self.current_status = f"No vehicles found for date range: {start_date_str} to {end_date_str}"
                        else:
                            self.current_status = "No calls found in the table"
                    else:
                        # Process the call numbers we found directly
                        vehicles = []
                        for index, call_number in enumerate(call_numbers, 1):
                            try:
                                self.current_status = f"Processing call {index}/{self.total_entries} (Call #: {call_number})"
                                logging.info(f"Processing call {index}/{self.total_entries}: Call #: {call_number}")
                                
                                # Initialize with the call number
                                vehicle_data = {
                                    'towbook_call_number': call_number,
                                    'jurisdiction': "", 'tow_date': "", 'tow_time': "", 'location': "",
                                    'requestor': "PROPERTY OWNER", 'vin': "", 'year': "", 'make': "", 'model': "", 'color': "",
                                    'plate': "", 'state': "", 'case_number': "", 'officer_name': "", 'reference_number': ""
                                }
                                
                                # Find and click the call number to open details
                                call_link = None
                                call_links = self.driver.find_elements(By.XPATH, f"//td[contains(text(), '{call_number}')]")
                                if call_links:
                                    call_link = call_links[0]
                                
                                if not call_link:
                                    # Try to find it as a link
                                    call_links = self.driver.find_elements(By.XPATH, f"//a[contains(text(), '{call_number}')]")
                                    if call_links:
                                        call_link = call_links[0]
                                
                                if not call_link:
                                    # If still not found, try looking for it in the table's rows
                                    rows = self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
                                    for row in rows:
                                        cells = row.find_elements(By.TAG_NAME, "td")
                                        for cell in cells:
                                            if call_number in cell.text:
                                                call_link = cell
                                                break
                                        if call_link:
                                            break
                                
                                if not call_link:
                                    logging.warning(f"Could not find clickable element for call number {call_number}")
                                    vehicles.append(vehicle_data)
                                    self.processed_entries = index
                                    continue
                                
                                # Try to open the modal
                                modal_opened = False
                                try:
                                    self.driver.execute_script("arguments[0].click();", call_link)
                                    
                                    # Wait for modal to appear
                                    WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((
                                        By.CSS_SELECTOR, ".modal-content, div.modal, div[role='dialog'], #callEditor, form.edit-form"
                                    )))
                                    modal_opened = True
                                    logging.info(f"Modal opened for call {call_number}")
                                except Exception as modal_error:
                                    logging.warning(f"Error opening modal: {modal_error}")
                                
                                if not modal_opened:
                                    logging.warning(f"Could not open modal for Call #: {call_number}")
                                    vehicles.append(vehicle_data)
                                    self.processed_entries = index
                                    continue
                                
                                # Extract data from modal
                                vehicle_data = self.extract_datetime_fields(vehicle_data)
                                
                                # Extract other fields using the field selectors
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
                                                break
                                        except:
                                            continue
                                
                                if vehicle_data['location']:
                                    vehicle_data['jurisdiction'] = self.get_jurisdiction(vehicle_data['location'])
                                
                                vehicles.append(vehicle_data)
                                self.close_modal_safely()
                                self.processed_entries = index
                                
                                # Add a small delay to avoid overloading the server
                                time.sleep(1)
                                
                            except Exception as e:
                                logging.error(f"Error processing call {index}: {str(e)}")
                                if self.is_alert_present():
                                    self.handle_alert()
                                try:
                                    self.close_modal_safely()
                                except:
                                    pass
                                self.processed_entries = index
                                time.sleep(1)
                                continue
                        
                        # Store the vehicles we found
                        if vehicles:
                            self.store_vehicles(vehicles)
                            self.current_status = f"Completed scraping for date range: {start_date_str} to {end_date_str}"
                        else:
                            self.current_status = f"No vehicles found for date range: {start_date_str} to {end_date_str}"
                else:
                    self.current_status = "Failed to update search results"
                    
            else:
                self.current_status = "Failed to navigate to TowBook search page"
                
        except Exception as e:
            logging.error(f"Error in date range scraping: {str(e)}")
            self.error_message = f"Scraping failed: {str(e)}"
            self.current_status = "Failed"
        finally:
            self.is_running = False
            self.cleanup()
            
    def scrape_specific_call_numbers(self, call_refs):
        """Scrape specific call numbers provided in call_refs list"""
        try:
            self.is_running = True
            self.error_message = None
            self.current_status = "Starting scraping for specific call numbers"
            logging.info(f"Scraping {len(call_refs)} specific call numbers")

            # Login and navigate to the Call Analysis page
            if not (self.login() and self.navigate_to_reports() and self.close_welcome_modal() and
                    self.navigate_to_dispatching_reports() and self.navigate_to_call_analysis() and
                    self.select_ppi_account()):
                self.current_status = "Failed to navigate to Call Analysis"
                self.error_message = "Navigation failed"
                self.is_running = False
                return

            # Update the search to filter by specific call numbers
            vehicles = []
            self.total_entries = len(call_refs)
            self.processed_entries = 0

            for index, call_ref in enumerate(call_refs, 1):
                call_number = call_ref['towbook_call_number']
                reference_number = call_ref.get('reference_number', '')
                self.current_status = f"Processing call {index}/{self.total_entries} (Call ID: {call_number})"
                logging.info(f"Processing call {index}/{self.total_entries}: Call ID {call_number}")

                try:
                    # Search for the specific call number
                    search_input = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input#callNumber")))
                    search_input.clear()
                    search_input.send_keys(call_number)
                    self.click_update_button()

                    # Extract data for this call
                    call_links = self.wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "tr[data-id] a[id^='callEditorLink_']")))
                    if not call_links:
                        logging.warning(f"No data found for Call ID {call_number}")
                        self.processed_entries = index
                        continue

                    # Process the first matching call (should be the only one)
                    call_link = call_links[0]
# In scrape_specific_call_numbers
                    vehicle_data = {
                        'towbook_call_number': call_number,  # Changed from 'call_number'
                        'jurisdiction': "", 'tow_date': "", 'tow_time': "", 'location': "",
                        'requestor': "PROPERTY OWNER", 'vin': "", 'year': "", 'make': "", 'model': "", 'color': "",
                        'plate': "", 'state': "", 'case_number': "", 'officer_name': "", 'reference_number': reference_number
                    }
                    modal_opened = self.try_open_modal(call_link, call_number)
                    if not modal_opened:
                        vehicles.append(vehicle_data)
                        self.processed_entries = index
                        logging.warning(f"Could not open modal for Call ID {call_number}")
                        continue

                    vehicle_data = self.extract_datetime_fields(vehicle_data)

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
                                    logging.debug(f"Extracted {field}: '{value}' with {selector}")
                                    break
                            except:
                                continue

                    if vehicle_data['location']:
                        vehicle_data['jurisdiction'] = self.get_jurisdiction(vehicle_data['location'])

                    vehicles.append(vehicle_data)
                    self.processed_entries = index
                    self.close_modal_safely()

                except Exception as e:
                    logging.error(f"Error processing call {call_number}: {str(e)}")
                    self.processed_entries = index
                    self.close_modal_safely()
                    continue

            # Store the scraped vehicles
            if vehicles:
                self.store_vehicles(vehicles)
                self.current_status = "Completed scraping specific call numbers"
                logging.info(f"Scraped and stored {len(vehicles)} vehicles")
            else:
                self.current_status = "No vehicles found for the given call numbers"
                logging.warning("No vehicles to store")

        except Exception as e:
            logging.error(f"Error in scrape_specific_call_numbers: {str(e)}")
            self.error_message = f"Scraping failed: {str(e)}"
            self.current_status = "Failed"
        finally:
            self.is_running = False
            self.cleanup()

    def cleanup(self):
        """Close the browser"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                logging.info("Browser closed")
            except Exception as e:
                logging.error(f"Error closing browser: {str(e)}")

    def is_alert_present(self):
        """Check for alert presence"""
        try:
            self.driver.switch_to.alert
            return True
        except:
            return False

    def handle_alert(self):
        """Handle any alert"""
        try:
            alert = self.driver.switch_to.alert
            logging.info(f"Alert detected: {alert.text}")
            alert.accept()
            return True
        except:
            return False