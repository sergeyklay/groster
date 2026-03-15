from datetime import UTC, datetime
from typing import Any

from groster.repository.base import RosterRepository


class InMemoryRosterRepository(RosterRepository):
    """In-memory implementation of RosterRepository for testing.

    Stores all data in plain Python collections instead of CSV files,
    enabling fast, isolated unit tests without filesystem I/O.
    """

    def __init__(self):
        self._classes: list[dict[str, Any]] = []
        self._races: list[dict[str, Any]] = []
        self._ranks: dict[str, list[dict[str, Any]]] = {}
        self._links: dict[str, list[dict[str, Any]]] = {}
        self._roster: dict[str, list[dict[str, Any]]] = {}
        self._profiles: dict[str, dict[str, Any]] = {}
        self._pets: dict[str, dict[str, Any]] = {}
        self._mounts: dict[str, dict[str, Any]] = {}
        self._alts: dict[str, list[dict[str, Any]]] = {}
        self._achievements: dict[str, list[dict[str, Any]]] = {}
        self._dashboard: dict[str, list[dict[str, Any]]] = {}
        self._dashboard_modified: dict[str, datetime] = {}

    @staticmethod
    def _guild_key(region: str, realm: str, guild: str) -> str:
        """Build composite key for guild-scoped data."""
        return f"{region}/{realm}/{guild}"

    @staticmethod
    def _char_key(region: str, realm: str, char_name: str) -> str:
        """Build composite key for character-scoped data."""
        return f"{region}/{realm}/{char_name.lower()}"

    async def get_playable_classes(self) -> dict[int, str] | None:
        """Retrieve saved playable classes mapping."""
        if not self._classes:
            return None
        return {row["id"]: row["name"] for row in self._classes}

    async def save_playable_classes(self, classes: list[dict[str, Any]]) -> None:
        """Save the list of playable classes."""
        self._classes = list(classes)

    async def get_playable_races(self) -> dict[int, str] | None:
        """Retrieve saved playable races mapping."""
        if not self._races:
            return None
        return {row["id"]: row["name"] for row in self._races}

    async def save_playable_races(self, races: list[dict[str, Any]]) -> None:
        """Save the list of playable races."""
        self._races = list(races)

    async def get_guild_ranks(
        self, region: str, realm: str, guild: str
    ) -> dict[int, str] | None:
        """Retrieve saved guild ranks mapping for a specific guild."""
        key = self._guild_key(region, realm, guild)
        ranks = self._ranks.get(key)
        if not ranks:
            return None
        return {row["id"]: row["name"] for row in ranks}

    async def save_guild_ranks(
        self, ranks: list[dict[str, Any]], region: str, realm: str, guild: str
    ) -> None:
        """Save the list of guild ranks for a specific guild."""
        self._ranks[self._guild_key(region, realm, guild)] = list(ranks)

    async def save_profile_links(
        self, links_data: list[dict[str, Any]], region: str, realm: str, guild: str
    ) -> None:
        """Save generated profile links for guild members."""
        self._links[self._guild_key(region, realm, guild)] = list(links_data)

    async def save_roster_details(
        self, roster_data: list[dict[str, Any]], region: str, realm: str, guild: str
    ) -> None:
        """Save processed roster details for a specific guild."""
        self._roster[self._guild_key(region, realm, guild)] = list(roster_data)

    async def save_character_profile(
        self,
        profile_data: dict[str, Any],
        region: str,
        realm: str,
        char_name: str,
    ) -> None:
        """Save raw JSON profile data for a single character."""
        self._profiles[self._char_key(region, realm, char_name)] = dict(profile_data)

    async def save_character_pets(
        self,
        pets_data: dict[str, Any],
        region: str,
        realm: str,
        character_name: str,
    ) -> None:
        """Save pet collection data for a single character."""
        self._pets[self._char_key(region, realm, character_name)] = dict(pets_data)

    async def save_character_mounts(
        self,
        mounts_data: dict[str, Any],
        region: str,
        realm: str,
        character_name: str,
    ) -> None:
        """Save mount collection data for a single character."""
        self._mounts[self._char_key(region, realm, character_name)] = dict(mounts_data)

    async def save_alts_data(
        self, alts_data: list[dict[str, Any]], region: str, realm: str, guild: str
    ) -> None:
        """Save processed alts data for a specific guild."""
        self._alts[self._guild_key(region, realm, guild)] = list(alts_data)

    async def save_achievements_summary(
        self, summary_data: list[dict[str, Any]], region: str, realm: str, guild: str
    ) -> None:
        """Save the summary of achievements for all members."""
        self._achievements[self._guild_key(region, realm, guild)] = list(summary_data)

    async def get_character_info_by_name(
        self, name: str, region: str, realm: str, guild: str
    ) -> tuple[dict[str, Any] | None, datetime | None]:
        """Retrieve character information by name from the dashboard data."""
        key = self._guild_key(region, realm, guild)
        dashboard = self._dashboard.get(key)
        if not dashboard:
            return None, None

        modified_at = self._dashboard_modified.get(key)

        # Search for character (case-insensitive)
        char_row = None
        for row in dashboard:
            if row["Name"].lower() == name.lower():
                char_row = row
                break

        if char_row is None:
            return None, modified_at

        # Determine main character name
        main_name = char_row["Main"] if char_row.get("Alt?") else char_row["Name"]

        # Find main character row
        main_row = None
        for row in dashboard:
            if row["Name"].lower() == main_name.lower():
                main_row = row
                break

        source_row = main_row if main_row is not None else char_row
        main_info = self._build_character_info(source_row)

        # Collect alts
        alts = [
            self._build_character_info(row)
            for row in dashboard
            if row.get("Alt?") and row.get("Main", "").lower() == main_name.lower()
        ]

        main_info["alts"] = alts
        return main_info, modified_at

    @staticmethod
    def _build_character_info(row: dict[str, Any]) -> dict[str, Any]:
        """Build character info dict from a plain dictionary row.

        Replicates the output shape of ``create_character_info`` from
        ``groster.models`` without depending on pandas.
        """
        name = row.get("Name", "")
        return {
            "name": str(name),
            "realm": str(row.get("Realm", "")),
            "level": int(row["Level"]) if row.get("Level") is not None else 0,
            "class": str(row["Class"]) if row.get("Class") is not None else "Unknown",
            "race": str(row["Race"]) if row.get("Race") is not None else "Unknown",
            "rank": str(row["Rank"]) if row.get("Rank") is not None else "Unknown",
            "ilvl": int(row["iLvl"]) if row.get("iLvl") is not None else 0,
            "last_login": (
                str(row["Last Login"]) if row.get("Last Login") is not None else "N/A"
            ),
            "is_alt": bool(row["Alt?"]) if row.get("Alt?") is not None else False,
            "main": (str(row["Main"]) if row.get("Main") is not None else str(name)),
        }

    def seed_dashboard(
        self,
        data: list[dict[str, Any]],
        region: str,
        realm: str,
        guild: str,
        modified_at: datetime | None = None,
    ) -> None:
        """Populate dashboard data for testing.

        Args:
            data: List of dashboard row dicts with keys matching CSV columns.
            region: The region identifier.
            realm: The realm slug.
            guild: The guild slug.
            modified_at: Optional timestamp; defaults to now (UTC).
        """
        key = self._guild_key(region, realm, guild)
        self._dashboard[key] = list(data)
        self._dashboard_modified[key] = modified_at or datetime.now(tz=UTC)
