from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, Flowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
import os
from io import BytesIO
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import String
from reportlab.graphics.shapes import Circle
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer, Image, Flowable
from reportlab.lib.utils import ImageReader
from PIL import Image as PILImage
import requests
import io
import qrcode
from dateutil.relativedelta import relativedelta

def create_approval_stamp(canvas, x, y):
    """Create a digital approval stamp"""
    d = Drawing(150, 75)
    
    # Create stamp circle
    circle = Circle(75, 37, 35, fillColor=colors.green, strokeColor=colors.green)
    d.add(circle)
    
    # Add text
    text = String(75, 37, "APPROVED", fontSize=14, fillColor=colors.white, textAnchor="middle")
    d.add(text)
    
    # Add date
    date_text = String(75, 20, datetime.now().strftime("%d-%m-%Y"), fontSize=8, fillColor=colors.white, textAnchor="middle")
    d.add(date_text)
    
    # Render the stamp
    renderPDF.draw(d, canvas, x, y)

def create_status_stamp(canvas, x, y, status):
    """Create a status stamp (approved/rejected)"""
    d = Drawing(150, 50)
    
    # Set colors based on status
    if status == 'approved':
        fill_color = colors.green
        text = "APPROVED"
    else:
        fill_color = colors.red
        text = "NOT APPROVED"
    
    # Create stamp circle
    circle = Circle(75, 25, 20, fillColor=fill_color, strokeColor=fill_color)
    d.add(circle)
    
    # Add text
    text = String(75, 25, text, fontSize=10, fillColor=colors.white, textAnchor="middle")
    d.add(text)
    
    # Add date
    date_text = String(75, 10, datetime.now().strftime("%d-%m-%Y"), fontSize=8, fillColor=colors.white, textAnchor="middle")
    d.add(date_text)
    
    # Render the stamp
    renderPDF.draw(d, canvas, x, y)

