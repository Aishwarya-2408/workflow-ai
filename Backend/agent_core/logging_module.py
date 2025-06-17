# Placeholder for Logging & Monitoring Module 

import logging
import sys
import os

class LoggingModule:
    def __init__(self, log_file="agent.log", log_level=logging.INFO, log_folder="LOGS"):
        self.logger = logging.getLogger("AutonomousAgent")
        self.logger.setLevel(log_level)

        # Ensure the log folder exists
        if not os.path.exists(log_folder):
            os.makedirs(log_folder, exist_ok=True)

        # Create handlers
        full_log_file_path = os.path.join(log_folder, log_file)
        file_handler = logging.FileHandler(full_log_file_path, encoding='utf-8')
        file_handler.setLevel(log_level)

        stream_handler = logging.StreamHandler(sys.stdout) # Output to console
        stream_handler.setLevel(log_level)

        # Create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        stream_handler.setFormatter(formatter)

        # Add handlers to the logger
        if not self.logger.handlers: # Avoid adding multiple handlers if re-initialized
            self.logger.addHandler(file_handler)
            self.logger.addHandler(stream_handler)

    def info(self, message):
        self.logger.info(message)

    def error(self, message, exc_info=False):
        self.logger.error(message, exc_info=exc_info)

    def debug(self, message):
        self.logger.debug(message)

    def warning(self, message):
        self.logger.warning(message)

if __name__ == '__main__':
    # Example Usage
    logger = LoggingModule(log_level=logging.DEBUG)
    logger.info("This is an info message.")
    logger.debug("This is a debug message.")
    logger.warning("This is a warning message.")
    try:
        x = 1 / 0
    except ZeroDivisionError:
        logger.error("Error: Division by zero!", exc_info=True) 