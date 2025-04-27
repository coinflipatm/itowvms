import sqlite3
from datetime import datetime, timedelta
import logging
from utils import calculate_next_auction_date, calculate_newspaper_ad_date, get_status_filter
import json

def get_db_connection():
    db_path = '/home/coinflip/itowvms/vehicles.db'  # Use absolute path
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def transaction():
    """Context manager for database transactions"""
    class Transaction:
        def __enter__(self):
            self.conn = get_db_connection()
            return self.conn

        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type is not None:
                self.conn.rollback()
            else:
                self.conn.commit()
            self.conn.close()

    return Transaction()

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vehicles (
            towbook_call_number TEXT PRIMARY KEY,
            complaint_number TEXT,
            vin TEXT,
            make TEXT,
            model TEXT,
            year TEXT,
            color TEXT,
            tow_date TEXT,
            tow_time TEXT,
            location TEXT,
            requestor TEXT,
            jurisdiction TEXT,
            status TEXT DEFAULT 'New',
            top_form_sent_date TEXT,
            tr52_available_date TEXT,
            decision TEXT,
            decision_date TEXT,
            auction_date TEXT,
            last_updated TEXT,
            archived INTEGER DEFAULT 0,
            release_reason TEXT,
            release_date TEXT,
            release_time TEXT,
            recipient TEXT,
            complaint_sequence INTEGER,
            complaint_year TEXT,
            plate TEXT,
            state TEXT,
            case_number TEXT,
            officer_name TEXT,
            days_until_next_step INTEGER,
            paperwork_received_date TEXT,
            estimated_date TEXT,
            ad_placement_date TEXT,
            photo_paths TEXT,
            notice_sent_date TEXT,
            redemption_end_date TEXT,
            sale_amount REAL,
            fees REAL,
            net_proceeds REAL,
            distribution_details TEXT,
            top_notification_sent INTEGER DEFAULT 0,  -- Track TOP notification
            auction_ad_sent INTEGER DEFAULT 0,        -- Track auction ad notification
            release_notification_sent INTEGER DEFAULT 0, -- Track release notification
            requested_by TEXT,
            hearing_date TEXT,
            hearing_requested INTEGER DEFAULT 0,
            certified_mail_number TEXT,
            certified_mail_sent_date TEXT,
            certified_mail_received_date TEXT,
            newspaper_name TEXT,
            newspaper_contact TEXT,
            salvage_value REAL,
            lien_amount REAL,
            storage_fee_per_day REAL,
            storage_days INTEGER,
            additional_fees TEXT,

            /* New fields for TR208 support */
            inoperable INTEGER DEFAULT 0,  -- Is the vehicle inoperable?
            damage_extent TEXT,            -- Description of damage
            condition_notes TEXT,          -- General condition notes
            tr208_eligible INTEGER DEFAULT 0, -- Is vehicle eligible for TR208?
            tr208_available_date TEXT,     -- When TR208 can be processed
            tr208_received_date TEXT,      -- When TR208 was received
            buyer_name TEXT,               -- Auction buyer name
            buyer_id TEXT,                 -- Auction buyer ID/license
            auction_price REAL,            -- Auction sale price
            vehicle_disposition TEXT       -- Final disposition (auction/scrap/redeemed/transferred)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS police_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id TEXT,
            communication_date TEXT,
            communication_type TEXT,
            notes TEXT,
            recipient TEXT,
            contact_method TEXT, -- 'email', 'fax', 'phone', 'mail'
            attachment_path TEXT,
            FOREIGN KEY (vehicle_id) REFERENCES vehicles (towbook_call_number)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type TEXT,
            vehicle_id TEXT,
            details TEXT,
            timestamp TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id TEXT,
            type TEXT,  -- e.g., 'TR52', 'Release Notice', 'Auction Ad'
            filename TEXT,
            upload_date TEXT,
            generated_date TEXT,
            sent_date TEXT,
            sent_to TEXT,
            sent_method TEXT, -- 'email', 'fax', 'mail'
            delivery_status TEXT, -- 'sent', 'delivered', 'failed'
            tracking_number TEXT,
            FOREIGN KEY (vehicle_id) REFERENCES vehicles (towbook_call_number)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS auctions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            auction_date TEXT,
            status TEXT,  -- 'Scheduled', 'Completed', 'Cancelled'
            location TEXT,
            auctioneer TEXT,
            advertisement_date TEXT,
            newspaper_name TEXT,
            vin_list TEXT,
            created_date TEXT,
            completed_date TEXT,
            notes TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jurisdiction TEXT UNIQUE,
            contact_name TEXT,
            phone TEXT,
            email TEXT,
            fax TEXT,
            address TEXT,
            preferred_method TEXT,  -- 'email', 'fax', 'mail'
            notes TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id TEXT,
            notification_type TEXT, -- 'TOP', 'TR52', 'Auction', 'Release'
            due_date TEXT,
            sent_date TEXT,
            sent_method TEXT,
            recipient TEXT,
            status TEXT, -- 'pending', 'sent', 'failed'
            reminder_sent INTEGER DEFAULT 0,
            document_path TEXT,
            FOREIGN KEY (vehicle_id) REFERENCES vehicles (towbook_call_number)
        )
    ''')
    # Add indices for performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_vehicles_status ON vehicles(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_vehicles_tow_date ON vehicles(tow_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_vehicles_jurisdiction ON vehicles(jurisdiction)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_police_logs_vehicle_id ON police_logs(vehicle_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_vehicle_id ON documents(vehicle_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_notifications_vehicle_id ON notifications(vehicle_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_notifications_due_date ON notifications(due_date)')

    # Insert default contacts for common jurisdictions if table is empty
    cursor.execute("SELECT COUNT(*) FROM contacts")
    if cursor.fetchone()[0] == 0:
        default_jurisdictions = [
            ('Flint', 'Flint Police Department', '810-555-0100', 'flint-pd@example.com', '810-555-0101', '123 Main St, Flint, MI', 'email'),
            ('Burton', 'Burton Police Department', '810-555-0200', 'burton-pd@example.com', '810-555-0201', '456 Oak St, Burton, MI', 'fax'),
            ('Grand Blanc', 'Grand Blanc Police', '810-555-0300', 'grandblanc-pd@example.com', '810-555-0301', '789 Maple St, Grand Blanc, MI', 'email'),
            ('Flushing', 'Flushing Police Department', '810-555-0400', 'flushing-pd@example.com', '810-555-0401', '101 Pine St, Flushing, MI', 'fax'),
            ('Clio', 'Clio Police Department', '810-555-0500', 'clio-pd@example.com', '810-555-0501', '202 Elm St, Clio, MI', 'email')
        ]
        for jurisdiction in default_jurisdictions:
            cursor.execute('''
                INSERT INTO contacts (jurisdiction, contact_name, phone, email, fax, address, preferred_method)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', jurisdiction)

    conn.commit()
    conn.close()
    logging.info("Database initialized")

