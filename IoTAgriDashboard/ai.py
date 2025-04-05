import os
import json
from datetime import datetime, timedelta
import google.generativeai as genai
from app import db
from models import SensorData, AIAnalysis

def get_ai_analysis(device_id, language='fr'):
    """
    Generate AI analysis and recommendations using Google Gemini API
    
    Args:
        device_id (str): The device ID
        language (str): The language code (fr, en, ar)
    """
    # Get API key from environment
    api_key = os.environ.get('GEMINI_API_KEY', 'AIzaSyBrKN0yZ8y9rQH9EgJoZpHvi3_re4V_2dk')
    
    # Configure the Gemini API
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-pro')
    
    # Get recent sensor data (last 24 hours)
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=1)
    
    recent_data = SensorData.query.filter_by(device_id=device_id).filter(
        SensorData.timestamp.between(start_time, end_time)
    ).order_by(SensorData.timestamp.asc()).all()
    
    if not recent_data:
        print("No data available for AI analysis")
        return None
    
    # Prepare data for AI analysis
    data_points = []
    for entry in recent_data:
        data_point = {
            'timestamp': entry.timestamp.isoformat(),
            'moisture': entry.moisture,
            'temperature': entry.temperature,
            'ec': entry.ec,
            'ph': entry.ph,
            'nitrogen': entry.nitrogen,
            'phosphorous': entry.phosphorous,
            'potassium': entry.potassium,
            'salinity': entry.salinity,
            'bme_temperature': entry.bme_temperature,
            'bme_humidity': entry.bme_humidity,
            'bme_pressure': entry.bme_pressure,
            'bme_gas': entry.bme_gas,
            'uv_index': entry.uv_index,
            'rain_level': entry.rain_level
        }
        data_points.append(data_point)
    
    # Define prompts for different languages
    prompts = {
        'fr': f"""
        En tant qu'expert agricole, analysez les données suivantes provenant d'un capteur IoT dans un champ agricole.
        Les données incluent l'humidité du sol, la température, le pH, la conductivité électrique (CE), les niveaux NPK (azote, phosphore, potassium),
        la salinité, la température et l'humidité ambiantes, la pression, les niveaux de gaz, l'indice UV et le niveau de pluie.
        
        Veuillez fournir:
        1. Une analyse complète des conditions de culture basée sur ces données
        2. Identifier les tendances ou problèmes préoccupants
        3. Fournir des recommandations d'actions spécifiques pour l'irrigation, la fertilisation ou d'autres interventions
        4. Suggérer un timing optimal pour ces interventions en fonction des tendances des données
        
        Formatez votre réponse en deux sections clairement séparées:
        - ANALYSIS: Votre évaluation détaillée des conditions
        - RECOMMENDATIONS: Les étapes d'action spécifiques que l'agriculteur devrait prendre
        
        Données des capteurs des dernières 24 heures:
        {json.dumps(data_points, indent=2)}
        """,
        'en': f"""
        As an agricultural expert, analyze the following sensor data from an IoT device in a farm field.
        The data includes soil moisture, temperature, pH, electrical conductivity (EC), NPK levels (nitrogen, phosphorous, potassium),
        salinity, environmental temperature and humidity, pressure, gas levels, UV index, and rain level.
        
        Please provide:
        1. A comprehensive analysis of the crop conditions based on this data
        2. Identify any concerning trends or issues
        3. Provide specific actionable recommendations for irrigation, fertilization, or other interventions
        4. Suggest optimal timing for these interventions based on the data trends
        
        Format your response in two clearly separated sections:
        - ANALYSIS: Your detailed assessment of the conditions
        - RECOMMENDATIONS: Specific actionable steps the farmer should take
        
        Sensor data from past 24 hours:
        {json.dumps(data_points, indent=2)}
        """,
        'ar': f"""
        بصفتك خبيرًا زراعيًا، قم بتحليل بيانات المستشعر التالية من جهاز إنترنت الأشياء في حقل زراعي.
        تتضمن البيانات رطوبة التربة، ودرجة الحرارة، ودرجة الحموضة، والتوصيل الكهربائي (EC)، ومستويات NPK (النيتروجين والفوسفور والبوتاسيوم)،
        والملوحة، ودرجة الحرارة والرطوبة البيئية، والضغط، ومستويات الغاز، ومؤشر الأشعة فوق البنفسجية، ومستوى المطر.
        
        يرجى تقديم:
        1. تحليل شامل لظروف المحاصيل بناءً على هذه البيانات
        2. تحديد أي اتجاهات أو مشكلات مثيرة للقلق
        3. تقديم توصيات قابلة للتنفيذ محددة للري أو التسميد أو غيرها من التدخلات
        4. اقتراح التوقيت الأمثل لهذه التدخلات بناءً على اتجاهات البيانات
        
        قم بتنسيق إجابتك في قسمين منفصلين بوضوح:
        - ANALYSIS: تقييمك المفصل للظروف
        - RECOMMENDATIONS: خطوات إجرائية محددة يجب على المزارع اتخاذها
        
        بيانات المستشعر من الـ 24 ساعة الماضية:
        {json.dumps(data_points, indent=2)}
        """
    }
    
    # Get the appropriate prompt or default to French
    prompt = prompts.get(language, prompts['fr'])
    
    try:
        # Generate analysis using Gemini
        response = model.generate_content(prompt)
        analysis_text = response.text
        
        # Parse the response to separate analysis and recommendations
        parts = analysis_text.split("RECOMMENDATIONS:")
        
        analysis_part = parts[0].replace("ANALYSIS:", "").strip()
        recommendations_part = parts[1].strip() if len(parts) > 1 else ""
        
        # Store the analysis in the database
        ai_analysis = AIAnalysis(
            device_id=device_id,
            timestamp=datetime.utcnow(),
            analysis_text=analysis_part,
            recommendations=recommendations_part
        )
        
        db.session.add(ai_analysis)
        db.session.commit()
        
        return ai_analysis
    
    except Exception as e:
        print(f"Error generating AI analysis: {e}")
        return None

