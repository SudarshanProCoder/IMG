import os
import io
from datetime import datetime
from jinja2 import Template
import base64

# Try to import different PDF libraries
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    print("WeasyPrint not available, will use alternative methods")

try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.colors import blue, red, green, black
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("ReportLab not available, will use alternative methods")

def generate_html_certificate(student, credit_points):
    """
    Generate a certificate using the provided HTML template with dynamic student data
    """
    
    # Read the certificate template
    template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'admin', 'certificate.html')
    
    with open(template_path, 'r', encoding='utf-8') as file:
        template_content = file.read()
    
    # Create Jinja2 template
    template = Template(template_content)
    
    # Prepare data for the template
    certificate_data = {
        'student_name': student.full_name,
        'credit_points': f"{credit_points} POINTS",
        'current_date': datetime.now().strftime('%B %d, %Y'),
        'academic_year': datetime.now().strftime('%Y')
    }
    
    # Render the template with student data
    html_content = template.render(**certificate_data)
    
    # Try different PDF generation methods
    pdf_buffer = None
    
    # Method 1: Try WeasyPrint with enhanced CSS for better text rendering
    if WEASYPRINT_AVAILABLE and pdf_buffer is None:
        try:
            # Enhanced CSS for better PDF rendering and text justification
            css_content = """
            @page {
                size: A4 landscape;
                margin: 0;
            }
            body {
                font-family: 'Times New Roman', serif;
                font-size: 16px;
                line-height: 1.4;
                margin: 0;
                padding: 0;
            }
            .certificate {
                width: 297mm;
                height: 210mm;
                margin: 0;
                padding: 25mm;
                box-sizing: border-box;
            }
            .certificate-text, .completion-text, .recognition-text {
                text-align: center !important;
                text-justify: inter-word;
                word-spacing: 2px;
                letter-spacing: 0.5px;
            }
            .student-name {
                text-align: center !important;
                font-weight: bold;
            }
            .credit-box {
                text-align: center !important;
            }
            .signatures {
                text-align: center !important;
            }
            """
            
            # Create PDF from HTML with enhanced CSS
            pdf = HTML(string=html_content).write_pdf(stylesheets=[CSS(string=css_content)])
            pdf_buffer = io.BytesIO()
            pdf_buffer.write(pdf)
            pdf_buffer.seek(0)
            print("Successfully generated PDF with WeasyPrint")
            
        except Exception as e:
            print(f"WeasyPrint failed: {str(e)}")
            pdf_buffer = None
    
    # Method 2: Fallback to ReportLab with proper formatting
    if REPORTLAB_AVAILABLE and pdf_buffer is None:
        try:
            pdf_buffer = generate_reportlab_certificate(student, credit_points)
            print("Successfully generated PDF with ReportLab")
        except Exception as e:
            print(f"ReportLab failed: {str(e)}")
            pdf_buffer = None
    
    # If all methods fail, return a simple fallback
    if pdf_buffer is None:
        print("All PDF generation methods failed, using simple fallback")
        return generate_simple_fallback_certificate(student, credit_points)
    
    return pdf_buffer

