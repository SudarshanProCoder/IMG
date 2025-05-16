from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
import os
from io import BytesIO
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import String
from reportlab.graphics.shapes import Circle

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