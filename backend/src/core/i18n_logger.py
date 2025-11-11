"""
Internationalized logging system with proper configuration
Logs are stored with translation keys, then rendered in user's language
"""
import logging
import json
import sys
from enum import StrEnum
from typing import Dict, Any, Optional
from pathlib import Path
from config import LANG, LOGLEVEL


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
    
    _translations_cache: Dict[str, Dict[str, str]] = {}  # Shared cache across instances
    _configured_loggers: set = set()  # Track configured loggers
    
    def __init__(self, name: str, translations_dir: Optional[str] = None):
        self.logger = logging.getLogger(name)
        
        # Find translations directory dynamically
        if translations_dir:
            self.translations_dir = Path(translations_dir)
        else:
            # Try multiple common locations
            possible_dirs = [
                Path.cwd() / "src" / "locales",
                Path.cwd() / "locales",
                Path.cwd() / "backend" / "src" / "locales",
                Path(__file__).parent.parent / "locales",
            ]
            
            self.translations_dir = None
            for dir_path in possible_dirs:
                if dir_path.exists() and dir_path.is_dir():
                    self.translations_dir = dir_path
                    break
            
            if not self.translations_dir:
                # Fallback: create a default location
                self.translations_dir = Path.cwd() / "locales"
                self.translations_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure logger only once per name
        if name not in I18nLogger._configured_loggers:
            self._configure_logger()
            I18nLogger._configured_loggers.add(name)
    
    def _configure_logger(self):
        """Configure logger with proper handlers and formatters"""
        # Remove any existing handlers to avoid duplicates
        self.logger.handlers.clear()
        
        # Set logger level based on LOGLEVEL environment variable
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        
        log_level = level_map.get(LOGLEVEL, logging.INFO)
        self.logger.setLevel(log_level)
        
        # Create console handler with a higher log level
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        
        # Create formatter with colors for better visibility
        formatter = ColoredFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # Prevent propagation to root logger to avoid duplicate logs
        self.logger.propagate = False
    
    def _load_translations(self, language: str) -> Dict[str, str]:
        """Load translation file for a language (cached)"""
        if language in I18nLogger._translations_cache:
            return I18nLogger._translations_cache[language]
        
        translation_file = self.translations_dir / f"{language}.json"
        
        if not translation_file.exists():
            # Fallback to English if language not found
            translation_file = self.translations_dir / "en.json"
            
            if not translation_file.exists():
                self.logger.warning(f"No translation file found for {language}, using keys as-is")
                return {}
        
        try:
            with open(translation_file, 'r', encoding='utf-8') as f:
                translations = json.load(f)
                I18nLogger._translations_cache[language] = translations
                return translations
        except Exception as e:
            self.logger.error(f"Failed to load translations for {language}: {e}")
            return {}
    
    def _format_message(
        self, 
        key: str, 
        language: str = LANG, 
        **kwargs
    ) -> str:
        """
        Format a log message by translating key and substituting parameters.
        
        Args:
            key: Translation key like "order.created"
            language: Target language code (defaults to config LANG)
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
            return f"{template} (missing params: {e})"
        except Exception as e:
            self.logger.warning(f"Error formatting message for key {key}: {e}")
            return key
    
    def _log_structured(
        self,
        level: LogLevel,
        key: str,
        language: str = LANG,
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
    
    def debug(self, key: str, language: str = LANG, **kwargs):
        """Log debug message with translation"""
        self._log_structured(LogLevel.DEBUG, key, language, **kwargs)
    
    def info(self, key: str, language: str = LANG, **kwargs):
        """Log info message with translation"""
        self._log_structured(LogLevel.INFO, key, language, **kwargs)
    
    def warning(self, key: str, language: str = LANG, **kwargs):
        """Log warning message with translation"""
        self._log_structured(LogLevel.WARNING, key, language, **kwargs)
    
    def error(self, key: str, language: str = LANG, **kwargs):
        """Log error message with translation"""
        self._log_structured(LogLevel.ERROR, key, language, **kwargs)
    
    def critical(self, key: str, language: str = LANG, **kwargs):
        """Log critical message with translation"""
        self._log_structured(LogLevel.CRITICAL, key, language, **kwargs)


class ColoredFormatter(logging.Formatter):
    """Formatter that adds colors to log levels for better visibility"""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        
        return super().format(record)


# Global logger factory
def get_i18n_logger(name: str, translations_dir: Optional[str] = None) -> I18nLogger:
    """
    Get or create an i18n logger instance
    
    Args:
        name: Logger name (usually __name__)
        translations_dir: Optional custom path to translations directory
    
    Returns:
        Configured I18nLogger instance
    """
    return I18nLogger(name, translations_dir)


# Example usage in your code:
'''
from src.core.i18n_logger import get_i18n_logger
from config import LANG

logger = get_i18n_logger(__name__)

# When creating an order (uses default LANG from config)
logger.info(
    "order.created", 
    order_id=order.id, 
    table_number=table.number,
    username=user.username
)

# When order status changes with explicit language
logger.info(
    "order.status_changed",
    language="es",  # Spanish
    order_id=order.id,
    old_status=old_status.value,
    new_status=new_status.value
)

# Debug logging
logger.debug(
    "database.query",
    query="SELECT * FROM users",
    execution_time=0.05
)

# Error logging
logger.error(
    "auth.login.failed",
    username=username,
    reason="Invalid password",
    ip_address=request.client.host
)
'''