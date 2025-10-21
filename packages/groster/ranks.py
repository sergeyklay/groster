import logging
from collections import namedtuple
from types import MappingProxyType

logger = logging.getLogger(__name__)

Rank = namedtuple("Rank", ["id", "name"])

_DEFAULT_RANKS = (
    Rank(0, "Guild Master"),
    Rank(1, "Vice Guild Master"),
    Rank(2, "Guild Officer"),
    Rank(3, "Officer Alt"),
    Rank(4, "Super Moon"),
    Rank(5, "Active Moon"),
    Rank(6, "Full Moon"),
    Rank(7, "Waxing Moon"),
    Rank(8, "Half Moon"),
    Rank(9, "New Moon"),
)
"""Hold the default rank structure as a tuple of Rank objects."""


def create_rank_mapping(
    overrides: dict[int, str] | None = None,
) -> MappingProxyType[int, Rank]:
    """
    Factory function to create a read-only mapping of guild ranks.

    It starts with a default set of ranks and applies any provided
    overrides. This makes the rank system flexible and configurable.

    Args:
        overrides: A dictionary to override default rank names,
                   e.g., {1: "General", 2: "Senior Officer"}.

    Returns:
        An immutable, read-only dictionary mapping rank IDs to Rank objects.
    """
    ranks = {rank.id: rank for rank in _DEFAULT_RANKS}

    if overrides:
        logger.info("Applying %d custom rank name overrides.", len(overrides))
        for rank_id, new_name in overrides.items():
            if rank_id in ranks:
                ranks[rank_id] = ranks[rank_id]._replace(name=new_name)
            else:
                logger.warning(
                    "Attempted to override non-existent rank ID: %d", rank_id
                )

    return MappingProxyType(ranks)
