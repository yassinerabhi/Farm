import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.barcharts import VerticalBarChart
from app import db
from models import SensorData, AIAnalysis, WeatherData, Device

def generate_pdf_report(device_id, title, start_date, end_date):
    """
    Generate a PDF report with sensor data analysis
    """
    # Create directory for reports if it doesn't exist
    reports_dir = os.path.join(os.getcwd(), 'static', 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    
    # Create filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"report_{device_id}_{timestamp}.pdf"
    filepath = os.path.join(reports_dir, filename)
    
    # Create PDF document
    doc = SimpleDocTemplate(filepath, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    
    # Add title
    title_style = styles['Title']
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 12))
    
    # Add date range
    date_range = f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
    elements.append(Paragraph(date_range, styles['Heading2']))
    elements.append(Spacer(1, 12))
    
    # Add introduction
    intro_text = """
    This report provides a comprehensive analysis of the agricultural conditions based on IoT sensor data.
    It includes soil parameters, environmental conditions, and AI-generated recommendations for optimal crop management.
    """
    elements.append(Paragraph("Introduction", styles['Heading2']))
    elements.append(Paragraph(intro_text, styles['Normal']))
    elements.append(Spacer(1, 12))
    
    # Get device details
    device = Device.query.filter_by(id=device_id).first()
    device_name = device.name if device and device.name else device_id
    
    elements.append(Paragraph(f"Device: {device_name} ({device_id})", styles['Heading3']))
    elements.append(Spacer(1, 12))
    
    # Get sensor data for the period
    data = SensorData.query.filter_by(device_id=device_id).filter(
        SensorData.timestamp.between(start_date, end_date)
    ).order_by(SensorData.timestamp.asc()).all()
    
    if not data:
        elements.append(Paragraph("No data available for the selected period.", styles['Normal']))
    else:
        # Add soil parameters section
        elements.append(Paragraph("Soil Parameters", styles['Heading2']))
        elements.append(Spacer(1, 12))
        
        # Create table with average values
        soil_data = [
            ["Parameter", "Minimum", "Maximum", "Average"],
            ["Moisture (%)", "0", "0", "0"],
            ["Temperature (°C)", "0", "0", "0"],
            ["pH", "0", "0", "0"],
            ["EC", "0", "0", "0"],
            ["Nitrogen", "0", "0", "0"],
            ["Phosphorous", "0", "0", "0"],
            ["Potassium", "0", "0", "0"],
            ["Salinity", "0", "0", "0"]
        ]
        
        # Calculate statistics
        if data:
            moisture_values = [d.moisture for d in data if d.moisture is not None]
            temp_values = [d.temperature for d in data if d.temperature is not None]
            ph_values = [d.ph for d in data if d.ph is not None]
            ec_values = [d.ec for d in data if d.ec is not None]
            n_values = [d.nitrogen for d in data if d.nitrogen is not None]
            p_values = [d.phosphorous for d in data if d.phosphorous is not None]
            k_values = [d.potassium for d in data if d.potassium is not None]
            salinity_values = [d.salinity for d in data if d.salinity is not None]
            
            # Update table with calculated values
            if moisture_values:
                soil_data[1] = ["Moisture (%)", f"{min(moisture_values):.1f}", f"{max(moisture_values):.1f}", f"{sum(moisture_values)/len(moisture_values):.1f}"]
            if temp_values:
                soil_data[2] = ["Temperature (°C)", f"{min(temp_values):.1f}", f"{max(temp_values):.1f}", f"{sum(temp_values)/len(temp_values):.1f}"]
            if ph_values:
                soil_data[3] = ["pH", f"{min(ph_values):.1f}", f"{max(ph_values):.1f}", f"{sum(ph_values)/len(ph_values):.1f}"]
            if ec_values:
                soil_data[4] = ["EC", f"{min(ec_values)}", f"{max(ec_values)}", f"{sum(ec_values)/len(ec_values):.1f}"]
            if n_values:
                soil_data[5] = ["Nitrogen", f"{min(n_values)}", f"{max(n_values)}", f"{sum(n_values)/len(n_values):.1f}"]
            if p_values:
                soil_data[6] = ["Phosphorous", f"{min(p_values)}", f"{max(p_values)}", f"{sum(p_values)/len(p_values):.1f}"]
            if k_values:
                soil_data[7] = ["Potassium", f"{min(k_values)}", f"{max(k_values)}", f"{sum(k_values)/len(k_values):.1f}"]
            if salinity_values:
                soil_data[8] = ["Salinity", f"{min(salinity_values):.1f}", f"{max(salinity_values):.1f}", f"{sum(salinity_values)/len(salinity_values):.1f}"]
        
        # Create table
        soil_table = Table(soil_data, colWidths=[120, 80, 80, 80])
        soil_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(soil_table)
        elements.append(Spacer(1, 24))
        
        # Add environmental parameters section
        elements.append(Paragraph("Environmental Parameters", styles['Heading2']))
        elements.append(Spacer(1, 12))
        
        # Create table with average values
        env_data = [
            ["Parameter", "Minimum", "Maximum", "Average"],
            ["Air Temperature (°C)", "0", "0", "0"],
            ["Humidity (%)", "0", "0", "0"],
            ["Pressure (hPa)", "0", "0", "0"],
            ["Gas Resistance (KOhms)", "0", "0", "0"],
            ["UV Index", "0", "0", "0"],
            ["Rain Level (%)", "0", "0", "0"]
        ]
        
        # Calculate statistics
        if data:
            bme_temp_values = [d.bme_temperature for d in data if d.bme_temperature is not None]
            humidity_values = [d.bme_humidity for d in data if d.bme_humidity is not None]
            pressure_values = [d.bme_pressure for d in data if d.bme_pressure is not None]
            gas_values = [d.bme_gas for d in data if d.bme_gas is not None]
            uv_values = [d.uv_index for d in data if d.uv_index is not None]
            rain_values = [d.rain_level for d in data if d.rain_level is not None]
            
            # Update table with calculated values
            if bme_temp_values:
                env_data[1] = ["Air Temperature (°C)", f"{min(bme_temp_values):.1f}", f"{max(bme_temp_values):.1f}", f"{sum(bme_temp_values)/len(bme_temp_values):.1f}"]
            if humidity_values:
                env_data[2] = ["Humidity (%)", f"{min(humidity_values):.1f}", f"{max(humidity_values):.1f}", f"{sum(humidity_values)/len(humidity_values):.1f}"]
            if pressure_values:
                env_data[3] = ["Pressure (hPa)", f"{min(pressure_values):.1f}", f"{max(pressure_values):.1f}", f"{sum(pressure_values)/len(pressure_values):.1f}"]
            if gas_values:
                env_data[4] = ["Gas Resistance (KOhms)", f"{min(gas_values):.1f}", f"{max(gas_values):.1f}", f"{sum(gas_values)/len(gas_values):.1f}"]
            if uv_values:
                env_data[5] = ["UV Index", f"{min(uv_values):.1f}", f"{max(uv_values):.1f}", f"{sum(uv_values)/len(uv_values):.1f}"]
            if rain_values:
                env_data[6] = ["Rain Level (%)", f"{min(rain_values)}", f"{max(rain_values)}", f"{sum(rain_values)/len(rain_values):.1f}"]
        
        # Create table
        env_table = Table(env_data, colWidths=[120, 80, 80, 80])
        env_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(env_table)
        elements.append(Spacer(1, 24))
        
        # Get latest AI analysis
        analysis = AIAnalysis.query.filter_by(device_id=device_id).order_by(AIAnalysis.timestamp.desc()).first()
        
        if analysis:
            # Add AI analysis section
            elements.append(Paragraph("AI Analysis", styles['Heading2']))
            elements.append(Spacer(1, 12))
            elements.append(Paragraph(analysis.analysis_text, styles['Normal']))
            elements.append(Spacer(1, 12))
            
            # Add recommendations section
            elements.append(Paragraph("Recommendations", styles['Heading2']))
            elements.append(Spacer(1, 12))
            elements.append(Paragraph(analysis.recommendations, styles['Normal']))
            elements.append(Spacer(1, 24))
        
        # Add conclusion
        elements.append(Paragraph("Conclusion", styles['Heading2']))
        elements.append(Spacer(1, 12))
        
        conclusion_text = """
        This report provides valuable insights into the current agricultural conditions based on IoT sensor data.
        By following the recommendations provided, you can optimize irrigation, nutrient management, and overall crop health.
        Regular monitoring and timely interventions will help maximize yield and resource efficiency.
        """
        elements.append(Paragraph(conclusion_text, styles['Normal']))
    
    # Build PDF
    doc.build(elements)
    
    return filepath
