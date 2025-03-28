# generator.py
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import logging
import os

class PDFGenerator:
    def __init__(self):
        self.setup_styles()
    
    def setup_styles(self):
        styles = getSampleStyleSheet()
        self.header_style = ParagraphStyle(
            'Header',
            parent=styles['Normal'],
            fontSize=12,
            alignment=1,
            spaceAfter=20
        )
        
        self.field_style = ParagraphStyle(
            'FieldStyle',
            parent=styles['Normal'],
            fontSize=11,
            spaceBefore=6,
            spaceAfter=6,
            leading=14
        )
        
        self.title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=16,
            alignment=1,
            spaceBefore=12,
            spaceAfter=12
        )

    def generate_top(self, data, pdf_path):
        try:
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

            doc = SimpleDocTemplate(
                pdf_path,
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )

            elements = []

            header = '''
                <para alignment="center">
                <b>iTow</b><br/>
                205 W Johnson St, Clio, MI 48420<br/>
                Phone 810-394-5937 · EMAIL: itow2017@gmail.com
                </para>
            '''
            elements.append(Paragraph(header, self.header_style))
            elements.append(Spacer(1, 12))

            notice = '''
                This is notification of a vehicle removal off of private property.<br/>
                Keeping with the state law in regards to MCL 257.252a(9)
            '''
            elements.append(Paragraph(notice, self.field_style))
            elements.append(Spacer(1, 12))

            vehicle_desc = ' '.join(str(x) for x in [
                data.get('year', 'Unknown'),
                data.get('make', 'Unknown'),
                data.get('model', 'Unknown'),
                data.get('color', 'Unknown'),
                data.get('style', '')
            ] if x)

            details = [
                ('TO:', data.get('jurisdiction', 'N/A')),
                ('DATE OF TOW:', data.get('tow_date', 'N/A')),
                ('TIME OF TOW:', data.get('tow_time', 'N/A')),
                ('TOWED FROM:', data.get('location', 'N/A')),
                ('TOW REQUESTED BY:', data.get('requestor', 'N/A')),
                ('VEHICLE NUMBER (VIN):', data.get('vin', 'N/A')),
                ('VEHICLE DESCRIPTION:', vehicle_desc),
                ('PLATE NUMBER:', data.get('plate', 'N/A')),
                ('COMPLAINT #:', data.get('complaint_number', '')),
                ('CASE NUMBER:', data.get('case_number', 'N/A')),
                ('OFFICER NAME:', data.get('officer_name', 'N/A'))
            ]

            for label, value in details:
                field_text = f'''
                    <para leftIndent="0" firstLineIndent="0">
                    <b>{label}</b> {value or 'N/A'}
                    </para>
                '''
                elements.append(Paragraph(field_text, self.field_style))
                elements.append(Spacer(1, 6))

            doc.build(elements)
            return True, None
        except Exception as e:
            logging.error(f"Error generating PDF: {e}")
            return False, str(e)
            
    def generate_release_notice(self, data, pdf_path):
        try:
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

            doc = SimpleDocTemplate(
                pdf_path,
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )

            elements = []

            # Header
            header = '''
                <para alignment="center">
                <b>iTow</b><br/>
                205 W Johnson St, Clio, MI 48420<br/>
                Phone 810-394-5937 · EMAIL: itow2017@gmail.com
                </para>
            '''
            elements.append(Paragraph(header, self.header_style))
            elements.append(Spacer(1, 12))

            # Title
            title = "VEHICLE RELEASE NOTICE"
            elements.append(Paragraph(title, self.title_style))
            elements.append(Spacer(1, 12))

            # Vehicle Information
            vehicle_desc = ' '.join(str(x) for x in [
                data.get('year'), data.get('make'),
                data.get('model'), data.get('color')
            ] if x)

            details = [
                ('INVOICE NUMBER:', data.get('invoice_number', 'N/A')),
                ('RELEASE DATE:', data.get('release_date', 'N/A')),
                ('RELEASE TIME:', data.get('release_time', 'N/A')),
                ('RELEASED TO:', data.get('recipient', 'N/A')),
                ('RELEASE REASON:', data.get('release_reason', 'N/A')),
                ('VEHICLE DESCRIPTION:', vehicle_desc),
                ('VIN:', data.get('vin', 'N/A')),
                ('PLATE NUMBER:', data.get('plate', 'N/A')),
                ('TOW DATE:', data.get('tow_date', 'N/A'))
            ]

            for label, value in details:
                field_text = f'''
                    <para leftIndent="0" firstLineIndent="0">
                    <b>{label}</b> {value or 'N/A'}
                    </para>
                '''
                elements.append(Paragraph(field_text, self.field_style))
                elements.append(Spacer(1, 6))

            # Release Statement
            statement = f'''
                <para>
                This is to certify that the above-described vehicle has been released 
                from the custody of iTow on {data.get('release_date', '[Date]')} at 
                {data.get('release_time', '[Time]')} for the purpose of 
                {data.get('release_reason', '[Reason]')}.
                </para>
            '''
            elements.append(Spacer(1, 12))
            elements.append(Paragraph(statement, self.field_style))
            
            # Signature Section
            elements.append(Spacer(1, 36))
            
            signature_text = '''
                <para>
                ____________________________     ____________________________<br/>
                iTow Representative Signature     Recipient Signature
                </para>
            '''
            elements.append(Paragraph(signature_text, self.field_style))

            doc.build(elements)
            return True, None
        except Exception as e:
            logging.error(f"Error generating release notice: {e}")
            return False, str(e)