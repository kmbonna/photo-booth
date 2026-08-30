import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler

_configured = False

FMT = '%(asctime)s [%(levelname)-5s]  visitor=%(visitor)-8s  session=%(session)-10s %(message)s'


class _DefaultFields(logging.Filter):
    """Inject visitor=- and session=- on any record that doesn't set them."""
    def filter(self, record):
        if not hasattr(record, 'visitor'):
            record.visitor = '-'
        if not hasattr(record, 'session'):
            record.session = '-'
        return True


def setup():
    global _configured
    if _configured:
        return
    _configured = True

    log_dir = os.environ.get('LOGS_DIR') or os.path.join(os.path.dirname(__file__), '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)

    file_handler = TimedRotatingFileHandler(
        os.path.join(log_dir, 'photobooth.log'),
        when='midnight',
        backupCount=30,
        encoding='utf-8',
    )
    file_handler.setFormatter(logging.Formatter(FMT))
    file_handler.addFilter(_DefaultFields())

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)

    if os.environ.get('LOG_STDOUT', 'true').lower() == 'true':
        stream_handler = logging.StreamHandler(sys.__stderr__)
        stream_handler.setFormatter(logging.Formatter(FMT))
        stream_handler.addFilter(_DefaultFields())
        root.addHandler(stream_handler)


def get(name: str) -> logging.Logger:
    setup()
    return logging.getLogger(name)
