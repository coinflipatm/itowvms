from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import logging
import os

class PDFGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.header_style = ParagraphStyle('Header', parent=self.styles['Normal'], fontSize=12, alignment=1, spaceAfter=20)
        self.field_style = ParagraphStyle('Field', parent=self.styles['Normal'], fontSize=11, spaceBefore=6, spaceAfter=6)

    def generate_top(self, data, pdf_path):
        try:
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
            elements = []
            header = '<para alignment="center"><b>iTow</b><br/>205 W Johnson St, Clio, MI 48420<br/>Phone 810-394-5937 · EMAIL: itow2017@gmail.com</para>'
            elements.append(Paragraph(header, self.header_style))
            elements.append(Spacer(1, 12))
            notice = 'This is notification of a vehicle removal off of private property.<br/>Per MCL 257.252a(9)'
            elements.append(Paragraph(notice, self.field_style))
            elements.append(Spacer(1, 12))
            vehicle_desc = ' '.join(filter(None, [data.get('year'), data.get('make'), data.get('model'), data.get('color')]))
            details = [
                ('TO:', data.get('jurisdiction', 'N/A')),
                ('DATE OF TOW:', data.get('tow_date', 'N/A')),
                ('TIME OF TOW:', data.get('tow_time', 'N/A')),
                ('TOWED FROM:', data.get('location', 'N/A')),
                ('TOW REQUESTED BY:', data.get('requestor', 'N/A')),
                ('VEHICLE DESCRIPTION:', vehicle_desc),
                ('VIN:', data.get('vin', 'N/A')),
                ('PLATE NUMBER:', data.get('plate', 'N/A')),
                ('COMPLAINT #:', data.get('complaint_number', 'N/A')),
                ('CASE NUMBER:', data.get('case_number', 'N/A')),
                ('OFFICER NAME:', data.get('officer_name', 'N/A'))
            ]
            for label, value in details:
                elements.append(Paragraph(f'<b>{label}</b> {value or "N/A"}', self.field_style))
                elements.append(Spacer(1, 6))
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
            header = '<para alignment="center"><b>iTow</b><br/>205 W Johnson St, Clio, MI 48420<br/>Phone 810-394-5937 · EMAIL: itow2017@gmail.com</para>'
            elements.append(Paragraph(header, self.header_style))
            elements.append(Spacer(1, 12))
            elements.append(Paragraph("VEHICLE RELEASE NOTICE", self.styles['Heading1']))
            elements.append(Spacer(1, 12))
            vehicle_desc = ' '.join(filter(None, [data.get('year'), data.get('make'), data.get('model'), data.get('color')]))
            details = [
                ('COMPLAINT NUMBER:', data.get('complaint_number', 'N/A')),
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
                elements.append(Paragraph(f'<b>{label}</b> {value or "N/A"}', self.field_style))
                elements.append(Spacer(1, 6))
            statement = f'This certifies that the vehicle was released from iTow custody on {data.get("release_date", "[Date]")} at {data.get("release_time", "[Time]")} for {data.get("release_reason", "[Reason]")}.'
            elements.append(Spacer(1, 12))
            elements.append(Paragraph(statement, self.field_style))
            elements.append(Spacer(1, 36))
            elements.append(Paragraph('____________________________     ____________________________<br/>iTow Signature     Recipient Signature', self.field_style))
            doc.build(elements)
            return True, None
        except Exception as e:
            logging.error(f"Error generating release: {e}")
            return False, str(e)