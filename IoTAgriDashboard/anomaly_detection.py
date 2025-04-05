"""
Module de détection d'anomalies pour les données de capteurs agricoles
Utilise des algorithmes de machine learning pour détecter les valeurs aberrantes
"""

import os
import logging
import pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib
from datetime import datetime, timedelta
import sqlite3

# Configuration du logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Import des traductions et utilitaires
from translations import get_translation
from device_db_util import get_device_db_path
from models import Alert, db

# Dossier pour stocker les modèles entraînés
ML_MODELS_DIR = "ml_models"

def get_model_path(device_id, sensor_type):
    """
    Obtenir le chemin du fichier pour le modèle de détection d'anomalies
    
    Args:
        device_id (str): Identifiant de l'appareil
        sensor_type (str): Type de capteur (temperature, humidity, etc.)
        
    Returns:
        str: Chemin du fichier du modèle
    """
    os.makedirs(ML_MODELS_DIR, exist_ok=True)
    return os.path.join(ML_MODELS_DIR, f"{device_id}_{sensor_type}_model.joblib")

def get_scaler_path(device_id, sensor_type):
    """
    Obtenir le chemin du fichier pour le scaler
    
    Args:
        device_id (str): Identifiant de l'appareil
        sensor_type (str): Type de capteur (temperature, humidity, etc.)
        
    Returns:
        str: Chemin du fichier du scaler
    """
    os.makedirs(ML_MODELS_DIR, exist_ok=True)
    return os.path.join(ML_MODELS_DIR, f"{device_id}_{sensor_type}_scaler.joblib")

def preprocess_data(data, sensor_param):
    """
    Prétraitement des données pour l'entraînement du modèle
    
    Args:
        data (list): Liste de dictionnaires contenant les données des capteurs
        sensor_param (str): Paramètre de capteur à analyser
        
    Returns:
        numpy.ndarray: Données prétraitées pour le ML
    """
    try:
        # Extraire les valeurs du paramètre du capteur
        values = []
        for entry in data:
            if sensor_param in entry and entry[sensor_param] is not None:
                try:
                    value = float(entry[sensor_param])
                    values.append(value)
                except (ValueError, TypeError):
                    pass
        
        # Convertir en array numpy
        values_array = np.array(values).reshape(-1, 1)
        
        if len(values_array) < 10:
            logger.warning(f"Données insuffisantes pour le paramètre {sensor_param}. Minimum 10 entrées nécessaires.")
            return None
            
        return values_array
    except Exception as e:
        logger.error(f"Erreur lors du prétraitement des données: {str(e)}")
        return None

def train_anomaly_detection_model(device_id, sensor_param, n_estimators=100, contamination=0.05):
    """
    Entraîner un modèle de détection d'anomalies pour un capteur spécifique
    
    Args:
        device_id (str): Identifiant de l'appareil
        sensor_param (str): Paramètre du capteur à analyser
        n_estimators (int): Nombre d'estimateurs pour l'Isolation Forest
        contamination (float): Proportion estimée de valeurs aberrantes
        
    Returns:
        tuple: (modèle, scaler) - le modèle entraîné et le scaler
    """
    try:
        db_path = get_device_db_path(device_id)
        if not db_path:
            logger.warning(f"Aucune base de données trouvée pour l'appareil {device_id}")
            return None, None
            
        # Récupérer les données de la base de données
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sensor_data ORDER BY timestamp DESC LIMIT 1000")
        data = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        if not data:
            logger.warning(f"Aucune donnée trouvée pour l'appareil {device_id}")
            return None, None
            
        # Prétraiter les données
        X = preprocess_data(data, sensor_param)
        if X is None or len(X) < 10:
            logger.warning(f"Données insuffisantes pour entraîner un modèle pour {sensor_param}")
            return None, None
            
        # Standardiser les données
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Entraîner le modèle Isolation Forest
        model = IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            random_state=42,
            n_jobs=-1
        )
        model.fit(X_scaled)
        
        # Sauvegarder le modèle et le scaler
        joblib.dump(model, get_model_path(device_id, sensor_param))
        joblib.dump(scaler, get_scaler_path(device_id, sensor_param))
        
        logger.info(f"Modèle entraîné avec succès pour {device_id}/{sensor_param}")
        return model, scaler
    except Exception as e:
        logger.error(f"Erreur lors de l'entraînement du modèle: {str(e)}")
        return None, None

