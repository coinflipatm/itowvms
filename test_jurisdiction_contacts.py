#!/usr/bin/env python3
"""
Test script for the comprehensive jurisdiction contacts system
Tests all the enhanced functionality including jurisdiction dropdowns,
contact management, and enhanced UI components.
"""

import requests
import json
import sqlite3
import os
from datetime import datetime

# Configuration
BASE_URL = "http://127.0.0.1:5001"
DB_PATH = "/workspaces/itowvms/vehicles.db"

def test_database_schema():
    """Test that the database schema has been updated correctly"""
    print("=" * 60)
    print("TESTING DATABASE SCHEMA")
    print("=" * 60)
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check contacts table schema
        cursor.execute("PRAGMA table_info(contacts)")
        columns = cursor.fetchall()
        
        expected_columns = {
            'preferred_contact_method', 'secondary_contact_method', 'contact_hours',
            'department', 'mobile_number', 'contact_title', 'emergency_contact',
            'active', 'last_contacted'
        }
        
        existing_columns = {col['name'] for col in columns}
        
        print(f"✓ Contacts table has {len(columns)} columns")
        
        missing_columns = expected_columns - existing_columns
        if missing_columns:
            print(f"✗ Missing columns: {missing_columns}")
            return False
        else:
            print("✓ All new contact fields present")
            
        # Display schema
        print("\nContacts table schema:")
        for col in columns:
            print(f"  - {col['name']}: {col['type']}")
            
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Database schema test failed: {e}")
        return False

def test_api_endpoints():
    """Test API endpoints for jurisdictions and contacts"""
    print("\n" + "=" * 60)
    print("TESTING API ENDPOINTS")
    print("=" * 60)
    
    try:
        # Test jurisdictions endpoint
        response = requests.get(f"{BASE_URL}/api/jurisdictions")
        if response.status_code == 200:
            jurisdictions = response.json()
            print(f"✓ Jurisdictions API working - {len(jurisdictions)} jurisdictions available")
            print(f"  Sample jurisdictions: {jurisdictions[:3]}...")
        else:
            print(f"✗ Jurisdictions API failed: {response.status_code}")
            return False
            
        # Test contacts endpoint
        response = requests.get(f"{BASE_URL}/api/contacts")
        if response.status_code == 200:
            contacts = response.json()
            print(f"✓ Contacts API working - {len(contacts)} contacts found")
        else:
            print(f"✗ Contacts API failed: {response.status_code}")
            return False
            
        return True
        
    except Exception as e:
        print(f"✗ API endpoints test failed: {e}")
        return False

def test_add_sample_contact():
    """Test adding a new contact with enhanced fields"""
    print("\n" + "=" * 60)
    print("TESTING CONTACT CREATION")
    print("=" * 60)
    
    try:
        # Create a comprehensive test contact
        contact_data = {
            "jurisdiction": "Flint Township",
            "contact_name": "John Smith",
            "contact_title": "Police Chief",
            "department": "Police Department",
            "phone_number": "810-555-0123",
            "mobile_number": "810-555-0124",
            "email_address": "jsmith@flinttownship.org",
            "fax_number": "810-555-0125",
            "preferred_contact_method": "email",
            "secondary_contact_method": "phone",
            "contact_hours": "8:00 AM - 4:30 PM",
            "address": "5200 Norko Dr, Flint Township, MI 48507",
            "notes": "Primary contact for towing requests. Prefers email communication during business hours.",
            "emergency_contact": True,
            "active": True
        }
        
        response = requests.post(f"{BASE_URL}/api/contacts", json=contact_data)
        
        if response.status_code == 201:
            result = response.json()
            contact_id = result.get('id')
            print(f"✓ Contact created successfully with ID: {contact_id}")
            
            # Verify the contact was created with all fields
            response = requests.get(f"{BASE_URL}/api/contacts/{contact_id}")
            if response.status_code == 200:
                contact = response.json()
                print("✓ Contact retrieved successfully")
                print(f"  Name: {contact.get('contact_name')} ({contact.get('contact_title')})")
                print(f"  Department: {contact.get('department')}")
                print(f"  Preferred method: {contact.get('preferred_contact_method')}")
                print(f"  Emergency contact: {contact.get('emergency_contact')}")
                print(f"  Active: {contact.get('active')}")
                return contact_id
            else:
                print(f"✗ Failed to retrieve created contact: {response.status_code}")
                return False
        else:
            print(f"✗ Failed to create contact: {response.status_code}")
            if response.content:
                print(f"  Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Contact creation test failed: {e}")
        return False

def test_update_contact(contact_id):
    """Test updating a contact with new fields"""
    print("\n" + "=" * 60)
    print("TESTING CONTACT UPDATE")
    print("=" * 60)
    
    try:
        update_data = {
            "contact_hours": "7:00 AM - 5:00 PM",
            "notes": "Updated: Now handles emergency calls 24/7. Primary contact for all towing operations.",
            "secondary_contact_method": "text",
            "mobile_number": "810-555-9999"
        }
        
        response = requests.put(f"{BASE_URL}/api/contacts/{contact_id}", json=update_data)
        
        if response.status_code == 200:
            print("✓ Contact updated successfully")
            
            # Verify the update
            response = requests.get(f"{BASE_URL}/api/contacts/{contact_id}")
            if response.status_code == 200:
                contact = response.json()
                print(f"✓ Updated hours: {contact.get('contact_hours')}")
                print(f"✓ Updated mobile: {contact.get('mobile_number')}")
                print(f"✓ Updated secondary method: {contact.get('secondary_contact_method')}")
                return True
            else:
                print(f"✗ Failed to retrieve updated contact: {response.status_code}")
                return False
        else:
            print(f"✗ Failed to update contact: {response.status_code}")
            if response.content:
                print(f"  Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Contact update test failed: {e}")
        return False

