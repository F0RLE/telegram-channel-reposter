"""
Internationalization (i18n) module for launcher
Supports English (default) and Russian
"""
import os
import json
import locale
from typing import Dict, Optional
from pathlib import Path

# Default language
DEFAULT_LANGUAGE = "en"

# Supported languages
SUPPORTED_LANGUAGES = ["en", "ru"]

# Language names for display
LANGUAGE_NAMES = {
    "en": "English",
    "ru": "Русский"
}

# Translations dictionary
_translations: Dict[str, Dict[str, str]] = {}

# Current language
_current_language = DEFAULT_LANGUAGE


def detect_system_language() -> str:
    """
    Detect system language and return language code.
    Returns 'ru' for Russian, 'en' for others.
    Optimized: tries fastest methods first.
    """
    try:
        # Method 1: Try Windows API first (fastest and most accurate on Windows)
        try:
            import ctypes
            windll = ctypes.windll.kernel32
            lcid = windll.GetUserDefaultUILanguage()
            lang_id = lcid & 0x3FF
            # Russian language ID is 0x19 (25)
            if lang_id == 0x19:
                return 'ru'
            # English is 0x09 (9) or default
            if lang_id == 0x09:
                return 'en'
        except Exception:
            pass
        
        # Method 2: Try environment variable (fast)
        import os
        lang_env = os.environ.get('LANG', '').split('_')[0].lower()
        if lang_env in SUPPORTED_LANGUAGES:
            return lang_env
        
        # Method 3: Try to get system locale (slower)
        try:
            system_locale, _ = locale.getdefaultlocale()
            if system_locale:
                lang_code = system_locale.split('_')[0].lower()
                if lang_code in SUPPORTED_LANGUAGES:
                    return lang_code
        except Exception:
            pass
        
        # Method 4: Try locale.getlocale() (slowest, fallback)
        try:
            loc = locale.getlocale()[0]
            if loc:
                lang_code = loc.split('_')[0].lower()
                if lang_code in SUPPORTED_LANGUAGES:
                    return lang_code
        except Exception:
            pass
    except Exception:
        pass
    
    # Default to English
    return 'en'


def load_translations(lang: str = None) -> Dict[str, str]:
    """Load translations for specified language"""
    if lang is None:
        lang = _current_language
    
    if lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE
    
    # Return cached translations if available
    if lang in _translations:
        return _translations[lang]
    
    # Load from JSON file
    translations_file = Path(__file__).parent / "locales" / f"{lang}.json"
    
    if translations_file.exists():
        try:
            with open(translations_file, 'r', encoding='utf-8') as f:
                _translations[lang] = json.load(f)
                return _translations[lang]
        except Exception:
            pass
    
    # Return empty dict if file not found
    return {}


def set_language(lang: str) -> bool:
    """
    Set current language.
    Returns True if language was set successfully.
    """
    global _current_language
    
    if lang in SUPPORTED_LANGUAGES:
        _current_language = lang
        # Reload translations
        load_translations(lang)
        return True
    return False


def get_language() -> str:
    """Get current language code"""
    return _current_language


def t(key: str, default: Optional[str] = None, **kwargs) -> str:
    """
    Translate a key to current language.
    
    Args:
        key: Translation key (e.g., "ui.launcher.title")
        default: Default text if key not found
        **kwargs: Variables to substitute in translation (e.g., {name} -> name="value")
    
    Returns:
        Translated string
    """
    translations = load_translations()
    text = translations.get(key, default or key)
    
    # Substitute variables
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass
    
    return text


def init_i18n(lang: Optional[str] = None) -> str:
    """
    Initialize i18n system.
    If lang is None, detects system language.
    
    Returns:
        Language code that was set
    """
    if lang is None:
        lang = detect_system_language()
    
    set_language(lang)
    return lang