def load_or_train_model(device_id, sensor_param):
    """
    Charger un modèle existant ou en entraîner un nouveau si nécessaire
    
    Args:
        device_id (str): Identifiant de l'appareil
        sensor_param (str): Paramètre du capteur à analyser
        
    Returns:
        tuple: (modèle, scaler) - le modèle et le scaler
    """
    model_path = get_model_path(device_id, sensor_param)
    scaler_path = get_scaler_path(device_id, sensor_param)
    
    # Vérifier si le modèle et le scaler existent
    if os.path.exists(model_path) and os.path.exists(scaler_path):
        try:
            model = joblib.load(model_path)
            scaler = joblib.load(scaler_path)
            return model, scaler
        except Exception as e:
            logger.error(f"Erreur lors du chargement du modèle: {str(e)}")
            
    # Entraîner un nouveau modèle si nécessaire
    return train_anomaly_detection_model(device_id, sensor_param)

def detect_anomalies(device_id, sensor_data, lang='fr'):
    """
    Détecter les anomalies dans les données des capteurs
    
    Args:
        device_id (str): Identifiant de l'appareil
        sensor_data (dict): Données du capteur
        lang (str): Code de langue pour les messages d'alerte
        
    Returns:
        list: Liste des anomalies détectées
    """
    anomalies = []
    
    # Paramètres à surveiller pour les anomalies
    params_to_monitor = [
        'temperature', 'moisture', 'ph', 'ec', 'nitrogen', 
        'phosphorous', 'potassium', 'bme_temperature', 
        'bme_humidity', 'bme_pressure', 'uv_index'
    ]
    
    for param in params_to_monitor:
        # Vérifier si le paramètre existe dans les données du capteur
        if param not in sensor_data or sensor_data[param] is None:
            continue
            
        try:
            value = float(sensor_data[param])
            
            # Charger ou entraîner le modèle
            model, scaler = load_or_train_model(device_id, param)
            if model is None or scaler is None:
                continue
                
            # Prétraiter la valeur
            value_scaled = scaler.transform([[value]])
            
            # Prédire si c'est une anomalie (-1) ou normal (1)
            prediction = model.predict(value_scaled)[0]
            
            # Obtenir le score d'anomalie (plus négatif = plus anormal)
            anomaly_score = model.decision_function(value_scaled)[0]
            
            # Si c'est une anomalie
            if prediction == -1:
                # Déterminer le niveau d'alerte en fonction du score
                if anomaly_score < -0.3:
                    level = 'danger'
                elif anomaly_score < -0.15:
                    level = 'warning'
                else:
                    level = 'info'
                
                # Créer un message d'alerte
                param_name = get_translation(param, lang)
                if level == 'danger':
                    message = f"{get_translation('anomaly_detected_danger', lang)}: {param_name} = {value:.2f}"
                elif level == 'warning':
                    message = f"{get_translation('anomaly_detected_warning', lang)}: {param_name} = {value:.2f}"
                else:
                    message = f"{get_translation('anomaly_detected_info', lang)}: {param_name} = {value:.2f}"
                
                # Créer une alerte dans la base de données
                alert = Alert(
                    device_id=device_id,
                    type=param,
                    message=message,
                    level=level,
                    acknowledged=False
                )
                db.session.add(alert)
                db.session.commit()
                
                # Ajouter à la liste des anomalies
                anomalies.append({
                    'parameter': param,
                    'value': value,
                    'score': anomaly_score,
                    'level': level,
                    'message': message
                })
                
                logger.info(f"Anomalie détectée: {param} = {value:.2f}, score = {anomaly_score:.2f}")
        except Exception as e:
            logger.error(f"Erreur lors de la détection d'anomalie pour {param}: {str(e)}")
    
    return anomalies

def train_models_for_all_devices():
    """
    Entraîner des modèles de détection d'anomalies pour tous les appareils enregistrés
    """
    from models import Device
    
    devices = Device.query.all()
    results = {
        'success': [],
        'failed': []
    }
    
    for device in devices:
        device_id = device.id
        
        # Paramètres à surveiller
        params_to_train = [
            'temperature', 'moisture', 'ph', 'ec', 'nitrogen', 
            'phosphorous', 'potassium', 'bme_temperature', 
            'bme_humidity', 'bme_pressure', 'uv_index'
        ]
        
        for param in params_to_train:
            model, scaler = train_anomaly_detection_model(device_id, param)
            if model is not None and scaler is not None:
                results['success'].append(f"{device_id}/{param}")
            else:
                results['failed'].append(f"{device_id}/{param}")
    
    return results