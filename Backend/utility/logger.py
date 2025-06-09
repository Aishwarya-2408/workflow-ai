import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

class AppLogger:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppLogger, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._initialized = True
            self._setup_logger()

    def _setup_logger(self):
        """Set up the logger with both file and console handlers."""
        # Create logs directory if it doesn't exist
        log_dir = "LOGS"
        os.makedirs(log_dir, exist_ok=True)

        # Create base logger
        self.logger = logging.getLogger('GenAIWorkflow')
        self.logger.setLevel(logging.DEBUG)
        
        # Prevent adding handlers multiple times
        if self.logger.handlers:
            return

        # Create formatters with milliseconds
        detailed_formatter = logging.Formatter(
            '%(asctime)s.%(msecs)03d | %(levelname)-8s | %(filename)s:%(lineno)d | %(funcName)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_formatter = logging.Formatter(
            '%(asctime)s.%(msecs)03d | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # File handler for detailed logging with rotation by size (10MB)
        detailed_file_handler = RotatingFileHandler(
            os.path.join(log_dir, 'detailed.log'),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        detailed_file_handler.setLevel(logging.DEBUG)
        detailed_file_handler.setFormatter(detailed_formatter)

        # Daily rotating file handler for errors
        error_file_handler = TimedRotatingFileHandler(
            os.path.join(log_dir, 'errors.log'),
            when='midnight',
            interval=1,
            backupCount=30
        )
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(detailed_formatter)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)

        # Add handlers to logger
        self.logger.addHandler(detailed_file_handler)
        self.logger.addHandler(error_file_handler)
        self.logger.addHandler(console_handler)

    def get_logger(self):
        """Get the configured logger instance."""
        return self.logger

# Global function to get logger instance
def get_logger():
    """Get the application logger instance."""
    return AppLogger().get_logger() 