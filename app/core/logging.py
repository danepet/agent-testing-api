import logging
import json
import sys
import time
from logging.config import dictConfig
from pathlib import Path

from app.core.config import settings


class CustomFormatter(logging.Formatter):
    """
    Custom log formatter that outputs JSON.
    """
    
    def __init__(self):
        super().__init__()
        self.hostname = settings.HOSTNAME
    
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "hostname": self.hostname,
        }
        
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        
        if hasattr(record, 'job_id'):
            log_record['job_id'] = record.job_id
        
        if hasattr(record, 'test_id'):
            log_record['test_id'] = record.test_id
        
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id
        
        return json.dumps(log_record)


def setup_logging():
    """
    Set up application logging.
    """
    # Ensure logs directory exists
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": CustomFormatter,
            },
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            },
        },
        "handlers": {
            "console": {
                "level": settings.LOG_LEVEL,
                "class": "logging.StreamHandler",
                "formatter": "standard" if settings.LOG_FORMAT == "standard" else "json",
                "stream": sys.stdout,
            },
            "file": {
                "level": settings.LOG_LEVEL,
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "json",
                "filename": logs_dir / "app.log",
                "maxBytes": 10485760,  # 10 MB
                "backupCount": 10,
            },
            "error_file": {
                "level": "ERROR",
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "json",
                "filename": logs_dir / "error.log",
                "maxBytes": 10485760,  # 10 MB
                "backupCount": 10,
            },
        },
        "loggers": {
            "app": {
                "handlers": ["console", "file", "error_file"],
                "level": settings.LOG_LEVEL,
                "propagate": False,
            },
            "uvicorn": {
                "handlers": ["console", "file", "error_file"],
                "level": settings.LOG_LEVEL,
                "propagate": False,
            },
            "sqlalchemy": {
                "handlers": ["console", "file", "error_file"],
                "level": settings.SQL_LOG_LEVEL,
                "propagate": False,
            },
        },
        "root": {
            "handlers": ["console", "file", "error_file"],
            "level": settings.LOG_LEVEL,
        },
    }
    
    dictConfig(log_config)
    
    # Log startup information
    logger = logging.getLogger("app")
    logger.info(f"Starting application with log level: {settings.LOG_LEVEL}")