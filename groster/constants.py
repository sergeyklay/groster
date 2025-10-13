from collections import namedtuple
from pathlib import Path
from types import MappingProxyType

# Defines the structure for an immutable rank object
Rank = namedtuple("Rank", ["id", "name"])

# Private dictionary of rank objects
_RANKS = {
    0: Rank(0, "Guild Master"),
    1: Rank(1, "Officer"),
    2: Rank(2, "Veteran"),
    3: Rank(3, "Member"),
    4: Rank(4, "Initiate"),
    5: Rank(5, "Social"),
    6: Rank(6, "Alt"),
    7: Rank(7, "Trial"),
    8: Rank(8, "Inactive"),
    9: Rank(9, "Recruit"),
}

# Public, read-only view of our ranks dictionary
GUILD_RANKS = MappingProxyType(_RANKS)

DATA_PATH = Path().cwd() / "data"
CACHE_PATH = Path().cwd() / "cache"
