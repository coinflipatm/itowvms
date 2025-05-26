#!/usr/bin/env python3

from generator import PDFGenerator
import os

def test_tr208():
    print("Starting TR208 test...")
    
    try:
        generator = PDFGenerator()
        print("✅ Generator created successfully")
        
        vehicle_data = {
            'year': '2015',
            'make': 'Honda', 
            'model': 'Civic',
            'vin': '1HGBH41JXMN109186',
            'color': 'Blue',
            'complaint_number': 'COMP123',
            'tow_date': '2024-01-15',
            'condition_notes': 'Vehicle is severely damaged, inoperable',
            'inoperable': 1,
            'damage_extent': 'Extensive',
            'jurisdiction': 'Clio Police',
            'case_number': 'CASE456'
        }
        
        print("Testing TR208 generation...")
        success, message = generator.generate_tr208_form(vehicle_data, 'test_tr208.pdf')
        print(f"Result: success={success}, message={message}")
        
        if success:
            if os.path.exists('test_tr208.pdf'):
                size = os.path.getsize('test_tr208.pdf')
                print(f"✅ SUCCESS: PDF created with {size} bytes")
                return True
            else:
                print("❌ Success reported but no file found")
                return False
        else:
            print(f"❌ FAILED: {message}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_tr208()
