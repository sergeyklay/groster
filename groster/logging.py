import logging
import os
import sys
import time
from pathlib import Path

from pythonjsonlogger.json import JsonFormatter

from groster import __version__

logger = logging.getLogger(__name__)


def setup_logging(debug: bool = False) -> None:
    """Configure logging for the application.

    Args:
        debug: If True, enable debug logging for httpx/httpcore requests.
    """
    log_level = logging.DEBUG if debug else logging.INFO
    log_format = os.environ.get("GROSTER_LOG_FORMAT", "text").lower()

    if log_format == "json":
        handler = logging.StreamHandler(sys.stdout)
        formatter = JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s "
            "%(module)s %(funcName)s %(lineno)d",
            rename_fields={
                "asctime": "timestamp",
                "levelname": "level",
                "name": "logger",
                "funcName": "function",
                "lineno": "line",
            },
            static_fields={
                "service": "groster",
                "version": __version__,
            },
        )
        formatter.converter = time.gmtime
        formatter.default_time_format = "%Y-%m-%dT%H:%M:%S"
        formatter.default_msec_format = "%s.%03dZ"
        handler.setFormatter(formatter)
        logging.basicConfig(level=log_level, handlers=[handler])
    else:
        log_path = Path().cwd() / "groster.log"
        logging.basicConfig(
            level=log_level,
            format="[%(asctime)s] [%(levelname)s] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(str(log_path)),
            ],
        )

    if not debug:
        # Reduce httpx/httpcore logging noise - only show WARNING and above
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
