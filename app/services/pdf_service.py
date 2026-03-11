import os
import logging
from io import BytesIO
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from app.schemas.soil_test import SoilTestResponse

class PDFService:
    @classmethod
    def get_report_elements(cls, report_data: SoilTestResponse) -> list:
        """
        Returns a list of reportlab elements for the soil report.
        """
        styles = getSampleStyleSheet()
        
        # Brand Colors
        BRAND_GREEN = colors.HexColor("#1A3C2A")
        TEXT_DARK_GRAY = colors.HexColor("#333333")
        TABLE_HEADER_GREEN = colors.HexColor("#3E5F3F")
        STATUS_BG_GREEN = colors.HexColor("#D4EDDA")
        STATUS_TEXT_GREEN = colors.HexColor("#155724")
        ROW_BEIGE = colors.HexColor("#FDF9F0")

        elements = []

        # --- 1. Header with Circular Logo ---
        logo_png = os.path.join(os.getcwd(), "static", "logo.png")
        logo_jpg = os.path.join(os.getcwd(), "static", "logo.jpg")
        logo_path = logo_png if os.path.exists(logo_png) else (logo_jpg if os.path.exists(logo_jpg) else None)
        
        logo_element = None
        if logo_path:
            try:
                logo_element = Image(logo_path, width=1.2*inch, height=1.2*inch, mask='auto')
            except Exception as e:
                logging.warning(f"Failed to load logo in Soil PDF: {e}")

        company_title_style = ParagraphStyle('CompTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=18, textColor=BRAND_GREEN, alignment=1)
        report_title_style = ParagraphStyle('ReportTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=16, textColor=TEXT_DARK_GRAY, alignment=1)
        
        if logo_element:
            logo_element.hAlign = 'CENTER'
            elements.append(logo_element)
            elements.append(Spacer(1, 10))
        
        elements.append(Paragraph("Jaiswal Khad Bhandar", company_title_style))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("Agro Management System - Soil Test Report", report_title_style))
        elements.append(Spacer(1, 20))

        # --- 2. Meta Info Table ---
        meta = report_data.report_meta
        meta_data = [
            [Paragraph("<b>Report ID:</b>", styles['Normal']), str(meta.report_id), Paragraph("<b>Date:</b>", styles['Normal']), meta.created_at.strftime("%Y-%m-%d %H:%M")],
            [Paragraph("<b>Farmer Name:</b>", styles['Normal']), meta.farmer_name, Paragraph("<b>WhatsApp:</b>", styles['Normal']), meta.whatsapp_number],
            [Paragraph("<b>Crop Type:</b>", styles['Normal']), meta.crop_type, Paragraph("<b>Sensor Status:</b>", styles['Normal']), meta.sensor_status],
            [Paragraph("<b>Soil Score:</b>", styles['Normal']), Paragraph(f"<b>{report_data.summary.soil_score}</b>", styles['Normal']), "", ""]
        ]
        
        meta_table = Table(meta_data, colWidths=[1*inch, 2.5*inch, 1*inch, 1.8*inch])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('BACKGROUND', (1,3), (1,3), colors.lightgreen) # Soil score highlight
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 15))

        # Summary Text
        elements.append(Paragraph(f"<b>Summary:</b> {report_data.summary_message}", styles['Normal']))
        elements.append(Spacer(1, 25))

        # --- 3. Organized Parameter Tables ---
        def create_table_with_badges(title, items):
            elements.append(Paragraph(f"<b>{title}</b>", styles['Heading3']))
            elements.append(Spacer(1, 8))
            
            data = [["Nutrient" if "Nutrients" in title else ("Temperature" if "Temperature" in title else "Parameter"), "Value", "Unit", "Ideal Range", "Status"]]
            
            for item in items:
                status_text = item.status.upper()
                status_color = STATUS_BG_GREEN
                status_text_color = STATUS_TEXT_GREEN
                
                if status_text == "LOW":
                    status_color = colors.HexColor("#FFF3CD")
                    status_text_color = colors.HexColor("#856404")
                elif status_text == "HIGH":
                    status_color = colors.HexColor("#F8D7DA")
                    status_text_color = colors.HexColor("#721C24")

                badge_style = ParagraphStyle(
                    'Badge',
                    fontName='Helvetica-Bold',
                    fontSize=8,
                    textColor=status_text_color,
                    alignment=1,
                    backColor=status_color,
                    borderPadding=4,
                    borderRadius=4
                )
                
                data.append([
                    item.name,
                    f"{item.value:.1f}" if item.name not in ["Calcium", "EC", "pH Value"] else (f"{item.value:.1f}" if item.name != "Calcium" else f"{int(item.value)}"),
                    item.unit,
                    item.ideal_range,
                    Paragraph(status_text, badge_style)
                ])

            tbl = Table(data, colWidths=[1.8*inch, 0.8*inch, 0.8*inch, 1.5*inch, 0.8*inch])
            tbl.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), TABLE_HEADER_GREEN),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('ALIGN', (0,0), (0,-1), 'LEFT'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 10),
                ('BOTTOMPADDING', (0,0), (-1,0), 8),
                ('TOPPADDING', (0,0), (-1,0), 8),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('BACKGROUND', (0,1), (-1,-1), ROW_BEIGE),
            ]))
            elements.append(tbl)
            elements.append(Spacer(1, 20))

        create_table_with_badges("Primary Nutrients", report_data.primary_nutrients)
        create_table_with_badges("Micronutrients", report_data.micronutrients)
        create_table_with_badges("Environmental Parameters", report_data.environmental_parameters)

        return elements

    @staticmethod
    def generate_soil_report_pdf(report_data: SoilTestResponse) -> BytesIO:
        """
        Generates a professional A4 PDF Soil Test Report matching the provided UI image.
        Includes circular logo, three categorized tables, and status badges.
        """
        try:
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, 
                                    rightMargin=40, leftMargin=40, 
                                    topMargin=40, bottomMargin=40)
            
            elements = PDFService.get_report_elements(report_data)

            # Build Document
            doc.build(elements)
            buffer.seek(0)
            return buffer

        except Exception as e:
            logging.error(f"Critical failure building Soil PDF structure: {e}")
            raise ValueError(f"Soil Report PDF generation failed: {str(e)}")

            # Build Document
            doc.build(elements)
            buffer.seek(0)
            return buffer

        except Exception as e:
            logging.error(f"Critical failure building Soil PDF structure: {e}")
            raise ValueError(f"Soil Report PDF generation failed: {str(e)}")
