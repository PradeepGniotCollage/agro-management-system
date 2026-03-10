import os
import logging
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from app.schemas.invoice import InvoiceResponse

class InvoicePDFService:
    @classmethod
    def get_invoice_elements(cls, invoice_data: InvoiceResponse, doc_width: float) -> list:
        """
        Returns a list of reportlab elements for the invoice.
        """
        styles = getSampleStyleSheet()
        
        # Brand Colors
        BRAND_GREEN = colors.HexColor("#1A3C2A")
        BRAND_GOLD = colors.HexColor("#D4AF37")
        TEXT_DARK_GRAY = colors.HexColor("#333333")
        
        # Typography
        company_title_style = ParagraphStyle('CompanyTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=22, textColor=BRAND_GREEN, spaceAfter=4)
        tagline_style = ParagraphStyle('Tagline', parent=styles['Normal'], fontName='Helvetica', fontSize=11, textColor=TEXT_DARK_GRAY, spaceAfter=20)
        invoice_title_style = ParagraphStyle('InvoiceTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=26, textColor=BRAND_GREEN, alignment=2)
        meta_bold_style = ParagraphStyle('MetaBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=TEXT_DARK_GRAY, alignment=2)
        meta_style = ParagraphStyle('Meta', parent=styles['Normal'], fontName='Helvetica', fontSize=10, textColor=TEXT_DARK_GRAY, alignment=2)
        shop_address_style = ParagraphStyle('ShopAddress', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=colors.gray, spaceAfter=4, leading=12)

        elements = []

        # Header logic
        logo_png = os.path.join(os.getcwd(), "static", "logo.png")
        logo_jpg = os.path.join(os.getcwd(), "static", "logo.jpg")
        logo_path = logo_png if os.path.exists(logo_png) else (logo_jpg if os.path.exists(logo_jpg) else None)
        
        logo_element = None
        if logo_path:
            try:
                logo_element = Image(logo_path, width=1.5*inch, height=1.5*inch, mask='auto')
                logo_element.hAlign = 'LEFT'
            except Exception as e:
                logging.warning(f"Failed to load logo image: {e}")

        company_info = [
            Paragraph("Jaiswal Khad Bhandar", company_title_style),
            Paragraph("Fertilizers & Agro Solutions", tagline_style),
            Paragraph("Mathiya Mahawal Mahuapatan bazar", shop_address_style),
            Paragraph("deoria - 274408", shop_address_style)
        ]
        
        left_block = ([logo_element, Spacer(1, 10)] if logo_element else []) + company_info

        right_block = [
            Paragraph("INVOICE", invoice_title_style),
            Spacer(1, 15),
            Paragraph("Invoice Number:", meta_bold_style),
            Paragraph(invoice_data.invoice_meta.invoice_number, meta_style),
            Spacer(1, 5),
            Paragraph("Date:", meta_bold_style),
            Paragraph(invoice_data.invoice_meta.invoice_date.strftime("%d-%b-%Y"), meta_style)
        ]
        
        header_table = Table([[left_block, right_block]], colWidths=[doc_width/2.0, doc_width/2.0])
        header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('ALIGN', (1,0), (1,0), 'RIGHT')]))
        elements.append(header_table)
        
        elements.append(Spacer(1, 10))
        line_table = Table([[""]], colWidths=[doc_width])
        line_table.setStyle(TableStyle([('LINEABOVE', (0,0), (-1,-1), 2, BRAND_GOLD)]))
        elements.append(line_table)
        elements.append(Spacer(1, 20))

        # Customer Section
        bill_to_title = ParagraphStyle('BillToTitle', parent=styles['Heading3'], fontName='Helvetica-Bold', textColor=BRAND_GREEN, spaceAfter=8)
        bill_to_text = ParagraphStyle('BillToText', parent=styles['Normal'], fontName='Helvetica', fontSize=10, textColor=TEXT_DARK_GRAY, leading=14)
        
        elements.append(Paragraph("Billed To:", bill_to_title))
        elements.append(Paragraph(invoice_data.invoice_meta.customer_name, bill_to_text))
        elements.append(Paragraph(invoice_data.invoice_meta.mobile_number, bill_to_text))
        elements.append(Paragraph(invoice_data.invoice_meta.address, bill_to_text))
        elements.append(Spacer(1, 25))
        
        # Items Table
        table_data = [["Item Description", "Quantity", "Rate", "Amount"]]
        for item in invoice_data.items:
            table_data.append([item.item_name, f"{item.quantity:.2f}", f"Rs. {item.rate:.2f}", f"Rs. {item.total:.2f}"])
            
        col_widths = [doc_width * 0.45, doc_width * 0.15, doc_width * 0.2, doc_width * 0.2]
        table = Table(table_data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), BRAND_GREEN),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('TEXTCOLOR', (0, 1), (-1, -1), TEXT_DARK_GRAY),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 20))
        
        # Footer Totals
        totals_data = [["Subtotal:", f"Rs. {invoice_data.subtotal:.2f}"], ["Grand Total:", f"Rs. {invoice_data.grand_total:.2f}"]]
        totals_table = Table(totals_data, colWidths=[doc_width * 0.8, doc_width * 0.2])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'), 
            ('TEXTCOLOR', (0, 1), (-1, 1), BRAND_GREEN),
            ('LINEABOVE', (0, 1), (-1, 1), 1, BRAND_GOLD),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(totals_table)
        elements.append(Spacer(1, 40))
        
        footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontName='Helvetica-Oblique', fontSize=8, textColor=colors.gray, alignment=1)
        elements.append(Paragraph("This is a computer generated invoice and requires no signature.", footer_style))
        
        return elements

    @staticmethod
    def generate_invoice_pdf(invoice_data: InvoiceResponse) -> BytesIO:
        """
        Generates a professional A4 PDF invoice incorporating standard corporate layout rules.
        Includes logo handling, structured tables, and explicit error handling.
        """
        try:
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4,
                                    rightMargin=40, leftMargin=40,
                                    topMargin=40, bottomMargin=40)
            
            elements = InvoicePDFService.get_invoice_elements(invoice_data, doc.width)

            # Build Document
            doc.build(elements)
            buffer.seek(0)
            return buffer

        except Exception as e:
            logging.error(f"Critical failure building PDF canvas: {e}")
            raise ValueError(f"PDF structure generation failed: {str(e)}")

            # Build Document
            doc.build(elements)
            buffer.seek(0)
            
            return buffer

        except Exception as e:
            logging.error(f"Critical failure building PDF canvas: {e}")
            raise ValueError(f"PDF structure generation failed: {str(e)}")
