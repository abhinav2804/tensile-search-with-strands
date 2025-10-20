# utils/logger.py
import logging
import json
from logging.handlers import RotatingFileHandler

def setup_logger(name="app_logger", log_file="app.log"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3)
    formatter = logging.Formatter(json.dumps({
        "time": "%(asctime)s",
        "level": "%(levelname)s",
        "message": "%(message)s"
    }))
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

logger = setup_logger()
