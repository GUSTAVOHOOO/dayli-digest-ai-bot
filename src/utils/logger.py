import os
import sys
import logging
from logging.handlers import RotatingFileHandler
try:
    import structlog
except ImportError:
    structlog = None
from pathlib import Path

LOG_DIR = Path(os.getenv('LOG_DIR', 'logs'))
LOG_FILE = LOG_DIR / 'digest.log'
MAX_BYTES = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 7

def configure_logging():
    """Configures structlog with JSON output and rotating file handlers."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    if structlog is None:
        logging.basicConfig(level=logging.INFO)
        return

    # Avoid duplicate configuration
    if structlog.is_configured():
        return

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # File handler with rotation
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding='utf-8',
    )
    file_handler.setFormatter(logging.Formatter('%(message)s'))

    root_logger = logging.getLogger()
    # Remove existing handlers to avoid duplicates during re-config
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)
        
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.INFO)

    # Optional stdout handler (for Docker)
    if os.getenv('LOG_TO_STDOUT', 'true').lower() == 'true':
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(logging.Formatter('%(message)s'))
        root_logger.addHandler(stdout_handler)

def get_logger(name: str):
    """Retrieves a configured structlog logger."""
    configure_logging()
    if structlog is None:
        return _FallbackLogger(logging.getLogger(name))
    return structlog.get_logger(name)


class _FallbackLogger:
    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def info(self, event: str, **kwargs):
        self.logger.info(self._format(event, kwargs))

    def warning(self, event: str, **kwargs):
        self.logger.warning(self._format(event, kwargs))

    def error(self, event: str, **kwargs):
        self.logger.error(self._format(event, kwargs))

    def _format(self, event: str, kwargs: dict) -> str:
        if not kwargs:
            return event
        fields = " ".join(f"{key}={value}" for key, value in kwargs.items())
        return f"{event} {fields}"
