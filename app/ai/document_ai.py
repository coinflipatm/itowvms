"""
Document AI Engine for iTow VMS

This module provides AI-powered document processing capabilities:
- OCR (Optical Character Recognition) for vehicle documents
- Intelligent form field extraction and validation
- Document classification and routing
- Handwriting recognition and processing
- Automated data entry and verification
"""

import logging
import re
import base64
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import json
import os
from PIL import Image
import io

logger = logging.getLogger(__name__)

@dataclass
class DocumentExtractionResult:
    """Result of document extraction processing"""
    document_type: str
    extracted_fields: Dict[str, Any]
    confidence: float
    validation_status: str
    errors: List[str]
    suggestions: List[str]
    processing_time: float

@dataclass
class OCRResult:
    """Result of OCR processing"""
    text: str
    confidence: float
    bounding_boxes: List[Dict[str, Any]]
    detected_fields: Dict[str, str]
    language: str

@dataclass
class FormField:
    """Extracted form field information"""
    field_name: str
    value: str
    confidence: float
    validation_status: str
    suggested_corrections: List[str]

class DocumentAI:
    """AI-powered document processing and extraction engine"""
    
    def __init__(self, app=None):
        self.app = app
        self.document_templates = self._setup_document_templates()
        self.field_patterns = self._setup_field_patterns()
        self.validation_rules = self._setup_validation_rules()
        self.ocr_engines = self._setup_ocr_engines()
        
        logger.info("DocumentAI initialized")
    
    def process_document(self, image_data: bytes, document_type: str = 'auto') -> DocumentExtractionResult:
        """Process document image and extract structured data"""
        start_time = datetime.now()
        
        try:
            # Detect document type if auto
            if document_type == 'auto':
                document_type = self._detect_document_type(image_data)
            
            # Perform OCR
            ocr_result = self._perform_ocr(image_data)
            
            # Extract structured fields
            extracted_fields = self._extract_fields(ocr_result, document_type)
            
            # Validate extracted data
            validation_result = self._validate_fields(extracted_fields, document_type)
            
            # Calculate overall confidence
            confidence = self._calculate_extraction_confidence(ocr_result, extracted_fields)
            
            # Generate suggestions
            suggestions = self._generate_improvement_suggestions(
                extracted_fields, validation_result, document_type
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return DocumentExtractionResult(
                document_type=document_type,
                extracted_fields=extracted_fields,
                confidence=confidence,
                validation_status=validation_result['status'],
                errors=validation_result['errors'],
                suggestions=suggestions,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return DocumentExtractionResult(
                document_type='unknown',
                extracted_fields={},
                confidence=0.0,
                validation_status='error',
                errors=[f"Processing error: {str(e)}"],
                suggestions=['Try uploading a clearer image'],
                processing_time=processing_time
            )
    
    def extract_vehicle_info(self, image_data: bytes) -> Dict[str, Any]:
        """Extract vehicle information from registration or title documents"""
        try:
            ocr_result = self._perform_ocr(image_data)
            vehicle_fields = {}
            
            # Extract VIN
            vin_match = self._extract_vin(ocr_result.text)
            if vin_match:
                vehicle_fields['vin'] = vin_match
            
            # Extract license plate
            plate_match = self._extract_license_plate(ocr_result.text)
            if plate_match:
                vehicle_fields['license_plate'] = plate_match
            
            # Extract make and model
            make_model = self._extract_make_model(ocr_result.text)
            vehicle_fields.update(make_model)
            
            # Extract year
            year_match = self._extract_year(ocr_result.text)
            if year_match:
                vehicle_fields['year'] = year_match
            
            # Extract owner information
            owner_info = self._extract_owner_info(ocr_result.text)
            vehicle_fields.update(owner_info)
            
            return {
                'vehicle_info': vehicle_fields,
                'confidence': ocr_result.confidence,
                'raw_text': ocr_result.text
            }
            
        except Exception as e:
            logger.error(f"Error extracting vehicle info: {str(e)}")
            return {
                'vehicle_info': {},
                'confidence': 0.0,
                'raw_text': '',
                'error': str(e)
            }
    
    def validate_document_fields(self, fields: Dict[str, Any], document_type: str) -> Dict[str, Any]:
        """Validate extracted document fields"""
        try:
            validation_result = {
                'valid_fields': {},
                'invalid_fields': {},
                'missing_fields': [],
                'warnings': [],
                'overall_status': 'valid'
            }
            
            template = self.document_templates.get(document_type, {})
            required_fields = template.get('required_fields', [])
            
            # Check required fields
            for field_name in required_fields:
                if field_name not in fields or not fields[field_name]:
                    validation_result['missing_fields'].append(field_name)
                    validation_result['overall_status'] = 'incomplete'
            
            # Validate each field
            for field_name, value in fields.items():
                validation = self._validate_field(field_name, value)
                
                if validation['valid']:
                    validation_result['valid_fields'][field_name] = {
                        'value': value,
                        'normalized': validation.get('normalized', value)
                    }
                else:
                    validation_result['invalid_fields'][field_name] = {
                        'value': value,
                        'errors': validation['errors']
                    }
                    validation_result['overall_status'] = 'invalid'
                
                if validation.get('warnings'):
                    validation_result['warnings'].extend(validation['warnings'])
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating document fields: {str(e)}")
            return {
                'valid_fields': {},
                'invalid_fields': fields,
                'missing_fields': [],
                'warnings': [f"Validation error: {str(e)}"],
                'overall_status': 'error'
            }
    
    def auto_fill_vehicle_form(self, document_result: DocumentExtractionResult) -> Dict[str, Any]:
        """Auto-fill vehicle form based on extracted document data"""
        try:
            form_data = {}
            fields = document_result.extracted_fields
            
            # Map document fields to form fields
            field_mapping = {
                'vin': 'vin',
                'license_plate': 'license_plate',
                'make': 'make',
                'model': 'model', 
                'year': 'year',
                'color': 'color',
                'owner_name': 'owner_name',
                'owner_address': 'owner_address',
                'owner_phone': 'owner_phone'
            }
            
            for doc_field, form_field in field_mapping.items():
                if doc_field in fields:
                    form_data[form_field] = fields[doc_field]
            
            # Add metadata
            form_data['_auto_filled'] = True
            form_data['_extraction_confidence'] = document_result.confidence
            form_data['_document_type'] = document_result.document_type
            form_data['_extraction_timestamp'] = datetime.now().isoformat()
            
            # Generate pre-fill suggestions
            suggestions = self._generate_form_suggestions(form_data, document_result)
            
            return {
                'form_data': form_data,
                'suggestions': suggestions,
                'confidence': document_result.confidence,
                'validation_required': document_result.confidence < 0.8
            }
            
        except Exception as e:
            logger.error(f"Error auto-filling form: {str(e)}")
            return {
                'form_data': {},
                'suggestions': [],
                'confidence': 0.0,
                'validation_required': True,
                'error': str(e)
            }
    
    def classify_document(self, image_data: bytes) -> Dict[str, Any]:
        """Classify document type and content"""
        try:
            ocr_result = self._perform_ocr(image_data)
            text = ocr_result.text.lower()
            
            classification_scores = {}
            
            # Check for registration documents
            if any(keyword in text for keyword in ['registration', 'certificate', 'vehicle title']):
                classification_scores['vehicle_registration'] = 0.8
            
            # Check for license documents
            if any(keyword in text for keyword in ['license', 'permit', 'identification']):
                classification_scores['license'] = 0.7
            
            # Check for insurance documents
            if any(keyword in text for keyword in ['insurance', 'policy', 'coverage']):
                classification_scores['insurance'] = 0.7
            
            # Check for tow receipts
            if any(keyword in text for keyword in ['tow', 'receipt', 'storage', 'impound']):
                classification_scores['tow_receipt'] = 0.6
            
            # Check for inspection documents
            if any(keyword in text for keyword in ['inspection', 'safety', 'emissions']):
                classification_scores['inspection'] = 0.6
            
            # Determine best classification
            if classification_scores:
                best_type = max(classification_scores.keys(), key=lambda x: classification_scores[x])
                confidence = classification_scores[best_type]
            else:
                best_type = 'unknown'
                confidence = 0.0
            
            return {
                'document_type': best_type,
                'confidence': confidence,
                'all_scores': classification_scores,
                'text_length': len(ocr_result.text),
                'language': ocr_result.language
            }
            
        except Exception as e:
            logger.error(f"Error classifying document: {str(e)}")
            return {
                'document_type': 'unknown',
                'confidence': 0.0,
                'all_scores': {},
                'text_length': 0,
                'language': 'unknown',
                'error': str(e)
            }
    
    def get_document_quality_score(self, image_data: bytes) -> Dict[str, Any]:
        """Assess document image quality for OCR processing"""
        try:
            # Load image
            image = Image.open(io.BytesIO(image_data))
            
            quality_metrics = {}
            
            # Check image dimensions
            width, height = image.size
            quality_metrics['resolution'] = {
                'width': width,
                'height': height,
                'total_pixels': width * height,
                'score': min(1.0, (width * height) / (1000 * 1000))  # Target 1MP
            }
            
            # Check if image is color or grayscale
            if image.mode in ['RGB', 'RGBA']:
                quality_metrics['color_mode'] = 'color'
                # Convert to grayscale for analysis
                gray_image = image.convert('L')
            else:
                quality_metrics['color_mode'] = 'grayscale'
                gray_image = image
            
            # Estimate blur/sharpness
            import numpy as np
            img_array = np.array(gray_image)
            
            # Simplified sharpness estimation using variance of Laplacian
            laplacian_var = self._calculate_laplacian_variance(img_array)
            quality_metrics['sharpness'] = {
                'laplacian_variance': float(laplacian_var),
                'score': min(1.0, laplacian_var / 100)  # Normalized score
            }
            
            # Estimate brightness
            mean_brightness = np.mean(img_array)
            quality_metrics['brightness'] = {
                'mean_value': float(mean_brightness),
                'score': 1.0 - abs(mean_brightness - 128) / 128  # Optimal around 128
            }
            
            # Estimate contrast
            contrast = np.std(img_array)
            quality_metrics['contrast'] = {
                'std_deviation': float(contrast),
                'score': min(1.0, contrast / 64)  # Normalized score
            }
            
            # Calculate overall quality score
            scores = [
                quality_metrics['resolution']['score'],
                quality_metrics['sharpness']['score'],
                quality_metrics['brightness']['score'],
                quality_metrics['contrast']['score']
            ]
            
            overall_score = sum(scores) / len(scores)
            
            # Generate recommendations
            recommendations = self._generate_quality_recommendations(quality_metrics)
            
            return {
                'overall_score': overall_score,
                'quality_grade': self._get_quality_grade(overall_score),
                'metrics': quality_metrics,
                'recommendations': recommendations,
                'ocr_ready': overall_score > 0.6
            }
            
        except Exception as e:
            logger.error(f"Error assessing document quality: {str(e)}")
            return {
                'overall_score': 0.0,
                'quality_grade': 'poor',
                'metrics': {},
                'recommendations': ['Unable to assess image quality'],
                'ocr_ready': False,
                'error': str(e)
            }
    
    # Private helper methods
    
    def _setup_document_templates(self) -> Dict[str, Dict[str, Any]]:
        """Setup document templates for different document types"""
        return {
            'vehicle_registration': {
                'required_fields': ['vin', 'license_plate', 'make', 'model', 'year'],
                'optional_fields': ['color', 'owner_name', 'registration_date'],
                'validation_rules': {
                    'vin': r'^[A-HJ-NPR-Z0-9]{17}$',
                    'year': r'^(19|20)\d{2}$'
                }
            },
            'license': {
                'required_fields': ['license_number', 'name', 'address'],
                'optional_fields': ['date_of_birth', 'expiration_date'],
                'validation_rules': {
                    'license_number': r'^[A-Z0-9]{8,12}$'
                }
            },
            'insurance': {
                'required_fields': ['policy_number', 'insured_name', 'vehicle_info'],
                'optional_fields': ['effective_date', 'expiration_date'],
                'validation_rules': {
                    'policy_number': r'^[A-Z0-9\-]{6,20}$'
                }
            },
            'tow_receipt': {
                'required_fields': ['receipt_number', 'tow_date', 'vehicle_info'],
                'optional_fields': ['tow_reason', 'storage_location'],
                'validation_rules': {
                    'receipt_number': r'^[0-9]{4,10}$'
                }
            }
        }
    
    def _setup_field_patterns(self) -> Dict[str, str]:
        """Setup regex patterns for field extraction"""
        return {
            'vin': r'\b[A-HJ-NPR-Z0-9]{17}\b',
            'license_plate': r'\b[A-Z0-9]{2,8}\b',
            'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'zip_code': r'\b\d{5}(?:-\d{4})?\b',
            'date': r'\b\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}\b',
            'year': r'\b(19|20)\d{2}\b',
            'money': r'\$\s*\d+(?:,\d{3})*(?:\.\d{2})?'
        }
    
    def _setup_validation_rules(self) -> Dict[str, Dict[str, Any]]:
        """Setup validation rules for different field types"""
        return {
            'vin': {
                'pattern': r'^[A-HJ-NPR-Z0-9]{17}$',
                'length': 17,
                'check_digit': True
            },
            'license_plate': {
                'pattern': r'^[A-Z0-9]{2,8}$',
                'min_length': 2,
                'max_length': 8
            },
            'year': {
                'pattern': r'^(19|20)\d{2}$',
                'min_value': 1900,
                'max_value': datetime.now().year + 1
            },
            'phone': {
                'pattern': r'^\d{10}$',
                'format': 'digits_only'
            }
        }
    
    def _setup_ocr_engines(self) -> Dict[str, Any]:
        """Setup OCR engine configurations"""
        return {
            'default': {
                'confidence_threshold': 0.6,
                'preprocessing': ['noise_reduction', 'contrast_enhancement'],
                'language': 'eng'
            },
            'handwriting': {
                'confidence_threshold': 0.4,
                'preprocessing': ['skew_correction', 'line_detection'],
                'language': 'eng'
            }
        }
    
    def _detect_document_type(self, image_data: bytes) -> str:
        """Detect document type from image"""
        classification_result = self.classify_document(image_data)
        return classification_result['document_type']
    
    def _perform_ocr(self, image_data: bytes) -> OCRResult:
        """Perform OCR on image data"""
        try:
            # This is a simplified OCR implementation
            # In production, you would use libraries like pytesseract, easyocr, or cloud APIs
            
            # Load image
            image = Image.open(io.BytesIO(image_data))
            
            # Simulate OCR result for demonstration
            # In real implementation, this would be actual OCR processing
            simulated_text = self._simulate_ocr_text()
            
            return OCRResult(
                text=simulated_text,
                confidence=0.85,
                bounding_boxes=[],  # Would contain actual bounding box data
                detected_fields={},
                language='eng'
            )
            
        except Exception as e:
            logger.error(f"OCR processing error: {str(e)}")
            return OCRResult(
                text="",
                confidence=0.0,
                bounding_boxes=[],
                detected_fields={},
                language='unknown'
            )
    
    def _simulate_ocr_text(self) -> str:
        """Simulate OCR text extraction for demonstration"""
        # This simulates typical text found in vehicle documents
        return """
        VEHICLE REGISTRATION CERTIFICATE
        
        VIN: 1HGBH41JXMN109186
        License Plate: ABC123
        Make: HONDA
        Model: CIVIC
        Year: 2021
        Color: BLUE
        
        Owner: JOHN DOE
        Address: 123 MAIN ST, ANYTOWN, CA 90210
        Phone: (555) 123-4567
        
        Registration Date: 01/15/2024
        Expiration Date: 01/15/2025
        """
    
    def _extract_fields(self, ocr_result: OCRResult, document_type: str) -> Dict[str, Any]:
        """Extract structured fields from OCR text"""
        fields = {}
        text = ocr_result.text
        
        # Extract VIN
        vin_match = re.search(self.field_patterns['vin'], text)
        if vin_match:
            fields['vin'] = vin_match.group()
        
        # Extract license plate
        # Look for patterns after "License Plate:" or "Plate:"
        plate_patterns = [
            r'(?:License Plate|Plate):\s*([A-Z0-9]{2,8})',
            r'(?:LP|LIC):\s*([A-Z0-9]{2,8})'
        ]
        
        for pattern in plate_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields['license_plate'] = match.group(1)
                break
        
        # Extract make and model
        make_model = self._extract_make_model(text)
        fields.update(make_model)
        
        # Extract year
        year_match = re.search(r'Year:\s*(\d{4})', text, re.IGNORECASE)
        if year_match:
            fields['year'] = int(year_match.group(1))
        
        # Extract color
        color_match = re.search(r'Color:\s*([A-Z]+)', text, re.IGNORECASE)
        if color_match:
            fields['color'] = color_match.group(1).lower()
        
        # Extract owner information
        owner_info = self._extract_owner_info(text)
        fields.update(owner_info)
        
        return fields
    
    def _extract_vin(self, text: str) -> Optional[str]:
        """Extract VIN from text"""
        match = re.search(self.field_patterns['vin'], text)
        return match.group() if match else None
    
    def _extract_license_plate(self, text: str) -> Optional[str]:
        """Extract license plate from text"""
        # Look for license plate patterns in context
        patterns = [
            r'(?:License Plate|Plate|LP):\s*([A-Z0-9]{2,8})',
            r'(?:Tag|Registration):\s*([A-Z0-9]{2,8})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_make_model(self, text: str) -> Dict[str, str]:
        """Extract vehicle make and model"""
        result = {}
        
        # Common vehicle makes
        makes = [
            'TOYOTA', 'HONDA', 'FORD', 'CHEVROLET', 'BMW', 'MERCEDES', 'AUDI',
            'NISSAN', 'HYUNDAI', 'KIA', 'VOLKSWAGEN', 'SUBARU', 'MAZDA'
        ]
        
        # Look for make
        make_match = re.search(r'Make:\s*([A-Z]+)', text, re.IGNORECASE)
        if make_match:
            result['make'] = make_match.group(1).upper()
        else:
            # Try to find make in text
            for make in makes:
                if make in text.upper():
                    result['make'] = make
                    break
        
        # Look for model
        model_match = re.search(r'Model:\s*([A-Z0-9\s]+)', text, re.IGNORECASE)
        if model_match:
            result['model'] = model_match.group(1).strip().upper()
        
        return result
    
    def _extract_year(self, text: str) -> Optional[int]:
        """Extract vehicle year"""
        year_match = re.search(r'Year:\s*(\d{4})', text, re.IGNORECASE)
        if year_match:
            year = int(year_match.group(1))
            if 1900 <= year <= datetime.now().year + 1:
                return year
        
        return None
    
    def _extract_owner_info(self, text: str) -> Dict[str, str]:
        """Extract owner information"""
        result = {}
        
        # Extract owner name
        name_match = re.search(r'Owner:\s*([A-Z\s]+)', text, re.IGNORECASE)
        if name_match:
            result['owner_name'] = name_match.group(1).strip().title()
        
        # Extract address
        address_match = re.search(r'Address:\s*([A-Z0-9\s,]+)', text, re.IGNORECASE)
        if address_match:
            result['owner_address'] = address_match.group(1).strip()
        
        # Extract phone
        phone_match = re.search(self.field_patterns['phone'], text)
        if phone_match:
            result['owner_phone'] = phone_match.group()
        
        return result
    
    def _validate_fields(self, fields: Dict[str, Any], document_type: str) -> Dict[str, Any]:
        """Validate extracted fields"""
        validation_result = {
            'status': 'valid',
            'errors': [],
            'warnings': []
        }
        
        template = self.document_templates.get(document_type, {})
        required_fields = template.get('required_fields', [])
        
        # Check required fields
        for field_name in required_fields:
            if field_name not in fields or not fields[field_name]:
                validation_result['errors'].append(f"Missing required field: {field_name}")
                validation_result['status'] = 'invalid'
        
        # Validate individual fields
        for field_name, value in fields.items():
            field_validation = self._validate_field(field_name, value)
            if not field_validation['valid']:
                validation_result['errors'].extend(field_validation['errors'])
                validation_result['status'] = 'invalid'
            
            if field_validation.get('warnings'):
                validation_result['warnings'].extend(field_validation['warnings'])
        
        return validation_result
    
    def _validate_field(self, field_name: str, value: Any) -> Dict[str, Any]:
        """Validate individual field"""
        validation = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        rules = self.validation_rules.get(field_name, {})
        
        if not rules:
            return validation  # No validation rules defined
        
        str_value = str(value)
        
        # Pattern validation
        if 'pattern' in rules:
            if not re.match(rules['pattern'], str_value):
                validation['valid'] = False
                validation['errors'].append(f"Invalid format for {field_name}")
        
        # Length validation
        if 'length' in rules and len(str_value) != rules['length']:
            validation['valid'] = False
            validation['errors'].append(f"{field_name} must be {rules['length']} characters")
        
        if 'min_length' in rules and len(str_value) < rules['min_length']:
            validation['valid'] = False
            validation['errors'].append(f"{field_name} must be at least {rules['min_length']} characters")
        
        if 'max_length' in rules and len(str_value) > rules['max_length']:
            validation['valid'] = False
            validation['errors'].append(f"{field_name} must be at most {rules['max_length']} characters")
        
        # Value range validation
        if field_name == 'year':
            try:
                year_val = int(value)
                current_year = datetime.now().year
                if year_val < 1900 or year_val > current_year + 1:
                    validation['valid'] = False
                    validation['errors'].append(f"Year must be between 1900 and {current_year + 1}")
            except ValueError:
                validation['valid'] = False
                validation['errors'].append("Year must be a valid number")
        
        # VIN check digit validation
        if field_name == 'vin' and rules.get('check_digit'):
            if not self._validate_vin_check_digit(str_value):
                validation['warnings'].append("VIN check digit validation failed")
        
        return validation
    
    def _validate_vin_check_digit(self, vin: str) -> bool:
        """Validate VIN check digit (simplified implementation)"""
        if len(vin) != 17:
            return False
        
        # This is a simplified VIN validation
        # Real implementation would use the actual VIN check digit algorithm
        transliteration = {
            'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7, 'H': 8,
            'J': 1, 'K': 2, 'L': 3, 'M': 4, 'N': 5, 'P': 7, 'R': 9,
            'S': 2, 'T': 3, 'U': 4, 'V': 5, 'W': 6, 'X': 7, 'Y': 8, 'Z': 9
        }
        
        weights = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]
        
        try:
            total = 0
            for i, char in enumerate(vin):
                if char.isdigit():
                    total += int(char) * weights[i]
                elif char in transliteration:
                    total += transliteration[char] * weights[i]
            
            check_digit = total % 11
            if check_digit == 10:
                check_digit = 'X'
            else:
                check_digit = str(check_digit)
            
            return vin[8] == check_digit
        except:
            return False
    
    def _calculate_extraction_confidence(self, ocr_result: OCRResult, 
                                       extracted_fields: Dict[str, Any]) -> float:
        """Calculate overall confidence for extraction"""
        base_confidence = ocr_result.confidence
        
        # Boost confidence based on number of fields extracted
        field_bonus = min(0.2, len(extracted_fields) * 0.05)
        base_confidence += field_bonus
        
        # Reduce confidence if important fields are missing
        if 'vin' not in extracted_fields:
            base_confidence -= 0.1
        if 'license_plate' not in extracted_fields:
            base_confidence -= 0.1
        
        return max(0.0, min(1.0, base_confidence))
    
    def _generate_improvement_suggestions(self, extracted_fields: Dict[str, Any],
                                        validation_result: Dict[str, Any],
                                        document_type: str) -> List[str]:
        """Generate suggestions for improving extraction results"""
        suggestions = []
        
        if validation_result['status'] == 'invalid':
            suggestions.append("Please verify and correct the highlighted fields")
        
        if not extracted_fields:
            suggestions.extend([
                "Try uploading a clearer image",
                "Ensure the document is well-lit and in focus",
                "Check that the document is right-side up"
            ])
        
        template = self.document_templates.get(document_type, {})
        required_fields = template.get('required_fields', [])
        
        missing_fields = [field for field in required_fields if field not in extracted_fields]
        if missing_fields:
            suggestions.append(f"Please manually enter: {', '.join(missing_fields)}")
        
        return suggestions
    
    def _generate_form_suggestions(self, form_data: Dict[str, Any], 
                                 document_result: DocumentExtractionResult) -> List[str]:
        """Generate suggestions for form auto-fill"""
        suggestions = []
        
        if document_result.confidence < 0.8:
            suggestions.append("Please verify auto-filled data due to lower confidence")
        
        if document_result.errors:
            suggestions.append("Some fields may need manual correction")
        
        if not form_data.get('vin'):
            suggestions.append("VIN not detected - please enter manually")
        
        if not form_data.get('license_plate'):
            suggestions.append("License plate not detected - please enter manually")
        
        return suggestions
    
    def _calculate_laplacian_variance(self, image_array) -> float:
        """Calculate Laplacian variance for sharpness estimation"""
        try:
            import numpy as np
            from scipy import ndimage
            
            # Apply Laplacian filter
            laplacian = ndimage.laplace(image_array)
            
            # Calculate variance
            return np.var(laplacian)
        except ImportError:
            # Fallback implementation without scipy
            import numpy as np
            
            # Simple approximation using gradient
            grad_x = np.diff(image_array, axis=1)
            grad_y = np.diff(image_array, axis=0)
            
            return float(np.var(grad_x) + np.var(grad_y))
    
    def _generate_quality_recommendations(self, quality_metrics: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on quality assessment"""
        recommendations = []
        
        resolution = quality_metrics.get('resolution', {})
        if resolution.get('score', 0) < 0.5:
            recommendations.append("Image resolution is low - try taking a closer photo")
        
        sharpness = quality_metrics.get('sharpness', {})
        if sharpness.get('score', 0) < 0.4:
            recommendations.append("Image appears blurry - ensure camera is focused")
        
        brightness = quality_metrics.get('brightness', {})
        if brightness.get('score', 0) < 0.5:
            mean_brightness = brightness.get('mean_value', 128)
            if mean_brightness < 64:
                recommendations.append("Image is too dark - try better lighting")
            elif mean_brightness > 192:
                recommendations.append("Image is too bright - reduce lighting or exposure")
        
        contrast = quality_metrics.get('contrast', {})
        if contrast.get('score', 0) < 0.3:
            recommendations.append("Image has low contrast - try adjusting lighting")
        
        if not recommendations:
            recommendations.append("Image quality is good for OCR processing")
        
        return recommendations
    
    def _get_quality_grade(self, score: float) -> str:
        """Get quality grade based on score"""
        if score >= 0.8:
            return 'excellent'
        elif score >= 0.6:
            return 'good'
        elif score >= 0.4:
            return 'fair'
        else:
            return 'poor'