def test_contact_search():
    """Test contact search and filtering functionality"""
    print("\n" + "=" * 60)
    print("TESTING CONTACT SEARCH")
    print("=" * 60)
    
    try:
        # Search by jurisdiction
        response = requests.get(f"{BASE_URL}/api/contacts?jurisdiction=Flint Township")
        if response.status_code == 200:
            contacts = response.json()
            print(f"✓ Jurisdiction search working - found {len(contacts)} contacts")
        else:
            print(f"✗ Jurisdiction search failed: {response.status_code}")
            return False
            
        # Search active contacts only
        response = requests.get(f"{BASE_URL}/api/contacts?active=true")
        if response.status_code == 200:
            contacts = response.json()
            print(f"✓ Active contacts filter working - found {len(contacts)} active contacts")
        else:
            print(f"✗ Active contacts filter failed: {response.status_code}")
            return False
            
        return True
        
    except Exception as e:
        print(f"✗ Contact search test failed: {e}")
        return False

def test_vehicle_jurisdiction_dropdown():
    """Test that vehicle forms use jurisdiction dropdowns"""
    print("\n" + "=" * 60)
    print("TESTING VEHICLE JURISDICTION INTEGRATION")
    print("=" * 60)
    
    try:
        # Get the main page HTML to check for jurisdiction dropdowns
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            html_content = response.text
            
            # Check for jurisdiction select elements in vehicle forms
            if 'id="add-jurisdiction"' in html_content and 'class="form-select"' in html_content:
                print("✓ Add vehicle form has jurisdiction dropdown")
            else:
                print("✗ Add vehicle form missing jurisdiction dropdown")
                return False
                
            if 'id="edit-jurisdiction"' in html_content and 'class="form-select"' in html_content:
                print("✓ Edit vehicle form has jurisdiction dropdown")
            else:
                print("✗ Edit vehicle form missing jurisdiction dropdown")
                return False
                
            print("✓ Vehicle forms properly configured for jurisdiction dropdowns")
            return True
        else:
            print(f"✗ Failed to load main page: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Vehicle jurisdiction integration test failed: {e}")
        return False

def test_frontend_components():
    """Test that frontend JavaScript components are properly loaded"""
    print("\n" + "=" * 60)
    print("TESTING FRONTEND COMPONENTS")
    print("=" * 60)
    
    try:
        # Get the main page to check for contact modal HTML
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            html_content = response.text
            
            # Check for contact modals
            if 'id="addContactModal"' in html_content:
                print("✓ Add Contact modal present")
            else:
                print("✗ Add Contact modal missing")
                return False
                
            if 'id="editContactModal"' in html_content:
                print("✓ Edit Contact modal present")
            else:
                print("✗ Edit Contact modal missing")
                return False
                
            # Check for enhanced contact form fields
            contact_fields = [
                'add-contact-title', 'add-contact-department', 'add-contact-mobile',
                'add-contact-preferred-method', 'add-contact-secondary-method',
                'add-contact-hours', 'add-contact-emergency', 'add-contact-active'
            ]
            
            missing_fields = []
            for field in contact_fields:
                if f'id="{field}"' not in html_content:
                    missing_fields.append(field)
                    
            if missing_fields:
                print(f"✗ Missing contact form fields: {missing_fields}")
                return False
            else:
                print("✓ All enhanced contact form fields present")
                
            print("✓ Frontend components properly configured")
            return True
        else:
            print(f"✗ Failed to load main page: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Frontend components test failed: {e}")
        return False

def run_all_tests():
    """Run all jurisdiction contacts system tests"""
    print("JURISDICTION CONTACTS SYSTEM - COMPREHENSIVE TEST")
    print("=" * 80)
    print(f"Test started at: {datetime.now()}")
    print(f"Testing against: {BASE_URL}")
    print("=" * 80)
    
    results = []
    
    # Run all tests
    results.append(("Database Schema", test_database_schema()))
    results.append(("API Endpoints", test_api_endpoints()))
    
    contact_id = test_add_sample_contact()
    results.append(("Contact Creation", bool(contact_id)))
    
    if contact_id:
        results.append(("Contact Update", test_update_contact(contact_id)))
    else:
        results.append(("Contact Update", False))
        
    results.append(("Contact Search", test_contact_search()))
    results.append(("Vehicle Integration", test_vehicle_jurisdiction_dropdown()))
    results.append(("Frontend Components", test_frontend_components()))
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name:<30} {status:>10}")
        if result:
            passed += 1
            
    print("-" * 40)
    print(f"Tests passed: {passed}/{total}")
    print(f"Success rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Jurisdiction contacts system is fully functional.")
    else:
        print(f"\n⚠️  {total-passed} test(s) failed. Please review the issues above.")
        
    print("=" * 80)

if __name__ == "__main__":
    run_all_tests()
