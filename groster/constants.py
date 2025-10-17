from pathlib import Path

# Path for storing generated data files.
DATA_PATH = Path().cwd() / "data"

# Path for storing cache files (e.g., roster hash).
CACHE_PATH = Path().cwd() / "cache"

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
