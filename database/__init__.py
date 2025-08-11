import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

def get_database_path():
    """Get the database path."""
    return os.environ.get('DATABASE_URL', 'vehicles.db')

@contextmanager
def transaction():
    """Database transaction context manager."""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def get_db_connection():
    """Get a database connection."""
    db_path = os.environ.get('DATABASE_URL', 'vehicles.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database schema."""
    db_path = os.environ.get('DATABASE_URL', 'vehicles.db')
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS vehicles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    towbook_call_number TEXT UNIQUE NOT NULL,
                    status TEXT NOT NULL,
                    make TEXT,
                    model TEXT,
                    year TEXT,
                    color TEXT,
                    vin TEXT,
                    plate TEXT,
                    state TEXT,
                    complaint_number TEXT,
                    jurisdiction TEXT,
                    tow_date TEXT,
                    tow_time TEXT,
                    location TEXT,
                    requestor TEXT,
                    case_number TEXT,
                    officer_name TEXT,
                    last_updated TEXT,
                    top_form_sent_date TEXT,
                    top_form_generated_at TEXT,
                    top_form_generated_by TEXT,
                    release_date TEXT,
                    released_to TEXT,
                    release_reason TEXT
                );

                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    phone TEXT,
                    email TEXT,
                    jurisdiction TEXT
                );

                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL
                );

                CREATE TABLE IF NOT EXISTS action_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    user_id INTEGER,
                    timestamp TEXT NOT NULL,
                    details TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_id INTEGER,
                    type TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    sent_at TEXT,
                    FOREIGN KEY(vehicle_id) REFERENCES vehicles(id)
                );

                -- Outbound document / message communications tracking
                CREATE TABLE IF NOT EXISTS communications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER,
                    vehicle_id INTEGER,
                    towbook_call_number TEXT,
                    contact_id INTEGER,
                    jurisdiction TEXT,
                    method TEXT NOT NULL, -- email, fax, sms, etc.
                    destination TEXT NOT NULL,
                    subject TEXT,
                    message_preview TEXT,
                    attachment_path TEXT,
                    status TEXT NOT NULL DEFAULT 'pending', -- pending, sent, failed
                    error TEXT,
                    tracking_number TEXT,
                    provider_message_id TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    sent_at DATETIME,
                    FOREIGN KEY(document_id) REFERENCES documents(id)
                );
            ''')
    finally:
        conn.close()

def get_vehicles_by_status(statuses, sort_column='tow_date', sort_direction='desc'):
    """Get vehicles by status with sorting."""
    conn = get_db_connection()
    try:
        placeholders = ','.join('?' for _ in statuses)
        query = f"SELECT * FROM vehicles WHERE status IN ({placeholders}) ORDER BY {sort_column} {sort_direction}"
        vehicles = conn.execute(query, statuses).fetchall()
        return [dict(vehicle) for vehicle in vehicles]
    finally:
        conn.close()

def get_vehicles():
    """Get all vehicles."""
    conn = get_db_connection()
    try:
        vehicles = conn.execute("SELECT * FROM vehicles ORDER BY tow_date DESC").fetchall()
        return [dict(vehicle) for vehicle in vehicles]
    finally:
        conn.close()

def get_vehicle_by_id(vehicle_id):
    """Get a vehicle by ID."""
    conn = get_db_connection()
    try:
        vehicle = conn.execute("SELECT * FROM vehicles WHERE id = ?", (vehicle_id,)).fetchone()
        return dict(vehicle) if vehicle else None
    finally:
        conn.close()

def get_vehicle_by_call_number(call_number):
    """Get a vehicle by call number."""
    conn = get_db_connection()
    try:
        vehicle = conn.execute("SELECT * FROM vehicles WHERE towbook_call_number = ?", (call_number,)).fetchone()
        return vehicle
    finally:
        conn.close()

def insert_vehicle(data):
    """Insert a new vehicle into the database."""
    conn = get_db_connection()
    try:
        columns = ', '.join(data.keys())
        placeholders = ', '.join('?' for _ in data)
        query = f"INSERT INTO vehicles ({columns}) VALUES ({placeholders})"
        cursor = conn.execute(query, list(data.values()))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def update_vehicle(vehicle_id, data):
    """Update a vehicle by ID."""
    conn = get_db_connection()
    try:
        set_clause = ', '.join(f"{key} = ?" for key in data.keys())
        query = f"UPDATE vehicles SET {set_clause} WHERE id = ?"
        conn.execute(query, list(data.values()) + [vehicle_id])
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def update_vehicle_by_call_number(call_number, data):
    """Update a vehicle by call number."""
    conn = get_db_connection()
    try:
        set_clause = ', '.join(f"{key} = ?" for key in data.keys())
        query = f"UPDATE vehicles SET {set_clause} WHERE towbook_call_number = ?"
        conn.execute(query, list(data.values()) + [call_number])
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def update_vehicle_status(call_number, status, additional_data=None):
    """Update vehicle status and optional additional data."""
    conn = get_db_connection()
    try:
        data = {'status': status, 'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        if additional_data:
            data.update(additional_data)
        
        set_clause = ', '.join(f"{key} = ?" for key in data.keys())
        query = f"UPDATE vehicles SET {set_clause} WHERE towbook_call_number = ?"
        conn.execute(query, list(data.values()) + [call_number])
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def delete_vehicle_by_call_number(call_number):
    """Delete a vehicle by call number."""
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM vehicles WHERE towbook_call_number = ?", (call_number,))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def check_and_update_statuses():
    """Check and update vehicle statuses based on business logic."""
    # Placeholder implementation
    return True

def get_pending_notifications():
    """Get pending notifications."""
    conn = get_db_connection()
    try:
        notifications = conn.execute(
            "SELECT * FROM notifications WHERE status = 'pending' ORDER BY created_at"
        ).fetchall()
        return [dict(notification) for notification in notifications]
    finally:
        conn.close()

def mark_notification_sent(notification_id):
    """Mark a notification as sent."""
    conn = get_db_connection()
    try:
        conn.execute(
            "UPDATE notifications SET status = 'sent', sent_at = ? WHERE id = ?",
            (datetime.now().isoformat(), notification_id)
        )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

# Contact management functions
def get_contacts():
    """Get all contacts."""
    conn = get_db_connection()
    try:
        contacts = conn.execute("SELECT * FROM contacts ORDER BY contact_name").fetchall()
        return [dict(contact) for contact in contacts]
    finally:
        conn.close()

def get_contact_by_id(contact_id):
    """Get a contact by ID."""
    conn = get_db_connection()
    try:
        contact = conn.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,)).fetchone()
        return dict(contact) if contact else None
    finally:
        conn.close()

def get_contact_by_jurisdiction(jurisdiction):
    """Get a contact by jurisdiction."""
    conn = get_db_connection()
    try:
        contact = conn.execute("SELECT * FROM contacts WHERE jurisdiction = ?", (jurisdiction,)).fetchone()
        return dict(contact) if contact else None
    finally:
        conn.close()

def save_contact(data):
    """Save a new contact."""
    conn = get_db_connection()
    try:
        columns = ', '.join(data.keys())
        placeholders = ', '.join('?' for _ in data)
        query = f"INSERT INTO contacts ({columns}) VALUES ({placeholders})"
        cursor = conn.execute(query, list(data.values()))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def add_contact_explicit(name, phone, email, jurisdiction):
    """Add a contact with explicit parameters."""
    data = {
        'name': name,
        'phone': phone,
        'email': email,
        'jurisdiction': jurisdiction
    }
    return save_contact(data)

def update_contact_explicit(contact_id, name, phone, email, jurisdiction):
    """Update a contact with explicit parameters."""
    conn = get_db_connection()
    try:
        conn.execute(
            "UPDATE contacts SET name = ?, phone = ?, email = ?, jurisdiction = ? WHERE id = ?",
            (name, phone, email, jurisdiction, contact_id)
        )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def delete_contact_explicit(contact_id):
    """Delete a contact by ID."""
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def safe_parse_date(date_string):
    """Safely parse a date string."""
    if not date_string:
        return None
    try:
        return datetime.strptime(date_string, '%Y-%m-%d').date()
    except ValueError:
        try:
            return datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S').date()
        except ValueError:
            return None

def add_document(call_number, document_name, document_type, file_path, uploaded_by='System', 
                compliance_requirement=None, photo_category=None, notes=None): 
    """Add a document for a vehicle with enhanced tracking"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Use the existing schema: vehicle_id (call_number), type, filename, upload_date
        # Additional fields will be stored in notes for now since they don't exist in current schema
        additional_info = []
        if compliance_requirement:
            additional_info.append(f"Compliance: {compliance_requirement}")
        if photo_category:
            additional_info.append(f"Photo Category: {photo_category}")
        if notes:
            additional_info.append(f"Notes: {notes}")
        
        combined_notes = "; ".join(additional_info) if additional_info else None
        
        # Determine full insert strategy (legacy + new columns)
        cols = [row[1] for row in cursor.execute("PRAGMA table_info(documents)").fetchall()]
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if {'file_path','document_name','document_type','uploaded_at','uploaded_by'}.issubset(set(cols)):
            # Newer schema present – insert richer row
            query = """
                INSERT INTO documents (vehicle_id, towbook_call_number, document_name, document_type, file_path, uploaded_by, uploaded_at, compliance_requirement)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (call_number, call_number, document_name, document_type, file_path, uploaded_by, ts, compliance_requirement)
            cursor.execute(query, params)
        else:
            # Fallback legacy minimal insert
            query = """
                INSERT INTO documents (vehicle_id, type, filename, upload_date)
                VALUES (?, ?, ?, ?)
            """
            params = (call_number, document_type, file_path, ts)
            cursor.execute(query, params)
        conn.commit()
        doc_id = cursor.lastrowid
        
        # If we have additional info and the doc was created successfully, 
        # we could store it elsewhere or log it
        if doc_id and combined_notes:
            print(f"Document {doc_id} created with additional info: {combined_notes}")
        
        conn.close()
        return doc_id
    except Exception as e:
        print(f"Error adding document for vehicle call_number {call_number}: {e}")
        return None

def get_vehicle_documents(call_number):
    """Get all documents for a vehicle by call number"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Use the existing schema
        query = """
            SELECT id, filename, type, upload_date, sent_to
            FROM documents
            WHERE vehicle_id = ?
            ORDER BY upload_date DESC
        """
        cursor.execute(query, (call_number,))
        documents = cursor.fetchall()
        
        # Convert to list of dictionaries with consistent naming
        document_list = []
        for doc in documents:
            document_list.append({
                'id': doc['id'],
                'document_name': doc['filename'],  # Map filename to document_name
                'document_type': doc['type'] or 'General',  # Map type to document_type
                'file_path': doc['filename'],  # Use filename as file_path
                'uploaded_at': doc['upload_date'] or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'uploaded_by': doc['sent_to'] or 'System'  # Map sent_to to uploaded_by
            })
        
        conn.close()    
        return document_list
        
    except Exception as e:
        print(f"Error getting documents for vehicle {call_number}: {e}")
        return []

def delete_vehicle_document(document_id, call_number=None):
    """Delete a vehicle document by ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get document info before deleting - use existing schema
        cursor.execute("SELECT filename FROM documents WHERE id = ?", (document_id,))
        doc_info = cursor.fetchone()
        
        if not doc_info:
            conn.close()
            return False, "Document not found"
            
        # Delete from database
        cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        conn.commit()
        
        # Try to delete the physical file
        try:
            file_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'uploads', 'documents', doc_info['filename'])
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Could not delete document file {doc_info['filename']}: {e}")
        
        conn.close()
        return True, f"Document '{doc_info['filename']}' deleted successfully"
        
    except Exception as e:
        print(f"Error deleting document {document_id}: {e}")
        return False, f"Database error: {str(e)}"

def update_document_delivery_status(document_id, sent_to=None, sent_via=None, tracking_number=None, delivery_confirmed=False):
    """Update document delivery tracking information"""
    try:
        conn = get_db_connection()
        
        update_fields = []
        params = []
        
        if sent_to is not None:
            update_fields.append("sent_to = ?")
            params.append(sent_to)
            
        if sent_via is not None:
            update_fields.append("sent_via = ?")
            params.append(sent_via)
            update_fields.append("sent_date = ?")
            params.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            
        if tracking_number is not None:
            update_fields.append("tracking_number = ?")
            params.append(tracking_number)
            
        if delivery_confirmed:
            update_fields.append("delivery_confirmed = ?")
            params.append(delivery_confirmed)
        
        if not update_fields:
            return False
            
        query = f"UPDATE documents SET {', '.join(update_fields)} WHERE id = ?"
        params.append(document_id)
        
        with conn:
            cursor = conn.execute(query, params)
            updated = cursor.rowcount > 0
            
        conn.close()
        return updated
        
    except Exception as e:
        print(f"Error updating document delivery status: {e}")
        return False

# ---------------------- Communications Helpers (Package Version) ----------------------

def log_document_communication(document_id, vehicle_id, towbook_call_number, method, destination,
                               status='pending', subject=None, message_preview=None, contact_id=None,
                               jurisdiction=None, tracking_number=None, error=None, provider_message_id=None,
                               attachment_path=None):
    """Log a communication attempt (email/fax/sms) for a document.

    Returns the new communication id or None on failure.
    """
    try:
        conn = get_db_connection()
        query = ("INSERT INTO communications (document_id, vehicle_id, towbook_call_number, contact_id, jurisdiction, method, "
                 "destination, subject, message_preview, attachment_path, status, error, tracking_number, provider_message_id, sent_at) "
                 "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)")
        sent_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S') if status == 'sent' else None
        params = (document_id, vehicle_id, towbook_call_number, contact_id, jurisdiction, method, destination,
                  subject, (message_preview[:500] if message_preview else None), attachment_path, status, error,
                  tracking_number, provider_message_id, sent_at)
        with conn:
            cur = conn.execute(query, params)
            return cur.lastrowid
    except Exception as e:
        print(f"Error logging communication: {e}")
        return None

def update_communication_status(comm_id, status, error=None, provider_message_id=None):
    try:
        conn = get_db_connection()
        fields = ["status = ?"]
        params = [status]
        if error is not None:
            fields.append("error = ?"); params.append(error)
        if provider_message_id is not None:
            fields.append("provider_message_id = ?"); params.append(provider_message_id)
        if status == 'sent':
            fields.append("sent_at = ?"); params.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        sql = f"UPDATE communications SET {', '.join(fields)} WHERE id = ?"
        params.append(comm_id)
        with conn:
            conn.execute(sql, params)
        return True
    except Exception as e:
        print(f"Error updating communication {comm_id}: {e}")
        return False

def get_document_communications(document_id):
    try:
        conn = get_db_connection()
        rows = conn.execute("SELECT * FROM communications WHERE document_id = ? ORDER BY created_at DESC", (document_id,)).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"Error fetching communications for document {document_id}: {e}")
        return []

def get_vehicle_communications(towbook_call_number):
    try:
        conn = get_db_connection()
        rows = conn.execute("SELECT * FROM communications WHERE towbook_call_number = ? ORDER BY created_at DESC", (towbook_call_number,)).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"Error fetching communications for vehicle {towbook_call_number}: {e}")
        return []

# Auction management functions
def create_auction(auction_date, auction_house, advertisement_date=None, newspaper_name=None, notes=None):
    """Create a new auction"""
    try:
        conn = get_db_connection()
        
        # Use the updated auction table schema with all new columns
        query = """
            INSERT INTO auctions (auction_date, auction_house, advertisement_date, newspaper_name, notes, status, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            auction_date, 
            auction_house,
            advertisement_date,
            newspaper_name,
            notes,
            'Scheduled',
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        
        with conn:
            cursor = conn.execute(query, params)
            auction_id = cursor.lastrowid
            
        conn.close()
        return auction_id
        
    except Exception as e:
        print(f"Error creating auction: {e}")
        return None

def add_vehicle_to_auction(auction_id, vehicle_call_number, lot_number=None):
    """Add a vehicle to an auction"""
    try:
        conn = get_db_connection()
        # Discover auction_vehicles schema
        av_cols = {row[1] for row in conn.execute("PRAGMA table_info(auction_vehicles)").fetchall()}
        if not av_cols:
            print("auction_vehicles table missing; cannot add vehicle")
            conn.close()
            return False

        # Fetch vehicle id
        v_row = conn.execute("SELECT id, towbook_call_number FROM vehicles WHERE towbook_call_number = ?", (vehicle_call_number,)).fetchone()
        if not v_row:
            print(f"Vehicle with call number {vehicle_call_number} not found")
            conn.close()
            return False
        vehicle_id = v_row['id'] if isinstance(v_row, sqlite3.Row) else v_row[0]

        # Existence check
        if 'vehicle_id' in av_cols:
            existing = conn.execute("SELECT 1 FROM auction_vehicles WHERE auction_id = ? AND vehicle_id = ?", (auction_id, vehicle_id)).fetchone()
        else:
            existing = conn.execute("SELECT 1 FROM auction_vehicles WHERE auction_id = ? AND vehicle_call_number = ?", (auction_id, vehicle_call_number)).fetchone()
        if existing:
            print(f"Vehicle {vehicle_call_number} is already in auction {auction_id}")
            conn.close()
            return False

        # Build dynamic insert
        cols = ['auction_id']
        vals = [auction_id]
        qmarks = ['?']
        if 'vehicle_id' in av_cols:
            cols.append('vehicle_id'); vals.append(vehicle_id); qmarks.append('?')
        if 'vehicle_call_number' in av_cols:
            cols.append('vehicle_call_number'); vals.append(vehicle_call_number); qmarks.append('?')
        if 'lot_number' in av_cols:
            cols.append('lot_number'); vals.append(lot_number); qmarks.append('?')
        if 'status' in av_cols:
            cols.append('status'); vals.append('Scheduled'); qmarks.append('?')
        insert_sql = f"INSERT INTO auction_vehicles ({', '.join(cols)}) VALUES ({', '.join(qmarks)})"

        with conn:
            conn.execute(insert_sql, tuple(vals))
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding vehicle to auction: {e}")
        return False

def remove_vehicle_from_auction(auction_id, vehicle_call_number):
    """Remove a vehicle from an auction"""
    try:
        conn = get_db_connection()
        
        # Check if vehicle is in this auction
        check_query = "SELECT 1 FROM auction_vehicles WHERE auction_id = ? AND vehicle_call_number = ?"
        existing = conn.execute(check_query, (auction_id, vehicle_call_number)).fetchone()
        
        if not existing:
            print(f"Vehicle {vehicle_call_number} is not in auction {auction_id}")
            conn.close()
            return False
        
        # Remove the vehicle from the auction
        delete_query = "DELETE FROM auction_vehicles WHERE auction_id = ? AND vehicle_call_number = ?"
        
        with conn:
            conn.execute(delete_query, (auction_id, vehicle_call_number))
            
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error removing vehicle from auction: {e}")
        return False

def get_auctions(status=None):
    """Get auctions, optionally filtered by status"""
    try:
        conn = get_db_connection()
        
        if status:
            query = "SELECT * FROM auctions WHERE status = ? ORDER BY auction_date DESC"
            params = (status,)
        else:
            query = "SELECT * FROM auctions ORDER BY auction_date DESC"
            params = ()
            
        cursor = conn.execute(query, params)
        auctions = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return auctions
        
    except Exception as e:
        print(f"Error getting auctions: {e}")
        return []

def get_auction_vehicles(auction_id):
    """Get vehicles in an auction"""
    try:
        conn = get_db_connection()
        
        query = """
            SELECT av.*, v.*
            FROM auction_vehicles av
            JOIN vehicles v ON av.vehicle_call_number = v.towbook_call_number
            WHERE av.auction_id = ?
            ORDER BY av.lot_number, v.towbook_call_number
        """
        cursor = conn.execute(query, (auction_id,))
        vehicles = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return vehicles
        
    except Exception as e:
        print(f"Error getting auction vehicles: {e}")
        return []

def add_auction_document(auction_id, document_name, document_type, document_category, file_path, uploaded_by='System'):
    """Add a document to an auction (e.g., newspaper receipts, auction house papers)"""
    try:
        conn = get_db_connection()
        
        query = """
            INSERT INTO documents (auction_id, document_name, document_type, document_category, 
                                 file_path, uploaded_by, uploaded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            auction_id, document_name, document_type, document_category,
            file_path, uploaded_by, datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        with conn:
            cursor = conn.execute(query, params)
            doc_id = cursor.lastrowid
        
        conn.close()
        print(f"Auction document '{document_name}' added for auction {auction_id} by {uploaded_by}. Doc ID: {doc_id}")
        return doc_id
    except Exception as e:
        print(f"Error adding auction document for auction {auction_id}: {e}")
        return None

# Document cluster management functions  
def create_document_cluster(cluster_name, jurisdiction, cluster_type, created_by):
    """Create a new document cluster"""
    try:
        conn = get_db_connection()
        
        query = """
            INSERT INTO document_clusters (cluster_name, jurisdiction, cluster_type, created_by, created_at)
            VALUES (?, ?, ?, ?, ?)
        """
        params = (cluster_name, jurisdiction, cluster_type, created_by, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        with conn:
            cursor = conn.execute(query, params)
            cluster_id = cursor.lastrowid
            
        conn.close()
        return cluster_id
        
    except Exception as e:
        print(f"Error creating document cluster: {e}")
        return None

def add_document_to_cluster(cluster_id, document_id):
    """Add a document to a cluster"""
    try:
        conn = get_db_connection()
        
        query = """
            INSERT INTO cluster_documents (cluster_id, document_id, added_at)
            VALUES (?, ?, ?)
        """
        params = (cluster_id, document_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        with conn:
            conn.execute(query, params)
            
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error adding document to cluster: {e}")
        return False

def get_document_clusters(jurisdiction=None):
    """Get document clusters, optionally filtered by jurisdiction"""
    try:
        conn = get_db_connection()
        
        if jurisdiction:
            query = "SELECT * FROM document_clusters WHERE jurisdiction = ? ORDER BY created_at DESC"
            params = (jurisdiction,)
        else:
            query = "SELECT * FROM document_clusters ORDER BY created_at DESC"
            params = ()
            
        cursor = conn.execute(query, params)
        clusters = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return clusters
        
    except Exception as e:
        print(f"Error getting document clusters: {e}")
        return []

def get_cluster_documents(cluster_id):
    """Get documents in a cluster"""
    try:
        conn = get_db_connection()
        
        query = """
            SELECT cd.*, d.document_name, d.document_type, d.file_path, d.towbook_call_number
            FROM cluster_documents cd
            JOIN documents d ON cd.document_id = d.id
            WHERE cd.cluster_id = ?
        """
        cursor = conn.execute(query, (cluster_id,))
        documents = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return documents
        
    except Exception as e:
        print(f"Error getting cluster documents: {e}")
        return []

def delete_auction(auction_id):
    """Delete an auction and remove all associated vehicles from auction_vehicles table"""
    try:
        conn = get_db_connection()
        
        # First, remove all vehicles from this auction
        conn.execute("DELETE FROM auction_vehicles WHERE auction_id = ?", (auction_id,))
        
        # Then delete the auction itself
        cursor = conn.execute("DELETE FROM auctions WHERE id = ?", (auction_id,))
        
        if cursor.rowcount > 0:
            conn.commit()
            conn.close()
            print(f"Deleted auction {auction_id} and removed associated vehicles")
            return True
        else:
            conn.close()
            print(f"No auction found with ID {auction_id}")
            return False
            
    except Exception as e:
        print(f"Error deleting auction {auction_id}: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False
