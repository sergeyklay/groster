import os
from pathlib import Path

from groster import __version__


def _default_data_path() -> Path:
    """Return the default directory for generated runtime data."""
    return Path.cwd() / "data"


def _default_log_dir() -> Path:
    """Return the default directory for application log files."""
    return Path.cwd() / "logs"


def _resolve_directory(
    env_var: str,
    default_path: Path,
    *,
    label: str,
) -> Path:
    """Resolve and validate a runtime directory from the environment."""
    raw_path = os.getenv(env_var)
    path = Path(raw_path).expanduser() if raw_path else default_path

    if path.exists() and not path.is_dir():
        raise RuntimeError(f"{env_var} must point to a directory: {path}")

    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RuntimeError(f"Failed to create {label} directory: {path}") from exc

    return path


def resolve_data_path() -> Path:
    """Resolve and validate the runtime data directory.

    The directory is controlled by the GROSTER_DATA_PATH environment variable.
    If the variable is unset, the default remains ./data relative to the
    current working directory.

    Returns:
        The validated data directory path.

    Raises:
        RuntimeError: If the resolved path is not a directory or cannot be
            created.
    """
    return _resolve_directory(
        "GROSTER_DATA_PATH",
        _default_data_path(),
        label="data",
    )


def resolve_log_dir() -> Path:
    """Resolve and validate the runtime log directory.

    The directory is controlled by the GROSTER_LOG_DIR environment variable.
    If the variable is unset, the default remains ./logs relative to the
    current working directory.

    Returns:
        The validated log directory path.

    Raises:
        RuntimeError: If the resolved path is not a directory or cannot be
            created.
    """
    return _resolve_directory(
        "GROSTER_LOG_DIR",
        _default_log_dir(),
        label="log",
    )


def resolve_log_path() -> Path:
    """Resolve the application log file path from the log directory."""
    return resolve_log_dir() / "groster.log"


# Path for storing generated data files.
DATA_PATH = resolve_data_path()

# Directory for storing log files.
LOG_DIR = resolve_log_dir()

# Default log file path.
LOG_PATH = LOG_DIR / "groster.log"

# Achievement ID for "Level 10" achievement, used to identify characters.
LEVEL_10_ACHIEVEMENT_ID = 6

# Jaccard similarity threshold for grouping alts.
ALT_SIMILARITY_THRESHOLD = 0.8

# Timezone for displaying timestamps.
TZ = "Europe/Paris"

# Set of common, account-wide achievements IDs used to identify characters.
FINGERPRINT_ACHIEVEMENT_IDS = {
    9670,  # Toying Around
    10693,  # Fashionista: Hand
    10691,  # Fashionista: Shirt
    10689,  # Fashionista: Weapon & Off-Hand
    10687,  # Fashionista: Back
    10685,  # Fashionista: Feet
    10682,  # Fashionista: Chest
    10692,  # Fashionista: Shoulder
    10690,  # Fashionista: Tabard
    10688,  # Fashionista: Wrist
    10686,  # Fashionista: Waist
    10684,  # Fashionista: Legs
    10681,  # Fashionista: Head
    11176,  # Fabulous
}

# Weights for multi-factor main character scoring.
# Each factor is normalized to 0.0–1.0 within the group, then multiplied
# by its weight. The character with the highest total score is the main.
MAIN_SCORE_WEIGHTS: dict[str, int] = {
    "level_10_timestamp": 40,
    "character_id": 20,
    "total_points": 25,
    "total_quantity": 15,
}

# Supported regions based on official Blizzard API documentation.
SUPPORTED_REGIONS = {"us", "eu", "kr", "tw", "cn"}


# Default user agent for the Blizzard API.
DEFAULT_USER_AGENT = f"groster/{__version__}"