def insert_vehicle(vehicle_data):
    from utils import log_action, generate_complaint_number
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        towbook_call_number = vehicle_data.get('towbook_call_number')
        cursor.execute("SELECT COUNT(*) FROM vehicles WHERE towbook_call_number = ?", (towbook_call_number,))
        exists = cursor.fetchone()[0] > 0

        # Clean data to prevent NULL values
        for key in vehicle_data:
            if vehicle_data[key] is None or vehicle_data[key] == '':
                vehicle_data[key] = 'N/A'

        # Handle complaints
        if 'complaint_number' not in vehicle_data or not vehicle_data['complaint_number'] or vehicle_data['complaint_number'] == 'N/A':
            complaint_number, sequence, year = generate_complaint_number()
            vehicle_data['complaint_number'] = complaint_number
            vehicle_data['complaint_sequence'] = sequence
            vehicle_data['complaint_year'] = year

        if exists:
            # Build update query dynamically based on provided fields
            fields = []
            values = []
            for key, value in vehicle_data.items():
                if key != 'towbook_call_number':  # Skip primary key
                    fields.append(f"{key} = ?")
                    values.append(value)

            # Add the WHERE condition value
            values.append(towbook_call_number)

            # Execute the update query
            cursor.execute(f"""
                UPDATE vehicles SET
                    {", ".join(fields)},
                    last_updated = ?
                WHERE towbook_call_number = ?
            """, values + [datetime.now().strftime('%Y-%m-%d %H:%M:%S'), towbook_call_number])

            logging.info(f"Updated existing vehicle {towbook_call_number}")
        else:
            # For INSERT, we need field names and placeholders
            field_names = list(vehicle_data.keys())
            field_names.append('last_updated')  # Add timestamp

            placeholders = ["?"] * (len(field_names))
            values = list(vehicle_data.values())
            values.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))  # Add timestamp value

            cursor.execute(f"""
                INSERT INTO vehicles (
                    {", ".join(field_names)}
                ) VALUES ({", ".join(placeholders)})
            """, values)

            logging.info(f"Inserted new vehicle {towbook_call_number}")

            # Create initial notification records
            if 'tow_date' in vehicle_data and vehicle_data['tow_date'] != 'N/A':
                tow_date = datetime.strptime(vehicle_data['tow_date'], '%Y-%m-%d')
                top_due_date = tow_date + timedelta(days=1)
                cursor.execute("""
                    INSERT INTO notifications
                    (vehicle_id, notification_type, due_date, status)
                    VALUES (?, ?, ?, ?)
                """, (towbook_call_number, 'TOP', top_due_date.strftime('%Y-%m-%d'), 'pending'))

        conn.commit()
        conn.close()
        log_action("INSERT", towbook_call_number, f"Added vehicle: {vehicle_data.get('make', 'N/A')} {vehicle_data.get('model', 'N/A')}")
        return True, "Vehicle added"
    except Exception as e:
        logging.error(f"Insert error: {e}")
        return False, str(e)

