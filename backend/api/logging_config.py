import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import structlog

def configure_production_logging():
    data_dir = os.getenv("RAPHAEL_DATA_DIR")
    if not data_dir:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        data_dir = os.path.join(project_root, "data")
        
    logs_dir = os.path.join(data_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(logs_dir, f"raphael-{date_str}.log")
    
    handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
