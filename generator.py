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
            data = [['Call #', 'Comp. #', 'Status', 'Tow Date', 'TOP Date', 'Auction/Scrap', 'Release']]
            
            for vehicle in vehicles:
                data.append([
                    self._handle_empty_value(vehicle.get('towbook_call_number', 'N/A')),
                    self._handle_empty_value(vehicle.get('complaint_number', 'N/A')),
                    self._handle_empty_value(vehicle.get('status', 'N/A')),
                    self._format_date_for_pdf(vehicle.get('tow_date', 'N/A')),
                    self._format_date_for_pdf(vehicle.get('top_form_sent_date', 'N/A')),
                    self._format_date_for_pdf(vehicle.get('auction_date', 'N/A')),
                    self._format_date_for_pdf(vehicle.get('release_date', 'N/A'))
                ])
            
            # Create the table with specific column widths
            table = Table(data, colWidths=[0.8*inch, 0.9*inch, 0.9*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.9*inch])
            
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