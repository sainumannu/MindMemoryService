"""
Logger configuration module.
"""

import os
import logging
from logging.handlers import RotatingFileHandler

def get_logger(name):
    """
    Get a logger instance with the specified name.
    """
    return logging.getLogger(name)

def setup_logging(log_level=None):
    """
    Set up logging configuration.
    
    Args:
        log_level: Log level to use. Defaults to INFO.
    """
    # Determine log level from environment variable or parameter
    if not log_level:
        log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Configure basic logging
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            # Console handler
            logging.StreamHandler(),
            
            # File handler with rotation
            RotatingFileHandler(
                os.path.join(logs_dir, "vectorstore_service.log"),
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=5
            )
        ]
    )
    
    # Return root logger
    return logging.getLogger()
