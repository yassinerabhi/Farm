"""
Module pour la gestion des traductions multilingues
"""
import json
import logging
import os
from flask import session, request, g

# Configurer le logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Langues supportées
SUPPORTED_LANGUAGES = ['en', 'fr', 'ar']
DEFAULT_LANGUAGE = 'fr'

# Dictionnaire des noms complets des langues
LANGUAGE_NAMES = {
    'en': 'English',
    'fr': 'Français',
    'ar': 'العربية'
}

# Direction du texte pour chaque langue
TEXT_DIRECTIONS = {
    'en': 'ltr',  # left-to-right
    'fr': 'ltr',  # left-to-right
    'ar': 'rtl'   # right-to-left
}

# Dictionnaire pour stocker les traductions
translations = {}

def load_translations():
    """Charger les traductions depuis les fichiers JSON"""
    global translations
    
    # Assurez-vous que le dossier 'translations' existe
    if not os.path.exists('translations'):
        os.makedirs('translations')
        
    # Charger les traductions pour chaque langue supportée
    for lang in SUPPORTED_LANGUAGES:
        try:
            file_path = f'translations/{lang}.json'
            # Si le fichier n'existe pas, créer un fichier vide
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
                    
            # Charger les traductions
            with open(file_path, 'r', encoding='utf-8') as f:
                translations[lang] = json.load(f)
                logger.info(f"Traductions chargées pour {lang}")
        except Exception as e:
            logger.error(f"Erreur lors du chargement des traductions pour {lang}: {e}")
            translations[lang] = {}

def get_translation(key, lang=None):
    """
    Obtenir la traduction d'une clé dans la langue spécifiée
    
    Args:
        key (str): La clé de traduction
        lang (str, optional): La langue. Par défaut, utilise la langue de la session ou DEFAULT_LANGUAGE
        
    Returns:
        str: La traduction ou la clé si non trouvée
    """
    # Si la langue n'est pas spécifiée, utiliser celle de la session ou la langue par défaut
    if not lang:
        lang = session.get('language', DEFAULT_LANGUAGE)
        
    # Si la langue n'est pas supportée, utiliser la langue par défaut
    if lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE
        
    # Retourner la traduction ou la clé si non trouvée
    return translations.get(lang, {}).get(key, key)

def init_translations(app):
    """
    Initialiser le système de traduction pour l'application Flask
    
    Args:
        app: L'application Flask
    """
    # Charger les traductions
    load_translations()
    
    # Ajouter les fonctions aux templates Jinja2
    app.jinja_env.globals.update(get_translation=get_translation)
    app.jinja_env.globals.update(get_language=lambda: session.get('language', DEFAULT_LANGUAGE))
    app.jinja_env.globals.update(get_text_direction=lambda: TEXT_DIRECTIONS.get(session.get('language', DEFAULT_LANGUAGE), 'ltr'))
    app.jinja_env.globals.update(get_supported_languages=lambda: SUPPORTED_LANGUAGES)
    app.jinja_env.globals.update(get_language_names=lambda: LANGUAGE_NAMES)
    
    # Définir une route pour changer de langue
    @app.route('/change-language/<language>')
    def change_language(language):
        if language in SUPPORTED_LANGUAGES:
            session['language'] = language
            # Rediriger vers la page précédente ou la page d'accueil
            return app.redirect(request.referrer or '/')
        return app.redirect('/')
    
    # Middleware pour définir la langue pour chaque requête
    @app.before_request
    def set_language():
        # Si la langue n'est pas définie dans la session, utiliser la langue par défaut
        if 'language' not in session:
            session['language'] = DEFAULT_LANGUAGE
        
        # Définir la langue pour g pour que les templates puissent y accéder
        g.language = session.get('language', DEFAULT_LANGUAGE)
        g.text_direction = TEXT_DIRECTIONS.get(g.language, 'ltr')

def _(key):
    """
    Fonction raccourci pour get_translation
    
    Args:
        key (str): La clé de traduction
        
    Returns:
        str: La traduction ou la clé si non trouvée
    """
    return get_translation(key)