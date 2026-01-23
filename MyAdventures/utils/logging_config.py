# Configuració bàsica de logging per a agents i sistema
import logging
import json
from datetime import datetime, timezone

class StructuredFormatter(logging.Formatter):
    """Formatter que produeix logs estructurats en JSON."""
    
    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module
        }
        return json.dumps(log_entry)

def setup_logging():
    """Configura logging estructurat per a tots els agents i sistema."""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Handler per a consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    
    # Handler per a fitxer amb format estructurat
    file_handler = logging.FileHandler('minecraft_agents.log')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(StructuredFormatter())
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger
