import sqlite3
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DATABASE_NAME = 'vehicles.db'

def get_database_path():
    # Get the directory where this script is located
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Define the database file path
    db_path = os.path.join(base_dir, DATABASE_NAME)
    return db_path

def column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns

def add_timestamp_column_if_not_exists(db_path, table_name, column_name):
    """Adds a TEXT column (typically for timestamps) if it doesn't exist,
       handling SQLite's non-constant default limitation for ALTER TABLE.
    """
    conn = None  # Initialize conn to None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        if not column_exists(cursor, table_name, column_name):
            logging.info(f"Column '{column_name}' does not exist in table '{table_name}'. Attempting to add.")
            try:
                # Try adding with DEFAULT CURRENT_TIMESTAMP first (works on newer SQLite versions for ALTER TABLE)
                alter_query_with_default = f"ALTER TABLE {table_name} ADD COLUMN {column_name} TEXT DEFAULT CURRENT_TIMESTAMP"
                cursor.execute(alter_query_with_default)
                logging.info(f"Successfully added column '{column_name}' with DEFAULT CURRENT_TIMESTAMP to table '{table_name}'.")
            except sqlite3.OperationalError as e:
                # Check if the error is specifically about non-constant default
                if "cannot add a column with non-constant default" in str(e).lower():
                    logging.warning(f"SQLite version does not support non-constant default for ALTER TABLE on '{column_name}'. "
                                    f"Adding column as TEXT and then updating existing rows to CURRENT_TIMESTAMP.")
                    
                    # Add the column as TEXT (allowing NULLs)
                    alter_query_no_default = f"ALTER TABLE {table_name} ADD COLUMN {column_name} TEXT"
                    cursor.execute(alter_query_no_default)
                    logging.info(f"Added column '{column_name}' as TEXT to table '{table_name}'.")
                    
                    # Now, update existing rows where this new column is NULL to CURRENT_TIMESTAMP
                    update_query = f"UPDATE {table_name} SET {column_name} = CURRENT_TIMESTAMP WHERE {column_name} IS NULL"
                    cursor.execute(update_query)
                    logging.info(f"Updated existing NULL values in '{column_name}' to CURRENT_TIMESTAMP for table '{table_name}'.")
                else:
                    # If it's a different OperationalError, re-raise it
                    logging.error(f"An unexpected OperationalError occurred while adding column '{column_name}': {e}")
                    raise # Re-raise other operational errors
            conn.commit()
        else:
            logging.info(f"Column '{column_name}' already exists in table '{table_name}'. No action taken.")

    except sqlite3.Error as e:
        # Log other SQLite errors
        logging.error(f"SQLite error while trying to modify table '{table_name}' for column '{column_name}' in database {db_path}: {e}")
    finally:
        if conn:
            conn.close()

def add_text_column_if_not_exists(db_path, table_name, column_name, default_value=None):
    """Adds a TEXT column if it doesn't exist.
       Optionally, a default value can be specified.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        if not column_exists(cursor, table_name, column_name):
            logging.info(f"Column '{column_name}' does not exist in table '{table_name}'. Attempting to add.")
            alter_query = f"ALTER TABLE {table_name} ADD COLUMN {column_name} TEXT"
            if default_value is not None:
                # Ensure default_value is properly quoted if it's a string
                alter_query += f" DEFAULT '{default_value}'"
            
            cursor.execute(alter_query)
            logging.info(f"Successfully added column '{column_name}' to table '{table_name}'" + (f" with default value '{default_value}'." if default_value else "."))
            conn.commit()
        else:
            logging.info(f"Column '{column_name}' already exists in table '{table_name}'. No action taken.")

    except sqlite3.Error as e:
        logging.error(f"SQLite error while trying to add column '{column_name}' to table '{table_name}' in database {db_path}: {e}")
    finally:
        if conn:
            conn.close()

def add_integer_column_if_not_exists(db_path, table_name, column_name, default_value=None):
    """Adds an INTEGER column if it doesn't exist.
       Optionally, a default value can be specified.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        if not column_exists(cursor, table_name, column_name):
            logging.info(f"Column '{column_name}' does not exist in table '{table_name}'. Attempting to add.")
            alter_query = f"ALTER TABLE {table_name} ADD COLUMN {column_name} INTEGER"
            if default_value is not None:
                alter_query += f" DEFAULT {default_value}" # No quotes for integer defaults
            
            cursor.execute(alter_query)
            logging.info(f"Successfully added column '{column_name}' to table '{table_name}'" + (f" with default value {default_value}." if default_value is not None else "."))
            conn.commit()
        else:
            logging.info(f"Column '{column_name}' already exists in table '{table_name}'. No action taken.")

    except sqlite3.Error as e:
        logging.error(f"SQLite error while trying to add column '{column_name}' to table '{table_name}' in database {db_path}: {e}")
    finally:
        if conn:
            conn.close()

def apply_schema_changes():
    """Applies the necessary schema changes to the database."""
    db_path = get_database_path()

    if not os.path.exists(db_path):
        logging.error(f"Database file not found at {db_path}. Please ensure the database exists and the script is in the correct directory relative to the DB.")
        return

    logging.info(f"Attempting to apply schema changes to {db_path}...")

    # Add created_at to notifications table
    add_timestamp_column_if_not_exists(db_path, 'notifications', 'created_at')

    # Add updated_at to notifications table
    add_timestamp_column_if_not_exists(db_path, 'notifications', 'updated_at')

    # Add tow_reason to vehicles table
    add_text_column_if_not_exists(db_path, 'vehicles', 'tow_reason')

    # Add new fields to vehicles table
    add_text_column_if_not_exists(db_path, 'vehicles', 'tr52_form_sent_date')
    add_text_column_if_not_exists(db_path, 'vehicles', 'tr208_form_sent_date')
    add_text_column_if_not_exists(db_path, 'vehicles', 'top_form_sent_date')
    add_integer_column_if_not_exists(db_path, 'vehicles', 'tr52_notification_sent', default_value=0)
    add_integer_column_if_not_exists(db_path, 'vehicles', 'tr208_notification_sent', default_value=0)
    # last_updated is typically handled by add_timestamp_column_if_not_exists or similar logic if it needs a default like CURRENT_TIMESTAMP
    # If it's just a TEXT field updated by the app, add_text_column_if_not_exists is fine.
    # Assuming 'last_updated' in 'vehicles' is already handled or added as TEXT. If it needs specific default, adjust.
    add_timestamp_column_if_not_exists(db_path, 'vehicles', 'last_updated')


    # Add new fields to documents table
    add_text_column_if_not_exists(db_path, 'documents', 'sent_date')
    add_text_column_if_not_exists(db_path, 'documents', 'sent_to')
    add_text_column_if_not_exists(db_path, 'documents', 'sent_method')


    logging.info("Schema update process finished.")

if __name__ == '__main__':
    apply_schema_changes()
