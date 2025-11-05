"""
Internationalized logging system
Logs are stored with translation keys, then rendered in user's language
"""
import logging
import json
from enum import StrEnum
from typing import Dict, Any, Optional
from pathlib import Path


class LogLevel(StrEnum):
    """Standard logging levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class I18nLogger:
    """
    Logger that stores structured logs with translation keys.
    
    Philosophy:
    - Logs contain keys like "order.created" instead of "Order created"
    - When displaying logs, we translate keys using the viewer's language
    - This keeps logs language-agnostic while supporting multilanguage UIs
    
    Example:
        logger.info("order.created", order_id=123, table=5)
        
        In English UI: "Order #123 created for table 5"
        In French UI:  "Commande #123 créée pour la table 5"
    """
    
    def __init__(self, name: str, translations_dir: str = "locales"):
        self.logger = logging.getLogger(name)
        self.translations_dir = Path(translations_dir)
        self._translations_cache: Dict[str, Dict[str, str]] = {}
        
    def _load_translations(self, language: str) -> Dict[str, str]:
        """Load translation file for a language (cached)"""
        if language in self._translations_cache:
            return self._translations_cache[language]
        
        translation_file = self.translations_dir / f"{language}.json"
        
        if not translation_file.exists():
            # Fallback to English if language not found
            translation_file = self.translations_dir / "en.json"
        
        try:
            with open(translation_file, 'r', encoding='utf-8') as f:
                translations = json.load(f)
                self._translations_cache[language] = translations
                return translations
        except Exception as e:
            self.logger.error(f"Failed to load translations for {language}: {e}")
            return {}
    
    def _format_message(
        self, 
        key: str, 
        language: str = "en", 
        **kwargs
    ) -> str:
        """
        Format a log message by translating key and substituting parameters.
        
        Args:
            key: Translation key like "order.created"
            language: Target language code
            **kwargs: Variables to substitute in the message
        
        Returns:
            Formatted, translated message
        """
        translations = self._load_translations(language)
        
        # Get template from translations, fallback to key if not found
        template = translations.get(key, key)
        
        # Substitute variables using format_map for safety
        try:
            return template.format_map(kwargs)
        except KeyError as e:
            self.logger.warning(f"Missing parameter {e} for translation key {key}")
            return f"{template} (missing params)"
    
    def _log_structured(
        self,
        level: LogLevel,
        key: str,
        language: str = "en",
        **kwargs
    ):
        """
        Internal method to log with structured data.
        
        The log record contains:
        - Human-readable message (translated)
        - Structured extra data with translation key and parameters
        """
        # Get translated message
        message = self._format_message(key, language, **kwargs)
        
        # Add structured data as extra fields
        extra = {
            'translation_key': key,
            'params': kwargs,
            'language': language
        }
        
        # Log with appropriate level
        log_method = getattr(self.logger, level.value.lower())
        log_method(message, extra=extra)
    
    # Convenience methods for each log level
    
    def debug(self, key: str, language: str = "en", **kwargs):
        """Log debug message with translation"""
        self._log_structured(LogLevel.DEBUG, key, language, **kwargs)
    
    def info(self, key: str, language: str = "en", **kwargs):
        """Log info message with translation"""
        self._log_structured(LogLevel.INFO, key, language, **kwargs)
    
    def warning(self, key: str, language: str = "en", **kwargs):
        """Log warning message with translation"""
        self._log_structured(LogLevel.WARNING, key, language, **kwargs)
    
    def error(self, key: str, language: str = "en", **kwargs):
        """Log error message with translation"""
        self._log_structured(LogLevel.ERROR, key, language, **kwargs)
    
    def critical(self, key: str, language: str = "en", **kwargs):
        """Log critical message with translation"""
        self._log_structured(LogLevel.CRITICAL, key, language, **kwargs)


# Global logger factory
def get_i18n_logger(name: str) -> I18nLogger:
    """Get or create an i18n logger instance"""
    return I18nLogger(name)


# Example usage in your code:
'''
from core.i18n_logger import get_i18n_logger

logger = get_i18n_logger("orders")

# When creating an order
logger.info(
    "order.created", 
    language="fr",  # French
    order_id=order.id, 
    table_number=table.number,
    username=user.username
)

# When order status changes
logger.info(
    "order.status_changed",
    language="es",  # Spanish
    order_id=order.id,
    old_status=old_status.value,
    new_status=new_status.value
)
'''