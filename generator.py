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
        if os.path.exists(self.logo_path):
            try:
                logo = Image(self.logo_path, width=1.5*inch, height=0.75*inch)
                elements.append(logo)
                elements.append(Spacer(1, 12))
            except Exception as e:
                logging.error(f"Error adding logo to PDF: {e}")
        
        header = '<para alignment="center"><b>iTow</b><br/>205 W Johnson St, Clio, MI 48420<br/>Phone 810-394-5937 · EMAIL: itow2017@gmail.com</para>'
        elements.append(Paragraph(header, self.header_style))
        elements.append(Spacer(1, 12))

    def _handle_empty_value(self, value):
        """Handle empty or None values"""
        if value is None or value == '' or value == 'None':
            return 'N/A'
        return value

    def generate_top(self, data, pdf_path):
        try:
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
            elements = []
            
            # Add header
            self._add_header(elements)
            
            # Add title
            elements.append(Paragraph('PRIVATE PROPERTY IMPOUND NOTIFICATION', self.title_style))
            elements.append(Spacer(1, 12))
            
            # Add notice text
            notice = 'This is notification of a vehicle removal off of private property.<br/>Per MCL 257.252a(9)'
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
                ['TO:', self._handle_empty_value(data.get('jurisdiction', 'N/A'))],
                ['DATE OF TOW:', self._handle_empty_value(data.get('tow_date', 'N/A'))],
                ['TIME OF TOW:', self._handle_empty_value(data.get('tow_time', 'N/A'))],
                ['TOWED FROM:', self._handle_empty_value(data.get('location', 'N/A'))],
                ['REQUESTED BY:', self._handle_empty_value(data.get('requestor', 'N/A'))],
                ['VEHICLE DESCRIPTION:', vehicle_desc],
                ['VIN:', self._handle_empty_value(data.get('vin', 'N/A'))],
                ['PLATE NUMBER:', self._handle_empty_value(data.get('plate', 'N/A'))],
                ['STATE:', self._handle_empty_value(data.get('state', 'N/A'))],
                ['COMPLAINT #:', self._handle_empty_value(data.get('complaint_number', 'N/A'))],
                ['CASE NUMBER:', self._handle_empty_value(data.get('case_number', 'N/A'))],
                ['OFFICER NAME:', self._handle_empty_value(data.get('officer_name', 'N/A'))]
            ]
            
            # Create table
            table = Table(details, colWidths=[1.5*inch, 4*inch])
            table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 6)
            ]))
            elements.append(table)
            
            # Add legal notice
            elements.append(Spacer(1, 24))
            legal_notice = """
            <para fontSize="10">
            NOTE: Per MCL 257.252a(9), this vehicle has been removed from private property at the request 
            of the property owner or authorized agent. The owner may reclaim the vehicle by paying the 
            accrued towing and storage fees. If the vehicle remains unclaimed for 20 days, it may be 
            considered abandoned and subject to procedures under MCL 257.252g.
            </para>
            """
            elements.append(Paragraph(legal_notice, self.small_style))
            
            # Add signature line
            elements.append(Spacer(1, 48))
            elements.append(Paragraph('_________________________     _________________________', self.field_style))
            elements.append(Paragraph('Towing Agent Signature     Police Department Receipt', self.small_style))
            
            # Build the document
            doc.build(elements)
            return True, None
        except Exception as e:
            logging.error(f"Error generating TOP: {e}")
            return False, str(e)

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
                ['TOW DATE:', self._handle_empty_value(data.get('tow_date', 'N/A'))]
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
            if top_sent_date and top_sent_date != 'N/A':
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
                ['TOW DATE:', tow_date.strftime('%Y-%m-%d')],
                ['TOP NOTIFICATION DATE:', top_sent_date.strftime('%Y-%m-%d')],
                ['REDEMPTION END DATE:', redemption_end_date.strftime('%Y-%m-%d')],
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
            legal_text = """
            <para fontSize="10">
            This vehicle was towed from private property at the request of the property owner or agent. 
            A Temporary Ownership Permit (TOP) notification was sent on the date indicated above. 
            The 20-day redemption period has now expired without the vehicle being claimed.
            </para>
            <para fontSize="10">
            Per MCL 257.252a, this vehicle may now be considered abandoned for disposition purposes.
            We are requesting a TR-52 form to be issued so that this vehicle can be:
            </para>
            """
            elements.append(Paragraph(legal_text, self.small_style))
            
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
                ['TOW DATE:', self._handle_empty_value(data.get('tow_date', 'N/A'))],
                ['LEGAL SCRAP DATE:', self._handle_empty_value(data.get('estimated_date', 'N/A'))],
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
                    self._handle_empty_value(vehicle.get('tow_date', 'N/A')),
                    self._handle_empty_value(vehicle.get('top_form_sent_date', 'N/A')),
                    self._handle_empty_value(vehicle.get('tr52_available_date', 'N/A')),
                    self._handle_empty_value(vehicle.get('auction_date', 'N/A')),
                    self._handle_empty_value(vehicle.get('release_date', 'N/A'))
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