def check_and_update_statuses():
    from utils import log_action
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vehicles WHERE archived = 0")
        vehicles = cursor.fetchall()
        today = datetime.now().date()

        # Create notifications table if needed
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id TEXT,
                notification_type TEXT,
                due_date TEXT,
                sent_date TEXT,
                sent_method TEXT,
                recipient TEXT,
                status TEXT,
                reminder_sent INTEGER DEFAULT 0,
                document_path TEXT,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles (towbook_call_number)
            )
        """)

        for vehicle in vehicles:
            tow_date = vehicle['tow_date']
            if tow_date:
                try:
                    tow_date = datetime.strptime(tow_date, '%Y-%m-%d').date()
                except ValueError:
                    tow_date = datetime.strptime(tow_date, '%m/%d/%Y').date()
                    cursor.execute("UPDATE vehicles SET tow_date = ? WHERE towbook_call_number = ?",
                                 (tow_date.strftime('%Y-%m-%d'), vehicle['towbook_call_number']))

                if vehicle['status'] == 'TOP Generated' and vehicle['top_form_sent_date']:
                    try:
                        top_date = datetime.strptime(vehicle['top_form_sent_date'], '%Y-%m-%d').date()
                        days_since_top = (today - top_date).days
                        if days_since_top >= 20:
                            cursor.execute("""
                                UPDATE vehicles SET status = ?, last_updated = ?
                                WHERE towbook_call_number = ?
                            """, ('TR52 Ready', datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                 vehicle['towbook_call_number']))

                            # Create notification for TR52 ready
                            cursor.execute("""
                                INSERT INTO notifications
                                (vehicle_id, notification_type, due_date, status)
                                VALUES (?, ?, ?, ?)
                            """, (vehicle['towbook_call_number'], 'TR52_Ready',
                                 today.strftime('%Y-%m-%d'), 'pending'))

                            log_action("AUTO_STATUS", vehicle['towbook_call_number'],
                                     "Automatically moved to TR52 Ready status after 20 days")
                        else:
                            days_left = 20 - days_since_top
                            cursor.execute("""
                                UPDATE vehicles SET days_until_next_step = ?
                                WHERE towbook_call_number = ?
                            """, (days_left, vehicle['towbook_call_number']))

                            # Check if we should send a reminder at 15 days
                            if days_since_top == 15:
                                cursor.execute("""
                                    INSERT INTO notifications
                                    (vehicle_id, notification_type, due_date, status)
                                    VALUES (?, ?, ?, ?)
                                """, (vehicle['towbook_call_number'], 'TOP_Reminder',
                                     today.strftime('%Y-%m-%d'), 'pending'))
                    except Exception as e:
                        logging.warning(f"TOP date processing error for {vehicle['towbook_call_number']}: {e}")

                elif vehicle['status'] == 'Ready for Auction' and vehicle['auction_date']:
                    try:
                        auction_date = datetime.strptime(vehicle['auction_date'], '%Y-%m-%d').date()
                        days_until_auction = (auction_date - today).days
                        cursor.execute("""
                            UPDATE vehicles SET days_until_auction = ?
                            WHERE towbook_call_number = ?
                        """, (max(0, days_until_auction), vehicle['towbook_call_number']))

                        # Create notification for auction ad 10 days before auction
                        if days_until_auction == 10 and not vehicle['auction_ad_sent']:
                            cursor.execute("""
                                INSERT INTO notifications
                                (vehicle_id, notification_type, due_date, status)
                                VALUES (?, ?, ?, ?)
                            """, (vehicle['towbook_call_number'], 'Auction_Ad',
                                 today.strftime('%Y-%m-%d'), 'pending'))

                        # Create notification for auction report day after auction
                        if days_until_auction == -1:
                            cursor.execute("""
                                INSERT INTO notifications
                                (vehicle_id, notification_type, due_date, status)
                                VALUES (?, ?, ?, ?)
                            """, (vehicle['towbook_call_number'], 'Auction_Report',
                                 today.strftime('%Y-%m-%d'), 'pending'))

                        if days_until_auction < -1:
                            cursor.execute("""
                                UPDATE vehicles SET status = ?, archived = 1, release_reason = ?,
                                release_date = ?, last_updated = ?
                                WHERE towbook_call_number = ?
                            """, ('Auctioned', 'Auto-completed auction',
                                 auction_date.strftime('%Y-%m-%d'),
                                 datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                 vehicle['towbook_call_number']))
                            log_action("AUTO_STATUS", vehicle['towbook_call_number'],
                                     "Automatically marked as Auctioned after auction date")
                    except Exception as e:
                        logging.warning(f"Auction date processing error for {vehicle['towbook_call_number']}: {e}")

                elif vehicle['status'] == 'Ready for Scrap':
                    try:
                        days_since_tow = (today - tow_date).days
                        if days_since_tow < 27:
                            days_left = 27 - days_since_tow
                            cursor.execute("""
                                UPDATE vehicles SET days_until_next_step = ?
                                WHERE towbook_call_number = ?
                            """, (days_left, vehicle['towbook_call_number']))

                            # Create notification for scrap photos 1 day before legal scrap date
                            if days_left == 1:
                                cursor.execute("""
                                    INSERT INTO notifications
                                    (vehicle_id, notification_type, due_date, status)
                                    VALUES (?, ?, ?, ?)
                                """, (vehicle['towbook_call_number'], 'Scrap_Photos',
                                     today.strftime('%Y-%m-%d'), 'pending'))
                        else:
                            cursor.execute("""
                                UPDATE vehicles SET days_until_next_step = 0
                                WHERE towbook_call_number = ?
                            """, (vehicle['towbook_call_number'],))
                    except Exception as e:
                        logging.warning(f"Scrap date processing error for {vehicle['towbook_call_number']}: {e}")

        # Check for any pending notifications
        cursor.execute("""
            SELECT n.*, v.jurisdiction
            FROM notifications n
            JOIN vehicles v ON n.vehicle_id = v.towbook_call_number
            WHERE n.status = 'pending' AND n.due_date <= ?
        """, (today.strftime('%Y-%m-%d'),))

        pending_notifications = cursor.fetchall()
        for notification in pending_notifications:
            # Get jurisdiction contact info
            cursor.execute("""
                SELECT * FROM contacts
                WHERE jurisdiction = ?
            """, (notification['jurisdiction'],))
            contact = cursor.fetchone()

            if contact:
                # Update notification with contact info
                cursor.execute("""
                    UPDATE notifications
                    SET recipient = ?, sent_method = ?
                    WHERE id = ?
                """, (contact['contact_name'], contact['preferred_method'], notification['id']))

            # Log the pending notification
            log_action("NOTIFICATION", notification['vehicle_id'],
                     f"Pending {notification['notification_type']} notification due {notification['due_date']}")

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Status check error: {e}")
        return False

def update_vehicle_status(towbook_call_number, new_status, update_fields=None):
    from utils import log_action, is_eligible_for_tr208, calculate_tr208_timeline
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vehicles WHERE towbook_call_number = ?", (towbook_call_number,))
        vehicle = cursor.fetchone()
        if not vehicle:
            conn.close()
            return False

        if not update_fields:
            update_fields = {}

        # Get valid column names
        cursor.execute("PRAGMA table_info(vehicles)")
        valid_columns = set(row[1] for row in cursor.fetchall())

        # Filter update_fields to only include valid columns
        update_fields = {k: v for k, v in update_fields.items() if k in valid_columns}

        update_fields['status'] = new_status
        update_fields['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if new_status == 'TOP Generated':
            top_date = datetime.now()
            update_fields['top_form_sent_date'] = top_date.strftime('%Y-%m-%d')

            # Check TR208 eligibility
            vehicle_data = dict(vehicle)
            tr208_eligible, _ = is_eligible_for_tr208(vehicle_data)
            update_fields['tr208_eligible'] = 1 if tr208_eligible else 0

            if tr208_eligible:
                # If eligible for TR208, set timeline to 27 days
                tr208_date = calculate_tr208_timeline(top_date)
                update_fields['tr208_available_date'] = tr208_date.strftime('%Y-%m-%d')
                update_fields['days_until_next_step'] = 27
            else:
                # Otherwise, standard TR52 path (20 days)
                tr52_date = top_date + timedelta(days=20)
                update_fields['tr52_available_date'] = tr52_date.strftime('%Y-%m-%d')
                update_fields['days_until_next_step'] = 20

            update_fields['redemption_end_date'] = (top_date + timedelta(days=30)).strftime('%Y-%m-%d')

            # Create notification record for either TR52 or TR208 document
            if tr208_eligible:
                cursor.execute("""
                    INSERT INTO notifications
                    (vehicle_id, notification_type, due_date, status)
                    VALUES (?, ?, ?, ?)
                """, (towbook_call_number, 'TR208', update_fields['tr208_available_date'], 'pending'))
            else:
                cursor.execute("""
                    INSERT INTO notifications
                    (vehicle_id, notification_type, due_date, status)
                    VALUES (?, ?, ?, ?)
                """, (towbook_call_number, 'TR52', update_fields['tr52_available_date'], 'pending'))

        elif new_status == 'TR52 Ready':
            # No specific fields to update, handled by update_fields parameter
            pass

        elif new_status == 'TR208 Ready':
            if 'tr208_received_date' not in update_fields:
                update_fields['tr208_received_date'] = datetime.now().strftime('%Y-%m-%d')

        elif new_status == 'Ready for Auction':
            auction_date = calculate_next_auction_date(vehicle['ad_placement_date'])
            update_fields['auction_date'] = auction_date.strftime('%Y-%m-%d')
            update_fields['decision'] = 'Auction'
            update_fields['decision_date'] = datetime.now().strftime('%Y-%m-%d')
            days_until_auction = (auction_date.date() - datetime.now().date()).days
            update_fields['days_until_auction'] = max(0, days_until_auction)

            # Set ad placement date if not already set
            if 'ad_placement_date' not in update_fields or not update_fields['ad_placement_date']:
                ad_date = calculate_newspaper_ad_date(auction_date)
                update_fields['ad_placement_date'] = ad_date.strftime('%Y-%m-%d')

            # Create notification record for auction advertisement
            cursor.execute("""
                INSERT INTO notifications
                (vehicle_id, notification_type, due_date, status)
                VALUES (?, ?, ?, ?)
            """, (towbook_call_number, 'Auction_Ad', update_fields['ad_placement_date'], 'pending'))

        elif new_status == 'Ready for Scrap':
            scrap_date = datetime.now() + timedelta(days=7)
            update_fields['estimated_date'] = scrap_date.strftime('%Y-%m-%d')
            update_fields['decision'] = 'Scrap'
            update_fields['decision_date'] = datetime.now().strftime('%Y-%m-%d')
            update_fields['days_until_next_step'] = 7
            update_fields['vehicle_disposition'] = 'Scrap'

            # Create notification record for scrap photos
            cursor.execute("""
                INSERT INTO notifications
                (vehicle_id, notification_type, due_date, status)
                VALUES (?, ?, ?, ?)
            """, (towbook_call_number, 'Scrap_Photos', scrap_date.strftime('%Y-%m-%d'), 'pending'))

        elif new_status == 'Released':
            update_fields['archived'] = 1
            update_fields['release_date'] = update_fields.get('release_date', datetime.now().strftime('%Y-%m-%d'))
            update_fields['release_time'] = update_fields.get('release_time', datetime.now().strftime('%H:%M'))
            update_fields['release_reason'] = update_fields.get('release_reason', 'Owner Redeemed')
            update_fields['vehicle_disposition'] = 'Redeemed'

            # Create notification record for release notification
            cursor.execute("""
                INSERT INTO notifications
                (vehicle_id, notification_type, due_date, status)
                VALUES (?, ?, ?, ?)
            """, (towbook_call_number, 'Release_Notice', update_fields['release_date'], 'pending'))

        elif new_status == 'Auctioned':
            update_fields['archived'] = 1
            update_fields['release_date'] = update_fields.get('release_date', datetime.now().strftime('%Y-%m-%d'))
            update_fields['release_time'] = update_fields.get('release_time', datetime.now().strftime('%H:%M'))
            update_fields['release_reason'] = 'Auctioned'
            update_fields['vehicle_disposition'] = 'Auctioned'

            if 'sale_amount' in update_fields and 'fees' in update_fields:
                try:
                    sale_amount = float(update_fields['sale_amount'])
                    fees = float(update_fields['fees'])
                    update_fields['net_proceeds'] = sale_amount - fees
                except (ValueError, TypeError):
                    update_fields['net_proceeds'] = 0

            # Create notification record for release notification
            cursor.execute("""
                INSERT INTO notifications
                (vehicle_id, notification_type, due_date, status)
                VALUES (?, ?, ?, ?)
            """, (towbook_call_number, 'Release_Notice', update_fields['release_date'], 'pending'))

        elif new_status == 'Scrapped':
            update_fields['archived'] = 1
            update_fields['release_date'] = update_fields.get('release_date', datetime.now().strftime('%Y-%m-%d'))
            update_fields['release_reason'] = 'Scrapped'
            update_fields['vehicle_disposition'] = 'Scrapped'

            # Create notification record for release notification
            cursor.execute("""
                INSERT INTO notifications
                (vehicle_id, notification_type, due_date, status)
                VALUES (?, ?, ?, ?)
            """, (towbook_call_number, 'Release_Notice', update_fields['release_date'], 'pending'))

        elif new_status == 'Transferred':
            update_fields['archived'] = 1
            update_fields['release_date'] = update_fields.get('release_date', datetime.now().strftime('%Y-%m-%d'))
            update_fields['release_reason'] = 'Transferred to Custodian'
            update_fields['vehicle_disposition'] = 'Transferred'

            # Create notification record for release notification
            cursor.execute("""
                INSERT INTO notifications
                (vehicle_id, notification_type, due_date, status)
                VALUES (?, ?, ?, ?)
            """, (towbook_call_number, 'Release_Notice', update_fields['release_date'], 'pending'))

        # Ensure all fields in update_fields exist in the database
        update_fields = {k: v for k, v in update_fields.items() if k in valid_columns}

        set_clause = ', '.join([f"{k} = ?" for k in update_fields.keys()])
        values = list(update_fields.values()) + [towbook_call_number]
        cursor.execute(f'UPDATE vehicles SET {set_clause} WHERE towbook_call_number = ?', values)
        conn.commit()
        conn.close()
        log_action("STATUS_CHANGE", towbook_call_number, f"Status changed to {new_status}")
        return True
    except Exception as e:
        logging.error(f"Status update error: {e}")
        return False

def get_vehicles(tab, sort_column=None, sort_direction='asc'):
    try:
        if tab == 'active':
            conn = get_db_connection()
            cursor = conn.cursor()
            sort_by = "tow_date DESC"
            if sort_column:
                valid_columns = [
                    'towbook_call_number', 'complaint_number', 'vin', 'make', 'model',
                    'year', 'color', 'tow_date', 'jurisdiction', 'status', 'last_updated'
                ]
                if sort_column in valid_columns:
                    sort_dir = "ASC" if sort_direction.lower() == 'asc' else "DESC"
                    sort_by = f"{sort_column} {sort_dir}"
            cursor.execute(f"SELECT * FROM vehicles WHERE archived = 0 ORDER BY {sort_by}")
            vehicles = cursor.fetchall()
            conn.close()
            return vehicles
        else:
            return get_vehicles_by_status(tab, sort_column, sort_direction)
    except Exception as e:
        logging.error(f"Get vehicles error (tab={tab}): {e}")
        return []

def get_vehicles_by_status(status_type, sort_column=None, sort_direction='asc'):
    from utils import get_status_filter
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        status_filter = get_status_filter(status_type)
        if not status_filter:
            conn.close()
            return []
        sort_clause = "tow_date ASC"
        if sort_column:
            valid_columns = [
                'towbook_call_number', 'complaint_number', 'vin', 'make', 'model',
                'year', 'color', 'tow_date', 'jurisdiction', 'status', 'last_updated'
            ]
            if sort_column in valid_columns:
                sort_dir = "ASC" if sort_direction.lower() == 'asc' else "DESC"
                sort_clause = f"{sort_column} {sort_dir}"
        if status_type == 'Completed':
            cursor.execute(f"""
                SELECT * FROM vehicles
                WHERE status IN ({','.join(['?' for _ in status_filter])}) OR archived = 1
                ORDER BY {sort_clause}
            """, status_filter)
        else:
            cursor.execute(f"""
                SELECT * FROM vehicles
                WHERE status IN ({','.join(['?' for _ in status_filter])}) AND archived = 0
                ORDER BY {sort_clause}
            """, status_filter)
        vehicles = [dict(row) for row in cursor.fetchall()]
        today = datetime.now().date()
        for vehicle in vehicles:
            if vehicle.get('tow_date') and vehicle['tow_date'] != 'N/A':
                try:
                    tow_date = datetime.strptime(vehicle['tow_date'], '%Y-%m-%d').date()
                    vehicle['days_since_tow'] = (today - tow_date).days
                except Exception as e:
                    logging.warning(f"Tow date processing error: {e}")
            if vehicle.get('status') == 'TOP Generated' and vehicle.get('top_form_sent_date') and vehicle['top_form_sent_date'] != 'N/A':
                try:
                    top_date = datetime.strptime(vehicle['top_form_sent_date'], '%Y-%m-%d').date()
                    tr52_date = top_date + timedelta(days=20)
                    vehicle['days_until_ready'] = max(0, (tr52_date - today).days)
                    vehicle['tr52_date'] = tr52_date.strftime('%Y-%m-%d')
                except Exception as e:
                    logging.warning(f"TOP date processing error: {e}")
            if vehicle.get('status') == 'Ready for Auction' and vehicle.get('auction_date') and vehicle['auction_date'] != 'N/A':
                try:
                    auction_date = datetime.strptime(vehicle['auction_date'], '%Y-%m-%d').date()
                    vehicle['days_until_auction'] = max(0, (auction_date - today).days)
                except Exception as e:
                    logging.warning(f"Auction date processing error: {e}")
        conn.close()
        return vehicles
    except Exception as e:
        logging.error(f"Get vehicles error: {e}")
        return []

def update_vehicle(old_call_number, data):
    from utils import log_action
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get existing columns from the database
        cursor.execute("PRAGMA table_info(vehicles)")
        existing_columns = [row[1] for row in cursor.fetchall()]

        # Filter out any fields that don't exist in the database
        filtered_data = {k: v for k, v in data.items() if k in existing_columns}

        # Explicitly handle the 'requested_by' case - map it to 'requestor' if needed
        if 'requested_by' in data and 'requested_by' not in existing_columns:
            if 'requestor' in existing_columns:
                filtered_data['requestor'] = data['requested_by']

        # Rest of function remains the same
        new_call_number = filtered_data.get('towbook_call_number', old_call_number)
        filtered_data['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Clean data to prevent NULL values
        for key in filtered_data:
            if filtered_data[key] is None or filtered_data[key] == '':
                filtered_data[key] = 'N/A'

        if new_call_number != old_call_number:
            # Code for handling call number change...
            pass
        else:
            set_clause = ', '.join([f"{k} = ?" for k in filtered_data.keys()])
            values = list(filtered_data.values()) + [old_call_number]
            cursor.execute(f'UPDATE vehicles SET {set_clause} WHERE towbook_call_number = ?', values)

        conn.commit()
        conn.close()
        log_action("UPDATE", new_call_number, "Vehicle updated")
        return True, "Vehicle updated"
    except Exception as e:
        logging.error(f"Update error: {e}")
        return False, str(e)

def toggle_archive_status(call_number):
    from utils import log_action
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT archived FROM vehicles WHERE towbook_call_number = ?", (call_number,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return False, "Vehicle not found"
        new_archived = 1 if result['archived'] == 0 else 0
        cursor.execute("UPDATE vehicles SET archived = ?, last_updated = ? WHERE towbook_call_number = ?",
                       (new_archived, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), call_number))
        conn.commit()
        conn.close()
        status_text = "completed" if new_archived else "active"
        log_action("ARCHIVE_TOGGLE", call_number, f"Status toggled to {status_text}")
        return True, f"Status changed to {status_text}"
    except Exception as e:
        logging.error(f"Toggle error: {e}")
        return False, str(e)

def get_logs(vehicle_id=None, limit=100):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if vehicle_id:
            cursor.execute("SELECT * FROM logs WHERE vehicle_id = ? ORDER BY timestamp DESC LIMIT ?", (vehicle_id, limit))
        else:
            cursor.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT ?", (limit,))
        logs = cursor.fetchall()
        conn.close()
        return logs
    except Exception as e:
        logging.error(f"Get logs error: {e}")
        return []

def create_auction(auction_date, vehicle_ids):
    from utils import log_action
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT vin FROM vehicles WHERE towbook_call_number IN ({','.join(['?' for _ in vehicle_ids])})", vehicle_ids)
        vin_list = ', '.join([row['vin'] for row in cursor.fetchall() if row['vin']])

        # Calculate ad placement date
        auction_date_obj = datetime.strptime(auction_date, '%Y-%m-%d')
        ad_date = calculate_newspaper_ad_date(auction_date_obj)

        cursor.execute("INSERT INTO auctions (auction_date, status, vin_list, created_date, advertisement_date) VALUES (?, 'Scheduled', ?, ?, ?)",
                       (auction_date, vin_list, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ad_date.strftime('%Y-%m-%d')))
        auction_id = cursor.lastrowid

        for vehicle_id in vehicle_ids:
            cursor.execute("UPDATE vehicles SET status = 'Auction', auction_date = ?, ad_placement_date = ?, last_updated = ? WHERE towbook_call_number = ?",
                           (auction_date, ad_date.strftime('%Y-%m-%d'), datetime.now().strftime('%Y-%m-%d %H:%M:%S'), vehicle_id))

            # Create notification for auction ad
            cursor.execute("""
                INSERT INTO notifications
                (vehicle_id, notification_type, due_date, status)
                VALUES (?, ?, ?, ?)
            """, (vehicle_id, 'Auction_Ad', ad_date.strftime('%Y-%m-%d'), 'pending'))

        conn.commit()
        conn.close()
        log_action("AUCTION", "BATCH", f"Auction #{auction_id} created with {len(vehicle_ids)} vehicles")
        return True, f"Auction #{auction_id} created"
    except Exception as e:
        logging.error(f"Auction error: {e}")
        return False, str(e)

def get_pending_notifications():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        today = datetime.now().date().strftime('%Y-%m-%d')

        cursor.execute("""
            SELECT n.*, v.jurisdiction, v.make, v.model, v.year, v.color, v.towbook_call_number, v.vin
            FROM notifications n
            JOIN vehicles v ON n.vehicle_id = v.towbook_call_number
            WHERE n.status = 'pending' AND n.due_date <= ?
            ORDER BY n.due_date
        """, (today,))

        notifications = [dict(row) for row in cursor.fetchall()]

        # Get contact information for each jurisdiction
        for notification in notifications:
            cursor.execute("SELECT * FROM contacts WHERE jurisdiction = ?", (notification['jurisdiction'],))
            contact = cursor.fetchone()
            if contact:
                notification['contact'] = dict(contact)

        conn.close()
        return notifications
    except Exception as e:
        logging.error(f"Get pending notifications error: {e}")
        return []

def mark_notification_sent(notification_id, method, recipient):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE notifications
            SET status = 'sent', sent_date = ?, sent_method = ?, recipient = ?
            WHERE id = ?
        """, (datetime.now().strftime('%Y-%m-%d'), method, recipient, notification_id))

        # Get notification details for logging
        cursor.execute("SELECT * FROM notifications WHERE id = ?", (notification_id,))
        notification = cursor.fetchone()

        if notification:
            # Update vehicle record based on notification type
            if notification['notification_type'] == 'TOP':
                cursor.execute("UPDATE vehicles SET top_notification_sent = 1 WHERE towbook_call_number = ?",
                              (notification['vehicle_id'],))

            elif notification['notification_type'] == 'Auction_Ad':
                cursor.execute("UPDATE vehicles SET auction_ad_sent = 1 WHERE towbook_call_number = ?",
                              (notification['vehicle_id'],))

            elif notification['notification_type'] == 'Release_Notice':
                cursor.execute("UPDATE vehicles SET release_notification_sent = 1 WHERE towbook_call_number = ?",
                              (notification['vehicle_id'],))

            # Log the action
            from utils import log_action
            log_action("NOTIFICATION_SENT", notification['vehicle_id'],
                      f"{notification['notification_type']} sent to {recipient} via {method}")

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Mark notification sent error: {e}")
        return False

