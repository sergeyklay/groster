import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def setup_logging(debug: bool = False):
    """Configure logging for the application.

    Args:
        debug: If True, enable debug logging for httpx/httpcore requests.
    """
    log_path = Path().cwd() / "groster.log"
    log_level = logging.DEBUG if debug else logging.INFO

    logging.basicConfig(
        level=log_level,
        format="[%(asctime)s] [%(levelname)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(), logging.FileHandler(str(log_path))],
    )

    if not debug:
        # Reduce httpx/httpcore logging noise - only show WARNING and above
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
