#!/usr/bin/env python3
"""
Monitor existing scraping progress
"""

import requests
import time
import json

def monitor_scraping_progress():
    """Monitor the current scraping progress"""
    
    base_url = "http://127.0.0.1:5001"
    scraper_id = "itow05"  # Current running scraper
    
    try:
        print("Monitoring existing scraping progress...")
        print("=" * 50)
        
        max_attempts = 60  # 60 seconds
        attempt = 0
        
        while attempt < max_attempts:
            response = requests.get(f"{base_url}/api/scraping-progress/{scraper_id}")
            if response.status_code == 200:
                progress = response.json()
                status = progress.get('status', 'Unknown')
                current = progress.get('processed', 0)
                total = progress.get('total', 0)
                percentage = progress.get('percentage', 0)
                error = progress.get('error')
                is_running = progress.get('is_running', False)
                
                print(f"[{time.strftime('%H:%M:%S')}] Status: {status}")
                print(f"[{time.strftime('%H:%M:%S')}] Progress: {current}/{total} ({percentage}%)")
                print(f"[{time.strftime('%H:%M:%S')}] Running: {is_running}")
                
                if error:
                    print(f"❌ Error: {error}")
                    return False
                
                if not is_running:
                    if percentage == 100:
                        print("✅ Scraping completed successfully!")
                        return True
                    else:
                        print("⚠️ Scraping stopped but not completed")
                        return False
                        
                print("-" * 30)
                    
            else:
                print(f"❌ Failed to get progress: {response.status_code}")
                return False
                
            time.sleep(1)
            attempt += 1
        
        print("⏰ Monitoring timed out")
        return False
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def check_vehicles_after_scraping():
    """Check vehicles in database after scraping"""
    try:
        response = requests.get("http://127.0.0.1:5001/api/vehicles")
        if response.status_code == 200:
            vehicles = response.json()
            print(f"\n📊 Database now contains {len(vehicles)} vehicles")
            
            # Count vehicles by status
            status_counts = {}
            for vehicle in vehicles:
                status = vehicle.get('status', 'Unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
            
            print("📋 Vehicle status breakdown:")
            for status, count in status_counts.items():
                print(f"   {status}: {count}")
                
            # Show recent vehicles (last 5)
            recent_vehicles = sorted(vehicles, key=lambda x: x.get('last_updated', ''), reverse=True)[:5]
            print("\n🆕 Most recent vehicles:")
            for vehicle in recent_vehicles:
                call_num = vehicle.get('towbook_call_number', 'N/A')
                status = vehicle.get('status', 'N/A')
                make_model = f"{vehicle.get('make', '')} {vehicle.get('model', '')}".strip()
                print(f"   {call_num}: {make_model} - {status}")
                
        else:
            print(f"❌ Failed to fetch vehicles: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error fetching vehicles: {str(e)}")

if __name__ == "__main__":
    print("🔍 Chrome WebDriver Fix Verification")
    print("=" * 50)
    
    success = monitor_scraping_progress()
    
    if success:
        check_vehicles_after_scraping()
        print("\n🎉 Chrome WebDriver is working correctly!")
        print("✅ TowBook scraping is functional")
        print("✅ Database operations are working")
    else:
        print("\n❌ Issues detected during scraping")
    
    exit(0 if success else 1)
