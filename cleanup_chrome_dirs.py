#!/usr/bin/env python3
"""
Chrome User Data Directory Cleanup Script
This script removes old Chrome user data directories created by the scraper
to prevent conflicts when starting new scraping sessions.
"""

import os
import shutil
import glob
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def cleanup_chrome_dirs(base_dir=None, age_hours=1):
    """
    Clean up chrome user data directories that are older than the specified age.
    
    Args:
        base_dir: Base directory to search for Chrome user data dirs (defaults to current directory)
        age_hours: Directories older than this many hours will be removed (default: 1)
    """
    if not base_dir:
        base_dir = os.getcwd()
    
    # Find all chrome_user_data directories
    chrome_dirs = glob.glob(os.path.join(base_dir, "chrome_user_data_*"))
    
    if not chrome_dirs:
        logging.info("No Chrome user data directories found.")
        return 0
    
    removed_count = 0
    current_time = time.time()
    cutoff_time = current_time - (age_hours * 3600)  # Convert hours to seconds
    
    logging.info(f"Found {len(chrome_dirs)} Chrome user data directories")
    
    for directory in chrome_dirs:
        try:
            # Check if directory is older than cutoff time
            if os.path.isdir(directory) and os.path.getmtime(directory) < cutoff_time:
                logging.info(f"Removing old directory: {directory}")
                shutil.rmtree(directory, ignore_errors=True)
                removed_count += 1
            else:
                logging.info(f"Keeping recent directory: {directory}")
        except Exception as e:
            logging.error(f"Error processing directory {directory}: {e}")
    
    logging.info(f"Cleanup complete. Removed {removed_count} directories.")
    return removed_count

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up Chrome user data directories created by the scraper")
    parser.add_argument("--age", type=float, default=1,
                        help="Remove directories older than this many hours (default: 1)")
    parser.add_argument("--dir", type=str, default=None,
                        help="Base directory to search (default: current directory)")
    
    args = parser.parse_args()
    
    removed = cleanup_chrome_dirs(args.dir, args.age)
    print(f"Removed {removed} old Chrome user data directories")