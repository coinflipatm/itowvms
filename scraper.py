import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import datetime
import sqlite3

logging.basicConfig(level=logging.INFO)

class TowBookScraper:
    def __init__(self, username, password, database='vehicles.db'):
        self.username = username
        self.password = password
        self.database = database
        self.driver = None
        self.wait = None
        self.total_entries = 0
        self.processed_entries = 0
        self.is_running = False

    def _init_driver(self):
        if self.driver:
            return
        options = Options()
        options.add_argument('--headless')
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 60)

    def get_progress(self):
        percentage = 0 if self.total_entries == 0 else min(100, int((self.processed_entries / self.total_entries) * 100))
        return {
            "percentage": percentage,
            "is_running": self.is_running,
            "processed": self.processed_entries,
            "total": self.total_entries
        }

    def login(self):
        self._init_driver()
        self.driver.get('https://app.towbook.com/Security/Login.aspx')
        self.wait.until(EC.presence_of_element_located((By.NAME, 'Username'))).send_keys(self.username)
        self.driver.find_element(By.NAME, 'Password').send_keys(self.password)
        self.driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()
        self.wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(text(), 'Reports')]")))

    def navigate_to_call_analysis(self):
        self.driver.find_element(By.XPATH, "//a[contains(text(), 'Reports')]").click()
        self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Dispatching Reports')]"))).click()
        self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Call Analysis')]"))).click()
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input.ui-combobox-input")))

    def start_scraping_with_date_range(self, start_date_str, end_date_str):
        try:
            self.is_running = True
            self.login()
            self.navigate_to_call_analysis()
            start_date_input = self.driver.find_element(By.ID, "dpStartDate")
            end_date_input = self.driver.find_element(By.ID, "dpEndDate")
            start_date_input.clear()
            end_date_input.clear()
            start_date_input.send_keys(datetime.strptime(start_date_str, '%Y-%m-%d').strftime('%m/%d/%Y'))
            end_date_input.send_keys(datetime.strptime(end_date_str, '%Y-%m-%d').strftime('%m/%d/%Y'))
            self.driver.find_element(By.XPATH, "//input[@value='Update']").click()
            time.sleep(3)
            call_links = self.driver.find_elements(By.CSS_SELECTOR, "a[id^='callEditorLink_']")
            self.total_entries = len(call_links)
            vehicles = []
            for index, link in enumerate(call_links, 1):
                self.processed_entries = index
                call_number = link.text.strip()
                self.driver.execute_script("arguments[0].click();", link)
                self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".modal-content")))
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
                    'plate': self.get_element_value("input.x-license-plate"),
                    'state': self.get_select_value("select.x-license-state")
                }
                vehicles.append(vehicle_data)
                self.driver.find_element(By.CSS_SELECTOR, "input[value='Cancel']").click()
                time.sleep(1)
            self.store_vehicles(vehicles)
        except Exception as e:
            logging.error(f"Scraping error: {e}")
        finally:
            self.is_running = False
            self.cleanup()

    def get_element_value(self, selector):
        try:
            return self.driver.find_element(By.CSS_SELECTOR, selector).get_attribute('value') or ''
        except:
            return ''

    def get_select_value(self, selector):
        try:
            select = self.driver.find_element(By.CSS_SELECTOR, selector)
            return select.find_element(By.CSS_SELECTOR, "option:checked").text or ''
        except:
            return ''

    def store_vehicles(self, vehicles):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS vehicles (towbook_call_number TEXT PRIMARY KEY)")
        cursor.execute("PRAGMA table_info(vehicles)")
        columns = [row[1] for row in cursor.fetchall()]
        for vehicle in vehicles:
            for field in vehicle.keys():
                if field not in columns:
                    cursor.execute(f"ALTER TABLE vehicles ADD COLUMN {field} TEXT")
                    columns.append(field)
            fields = ['towbook_call_number', 'tow_date', 'tow_time', 'location', 'requestor', 'vin', 'year', 'make', 'model', 'color', 'plate', 'state', 'status', 'last_updated']
            values = [vehicle.get(f, '') for f in fields]
            values[fields.index('status')] = 'New'
            values[fields.index('last_updated')] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            placeholders = ','.join(['?' for _ in fields])
            cursor.execute(f"INSERT OR IGNORE INTO vehicles ({','.join(fields)}) VALUES ({placeholders})", values)
        conn.commit()
        conn.close()

    def cleanup(self):
        if self.driver:
            self.driver.quit()
            self.driver = None