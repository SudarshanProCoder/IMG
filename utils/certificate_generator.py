from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, Flowable, HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Line
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import String
from reportlab.lib.utils import ImageReader
from io import BytesIO
import os
from datetime import datetime
import textwrap

# Import libraries for SVG handling
try:
    from svglib.svglib import svg2rlg
except ImportError:
    # If svglib is not installed, we'll handle the error gracefully
    svg2rlg = None

# Try to import cairosvg for SVG to PNG conversion
try:
    import cairosvg
    CAIROSVG_AVAILABLE = True
except ImportError:
    CAIROSVG_AVAILABLE = False
    print("CairoSVG not available, will use alternative methods")

# Try to import Pillow for image processing
try:
    from PIL import Image as PILImage
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    print("Pillow not available, will use alternative methods")

def convert_svg_to_png(svg_path, png_path=None, width=None, height=None):
    """
    Convert SVG to PNG using available libraries
    
    Args:
        svg_path: Path to the SVG file
        png_path: Path to save the PNG file (if None, will use svg_path with .png extension)
        width: Width of the output PNG (optional)
        height: Height of the output PNG (optional)
        
    Returns:
        Path to the PNG file if successful, None otherwise
    """
    if png_path is None:
        # Create PNG filename by replacing .svg with .png
        png_path = os.path.splitext(svg_path)[0] + '.png'
    
    # Check if PNG already exists
    if os.path.exists(png_path):
        print(f"PNG already exists: {png_path}")
        return png_path
    
    # Get absolute paths
    abs_svg_path = os.path.abspath(svg_path)
    abs_png_path = os.path.abspath(png_path)
    
    # Try conversion methods in order of preference
    success = False
    
    # Method 1: CairoSVG
    if CAIROSVG_AVAILABLE and not success:
        try:
            print(f"Attempting to convert {abs_svg_path} with CairoSVG")
            cairosvg.svg2png(url=abs_svg_path, write_to=abs_png_path, output_width=width, output_height=height)
            success = os.path.exists(abs_png_path)
            if success:
                print(f"Successfully converted with CairoSVG to {abs_png_path}")
                return abs_png_path
        except Exception as e:
            print(f"Error converting with CairoSVG: {e}")
    
    # Method 2: svglib + reportlab
    if svg2rlg is not None and not success:
        try:
            print(f"Attempting to convert {abs_svg_path} with svglib")
            from reportlab.graphics import renderPM
            drawing = svg2rlg(abs_svg_path)
            renderPM.drawToFile(drawing, abs_png_path, fmt="PNG")
            success = os.path.exists(abs_png_path)
            if success:
                print(f"Successfully converted with svglib to {abs_png_path}")
                return abs_png_path
        except Exception as e:
            print(f"Error converting with svglib: {e}")
    
    # Method 3: Create a simple fallback with Pillow
    if PILLOW_AVAILABLE and not success:
        try:
            print(f"Creating fallback PNG with Pillow at {abs_png_path}")
            # Determine if this is a seal or background based on filename
            is_seal = 'seal' in svg_path.lower()
            
            # Set default dimensions if not provided
            if width is None:
                width = 200 if is_seal else 800
            if height is None:
                height = 200 if is_seal else 600
            
            # Create a simple gold-colored image as fallback
            if is_seal:
                # Create a circular seal
                img = PILImage.new('RGBA', (width, height), (255, 255, 255, 0))
                # Draw a gold circle
                from PIL import ImageDraw
                draw = ImageDraw.Draw(img)
                center = width // 2
                radius = min(width, height) // 2 - 10
                # Gold color
                gold_color = (249, 212, 35, 255)
                draw.ellipse((center-radius, center-radius, center+radius, center+radius), fill=gold_color)
            else:
                # Create a patterned background
                img = PILImage.new('RGBA', (width, height), (255, 255, 255, 255))
                # Add some gold-colored elements
                from PIL import ImageDraw
                draw = ImageDraw.Draw(img)
                # Gold color with transparency
                gold_color = (249, 212, 35, 100)
                # Draw some decorative elements
                for i in range(0, width, 100):
                    draw.rectangle((i, 0, i+50, height), fill=gold_color)
            
            # Save the image
            img.save(abs_png_path, 'PNG')
            success = os.path.exists(abs_png_path)
            if success:
                print(f"Created fallback PNG at {abs_png_path}")
                return abs_png_path
        except Exception as e:
            print(f"Error creating fallback PNG: {e}")
    
    # If all methods fail
    print(f"All conversion methods failed for {svg_path}")
    return None

