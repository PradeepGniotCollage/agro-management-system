import logging
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, PageBreak
from app.services.pdf_service import PDFService
from app.services.invoice_pdf_service import InvoicePDFService
from app.schemas.soil_test import SoilTestResponse
from app.schemas.invoice import InvoiceResponse

class PrintService:
    @staticmethod
    def generate_combined_print_pdf(report_data: SoilTestResponse, invoice_data: InvoiceResponse) -> BytesIO:
        """
        Generates a single PDF containing the Soil Report on page 1 and Invoice on page 2.
        """
        try:
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4,
                                    rightMargin=40, leftMargin=40,
                                    topMargin=40, bottomMargin=40)
            
            # 1. Get Soil Report Elements
            report_elements = PDFService.get_report_elements(report_data)
            
            # 2. Add Page Break
            report_elements.append(PageBreak())
            
            # 3. Get Invoice Elements
            invoice_elements = InvoicePDFService.get_invoice_elements(invoice_data, doc.width)
            
            # 4. Combine all elements
            combined_elements = report_elements + invoice_elements
            
            # Build final document
            doc.build(combined_elements)
            buffer.seek(0)
            return buffer
            
        except Exception as e:
            logging.error(f"Failed to generate combined print PDF: {e}")
            raise ValueError(f"Combined PDF generation failed: {str(e)}")