def generate_chat_response(context):
    """
    Generate a conversational response for the chatbot using Google Gemini API
    
    Args:
        context (dict): A dictionary containing the user message, device ID, sensor data, and other context
        
    Returns:
        str: The AI-generated response to the user's message
    """
    # Get API key from environment
    api_key = os.environ.get('GEMINI_API_KEY', 'AIzaSyBrKN0yZ8y9rQH9EgJoZpHvi3_re4V_2dk')
    
    # Configure the Gemini API
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-pro')
    
    # Extract context items
    user_message = context.get('user_message', '')
    device_id = context.get('device_id', '')
    latest_data = context.get('latest_data')
    recent_data = context.get('recent_data', [])
    weather_data = context.get('weather_data')
    language = context.get('language', 'fr')  # Default to French if not specified
    
    # Determine language response parameters
    language_params = {
        'fr': {
            'persona': 'un expert agricole amical et compétent',
            'error_message': "Désolé, j'ai rencontré un problème lors de la génération d'une réponse. Veuillez réessayer plus tard."
        },
        'en': {
            'persona': 'a friendly and knowledgeable agricultural expert',
            'error_message': "Sorry, I encountered a problem generating a response. Please try again later."
        },
        'ar': {
            'persona': 'خبير زراعي ودود وذو خبرة',
            'error_message': "عذرًا، واجهت مشكلة في إنشاء استجابة. يرجى المحاولة مرة أخرى لاحقًا."
        }
    }
    
    persona = language_params.get(language, language_params['fr'])['persona']
    error_message = language_params.get(language, language_params['fr'])['error_message']
    
    # Prepare recent data for AI
    recent_data_points = []
    for entry in recent_data:
        data_point = {
            'timestamp': entry.timestamp.isoformat(),
            'moisture': entry.moisture,
            'temperature': entry.temperature,
            'ec': entry.ec,
            'ph': entry.ph,
            'nitrogen': entry.nitrogen,
            'phosphorous': entry.phosphorous,
            'potassium': entry.potassium,
            'salinity': entry.salinity,
            'bme_temperature': entry.bme_temperature,
            'bme_humidity': entry.bme_humidity,
            'bme_pressure': entry.bme_pressure,
            'bme_gas': entry.bme_gas,
            'uv_index': entry.uv_index,
            'rain_level': entry.rain_level
        }
        # Add calculated metrics if available
        if hasattr(entry, 'water_stress_index') and entry.water_stress_index is not None:
            data_point['water_stress_index'] = entry.water_stress_index
        if hasattr(entry, 'soil_fertility_index') and entry.soil_fertility_index is not None:
            data_point['soil_fertility_index'] = entry.soil_fertility_index
        if hasattr(entry, 'disease_risk') and entry.disease_risk is not None:
            data_point['disease_risk'] = entry.disease_risk
            
        recent_data_points.append(data_point)
    
    # Format latest data if available
    latest_data_formatted = {}
    if latest_data:
        latest_data_formatted = {
            'timestamp': latest_data.timestamp.isoformat(),
            'moisture': latest_data.moisture,
            'temperature': latest_data.temperature,
            'ec': latest_data.ec,
            'ph': latest_data.ph,
            'nitrogen': latest_data.nitrogen,
            'phosphorous': latest_data.phosphorous,
            'potassium': latest_data.potassium,
            'salinity': latest_data.salinity,
            'bme_temperature': latest_data.bme_temperature,
            'bme_humidity': latest_data.bme_humidity,
            'bme_pressure': latest_data.bme_pressure,
            'bme_gas': latest_data.bme_gas,
            'uv_index': latest_data.uv_index,
            'rain_level': latest_data.rain_level,
            'battery_percentage': latest_data.battery_percentage
        }
        
        # Add calculated metrics if available
        if hasattr(latest_data, 'water_stress_index') and latest_data.water_stress_index is not None:
            latest_data_formatted['water_stress_index'] = latest_data.water_stress_index
        if hasattr(latest_data, 'soil_fertility_index') and latest_data.soil_fertility_index is not None:
            latest_data_formatted['soil_fertility_index'] = latest_data.soil_fertility_index
        if hasattr(latest_data, 'disease_risk') and latest_data.disease_risk is not None:
            latest_data_formatted['disease_risk'] = latest_data.disease_risk
        if hasattr(latest_data, 'irrigation_recommendation') and latest_data.irrigation_recommendation is not None:
            latest_data_formatted['irrigation_recommendation'] = latest_data.irrigation_recommendation
    
    # Format weather data if available
    weather_formatted = {}
    if weather_data:
        weather_formatted = {
            'temperature': weather_data.temperature,
            'feels_like': weather_data.feels_like,
            'humidity': weather_data.humidity,
            'pressure': weather_data.pressure,
            'wind_speed': weather_data.wind_speed,
            'weather_main': weather_data.weather_main,
            'weather_description': weather_data.weather_description,
            'rain_1h': weather_data.rain_1h,
            'rain_3h': weather_data.rain_3h
        }
    
    # Create prompt for Gemini based on language
    prompt = f"""
    You are {persona} communicating through a chatbot interface on an IoT farming dashboard. 
    Your personality traits are:
    
    1. Friendly and approachable - you use a warm, conversational tone that makes farmers feel comfortable
    2. Highly knowledgeable - you understand agricultural science, crop management, and IoT sensor data interpretation
    3. Practical and solution-oriented - you focus on actionable advice that can be implemented immediately
    4. Empathetic - you understand the challenges farmers face and show genuine concern for their success
    5. Concise but thorough - you provide complete information without unnecessary technical jargon
    
    Respond to the farmer's question in a helpful, conversational style using the {language} language. 
    Your goal is to provide practical and accurate agricultural advice based on the sensor data.
    
    Guidelines for your response:
    1. Begin with a friendly greeting and direct response to the user's question
    2. Analyze the relevant sensor data and explain what it means in practical terms
    3. Provide customized recommendations based on the current readings and trends
    4. When appropriate, explain the reasoning behind your recommendations
    5. End with an encouraging comment and invitation for further questions
    6. IMPORTANT: If the user simply says hello or asks how you are, respond conversationally without diving into data analysis
    
    User's message: {user_message}
    
    Latest sensor data:
    {json.dumps(latest_data_formatted, indent=2)}
    
    Recent sensor data trend (past 24 hours, summarized):
    {json.dumps(recent_data_points[:3], indent=2)}
    
    Current weather conditions:
    {json.dumps(weather_formatted, indent=2)}
    
    Location: Sfax, Tunisia
    
    IMPORTANT: Respond ONLY in the {language} language.
    """
    
    try:
        # Generate response using Gemini
        response = model.generate_content(prompt)
        return response.text
    
    except Exception as e:
        print(f"Error generating chat response: {e}")
        return error_message