def generate_svg_certificate(student, credit_points):
    """
    Generate a certificate for a student using the SVG template
    
    Args:
        student: Student object with name and other details
        credit_points: Total credit points earned by the student
        
    Returns:
        BytesIO buffer containing the PDF certificate
    """
    # Create PDF document in landscape orientation with exact A4 dimensions to match SVG
    buffer = BytesIO()
    
    # Use exact A4 landscape dimensions (842x595 points) to match the SVG template
    width, height = landscape(A4)
    
    # Use minimal margins to ensure the SVG fills the entire page
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=0,  # No margins to allow SVG to fill entire page
        leftMargin=0,
        topMargin=0,
        bottomMargin=0
    )
    
    # Container for PDF elements
    elements = []
    
    # Define the function to draw the SVG certificate as background
    def draw_certificate_background(canvas, doc):
        # Use the SVG certificate template
        svg_path = os.path.join('static', 'images', 'certificate.svg.svg')
        if os.path.exists(svg_path):
            canvas.saveState()
            
            # Try direct SVG rendering first
            try:
                # Draw the SVG at exact page dimensions
                canvas.drawImage(svg_path, 0, 0, width=width, height=height)
                print(f"Using direct SVG rendering for certificate background")
                
                # Draw certificate content directly on the canvas instead of using flowables
                # This gives more precise control over positioning
                
                # Student name
                canvas.setFont('Helvetica-Bold', 36)
                canvas.setFillColorRGB(0.2, 0.2, 0.2)  # Dark gray
                canvas.drawCentredString(width/2, height/2 + 50, student.full_name)
                
                # Certificate text
                canvas.setFont('Helvetica', 16)
                certificate_text = f"This certificate is presented to the above named student"
                canvas.drawCentredString(width/2, height/2, certificate_text)
                
                certificate_text2 = f"for successfully completing internship requirements"
                canvas.drawCentredString(width/2, height/2 - 25, certificate_text2)
                
                certificate_text3 = f"and earning {credit_points} credit points."
                canvas.drawCentredString(width/2, height/2 - 50, certificate_text3)
                
                # Achievement text
                achievement_text = "This achievement demonstrates exceptional dedication and competence in the field."
                canvas.drawCentredString(width/2, height/2 - 90, achievement_text)
                
                # Current date
                current_date = datetime.now().strftime("%B %d, %Y")
                canvas.setFont('Helvetica', 12)
                canvas.drawCentredString(width/2, height/2 - 150, f"Issued on: {current_date}")
                
                # Add certificate seal
                seal_path = os.path.join('static', 'images', 'certificate_seal.svg')
                if os.path.exists(seal_path):
                    try:
                        # Position the seal at the bottom right
                        seal_width = 100
                        seal_height = 100
                        canvas.drawImage(seal_path, width - 150, 100, width=seal_width, height=seal_height)
                    except Exception as e:
                        print(f"Error rendering seal: {e}")
                        # Try with PNG if available
                        seal_png = os.path.join('static', 'images', 'certificate_seal.png')
                        if os.path.exists(seal_png):
                            try:
                                canvas.drawImage(seal_png, width - 150, 100, width=seal_width, height=seal_height)
                            except Exception as e:
                                print(f"Error rendering seal PNG: {e}")
                
            except Exception as e:
                print(f"Error rendering SVG with drawImage: {e}")
                
                # If direct rendering fails, try with svglib
                if svg2rlg is not None:
                    try:
                        # Get absolute path to ensure file is found
                        abs_svg_path = os.path.abspath(svg_path)
                        # Convert SVG to ReportLab drawing
                        drawing = svg2rlg(abs_svg_path)
                        # Render the drawing on the canvas
                        renderPDF.draw(drawing, canvas, 0, 0, width=width, height=height)
                        print(f"Successfully rendered certificate SVG with svglib")
                        
                        # Add the same text content as above
                        # Student name
                        canvas.setFont('Helvetica-Bold', 36)
                        canvas.setFillColorRGB(0.2, 0.2, 0.2)  # Dark gray
                        canvas.drawCentredString(width/2, height/2 + 50, student.full_name)
                        
                        # Certificate text
                        canvas.setFont('Helvetica', 16)
                        certificate_text = f"This certificate is presented to the above named student"
                        canvas.drawCentredString(width/2, height/2, certificate_text)
                        
                        certificate_text2 = f"for successfully completing internship requirements"
                        canvas.drawCentredString(width/2, height/2 - 25, certificate_text2)
                        
                        certificate_text3 = f"and earning {credit_points} credit points."
                        canvas.drawCentredString(width/2, height/2 - 50, certificate_text3)
                        
                        # Achievement text
                        achievement_text = "This achievement demonstrates exceptional dedication and competence in the field."
                        canvas.drawCentredString(width/2, height/2 - 90, achievement_text)
                        
                        # Current date
                        current_date = datetime.now().strftime("%B %d, %Y")
                        canvas.setFont('Helvetica', 12)
                        canvas.drawCentredString(width/2, height/2 - 150, f"Issued on: {current_date}")
                        
                    except Exception as e:
                        print(f"Error rendering SVG with svglib: {e}")
                        
                        # Last resort - try to convert to PNG
                        png_path = convert_svg_to_png(svg_path, width=int(width), height=int(height))
                        if png_path and os.path.exists(png_path):
                            try:
                                canvas.drawImage(png_path, 0, 0, width=width, height=height)
                                print(f"Using PNG for certificate background: {png_path}")
                                
                                # Add the same text content again
                                # Student name
                                canvas.setFont('Helvetica-Bold', 36)
                                canvas.setFillColorRGB(0.2, 0.2, 0.2)  # Dark gray
                                canvas.drawCentredString(width/2, height/2 + 50, student.full_name)
                                
                                # Certificate text
                                canvas.setFont('Helvetica', 16)
                                certificate_text = f"This certificate is presented to the above named student"
                                canvas.drawCentredString(width/2, height/2, certificate_text)
                                
                                certificate_text2 = f"for successfully completing internship requirements"
                                canvas.drawCentredString(width/2, height/2 - 25, certificate_text2)
                                
                                certificate_text3 = f"and earning {credit_points} credit points."
                                canvas.drawCentredString(width/2, height/2 - 50, certificate_text3)
                                
                                # Achievement text
                                achievement_text = "This achievement demonstrates exceptional dedication and competence in the field."
                                canvas.drawCentredString(width/2, height/2 - 90, achievement_text)
                                
                                # Current date
                                current_date = datetime.now().strftime("%B %d, %Y")
                                canvas.setFont('Helvetica', 12)
                                canvas.drawCentredString(width/2, height/2 - 150, f"Issued on: {current_date}")
                                
                            except Exception as e:
                                print(f"Error rendering PNG certificate background: {e}")
            
            canvas.restoreState()
    
    # Create a dummy element to ensure the document has at least one page
    elements.append(Spacer(1, 1))
    
    # Build the PDF with the SVG certificate background
    # All content is drawn directly on the canvas in the onFirstPage function
    doc.build(elements, onFirstPage=draw_certificate_background)
    
    buffer.seek(0)
    return buffer

