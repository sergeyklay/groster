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
        self._char_achievements: dict[str, dict[str, Any]] = {}
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

    async def get_roster_details(
        self, region: str, realm: str, guild: str
    ) -> list[dict[str, Any]] | None:
        """Retrieve previously saved roster details for a specific guild."""
        key = self._guild_key(region, realm, guild)
        roster = self._roster.get(key)
        if not roster:
            return None
        return list(roster)

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

    async def save_character_achievements(
        self,
        achievements_data: dict[str, Any],
        region: str,
        realm: str,
        char_name: str,
    ) -> None:
        """Save per-character achievement fingerprint data."""
        self._char_achievements[self._char_key(region, realm, char_name)] = dict(
            achievements_data
        )

    async def get_member_fingerprints(
        self,
        region: str,
        realm: str,
        member_names: list[str],
    ) -> dict[str, dict[str, Any]]:
        """Bulk-load cached achievement fingerprints for listed members."""
        result: dict[str, dict[str, Any]] = {}
        for name in member_names:
            key = self._char_key(region, realm, name)
            cached = self._char_achievements.get(key)
            if cached is None:
                continue
            entry = dict(cached)
            fp = entry.get("fingerprint", ())
            if isinstance(fp, list):
                entry["fingerprint"] = tuple(tuple(pair) for pair in fp)
            result[name] = entry
        return result

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

    async def build_dashboard(self, region: str, realm: str, guild: str) -> None:
        """Build and persist a consolidated dashboard from source data."""
        key = self._guild_key(region, realm, guild)
        roster = self._roster.get(key)
        if not roster:
            raise RuntimeError(
                "Failed to generate dashboard: a source CSV file is missing"
            )

        links = self._links.get(key, [])
        alts = self._alts.get(key, [])
        achievements = self._achievements.get(key, [])
        ranks = self._ranks.get(key, [])

        links_map: dict[tuple[Any, str], dict[str, Any]] = {
            (r["id"], r["name"]): r for r in links
        }
        alts_map: dict[tuple[Any, str], dict[str, Any]] = {
            (r["id"], r["name"]): r for r in alts
        }
        achievements_map: dict[tuple[Any, str], dict[str, Any]] = {
            (r["id"], r["name"]): r for r in achievements
        }
        classes_map = {r["id"]: r["name"] for r in self._classes}
        races_map = {r["id"]: r["name"] for r in self._races}
        ranks_map = {r["id"]: r["name"] for r in ranks}

        dashboard_rows: list[dict[str, Any]] = []
        for row in roster:
            row_key = (row["id"], row["name"])

            link_row = links_map.get(row_key)
            if link_row is None:
                continue

            alt_row = alts_map.get(row_key)
            if alt_row is None:
                continue

            ach_row = achievements_map.get(row_key, {})

            dashboard_rows.append(
                {
                    "Name": row["name"],
                    "Realm": row.get("realm"),
                    "Level": row.get("level"),
                    "Class": classes_map.get(row.get("class_id")),
                    "Race": races_map.get(row.get("race_id")),
                    "Rank": ranks_map.get(row.get("rank")),
                    "AQ": ach_row.get("total_quantity"),
                    "AP": ach_row.get("total_points"),
                    "Alt?": alt_row.get("alt"),
                    "Main": alt_row.get("main"),
                    "iLvl": row.get("ilvl"),
                    "Last Login": row.get("last_login"),
                    "Raider.io": link_row.get("rio_link"),
                    "Armory": link_row.get("armory_link"),
                    "Logs": link_row.get("warcraft_logs_link"),
                }
            )

        self._dashboard[key] = dashboard_rows
        self._dashboard_modified[key] = datetime.now(tz=UTC)

    async def get_alt_summary(
        self, region: str, realm: str, guild: str
    ) -> tuple[int, int] | None:
        """Retrieve a summary of alt detection results."""
        key = self._guild_key(region, realm, guild)
        alts = self._alts.get(key)
        if not alts:
            return None

        total_alts = sum(1 for row in alts if row.get("alt"))
        total_mains = len({row["main"] for row in alts})
        return (total_alts, total_mains)

    async def get_alts_per_main(
        self, region: str, realm: str, guild: str
    ) -> list[tuple[str, str, int]] | None:
        """Return per-main alt counts from the dashboard."""
        key = self._guild_key(region, realm, guild)
        dashboard = self._dashboard.get(key)
        if not dashboard:
            return None

        mains: dict[str, str] = {}
        for row in dashboard:
            if not row.get("Alt?"):
                mains[row["Name"]] = row.get("Class") or "Unknown"

        alt_counts: dict[str, int] = {}
        for row in dashboard:
            if row.get("Alt?"):
                main_name = row.get("Main", "")
                alt_counts[main_name] = alt_counts.get(main_name, 0) + 1

        result = [
            (name, class_name, alt_counts.get(name, 0))
            for name, class_name in mains.items()
        ]
        result.sort(key=lambda x: (-x[2], x[0]))
        return result

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

    async def search_character_names(
        self,
        prefix: str,
        region: str,
        realm: str,
        guild: str,
        *,
        limit: int = 25,
    ) -> list[str]:
        """Search character names in the dashboard by case-insensitive prefix."""
        key = self._guild_key(region, realm, guild)
        dashboard = self._dashboard.get(key)
        if not dashboard:
            return []

        lower_prefix = prefix.lower()
        names = [
            row["Name"]
            for row in dashboard
            if row["Name"].lower().startswith(lower_prefix)
        ]
        return sorted(names)[:limit]

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