def batch_update_status(vehicle_ids, new_status):
    from utils import log_action
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        updated_count = 0
        for call_number in vehicle_ids:
            cursor.execute("UPDATE vehicles SET status = ?, last_updated = ? WHERE towbook_call_number = ?",
                           (new_status, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), call_number))
            if cursor.rowcount > 0:
                updated_count += 1
                log_action("BATCH_UPDATE", call_number, f"Status updated to {new_status}")
        conn.commit()
        conn.close()
        return True, updated_count, f"Updated {updated_count} vehicles"
    except Exception as e:
        logging.error(f"Batch update error: {e}")
        return False, 0, str(e)

def get_contact_by_jurisdiction(jurisdiction):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM contacts WHERE jurisdiction = ?", (jurisdiction,))
        contact = cursor.fetchone()
        conn.close()
        return dict(contact) if contact else None
    except Exception as e:
        logging.error(f"Get contact error: {e}")
        return None

def save_contact(contact_data):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if contact exists
        cursor.execute("SELECT id FROM contacts WHERE jurisdiction = ?", (contact_data['jurisdiction'],))
        existing = cursor.fetchone()

        if existing:
            # Update existing contact
            fields = []
            values = []
            for key, value in contact_data.items():
                if key != 'id' and key != 'jurisdiction':  # Skip primary key and jurisdiction
                    fields.append(f"{key} = ?")
                    values.append(value)

            # Add jurisdiction for WHERE clause
            values.append(contact_data['jurisdiction'])

            cursor.execute(f"""
                UPDATE contacts SET {", ".join(fields)}
                WHERE jurisdiction = ?
            """, values)
        else:
            # Insert new contact
            fields = list(contact_data.keys())
            placeholders = ["?"] * len(fields)
            values = list(contact_data.values())

            cursor.execute(f"""
                INSERT INTO contacts ({", ".join(fields)})
                VALUES ({", ".join(placeholders)})
            """, values)

        conn.commit()
        conn.close()
        return True, "Contact saved successfully"
    except Exception as e:
        logging.error(f"Save contact error: {e}")
        return False, str(e)

def get_contacts():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM contacts ORDER BY jurisdiction")
        contacts = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return contacts
    except Exception as e:
        logging.error(f"Get contacts error: {e}")
        return []