def generate_internship_certificate(student, credit_points):
    """
    Generate an internship completion certificate for a student
    
    Args:
        student: Student object with name and other details
        credit_points: Total credit points earned by the student
        
    Returns:
        BytesIO buffer containing the PDF certificate
    """
    # Create PDF document in landscape orientation
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Container for PDF elements
    elements = []
    
    # Register custom fonts if needed
    # pdfmetrics.registerFont(TTFont('CustomFont', 'path/to/font.ttf'))
    
    # Background pattern for certificate
    def draw_background(canvas, doc):
        # Draw the certificate pattern background
        pattern_path = os.path.join('static', 'images', 'certificate-pattern.svg')
        if os.path.exists(pattern_path):
            canvas.saveState()
            
            # Get dimensions for the background
            width = doc.width + doc.leftMargin + doc.rightMargin
            height = doc.height + doc.topMargin + doc.bottomMargin
            
            # First try to convert SVG to PNG if needed
            png_path = convert_svg_to_png(pattern_path, width=int(width), height=int(height))
            
            if png_path and os.path.exists(png_path):
                # Use the PNG file
                try:
                    canvas.drawImage(png_path, 0, 0, width=width, height=height)
                    print(f"Using PNG for background: {png_path}")
                except Exception as e:
                    print(f"Error rendering PNG background: {e}")
            else:
                # If conversion failed and we have svglib, try direct rendering
                if svg2rlg is not None:
                    try:
                        # Get absolute path to ensure file is found
                        abs_pattern_path = os.path.abspath(pattern_path)
                        # Convert SVG to ReportLab drawing
                        drawing = svg2rlg(abs_pattern_path)
                        # Render the drawing on the canvas
                        renderPDF.draw(drawing, canvas, 0, 0, width=width, height=height)
                        print(f"Successfully rendered background SVG with svglib")
                    except Exception as e:
                        print(f"Error rendering SVG with svglib: {e}")
                        # Last resort - try with direct SVG rendering
                        try:
                            canvas.drawImage(pattern_path, 0, 0, width=width, height=height, mask='auto')
                            print(f"Using direct SVG rendering for background")
                        except Exception as e:
                            print(f"Error rendering SVG with drawImage: {e}")
                else:
                    # Last resort - try with direct SVG rendering
                    try:
                        canvas.drawImage(pattern_path, 0, 0, width=width, height=height, mask='auto')
                        print(f"Using direct SVG rendering for background")
                    except Exception as e:
                        print(f"Error rendering background image: {e}")
            
            canvas.restoreState()
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CertificateTitle',
        parent=styles['Heading1'],
        fontSize=36,
        alignment=1,  # Center alignment
        spaceAfter=30,
        fontName='Helvetica-Bold',
        textColor=colors.Color(0.6, 0.4, 0.2)  # Gold-brown color
    )
    
    # Certificate header style
    header_style = ParagraphStyle(
        'CertificateHeader',
        parent=styles['Heading2'],
        fontSize=24,
        alignment=1,  # Center alignment
        spaceAfter=20,
        fontName='Helvetica-Bold',
        textColor=colors.Color(0.2, 0.2, 0.2)  # Dark gray
    )
    
    # Certificate body style
    body_style = ParagraphStyle(
        'CertificateBody',
        parent=styles['Normal'],
        fontSize=14,
        alignment=1,  # Center alignment
        spaceAfter=12,
        leading=20,
        textColor=colors.Color(0.2, 0.2, 0.2)  # Dark gray
    )
    
    # Add college logo
    logo_path = os.path.join('static', 'images', 'college_logo.png')
    if os.path.exists(logo_path):
        img = Image(logo_path, width=2*inch, height=2*inch)
        img.hAlign = 'CENTER'
        elements.append(img)
    
    # Add certificate title
    elements.append(Paragraph("INTERNSHIP COMPLETION CERTIFICATE", title_style))
    elements.append(Paragraph("CERTIFICATE OF ACHIEVEMENT", header_style))
    elements.append(Spacer(1, 20))
    
    # Add certificate text
    elements.append(Paragraph("THE FOLLOWING AWARD IS GIVEN TO", body_style))
    elements.append(Spacer(1, 10))
    
    # Student name in large font
    student_name_style = ParagraphStyle(
        'StudentName',
        parent=styles['Heading1'],
        fontSize=28,
        alignment=1,  # Center alignment
        fontName='Helvetica-Bold'
    )
    elements.append(Paragraph(f"{student.full_name}", student_name_style))
    
    # Add decorative line
    class HorizontalLine(Flowable):
        def __init__(self, width, height=0):
            Flowable.__init__(self)
            self.width = width
            self.height = height
        
        def draw(self):
            self.canv.setStrokeColor(colors.gold)
            self.canv.setLineWidth(2)
            self.canv.line(0, 0, self.width, 0)
    
    elements.append(Spacer(1, 10))
    elements.append(HorizontalLine(400))
    elements.append(Spacer(1, 20))
    
    # Certificate body text
    certificate_text = f"""This certificate is given to {student.full_name} 
for successfully completing internship requirements 
and earning {credit_points} credit points.

This achievement demonstrates exceptional dedication and competence in the field."""
    elements.append(Paragraph(certificate_text, body_style))
    elements.append(Spacer(1, 40))
    
    # Add slogan
    slogan_style = ParagraphStyle(
        'Slogan',
        parent=styles['Italic'],
        alignment=1,  # Center alignment
        fontName='Helvetica-Oblique',
        fontSize=12,
        textColor=colors.Color(0.4, 0.4, 0.4),  # Medium gray
        spaceAfter=30
    )
    slogan_text = "Empowering Students Through Professional Experience"
    elements.append(Paragraph(slogan_text, slogan_style))
    elements.append(Spacer(1, 20))
    
    # Add decorative line
    elements.append(HRFlowable(
        width="80%",
        thickness=1,
        lineCap='round',
        color=colors.Color(0.6, 0.4, 0.2),  # Gold-brown color
        spaceBefore=10,
        spaceAfter=20
    ))
    
    # Add date
    current_date = datetime.now().strftime("%B %d, %Y")
    
    # Create a table for signatures
    signature_data = [
        [Paragraph("<b>Date:</b> " + current_date, styles['Normal']), "", Paragraph("<b>Mentor</b>", styles['Normal'])],
        ["", "", ""],
        [Paragraph("<b>Head of Department</b>", styles['Normal']), "", Paragraph("<b>Internship Incharge</b>", styles['Normal'])]
    ]
    
    signature_table = Table(signature_data, colWidths=[2.5*inch, 2*inch, 2.5*inch])
    signature_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.Color(0.2, 0.2, 0.2))  # Dark gray
    ]))
    
    elements.append(signature_table)
    
    # Add certificate seal/stamp image if available
    seal_path = os.path.join('static', 'images', 'certificate_seal.svg')
    if os.path.exists(seal_path):
        # Set dimensions for the seal
        seal_width = int(1.5*inch)
        seal_height = int(1.5*inch)
        
        # First try to convert SVG to PNG if needed
        png_path = convert_svg_to_png(seal_path, width=seal_width, height=seal_height)
        
        if png_path and os.path.exists(png_path):
            # Use the PNG file
            try:
                seal = Image(png_path, width=seal_width, height=seal_height)
                seal.hAlign = 'RIGHT'
                elements.append(seal)
                print(f"Using PNG for seal: {png_path}")
            except Exception as e:
                print(f"Error rendering PNG seal: {e}")
        else:
            # If conversion failed and we have svglib, try direct rendering
            if svg2rlg is not None:
                try:
                    # Get absolute path to ensure file is found
                    abs_seal_path = os.path.abspath(seal_path)
                    print(f"Using absolute path for seal: {abs_seal_path}")
                    # Convert SVG to ReportLab drawing
                    drawing = svg2rlg(abs_seal_path)
                    # Create an image from the drawing
                    seal = renderPDF.GraphicsFlowable(drawing, width=seal_width, height=seal_height)
                    seal.hAlign = 'RIGHT'
                    elements.append(seal)
                    print(f"Successfully rendered seal SVG with svglib")
                except Exception as e:
                    print(f"Error rendering seal SVG with svglib: {e}")
                    # Last resort - try with direct SVG rendering
                    try:
                        seal = Image(seal_path, width=seal_width, height=seal_height)
                        seal.hAlign = 'RIGHT'
                        elements.append(seal)
                        print("Using direct SVG rendering for seal")
                    except Exception as e:
                        print(f"Error rendering seal with direct SVG: {e}")
            else:
                # Last resort - try with direct SVG rendering
                try:
                    seal = Image(seal_path, width=seal_width, height=seal_height)
                    seal.hAlign = 'RIGHT'
                    elements.append(seal)
                    print("Using direct SVG rendering for seal")
                except Exception as e:
                    print(f"Error rendering seal image: {e}")
    
    # Build the PDF with background
    doc.build(elements, onFirstPage=draw_background, onLaterPages=draw_background)
    buffer.seek(0)
    return buffer