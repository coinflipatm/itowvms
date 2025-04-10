import sqlite3
import os

# Get the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(current_dir, "vehicles.db")

def query_vehicle_status():
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Execute the query
        cursor.execute("SELECT status, COUNT(*) as count FROM vehicles GROUP BY status")
        
        # Fetch all results
        results = cursor.fetchall()
        
        # Close the connection
        conn.close()
        
        # Print results
        print("\nVehicle Status Counts:")
        print("---------------------")
        
        try:
            # Try to use tabulate for nice formatting if installed
            headers = ["Status", "Count"]
            print(tabulate(results, headers=headers, tablefmt="simple"))
        except NameError:
            # Fallback to basic formatting if tabulate is not installed
            print("Status\t\tCount")
            print("----------------------")
            for row in results:
                print(f"{row[0]}\t\t{row[1]}")
                
        print("\n")
            
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    query_vehicle_status()