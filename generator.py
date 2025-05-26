from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import logging
import os
import time
from datetime import datetime, timedelta
import json

class PDFGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.header_style = ParagraphStyle('Header', parent=self.styles['Normal'], fontSize=12, alignment=1, spaceAfter=20)
        self.title_style = ParagraphStyle('Title', parent=self.styles['Heading1'], fontSize=14, alignment=1, spaceAfter=12)
        self.field_style = ParagraphStyle('Field', parent=self.styles['Normal'], fontSize=11, spaceBefore=6, spaceAfter=6)
        self.small_style = ParagraphStyle('Small', parent=self.styles['Normal'], fontSize=9, spaceBefore=3, spaceAfter=3)
        
        # Ensure directories exist
        os.makedirs('static/generated_pdfs', exist_ok=True)
        os.makedirs('static/uploads/vehicle_photos', exist_ok=True)
        os.makedirs('static/uploads/documents', exist_ok=True)
        
        # Logo path
        self.logo_path = 'static/logo.png'
        if not os.path.exists(self.logo_path):
            # Create a placeholder logo file if it doesn't exist
            logging.warning(f"Logo file not found at {self.logo_path}. PDF documents will not include a logo.")

    def _add_header(self, elements):
        """Add company header to document"""
        if (os.path.exists(self.logo_path)):
            try:
                logo = Image(self.logo_path, width=1.5*inch, height=0.75*inch)
                elements.append(logo)
                elements.append(Spacer(1, 6)) # Reduced spacer
            except Exception as e:
                logging.error(f"Error adding logo to PDF: {e}")
        
        # More concise header
        header_text = '<para alignment="center"><b>iTow</b> | 5265 Pierson Rd, Flushing, MI 48433, STE 6 | 810-394-5937 | itow2017@gmail.com</para>'
        elements.append(Paragraph(header_text, self.styles['Normal'])) # Using Normal style, adjust if needed
        elements.append(Spacer(1, 12))

    def _handle_empty_value(self, value):
        """Handle empty or None values"""
        if value is None or value == '' or value == 'None':
            return 'N/A'
        return value
    
    def _format_date_for_pdf(self, date_value):
        """Format date consistently for PDF display as MM/DD/YYYY"""
        if not date_value or date_value == 'N/A' or date_value == '':
            return 'N/A'
        
        try:
            # Handle various date formats
            if isinstance(date_value, str):
                # Try to parse different formats
                if '/' in date_value:
                    # MM/DD/YYYY format - already correct
                    return date_value
                elif '-' in date_value:
                    # YYYY-MM-DD format - convert to MM/DD/YYYY
                    date_obj = datetime.strptime(date_value, '%Y-%m-%d')
                    return date_obj.strftime('%m/%d/%Y')
                else:
                    # Try parsing as date object
                    date_obj = datetime.strptime(date_value, '%Y-%m-%d')
                    return date_obj.strftime('%m/%d/%Y')
            elif hasattr(date_value, 'strftime'):
                # If it's already a datetime object
                return date_value.strftime('%m/%d/%Y')
            else:
                return str(date_value)
        except Exception as e:
            logging.warning(f"Date formatting error in PDF: {e}, returning original value: {date_value}")
            return str(date_value)

    def generate_top(self, data, pdf_path): # Removed tow_reason parameter
        try:
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
            elements = []

            # Add header
            self._add_header(elements)

            # Add title
            elements.append(Paragraph("Abandoned Vehicle Tow-Off-Property Notification Form", self.title_style))
            elements.append(Spacer(1, 12))

            # Add description
            description_text = """
            <para fontSize="10">
            This form notifies the local police agency of an abandoned vehicle towed from private property under MCL 257.252a et seq., 
            providing vehicle and towing details for processing in the LEIN system.
            </para>
            """
            elements.append(Paragraph(description_text, self.styles['Normal']))
            elements.append(Spacer(1, 12))
            
            # Add timestamp
            timestamp = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            elements.append(Paragraph(timestamp, self.small_style))
            elements.append(Spacer(1, 12))

            # Build vehicle description
            vehicle_desc = ' '.join(filter(None, [
                self._handle_empty_value(data.get('year', 'N/A')), 
                self._handle_empty_value(data.get('make', 'N/A')), 
                self._handle_empty_value(data.get('model', 'N/A')), 
                self._handle_empty_value(data.get('color', 'N/A')), 
                self._handle_empty_value(data.get('vehicle_type', 'N/A'))
            ]))
            
            # Combine plate number and state
            plate_number_val = self._handle_empty_value(data.get('plate'))
            plate_state_val = self._handle_empty_value(data.get('state'))
            
            combined_plate_parts = []
            if plate_number_val != 'N/A':
                combined_plate_parts.append(plate_number_val)
            if plate_state_val != 'N/A':
                combined_plate_parts.append(plate_state_val)
            
            final_plate_info = ' '.join(combined_plate_parts) if combined_plate_parts else 'N/A'

            # Create details table
            details_data = [
                ['TO:', self._handle_empty_value(data.get('jurisdiction', 'N/A'))],
                ['DATE OF TOW:', self._format_date_for_pdf(data.get('tow_date', 'N/A'))],
                ['TIME OF TOW:', self._handle_empty_value(data.get('tow_time', 'N/A'))],
                ['TOWED FROM:', self._handle_empty_value(data.get('location', 'N/A'))],
                # Removed REASON FOR TOW from here
                ['REQUESTED BY:', self._handle_empty_value(data.get('requestor', data.get('requested_by', 'N/A')))], # Handles both field names
                ['VEHICLE DESCRIPTION:', vehicle_desc],
                ['VIN:', self._handle_empty_value(data.get('vin', 'N/A'))],
                ['PLATE NUMBER:', final_plate_info], # Combined plate number and state
                ['COMPLAINT #:', self._handle_empty_value(data.get('complaint_number', 'N/A'))],
            ]
            
            # Only add officer name and case number if they have actual values
            case_number = data.get('case_number', '')
            officer_name = data.get('officer_name', '')
            
            if case_number and case_number.strip() and case_number.strip().upper() != 'N/A':
                details_data.append(['CASE NUMBER:', case_number.strip()])
                
            if officer_name and officer_name.strip() and officer_name.strip().upper() != 'N/A':
                details_data.append(['OFFICER NAME:', officer_name.strip()])
            
            # Keep all details for TOP form
            details = details_data

            table = Table(details, colWidths=[2*inch, 4*inch])
            table.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('BACKGROUND', (0,0), (0,-1), colors.lightgrey), # Label column background
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('PADDING', (0,0), (-1,-1), 6)
            ]))
            elements.append(table)
            elements.append(Spacer(1, 24))

            doc.build(elements)
            logging.info(f"Successfully generated TOP form for {data.get('towbook_call_number', 'Unknown Call#')} at {pdf_path}")
            return True, None
        except Exception as e:
            logging.error(f"Error in PDFGenerator.generate_top for {data.get('towbook_call_number', 'Unknown Call#')} with path {pdf_path}: {e}", exc_info=True)
            return False, f"PDF generation failed: {str(e)}"

    def generate_release_notice(self, data, pdf_path):
        try:
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
            elements = []
            
            # Add header
            self._add_header(elements)
            
            # Add title
            elements.append(Paragraph("VEHICLE RELEASE NOTICE", self.title_style))
            elements.append(Spacer(1, 12))
            
            # Add timestamp
            timestamp = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            elements.append(Paragraph(timestamp, self.small_style))
            elements.append(Spacer(1, 12))
            
            # Build vehicle description
            vehicle_desc = ' '.join(filter(None, [
                self._handle_empty_value(data.get('year', 'N/A')), 
                self._handle_empty_value(data.get('make', 'N/A')), 
                self._handle_empty_value(data.get('model', 'N/A')), 
                self._handle_empty_value(data.get('color', 'N/A'))
            ]))
            
            # Create details table
            details = [
                ['COMPLAINT NUMBER:', self._handle_empty_value(data.get('complaint_number', 'N/A'))],
                ['RELEASE DATE:', self._handle_empty_value(data.get('release_date', 'N/A'))],
                ['RELEASE TIME:', self._handle_empty_value(data.get('release_time', 'N/A'))],
                ['RELEASED TO:', self._handle_empty_value(data.get('recipient', 'N/A'))],
                ['RELEASE REASON:', self._handle_empty_value(data.get('release_reason', 'N/A'))],
                ['COMPLIANCE:', self._handle_empty_value(data.get('compliance_text', 'N/A'))],
                ['VEHICLE DESCRIPTION:', vehicle_desc],
                ['VIN:', self._handle_empty_value(data.get('vin', 'N/A'))],
                ['PLATE NUMBER:', self._handle_empty_value(data.get('plate', 'N/A'))],
                ['STATE:', self._handle_empty_value(data.get('state', 'N/A'))],
                ['TOW DATE:', self._format_date_for_pdf(data.get('tow_date', 'N/A'))]
            ]
            
            # Add financial details if it's an auction release
            if data.get('release_reason') == 'Auctioned' and data.get('sale_amount'):
                details.extend([
                    ['SALE AMOUNT:', f"${float(data.get('sale_amount', 0)):.2f}"],
                    ['FEES:', f"${float(data.get('fees', 0)):.2f}"],
                    ['NET PROCEEDS:', f"${float(data.get('net_proceeds', 0)):.2f}"]
                ])
            
            # Create table
            table = Table(details, colWidths=[2*inch, 3.5*inch])
            table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 6)
            ]))
            elements.append(table)
            
            # Add release statement
            elements.append(Spacer(1, 24))
            statement = f'This certifies that the vehicle was released from iTow custody on {data.get("release_date", "N/A")} at {data.get("release_time", "N/A")} for {data.get("release_reason", "N/A")}.'
            elements.append(Paragraph(statement, self.field_style))
            elements.append(Spacer(1, 12))
            elements.append(Paragraph(data.get('compliance_text', 'N/A'), self.field_style))
            
            # Add signature lines
            elements.append(Spacer(1, 48))
            elements.append(Paragraph('____________________________     ____________________________', self.field_style))
            elements.append(Paragraph('iTow Signature     Recipient Signature', self.field_style))
            
            # Build the document
            doc.build(elements)
            return True, None
        except Exception as e:
            logging.error(f"Error generating release: {e}")
            return False, str(e)

    def generate_tr52_form(self, data, pdf_path):
        try:
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
            elements = []
            
            # Add header
            self._add_header(elements)
            
            # Add title
            elements.append(Paragraph("TR-52 ABANDONED VEHICLE NOTIFICATION", self.title_style))
            elements.append(Spacer(1, 12))
            
            # Add notice text
            notice = 'This form serves as notification that the redemption period has expired for the following vehicle abandoned on private property.'
            elements.append(Paragraph(notice, self.field_style))
            elements.append(Spacer(1, 12))
            
            # Add timestamp
            timestamp = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            elements.append(Paragraph(timestamp, self.small_style))
            elements.append(Spacer(1, 12))
            
            # Build vehicle description
            vehicle_desc = ' '.join(filter(None, [
                self._handle_empty_value(data.get('year', 'N/A')), 
                self._handle_empty_value(data.get('make', 'N/A')), 
                self._handle_empty_value(data.get('model', 'N/A')), 
                self._handle_empty_value(data.get('color', 'N/A'))
            ]))
            
            # Calculate relevant dates
            tow_date = datetime.strptime(self._handle_empty_value(data.get('tow_date', datetime.now().strftime('%Y-%m-%d'))), '%Y-%m-%d')
            top_sent_date = data.get('top_form_sent_date')
            if (top_sent_date and top_sent_date != 'N/A'):
                top_sent_date = datetime.strptime(top_sent_date, '%Y-%m-%d')
            else:
                top_sent_date = tow_date + timedelta(days=1)
                
            redemption_end_date = top_sent_date + timedelta(days=20)
            
            # Create details table
            details = [
                ['COMPLAINT NUMBER:', self._handle_empty_value(data.get('complaint_number', 'N/A'))],
                ['VEHICLE DESCRIPTION:', vehicle_desc],
                ['VIN:', self._handle_empty_value(data.get('vin', 'N/A'))],
                ['PLATE NUMBER:', self._handle_empty_value(data.get('plate', 'N/A'))],
                ['STATE:', self._handle_empty_value(data.get('state', 'N/A'))],
                ['TOW DATE:', self._format_date_for_pdf(tow_date)],
                ['TOP NOTIFICATION DATE:', self._format_date_for_pdf(top_sent_date)],
                ['REDEMPTION END DATE:', self._format_date_for_pdf(redemption_end_date)],
                ['LOCATION TOWED FROM:', self._handle_empty_value(data.get('location', 'N/A'))],
                ['JURISDICTION:', self._handle_empty_value(data.get('jurisdiction', 'N/A'))]
            ]
            
            # Create table
            table = Table(details, colWidths=[2*inch, 3.5*inch])
            table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 6)
            ]))
            elements.append(table)
            
            # Add legal text
            elements.append(Spacer(1, 24))
            legal_text1 = """
            <para fontSize="10">
            This vehicle was towed from private property at the request of the property owner or agent. 
            A Temporary Ownership Permit (TOP) notification was sent on the date indicated above. 
            The 20-day redemption period has now expired without the vehicle being claimed.
            </para>
            """
            elements.append(Paragraph(legal_text1, self.small_style))
            
            legal_text2 = """
            <para fontSize="10">
            Per MCL 257.252a, this vehicle may now be considered abandoned for disposition purposes.
            We are requesting a TR-52 form to be issued so that this vehicle can be:
            </para>
            """
            elements.append(Paragraph(legal_text2, self.small_style))
            
            # Add disposition options
            elements.append(Spacer(1, 12))
            elements.append(Paragraph("□ Sold at public auction", self.field_style))
            elements.append(Paragraph("□ Disposed of as junk", self.field_style))
            
            # Add certification
            elements.append(Spacer(1, 24))
            certification = """
            <para fontSize="10">
            I certify that all statutory requirements regarding notification have been met, 
            and that the information provided above is true and correct to the best of my knowledge.
            </para>
            """
            elements.append(Paragraph(certification, self.small_style))
            
            # Add signature lines
            elements.append(Spacer(1, 36))
            elements.append(Paragraph('____________________________     ____________________________', self.field_style))
            elements.append(Paragraph('Towing Agency Signature     Date', self.field_style))
            
            # Add police section
            elements.append(Spacer(1, 36))
            elements.append(Paragraph('FOR POLICE DEPARTMENT USE ONLY', self.field_style))
            elements.append(Spacer(1, 12))
            elements.append(Paragraph('TR-52 Form Number: _______________________', self.field_style))
            elements.append(Spacer(1, 12))
            elements.append(Paragraph('____________________________     ____________________________', self.field_style))
            elements.append(Paragraph('Police Department Signature     Date', self.field_style))
            
            # Build the document
            doc.build(elements)
            return True, None
        except Exception as e:
            logging.error(f"Error generating TR52 form: {e}")
            return False, str(e)
        
    def generate_tr208_form(self, vehicle_data, output_path):
        """
        Generate a TR208 form for scrappable vehicles
        
        Args:
            vehicle_data (dict): Vehicle information
            output_path (str): Path to save the PDF
            
        Returns:
            (bool, str): Success status and error message if any
        """
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            from reportlab.lib import colors
            from reportlab.platypus import Table, TableStyle
            import os
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Create canvas
            c = canvas.Canvas(output_path, pagesize=letter)
            width, height = letter
            
            # Add form title
            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(width/2, height - 50, "TR-208 ABANDONED SCRAP VEHICLE CERTIFICATION")
            
            # Add subtitle
            c.setFont("Helvetica", 12)
            c.drawCentredString(width/2, height - 70, "Michigan Department of State")
            
            # Add date
            c.setFont("Helvetica", 10)
            c.drawString(width - 150, height - 30, f"Date: {datetime.now().strftime('%m/%d/%Y')}")
            
            # Add towing agency info
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, height - 100, "TOWING AGENCY INFORMATION")
            c.setFont("Helvetica", 10)
            c.drawString(50, height - 120, "Agency Name: iTow Towing & Recovery")
            c.drawString(50, height - 135, "Address: 205 W Johnson St, Clio, MI 48420")
            c.drawString(50, height - 150, "Phone: (810) 553-2800")
            c.drawString(50, height - 165, f"Complaint #: {vehicle_data.get('complaint_number', 'N/A')}")
            
            # Add vehicle information
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, height - 195, "VEHICLE INFORMATION")
            c.setFont("Helvetica", 10)
            c.drawString(50, height - 215, f"Year: {vehicle_data.get('year', 'N/A')}")
            c.drawString(250, height - 215, f"Make: {vehicle_data.get('make', 'N/A')}")
            c.drawString(400, height - 215, f"Model: {vehicle_data.get('model', 'N/A')}")
            c.drawString(50, height - 230, f"VIN: {vehicle_data.get('vin', 'N/A')}")
            c.drawString(250, height - 230, f"License Plate: {vehicle_data.get('plate', 'N/A')}")
            c.drawString(400, height - 230, f"State: {vehicle_data.get('state', 'N/A')}")
            c.drawString(50, height - 245, f"Color: {vehicle_data.get('color', 'N/A')}")
            
            # Add tow information
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, height - 275, "TOW INFORMATION")
            c.setFont("Helvetica", 10)
            c.drawString(50, height - 295, f"Date of Tow: {self._format_date_for_pdf(vehicle_data.get('tow_date', 'N/A'))}")
            c.drawString(250, height - 295, f"Time of Tow: {vehicle_data.get('tow_time', 'N/A')}")
            c.drawString(50, height - 310, f"Location: {vehicle_data.get('location', 'N/A')}")
            c.drawString(50, height - 325, f"Police Agency: {vehicle_data.get('jurisdiction', 'N/A')}")
            c.drawString(250, height - 325, f"Case #: {vehicle_data.get('case_number', 'N/A')}")
            
            # Add TR-208 qualification criteria
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, height - 355, "QUALIFICATION CRITERIA")
            c.setFont("Helvetica", 10)
            
            # Safely parse vehicle year, default to 0 if missing or invalid
            vehicle_year_value = vehicle_data.get('year')
            try:
                vehicle_year = int(vehicle_year_value) if vehicle_year_value is not None and str(vehicle_year_value).isdigit() else 0
            except:
                vehicle_year = 0
            current_year = datetime.now().year
            vehicle_age = current_year - vehicle_year if vehicle_year > 0 else "Unknown"
            
            c.drawString(50, height - 375, f"1. Vehicle Age: {vehicle_age} years (must be 7+ years old)")
            c.drawString(50, height - 390, "2. Vehicle is inoperable")
            c.drawString(50, height - 405, "3. Vehicle is extensively damaged")
            
            # Add checkbox indicators
            c.drawString(350, height - 375, "✓" if vehicle_age != "Unknown" and vehicle_age >= 7 else "□")
            c.drawString(350, height - 390, "✓" if vehicle_data.get('inoperable', 0) == 1 else "□")
            c.drawString(350, height - 405, "✓" if vehicle_data.get('damage_extent') == 'Extensive' else "□")
            
            # Add damage description
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, height - 435, "DAMAGE DESCRIPTION")
            c.setFont("Helvetica", 10)
            c.drawString(50, height - 455, f"Condition Notes: {vehicle_data.get('condition_notes', 'N/A')}")
            
            # Add certification
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, height - 485, "CERTIFICATION")
            c.setFont("Helvetica", 10)
            c.drawString(50, height - 505, "I certify that this vehicle meets all requirements for disposal as a scrap vehicle:")
            c.drawString(50, height - 520, "1. It is at least 7 years old")
            c.drawString(50, height - 535, "2. It is inoperable")
            c.drawString(50, height - 550, "3. It has extensive damage")
            c.drawString(50, height - 565, "4. The 20-day owner redemption period has passed")
            c.drawString(50, height - 580, "5. All applicable notifications have been made to police and the Secretary of State")
            
            # Add signature line
            c.line(50, height - 620, 250, height - 620)
            c.drawString(50, height - 635, "Authorized Signature")
            
            c.line(300, height - 620, 500, height - 620)
            c.drawString(300, height - 635, "Date")
            
            # Add footer
            c.setFont("Helvetica", 8)
            c.drawCentredString(width/2, 30, "TR-208 ABANDONED SCRAP VEHICLE CERTIFICATION")
            c.drawCentredString(width/2, 15, f"Generated on {datetime.now().strftime('%m/%d/%Y %H:%M:%S')}")
            
            # Save the PDF
            c.save()
            return True, "TR208 form generated successfully"
        except Exception as e:
            import traceback
            error_msg = traceback.format_exc()
            logging.error(f"Error generating TR208 form: {error_msg}")
            return False, str(e)
    
    def generate_auction_notice(self, data, pdf_path):
        try:
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
            elements = []
            
            # Add header
            self._add_header(elements)
            
            # Add title
            elements.append(Paragraph("PUBLIC AUCTION NOTICE", self.title_style))
            elements.append(Spacer(1, 12))
            
            # Add auction info
            auction_date = self._handle_empty_value(data.get('auction_date', 'N/A'))
            auction_info = f"The following vehicle will be sold at public auction on {auction_date} at 10:00 AM"
            elements.append(Paragraph(auction_info, self.field_style))
            elements.append(Paragraph("Location: iTow, 205 W Johnson St, Clio, MI 48420", self.field_style))
            elements.append(Spacer(1, 12))
            
            # Add timestamp
            timestamp = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            elements.append(Paragraph(timestamp, self.small_style))
            elements.append(Spacer(1, 12))
            
            # Build vehicle description
            vehicle_desc = ' '.join(filter(None, [
                self._handle_empty_value(data.get('year', 'N/A')), 
                self._handle_empty_value(data.get('make', 'N/A')), 
                self._handle_empty_value(data.get('model', 'N/A')), 
                self._handle_empty_value(data.get('color', 'N/A'))
            ]))
            
            # Create details table
            details = [
                ['COMPLAINT NUMBER:', self._handle_empty_value(data.get('complaint_number', 'N/A'))],
                ['VEHICLE DESCRIPTION:', vehicle_desc],
                ['VIN:', self._handle_empty_value(data.get('vin', 'N/A'))],
                ['PLATE NUMBER:', self._handle_empty_value(data.get('plate', 'N/A'))],
                ['STATE:', self._handle_empty_value(data.get('state', 'N/A'))]
            ]
            
            # Create table
            table = Table(details, colWidths=[2*inch, 3.5*inch])
            table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 6)
            ]))
            elements.append(table)
            
            # Add legal text
            elements.append(Spacer(1, 24))
            legal_text = """
            <para fontSize="10">
            This vehicle is being auctioned in accordance with Michigan law MCL 257.252g regarding
            the disposition of abandoned vehicles. All items are sold as-is with no warranty or guarantee.
            Payment must be made in full at the time of sale by cash or certified funds.
            </para>
            <para fontSize="10">
            The buyer will receive a bill of sale and may apply for a title through the Michigan
            Secretary of State. A valid photo ID is required to participate in the auction.
            </para>
            """
            elements.append(Paragraph(legal_text, self.small_style))
            
            # Add newspaper publication info
            elements.append(Spacer(1, 24))
            ad_date = self._handle_empty_value(data.get('ad_placement_date', 'N/A'))
            newspaper = self._handle_empty_value(data.get('newspaper_name', 'Local newspaper'))
            ad_info = f"This notice was published in {newspaper} on {ad_date} in compliance with MCL 257.252g."
            elements.append(Paragraph(ad_info, self.small_style))
            
            # Build the document
            doc.build(elements)
            return True, None
        except Exception as e:
            logging.error(f"Error generating auction notice: {e}")
            return False, str(e)

    def generate_newspaper_ad(self, vehicles, pdf_path):
        try:
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
            elements = []
            
            # Add title
            elements.append(Paragraph("ABANDONED VEHICLE AUCTION", self.title_style))
            elements.append(Spacer(1, 12))
            
            # Add auction info
            if len(vehicles) > 0:
                auction_date = self._handle_empty_value(vehicles[0].get('auction_date', 'N/A'))
                auction_info = f"The following vehicles will be sold at public auction on {auction_date} at 10:00 AM"
                elements.append(Paragraph(auction_info, self.field_style))
                elements.append(Paragraph("Location: iTow, 205 W Johnson St, Clio, MI 48420", self.field_style))
                elements.append(Spacer(1, 12))
            
            # Create vehicle list
            data = [['Year', 'Make', 'Model', 'VIN', 'Complaint #']]
            for vehicle in vehicles:
                data.append([
                    self._handle_empty_value(vehicle.get('year', 'N/A')),
                    self._handle_empty_value(vehicle.get('make', 'N/A')),
                    self._handle_empty_value(vehicle.get('model', 'N/A')),
                    self._handle_empty_value(vehicle.get('vin', 'N/A')),
                    self._handle_empty_value(vehicle.get('complaint_number', 'N/A'))
                ])
            
            # Create table
            table = Table(data)
            table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 6)
            ]))
            elements.append(table)
            
            # Add legal text
            elements.append(Spacer(1, 24))
            legal_text = """
            <para fontSize="10">
            All vehicles are being auctioned in accordance with Michigan law MCL 257.252g regarding
            the disposition of abandoned vehicles. All items are sold as-is with no warranty or guarantee.
            Payment must be made in full at the time of sale by cash or certified funds. Buyers will
            receive a bill of sale and may apply for a title through the Michigan Secretary of State.
            A valid photo ID is required to participate in the auction.
            </para>
            """
            elements.append(Paragraph(legal_text, self.small_style))
            
            # Add contact info
            elements.append(Spacer(1, 12))
            elements.append(Paragraph("For more information, contact iTow at 810-394-5937", self.field_style))
            
            # Build the document
            doc.build(elements)
            return True, None
        except Exception as e:
            logging.error(f"Error generating newspaper ad: {e}")
            return False, str(e)

    def generate_scrap_certification(self, data, photos, pdf_path):
        try:
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
            elements = []
            
            # Add header
            self._add_header(elements)
            
            # Add title
            elements.append(Paragraph("SCRAP VEHICLE CERTIFICATION", self.title_style))
            elements.append(Spacer(1, 12))
            
            # Add notice text
            notice = 'This document certifies that the following vehicle has been disposed of as scrap in accordance with Michigan law.'
            elements.append(Paragraph(notice, self.field_style))
            elements.append(Spacer(1, 12))
            
            # Add timestamp
            timestamp = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            elements.append(Paragraph(timestamp, self.small_style))
            elements.append(Spacer(1, 12))
            
            # Build vehicle description
            vehicle_desc = ' '.join(filter(None, [
                self._handle_empty_value(data.get('year', 'N/A')), 
                self._handle_empty_value(data.get('make', 'N/A')), 
                self._handle_empty_value(data.get('model', 'N/A')), 
                self._handle_empty_value(data.get('color', 'N/A'))
            ]))
            
            # Create details table
            details = [
                ['COMPLAINT NUMBER:', self._handle_empty_value(data.get('complaint_number', 'N/A'))],
                ['VEHICLE DESCRIPTION:', vehicle_desc],
                ['VIN:', self._handle_empty_value(data.get('vin', 'N/A'))],
                ['PLATE NUMBER:', self._handle_empty_value(data.get('plate', 'N/A'))],
                ['TOW DATE:', self._format_date_for_pdf(data.get('tow_date', 'N/A'))],
                ['LEGAL SCRAP DATE:', self._format_date_for_pdf(data.get('estimated_date', 'N/A'))],
                ['SALVAGE VALUE:', f"${float(data.get('salvage_value', 0)):.2f}"]
            ]
            
            # Create table
            table = Table(details, colWidths=[2*inch, 3.5*inch])
            table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 6)
            ]))
            elements.append(table)
            
            # Add certification text
            elements.append(Spacer(1, 24))
            certification = """
            <para fontSize="10">
            I certify that this vehicle has been properly disposed of as scrap in accordance with
            Michigan law MCL 257.252b. The vehicle was held for the required time period,
            proper notifications were sent, and all statutory requirements were met.
            Photos documenting the vehicle condition are attached to this certification.
            </para>
            """
            elements.append(Paragraph(certification, self.small_style))
            
            # Add photo references
            elements.append(Spacer(1, 12))
            photo_text = f"Number of photos taken: {len(photos)}"
            elements.append(Paragraph(photo_text, self.field_style))
            
            # List photo filenames
            for photo in photos:
                elements.append(Paragraph(f"• {photo}", self.small_style))
            
            # Add signature lines
            elements.append(Spacer(1, 36))
            elements.append(Paragraph('____________________________     ____________________________', self.field_style))
            elements.append(Paragraph('iTow Representative             Date', self.field_style))
            
            # Build the document
            doc.build(elements)
            return True, None
        except Exception as e:
            logging.error(f"Error generating scrap certification: {e}")
            return False, str(e)

    def generate_compliance_report(self, vehicles, pdf_path):
        try:
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
            elements = []
            
            # Add header
            self._add_header(elements)
            
            # Add title
            elements.append(Paragraph("ABANDONED VEHICLE COMPLIANCE REPORT", self.title_style))
            elements.append(Spacer(1, 6))
            
            # Add report info
            report_info = f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            elements.append(Paragraph(report_info, self.small_style))
            elements.append(Paragraph(f"Total Vehicles: {len(vehicles)}", self.small_style))
            elements.append(Spacer(1, 12))
            
            # Create table
            data = [['Call #', 'Comp. #', 'Status', 'Tow Date', 'TOP Date', 'TR-52 Date', 'Auction/Scrap', 'Release']]
            
            for vehicle in vehicles:
                data.append([
                    self._handle_empty_value(vehicle.get('towbook_call_number', 'N/A')),
                    self._handle_empty_value(vehicle.get('complaint_number', 'N/A')),
                    self._handle_empty_value(vehicle.get('status', 'N/A')),
                    self._format_date_for_pdf(vehicle.get('tow_date', 'N/A')),
                    self._format_date_for_pdf(vehicle.get('top_form_sent_date', 'N/A')),
                    self._format_date_for_pdf(vehicle.get('tr52_available_date', 'N/A')),
                    self._format_date_for_pdf(vehicle.get('auction_date', 'N/A')),
                    self._format_date_for_pdf(vehicle.get('release_date', 'N/A'))
                ])
            
            # Create the table with specific column widths
            table = Table(data, colWidths=[0.8*inch, 0.9*inch, 0.9*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.9*inch, 0.8*inch])
            
            # Style the table
            table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('PADDING', (0, 0), (-1, -1), 4)
            ]))
            
            elements.append(table)
            
            # Add compliance statement
            elements.append(Spacer(1, 12))
            compliance_text = """
            <para fontSize="9">
            This report documents compliance with Michigan MCL 257.252 regarding abandoned vehicles.
            All vehicles listed have been processed according to statutory requirements, including
            proper notification, holding periods, and disposition procedures.
            </para>
            """
            elements.append(Paragraph(compliance_text, self.small_style))
            
            # Add certification
            elements.append(Spacer(1, 24))
            elements.append(Paragraph('I certify that this information is true and accurate:', self.small_style))
            elements.append(Spacer(1, 24))
            elements.append(Paragraph('____________________________     ____________________________', self.small_style))
            elements.append(Paragraph('Signature                       Date', self.small_style))
            
            # Build the document
            doc.build(elements)
            return True, None
        except Exception as e:
            logging.error(f"Error generating compliance report: {e}")
            return False, str(e)