def generate_marksheet(student, internships, activities, total_credit_points):
    # Create PDF document
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    # Container for PDF elements
    elements = []

    # Add college logo and name
    logo_path = os.path.join('static', 'images', 'college_logo.png')
    if os.path.exists(logo_path):
        img = Image(logo_path, width=1.5*inch, height=1.5*inch)
        elements.append(img)

    # College name and title
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    elements.append(Paragraph("Shah and Anchor Kutchhi Engineering College", title_style))
    elements.append(Paragraph("Internship and Activity Marksheet", title_style))
    elements.append(Spacer(1, 20))

    # Student Information
    info_style = ParagraphStyle(
        'InfoStyle',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=12
    )
    elements.append(Paragraph(f"<b>Student Name:</b> {student.full_name}", info_style))
    elements.append(Paragraph(f"<b>Student ID:</b> {student.id}", info_style))
    elements.append(Paragraph(f"<b>Department:</b> {student.department}", info_style))
    elements.append(Paragraph(f"<b>Batch:</b> {student.batch}", info_style))
    elements.append(Spacer(1, 20))

    # Internships Section
    elements.append(Paragraph("Internships", styles['Heading2']))
    
    # Filter approved internships only
    approved_internships = [i for i in internships if i.status == 'approved']
    
    if approved_internships:
        internship_data = [['Company', 'Project', 'Semester', 'Duration (Months)', 'Hours/Week', 'Total Hours', 'Credit Points', 'Skills']]
        for internship in approved_internships:
            try:
                # Parse dates, handling both date and datetime strings
                start_date = datetime.strptime(str(internship.start_date).split()[0], '%Y-%m-%d')
                end_date = datetime.strptime(str(internship.end_date).split()[0], '%Y-%m-%d')
                
                # Calculate duration in months (more accurate calculation)
                months_diff = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
                days_in_last_month = end_date.day - start_date.day
                if days_in_last_month < 0:
                    months_diff -= 1
                    days_in_last_month += 30  # Approximate days in a month
                duration_months = months_diff + (days_in_last_month / 30.44)
                duration_months = round(duration_months, 1)
                
                # Calculate total hours based on duration and hours per week
                weeks = duration_months * 4.345  # Average weeks in a month
                total_hours = round(weeks * internship.hours_per_week)
                
                # Calculate credit points (1 credit point per 40 hours)
                credit_points = round(total_hours / 40, 1)
                
            except (ValueError, AttributeError):
                # If date parsing fails, use provided values or defaults
                duration_months = internship.duration_months if hasattr(internship, 'duration_months') else 0
                total_hours = internship.total_hours if hasattr(internship, 'total_hours') else 0
                credit_points = round(total_hours / 40, 1)
            
            internship_data.append([
                internship.company_name,
                internship.project_name,
                internship.semester,
                str(duration_months),
                str(internship.hours_per_week),
                str(total_hours),
                str(credit_points),
                ', '.join(internship.skills) if internship.skills else '-'
            ])
        
        # Adjusted column widths for better fit
        internship_table = Table(internship_data, colWidths=[1.2*inch, 1.8*inch, 0.7*inch, 0.8*inch, 0.7*inch, 0.7*inch, 0.7*inch, 1.2*inch])
        internship_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('WORDWRAP', (0, 0), (-1, -1), True),
        ]))
        elements.append(internship_table)
    else:
        elements.append(Paragraph("No approved internships found.", info_style))
    
    elements.append(Spacer(1, 20))

    # Activities Section
    elements.append(Paragraph("Activities", styles['Heading2']))
    
    # Filter approved activities only
    approved_activities = [a for a in activities if a.status == 'approved']
    
    if approved_activities:
        activity_data = [['Type', 'Title', 'Semester', 'Hours/Week', 'Total Hours', 'Credit Points', 'Skills']]
        for activity in approved_activities:
            try:
                # Parse dates for activities
                start_date = datetime.strptime(str(activity.start_date).split()[0], '%Y-%m-%d')
                end_date = datetime.strptime(str(activity.end_date).split()[0], '%Y-%m-%d')
                
                # Calculate duration in months
                months_diff = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
                days_in_last_month = end_date.day - start_date.day
                if days_in_last_month < 0:
                    months_diff -= 1
                    days_in_last_month += 30
                duration_months = months_diff + (days_in_last_month / 30.44)
                duration_months = round(duration_months, 1)
                
                # Calculate total hours
                weeks = duration_months * 4.345
                total_hours = round(weeks * activity.hours_per_week)
                
                # Calculate credit points (1 credit point per 10 hours per week)
                credit_points = round(total_hours / 10, 1)
                
            except (ValueError, AttributeError):
                # If date parsing fails, use provided values or defaults
                total_hours = activity.total_hours if hasattr(activity, 'total_hours') else 0
                credit_points = round(total_hours / 10, 1)
            
            activity_data.append([
                activity.activity_type.title(),
                activity.title,
                activity.semester,
                str(activity.hours_per_week),
                str(total_hours),
                str(credit_points),
                ', '.join(activity.skills) if activity.skills else '-'
            ])
        
        # Adjusted column widths for better fit
        activity_table = Table(activity_data, colWidths=[1.2*inch, 1.8*inch, 0.7*inch, 0.7*inch, 0.7*inch, 0.7*inch, 1.2*inch])
        activity_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('WORDWRAP', (0, 0), (-1, -1), True),
        ]))
        elements.append(activity_table)
    else:
        elements.append(Paragraph("No approved activities found.", info_style))

    elements.append(Spacer(1, 20))

    # Summary Section
    elements.append(Paragraph("Summary", styles['Heading2']))
    
    # Calculate totals for approved entries only
    total_internship_hours = sum(i.total_hours for i in approved_internships)
    total_activity_hours = sum(a.total_hours for a in approved_activities)
    
    # Calculate total credit points
    internship_credit_points = sum(round(i.total_hours / 40, 1) for i in approved_internships)
    activity_credit_points = sum(round(a.total_hours / 10, 1) for a in approved_activities)
    total_credit_points = internship_credit_points + activity_credit_points
    
    summary_data = [
        ['Total Internship Hours', str(total_internship_hours)],
        ['Total Activity Hours', str(total_activity_hours)],
        ['Total Credit Points', str(round(total_credit_points, 1))]
    ]
    summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (0, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(summary_table)

    # Add date and signature
    elements.append(Spacer(1, 40))
    
    # Build PDF with stamp at bottom right
    def add_approval_stamp(canvas, doc):
        # Position stamp at bottom right
        stamp_x = doc.pagesize[0] - 200  # 200 points from right
        stamp_y = 100  # 100 points from bottom
        
        # Add the stamp
        create_approval_stamp(canvas, stamp_x, stamp_y)
        
        # Add date below stamp
        canvas.setFont('Helvetica', 10)
        canvas.drawString(
            stamp_x + 75,  # Align with stamp
            stamp_y - 20,  # Position below stamp
            f"Generated on: {datetime.now().strftime('%d %B %Y')}"
        )
        
        # Add signature below date
        canvas.drawString(
            stamp_x + 75,  # Align with stamp
            stamp_y - 40,  # Position below date
            "Authorized Signature"
        )
        
        canvas.saveState()

    doc.build(elements, onFirstPage=add_approval_stamp)
    buffer.seek(0)
    return buffer 

def generate_internship_pdf(student, internships):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    elements = []

    # --- BACKGROUND COLOR ---
    def draw_background(canvas, doc):
        canvas.saveState()
        # Light yellow/beige background
        canvas.setFillColorRGB(0.99, 0.96, 0.86)  # RGB for #f8f6e3
        canvas.rect(0, 0, doc.pagesize[0], doc.pagesize[1], fill=1, stroke=0)
        canvas.restoreState()

    # --- HEADER ---
    logo_path = os.path.join('static', 'images', 'college_logo.png')
    logo_img = None
    if os.path.exists(logo_path):
        logo_img = Image(logo_path, width=1.2*inch, height=1.2*inch)
    college_name = '<b>Shah & Anchor Kutchhi Engineering College</b><br/><font size=10>(An Autonomous Institute Affiliated to University of Mumbai)</font>'
    course_info = f'<b>Course:</b> {getattr(student, "branch", "")}<br/><b>Permanent Roll No:</b> {getattr(student, "registration_number", "")}<br/>'
    header_data = [
        [logo_img if logo_img else '', Paragraph(college_name, getSampleStyleSheet()['Title']), Paragraph(course_info, getSampleStyleSheet()['Normal'])]
    ]
    header_table = Table(header_data, colWidths=[1.5*inch, 3.5*inch, 2.0*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,0), 'CENTER'),
        ('ALIGN', (2,0), (2,0), 'RIGHT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
        ('TOPPADDING', (0,0), (-1,-1), 12),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 10))

    # --- STUDENT INFO ROW ---
    # Student photo (left)
    photo_path = getattr(student, 'profile_image', None)
    def get_fitted_image(photo_path, width, height):
        try:
            if photo_path and photo_path.startswith('http'):
                response = requests.get(photo_path)
                img = PILImage.open(io.BytesIO(response.content))
            else:
                if not photo_path or not os.path.exists(photo_path):
                    photo_path = os.path.join('static', 'images', 'default_avatar.png')
                img = PILImage.open(photo_path)
            img = img.convert('RGB')
            img = img.resize((int(width), int(height)), PILImage.LANCZOS)
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            return Image(img_byte_arr, width=width, height=height)
        except Exception:
            return Image(os.path.join('static', 'images', 'default_avatar.png'), width=width, height=height)
    photo_img = get_fitted_image(photo_path, 1.3*inch, 1.6*inch)
    student_details = f"""
    <b>Name:</b> {student.full_name}<br/>
    <b>Reg No:</b> {getattr(student, 'prn', getattr(student, 'registration_number', ''))}<br/>
    <b>Period of Study:</b> {getattr(student, 'batch', '')}<br/>
    """
    course_details = f"""
    <b>Course:</b> {getattr(student, 'branch', '')}<br/>
    <b>Permanent Roll No:</b> {getattr(student, 'registration_number', '')}<br/>
    """
    info_data = [
        [photo_img, Paragraph(student_details, getSampleStyleSheet()['Normal']), Paragraph(course_details, getSampleStyleSheet()['Normal'])]
    ]
    info_table = Table(info_data, colWidths=[1.5*inch, 3.5*inch, 2.0*inch])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,0), 'LEFT'),
        ('ALIGN', (2,0), (2,0), 'RIGHT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 10))
    # --- SECTION LINE ---
    from reportlab.platypus import HRFlowable
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceBefore=8, spaceAfter=8))
    # --- INTERNSHIP DETAILS TABLE ---
    elements.append(Paragraph('<b>Internship Details</b>', getSampleStyleSheet()['Heading2']))
    table_data = [[
        'Semester', 'Project Name', 'Duration', 'Skills/technology', 'Company Name / College Name'
    ]]
    total_months = 0
    for internship in internships:
        # Duration formatting
        start = getattr(internship, 'start_date', '')
        end = getattr(internship, 'end_date', '')
        try:
            start_dt = datetime.strptime(str(start).split()[0], '%Y-%m-%d')
            end_dt = datetime.strptime(str(end).split()[0], '%Y-%m-%d')
            months = (end_dt.year - start_dt.year) * 12 + (end_dt.month - start_dt.month) + 1
            total_months += months
            duration = f"Start: {start}\nEnd: {end}\nTotal Hours: {getattr(internship, 'total_hours', '')}"
        except Exception:
            months = 0
            duration = f"Start: {start}\nEnd: {end}\nTotal Hours: {getattr(internship, 'total_hours', '')}"
        table_data.append([
            getattr(internship, 'semester', ''),
            getattr(internship, 'project_name', ''),
            duration,
            ', '.join(getattr(internship, 'skills', [])),
            getattr(internship, 'company_name', '')
        ])
    table = Table(table_data, colWidths=[0.8*inch, 1.5*inch, 2.2*inch, 1.7*inch, 2.0*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 11),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('TOPPADDING', (0,0), (-1,0), 8),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 8))
    # --- SUMMARY ---
    elements.append(Paragraph(f"Total number of Internships: {len(internships)}", getSampleStyleSheet()['Normal']))
    elements.append(Paragraph(f"Total months worked: {total_months}", getSampleStyleSheet()['Normal']))
    elements.append(Spacer(1, 20))

    # --- FOOTER ---
    # Signature lines and QR code area (QR code placeholder as Flowable)
    class QRPlaceholder(Flowable):
        def __init__(self, width=60, height=60):
            Flowable.__init__(self)
            self.width = width
            self.height = height
        def draw(self):
            self.canv.rect(0, 0, self.width, self.height)
            self.canv.drawString(5, self.height/2, "QR")
    footer_data = [
        [
            Paragraph('Date:', getSampleStyleSheet()['Normal']),
            '',
            Paragraph("Principal's Sign:", getSampleStyleSheet()['Normal']),
            QRPlaceholder(),
        ],
        [
            Paragraph('Place:', getSampleStyleSheet()['Normal']),
            '',
            Paragraph("HOD's Sign:", getSampleStyleSheet()['Normal']),
            ''
        ],
        [
            '', '', Paragraph('Internship Cell Coordinator Sign:', getSampleStyleSheet()['Normal']), ''
        ]
    ]
    footer_table = Table(footer_data, colWidths=[1.2*inch, 2.2*inch, 2.5*inch, 1.2*inch])
    footer_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (2,0), (2,-1), 'LEFT'),
        ('ALIGN', (3,0), (3,0), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(footer_table)

    doc.build(elements, onFirstPage=lambda canvas, doc: (draw_background(canvas, doc)), onLaterPages=lambda canvas, doc: (draw_background(canvas, doc)))
    buffer.seek(0)
    return buffer 

def generate_custom_marksheet(student, internships, activities, marksheet_url):
    from reportlab.platypus import HRFlowable
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=24,
        leftMargin=24,
        topMargin=24,
        bottomMargin=24
    )
    elements = []

    # --- BACKGROUND COLOR ---
    def draw_background(canvas, doc):
        canvas.saveState()
        canvas.setFillColorRGB(0.99, 0.96, 0.86)  # #f8f6e3
        canvas.rect(0, 0, doc.pagesize[0], doc.pagesize[1], fill=1, stroke=0)
        canvas.restoreState()

    # --- HEADER ---
    logo_path = os.path.join('static', 'images', 'college_logo.png')
    logo_img = None
    if os.path.exists(logo_path):
        logo_img = Image(logo_path, width=1.3*inch, height=1.3*inch)
    # Center logo above the college name
    if logo_img:
        elements.append(Spacer(1, 8))
        elements.append(logo_img)
        elements.append(Spacer(1, 8))
    college_name = '<b>Shah & Anchor Kutchhi Engineering College</b><br/><font size=10>(An Autonomous Institute Affiliated to University of Mumbai)</font>'
    header_data = [
        ['', Paragraph(college_name, getSampleStyleSheet()['Title']), '']
    ]
    header_table = Table(header_data, colWidths=[1.2*inch, 4.2*inch, 1.2*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,0), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('LINEBELOW', (0,0), (-1,0), 1, colors.black),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 8))

    # --- STUDENT INFO ROW ---
    from reportlab.graphics.shapes import Drawing, Circle
    from reportlab.graphics import renderPDF
    class CircularImage(Flowable):
        def __init__(self, img_path, width, height):
            Flowable.__init__(self)
            self.width = width
            self.height = height
            self.img_path = img_path
        def draw(self):
            self.canv.saveState()
            x = self.width / 2
            y = self.height / 2
            r = min(self.width, self.height) / 2
            # Create a circular path
            path = self.canv.beginPath()
            path.circle(x, y, r)
            self.canv.clipPath(path, stroke=0)
            self.canv.drawImage(self.img_path, 0, 0, width=self.width, height=self.height, mask='auto')
            self.canv.restoreState()
    # Use CircularImage for the photo
    photo_path = getattr(student, 'profile_image', None)
    if not photo_path or (not photo_path.startswith('http') and not os.path.exists(photo_path)):
        photo_path = os.path.join('static', 'images', 'default_avatar.png')
    circ_photo = CircularImage(photo_path, 1.1*inch, 1.1*inch)
    name_style = ParagraphStyle('NameStyle', parent=getSampleStyleSheet()['Normal'], textColor=colors.HexColor('#1d3557'), fontSize=11, spaceAfter=4, leftIndent=8)
    student_details = f"""
    <b>Name:</b> {student.full_name}<br/>
    <b>Reg No:</b> {getattr(student, 'prn', getattr(student, 'registration_number', getattr(student, 'student_id', '')))}<br/>
    <b>Period of Study:</b> {getattr(student, 'batch', '')}<br/>
    """
    course_details = f"""
    <b>Course:</b> {getattr(student, 'department', getattr(student, 'branch', ''))}<br/>
    <b>Permanent Roll No:</b> {getattr(student, 'registration_number', getattr(student, 'student_id', ''))}<br/>
    """
    info_data = [
        [circ_photo, Paragraph(student_details, name_style), Paragraph(course_details, getSampleStyleSheet()['Normal'])]
    ]
    info_table = Table(info_data, colWidths=[1.1*inch, 3.8*inch, 2.0*inch])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,0), 'LEFT'),
        ('ALIGN', (2,0), (2,0), 'RIGHT'),
        ('LEFTPADDING', (1,0), (1,0), 18),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('LINEBELOW', (0,0), (-1,0), 1, colors.black),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8f6e3')),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 6))

    # --- INTERNSHIP DETAILS TABLE ---
    elements.append(Paragraph('<b>Internship Details</b>', getSampleStyleSheet()['Heading2']))
    internship_data = [[
        'Semester', 'Project Name', 'Duration', 'Skills/Technology', 'Company Name / College Name'
    ]]
    approved_internships = [i for i in internships if getattr(i, 'status', None) == 'approved']
    total_months = 0
    for internship in approved_internships:
        start = getattr(internship, 'start_date', '')
        end = getattr(internship, 'end_date', '')
        # Calculate months difference
        months = 0
        try:
            if start and end:
                from datetime import datetime
                start_dt = datetime.strptime(str(start).split()[0], '%Y-%m-%d')
                end_dt = datetime.strptime(str(end).split()[0], '%Y-%m-%d')
                rdelta = relativedelta(end_dt, start_dt)
                months = rdelta.years * 12 + rdelta.months
                if rdelta.days > 0:
                    months += 1
                if months < 0:
                    months = 0
                total_months += months
        except Exception:
            months = 0
        duration = f"Start: {start}\nEnd: {end}\nTotal Hours: {getattr(internship, 'total_hours', '')}\nMonths: {months}"
        internship_data.append([
            getattr(internship, 'semester', ''),
            getattr(internship, 'project_name', ''),
            duration,
            ', '.join(getattr(internship, 'skills', [])),
            getattr(internship, 'company_name', '')
        ])
    # Reduce font size and spacing to fit on one page
    internship_table = Table(internship_data, colWidths=[0.8*inch, 1.1*inch, 1.7*inch, 1.3*inch, 2.7*inch], repeatRows=1)
    internship_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f8f6e3')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#1d3557')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('ROWHEIGHT', (0,0), (-1,-1), 20),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 9),
        ('BOTTOMPADDING', (0,1), (-1,-1), 4),
        ('TOPPADDING', (0,1), (-1,-1), 4),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f8f6e3')),
    ]))
    elements.append(internship_table)
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(f"Total number of Internships: {len(approved_internships)}", getSampleStyleSheet()['Normal']))
    elements.append(Paragraph(f"Total months worked: {total_months}", getSampleStyleSheet()['Normal']))
    # Add a horizontal line between Internship and Activity Details
    elements.append(Spacer(1, 8))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1d3557'), spaceBefore=8, spaceAfter=8))
    elements.append(Spacer(1, 8))

    # --- ACTIVITY DETAILS TABLE ---
    elements.append(Paragraph('<b>Activity Details</b>', getSampleStyleSheet()['Heading2']))
    activity_data = [[
        'Semester', 'Title', 'Type', 'Duration', 'Skills'
    ]]
    approved_activities = [a for a in activities if getattr(a, 'status', None) == 'approved']
    total_activity_months = 0
    for activity in approved_activities:
        start = getattr(activity, 'start_date', '')
        end = getattr(activity, 'end_date', '')
        # Calculate months difference
        months = 0
        try:
            if start and end:
                from datetime import datetime
                start_dt = datetime.strptime(str(start).split()[0], '%Y-%m-%d')
                end_dt = datetime.strptime(str(end).split()[0], '%Y-%m-%d')
                rdelta = relativedelta(end_dt, start_dt)
                months = rdelta.years * 12 + rdelta.months
                if rdelta.days > 0:
                    months += 1
                if months < 0:
                    months = 0
                total_activity_months += months
        except Exception:
            months = 0
        duration = f"Start: {start}\nEnd: {end}\nTotal Hours: {getattr(activity, 'total_hours', '')}\nMonths: {months}"
        activity_data.append([
            getattr(activity, 'semester', ''),
            getattr(activity, 'title', ''),
            getattr(activity, 'activity_type', ''),
            duration,
            ', '.join(getattr(activity, 'skills', [])),
        ])
    activity_table = Table(activity_data, colWidths=[0.8*inch, 1.1*inch, 1.1*inch, 1.7*inch, 2.7*inch], repeatRows=1)
    activity_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f8f6e3')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#1d3557')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('ROWHEIGHT', (0,0), (-1,-1), 20),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 9),
        ('BOTTOMPADDING', (0,1), (-1,-1), 4),
        ('TOPPADDING', (0,1), (-1,-1), 4),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f8f6e3')),
    ]))
    elements.append(activity_table)
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(f"Total number of Activities: {len(approved_activities)}", getSampleStyleSheet()['Normal']))
    elements.append(Paragraph(f"Total months: {total_activity_months}", getSampleStyleSheet()['Normal']))
    elements.append(Spacer(1, 12))

    # --- FOOTER ---
    class QRImage(Flowable):
        def __init__(self, qr_img, width=60, height=60):
            Flowable.__init__(self)
            self.width = width
            self.height = height
            self.qr_img = qr_img
        def draw(self):
            self.canv.drawInlineImage(self.qr_img, 0, 0, width=self.width, height=self.height)
    qr = qrcode.QRCode(box_size=2, border=1)
    qr.add_data(marksheet_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_byte_arr = io.BytesIO()
    qr_img.save(qr_byte_arr, format='PNG')
    qr_byte_arr.seek(0)
    qr_img_for_pdf = PILImage.open(qr_byte_arr)
    qr_flowable = QRImage(qr_img_for_pdf, width=50, height=50)
    # Footer: left = QR code + sign lines, right = date/place
    left_col = [qr_flowable, Spacer(1, 6),
        Paragraph("<b>HOD sign:</b>", getSampleStyleSheet()['Normal']),
        Spacer(1, 2),
        Paragraph("<b>Mentor sign:</b>", getSampleStyleSheet()['Normal']),
        Spacer(1, 2),
        Paragraph("<b>Internship Incharge sign:</b>", getSampleStyleSheet()['Normal'])
    ]
    right_col = [Paragraph("<b>Date:</b>", getSampleStyleSheet()['Normal']), Spacer(1, 8), Paragraph("<b>Place:</b>", getSampleStyleSheet()['Normal'])]
    footer_data = [
        [left_col, right_col]
    ]
    footer_table = Table(footer_data, colWidths=[2.2*inch, 5.7*inch])
    footer_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (0,0), 'TOP'),
        ('VALIGN', (1,0), (1,0), 'TOP'),
        ('ALIGN', (0,0), (0,0), 'LEFT'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(footer_table)

    doc.build(elements, onFirstPage=lambda canvas, doc: (draw_background(canvas, doc)), onLaterPages=lambda canvas, doc: (draw_background(canvas, doc)))
    buffer.seek(0)
    return buffer 