def generate_reportlab_certificate(student, credit_points):
    """
    Generate certificate using ReportLab with proper text formatting and justification
    """
    # Create PDF buffer
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Create custom styles with proper formatting
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=42,
        textColor=blue,
        alignment=1,  # Center alignment
        spaceAfter=30,
        fontName='Helvetica-Bold',
        leading=50
    )
    
    institution_style = ParagraphStyle(
        'Institution',
        parent=styles['Heading2'],
        fontSize=32,
        textColor=blue,
        alignment=1,
        spaceAfter=20,
        fontName='Helvetica-Bold',
        leading=38
    )
    
    name_style = ParagraphStyle(
        'CustomName',
        parent=styles['Heading2'],
        fontSize=38,
        textColor=green,
        alignment=1,
        spaceAfter=25,
        fontName='Helvetica-Bold',
        leading=45
    )
    
    content_style = ParagraphStyle(
        'CustomContent',
        parent=styles['Normal'],
        fontSize=24,
        alignment=1,  # Center alignment for better readability
        spaceAfter=20,
        fontName='Helvetica',
        leading=32,
        wordWrap='CJK'  # Better word wrapping
    )
    
    credit_style = ParagraphStyle(
        'CreditStyle',
        parent=styles['Normal'],
        fontSize=32,
        textColor=red,
        alignment=1,
        spaceAfter=25,
        fontName='Helvetica-Bold',
        leading=38
    )
    
    signature_style = ParagraphStyle(
        'SignatureStyle',
        parent=styles['Normal'],
        fontSize=16,
        alignment=1,
        spaceAfter=15,
        fontName='Helvetica',
        leading=20
    )
    
    # Build the certificate content
    story = []
    
    # Title
    story.append(Paragraph("CERTIFICATE OF COMPLETION", title_style))
    story.append(Spacer(1, 30))
    
    # Institution
    story.append(Paragraph("SAKEC Institute of Technology", institution_style))
    story.append(Paragraph("Excellence in Education & Innovation", content_style))
    story.append(Spacer(1, 40))
    
    # Certificate text
    story.append(Paragraph("This is to certify that", content_style))
    story.append(Spacer(1, 25))
    
    # Student name
    story.append(Paragraph(student.full_name, name_style))
    story.append(Spacer(1, 25))
    
    # Completion text - properly formatted
    completion_text = "has successfully completed the <b>Summer Internship Program</b> and demonstrated exceptional performance throughout the program duration."
    story.append(Paragraph(completion_text, content_style))
    story.append(Spacer(1, 35))
    
    # Credit points
    credit_text = f"Credit Points Awarded: {credit_points}"
    story.append(Paragraph(credit_text, credit_style))
    story.append(Spacer(1, 35))
    
    # Recognition text - properly formatted
    recognition_text = "In recognition of dedication, professionalism, and outstanding contribution to the internship objectives and organizational goals."
    story.append(Paragraph(recognition_text, content_style))
    story.append(Spacer(1, 50))
    
    # Date
    date_text = f"Date: {datetime.now().strftime('%B %d, %Y')}"
    story.append(Paragraph(date_text, content_style))
    story.append(Spacer(1, 50))
    
    # Signatures section
    signatures = [
        "Head of Department",
        "Principal", 
        "Placement Cell",
        "Mentor",
        "Placement Incharge",
        date_text
    ]
    
    for signature in signatures:
        story.append(Paragraph(signature, signature_style))
        story.append(Spacer(1, 8))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    
    return buffer

def generate_simple_fallback_certificate(student, credit_points):
    """
    Simple fallback certificate generator
    """
    if REPORTLAB_AVAILABLE:
        return generate_reportlab_certificate(student, credit_points)
    else:
        # Create a simple text-based certificate
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
        
        styles = getSampleStyleSheet()
        story = []
        
        # Simple certificate content
        story.append(Paragraph("Certificate of Completion", styles['Heading1']))
        story.append(Spacer(1, 30))
        story.append(Paragraph(f"This is to certify that {student.full_name}", styles['Normal']))
        story.append(Spacer(1, 20))
        story.append(Paragraph("has successfully completed the Summer Internship Program", styles['Normal']))
        story.append(Spacer(1, 20))
        story.append(Paragraph(f"Credit Points: {credit_points}", styles['Normal']))
        story.append(Spacer(1, 30))
        story.append(Paragraph(f"Date: {datetime.now().strftime('%B %d, %Y')}", styles['Normal']))
        
        doc.build(story)
        buffer.seek(0)
        return buffer

# Keep existing functions for backward compatibility
def generate_svg_certificate(student, credit_points):
    """
    Legacy function - now redirects to HTML certificate generator
    """
    return generate_html_certificate(student, credit_points)

def generate_internship_certificate(student, credit_points):
    """
    Legacy function - now redirects to HTML certificate generator
    """
    return generate_html_certificate(student, credit_points)