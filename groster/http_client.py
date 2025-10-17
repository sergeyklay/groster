import asyncio
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Default user agent for the Blizzard API.
# TODO: Use project version from pyproject.toml
DEFAULT_USER_AGENT = "groster/0.3.0"

# Region-based host mappings for different Blizzard API endpoints.
_OAUTH_HOSTS = {
    "us": "https://oauth.battle.net",
    "eu": "https://oauth.battle.net",
    "kr": "https://oauth.battle.net",
    "tw": "https://oauth.battle.net",
    "cn": "https://oauth.battlenet.com.cn",
}

# Fallback region-based host mapping for different Blizzard API endpoints.
_API_HOSTS = {
    "cn": "https://gateway.battlenet.com.cn",
    "*": "https://{region}.api.blizzard.com",
}

# Supported regions based on official Blizzard API documentation.
SUPPORTED_REGIONS = {"us", "eu", "kr", "tw", "cn"}


def _validate_region(region: str) -> None:
    """Validate that the region is supported by the Blizzard API."""
    if region not in SUPPORTED_REGIONS:
        raise ValueError(
            f"Unsupported region '{region}'. "
            f"Supported regions are: {', '.join(sorted(SUPPORTED_REGIONS))}"
        )


class BlizzardAPIClient:
    """An HTTP client for the Blizzard Battle.net API."""

    def __init__(
        self,
        region: str,
        client_id: str,
        client_secret: str,
        locale: str = "en_US",
        timeout: int = 10,
        max_retries: int = 5,
    ):
        if not all([region, client_id, client_secret]):
            raise ValueError("Region, client ID, and client secret must be provided")

        _validate_region(region)
        self.region = region
        self.client_id = client_id
        self.client_secret = client_secret
        self.locale = locale

        self._api_token: str | None = None
        self._token_expires_at: float = 0

        self._profile_params = {
            "namespace": f"profile-{self.region}",
            "locale": self.locale,
        }

        self._static_params = {
            "namespace": f"static-{self.region}",
            "locale": self.locale,
        }

        self.max_retries = max_retries
        transport = httpx.AsyncHTTPTransport(retries=max_retries)

        lang_header = self.locale.replace("_", "-")
        self.client = httpx.AsyncClient(
            transport=transport,
            timeout=timeout,
            headers={
                "User-Agent": DEFAULT_USER_AGENT,
                "Accept": "application/json",
                "Accept-Language": lang_header,
            },
        )

    def _format_url(self, path: str) -> str:
        """Format the URL for the Blizzard Battle.net API."""
        path = path.lstrip("/")

        # Use region-specific API host or fallback to standard pattern
        if self.region in _API_HOSTS:
            base_url = _API_HOSTS[self.region]
        else:
            base_url = _API_HOSTS["*"].format(region=self.region)

        return f"{base_url}/{path}"

    async def _get_access_token(self) -> str:
        """Fetch or renews the OAuth access token."""
        if self._api_token and time.time() < self._token_expires_at:
            return self._api_token

        # Use region-specific OAuth host
        oauth_host = _OAUTH_HOSTS.get(self.region, _OAUTH_HOSTS["us"])
        url = f"{oauth_host}/token"
        data = {"grant_type": "client_credentials"}
        auth = (self.client_id, self.client_secret)

        logger.debug("Requesting new access token from Battle.net")
        try:
            response = await self.client.post(url, data=data, auth=auth)
            response.raise_for_status()
            token_data = response.json()

            access_token = token_data.get("access_token")
            if not access_token:
                logger.error(
                    "Failed to obtain access token: "
                    "'access_token' not found in the Blizzard API response"
                )
                logger.debug("Token response: %s", token_data)
                raise ValueError("'access_token' not found in the response")

            self._api_token = str(access_token)
            expires_in = token_data.get("expires_in", 3600)
            self._token_expires_at = time.time() + int(expires_in) - 60

            logger.debug("Access token successfully obtained")
            return self._api_token
        except httpx.HTTPError:
            logger.exception("Failed to obtain access token")
            raise

    async def _request(self, method: str, url: str, **kwargs) -> dict[str, Any]:
        """Make a HTTP request to the Blizzard API."""
        token = await self._get_access_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"

        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self.client.request(
                    method, url, headers=headers, **kwargs
                )
                if response.status_code in (429, 500, 502, 503, 504):
                    retry_after = response.headers.get("Retry-After")
                    if retry_after and retry_after.isdigit():
                        delay = int(retry_after)
                    else:
                        delay = min(0.5 * 2 ** (attempt - 1), 5)

                    logger.warning(
                        "Transient %d from %s (attempt %d/%d); retrying in %.1fs",
                        response.status_code,
                        url,
                        attempt,
                        self.max_retries,
                        delay,
                    )

                    await asyncio.sleep(delay)
                    continue
                response.raise_for_status()
                return response.json()
            except httpx.RequestError as e:
                req_url = e.request.url if getattr(e, "request", None) else url
                logger.warning(
                    "API request to %s failed (attempt %d/%d): %s",
                    req_url,
                    attempt,
                    self.max_retries,
                    e,
                )
                await asyncio.sleep(min(0.5 * 2 ** (attempt - 1), 5))
            except httpx.HTTPStatusError as e:
                logger.warning(
                    "API request to %s failed with status %d: %s",
                    e.request.url,
                    e.response.status_code,
                    e.response.text,
                )
                break

        return {}  # Return empty dict on failure

    async def _get_static_data(self, data_key: str) -> dict:
        path = f"data/wow/{data_key}/index"
        url = self._format_url(path)
        return await self._request("GET", url, params=self._static_params)

    async def get_guild_roster(self, realm_slug: str, guild_slug: str) -> dict:
        """Fetch the roster of a guild.

        Args:
            realm_slug: The realm slug (e.g., 'terokkar').
            guild_slug: The guild slug (e.g., 'darq-side-of-the-moon').

        Returns:
            A dict containing the guild roster data, or an empty dict on failure.
        """
        logger.debug("Fetching guild roster")
        url = self._format_url(f"data/wow/guild/{realm_slug}/{guild_slug}/roster")

        return await self._request("GET", url, params=self._profile_params)

    async def get_character_profile(self, realm_slug: str, char_name: str) -> dict:
        """Fetch a character's profile.

        Args:
            realm_slug: The realm slug where the character resides.
            char_name: The character name (case-insensitive).

        Returns:
            A dict containing the character profile data, or an empty dict on failure.
        """
        logger.debug("Fetching character profile for %s on %s", char_name, realm_slug)

        name = char_name.lower()
        url = self._format_url(f"profile/wow/character/{realm_slug}/{name}")

        return await self._request("GET", url, params=self._profile_params)

    async def get_character_achievements(self, realm_slug: str, char_name: str) -> dict:
        """Fetch a character's achievements.

        Args:
            realm_slug: The realm slug where the character resides.
            char_name: The character name (case-insensitive).

        Returns:
            A dict containing the character achievements data, or an empty dict on
            failure.
        """
        logger.debug(
            "Fetching character achievements for %s on %s", char_name, realm_slug
        )

        name = char_name.lower()
        url = self._format_url(
            f"profile/wow/character/{realm_slug}/{name}/achievements"
        )

        return await self._request("GET", url, params=self._profile_params)

    async def get_character_pets(self, realm_slug: str, char_name: str) -> dict:
        """Fetch a character's pets.

        Args:
            realm_slug: The realm slug where the character resides.
            char_name: The character name (case-insensitive).

        Returns:
            A dict containing the character pets data, or an empty dict on failure.
        """
        logger.debug("Fetching character pets for %s on %s", char_name, realm_slug)

        name = char_name.lower()
        url = self._format_url(
            f"profile/wow/character/{realm_slug}/{name}/collections/pets"
        )

        return await self._request("GET", url, params=self._profile_params)

    async def get_character_mounts(self, realm_slug: str, char_name: str) -> dict:
        """Fetch a character's mounts.

        Args:
            realm_slug: The realm slug where the character resides.
            char_name: The character name (case-insensitive).

        Returns:
            A dict containing the character mounts data, or an empty dict on failure.
        """
        logger.debug("Fetching character mounts for %s on %s", char_name, realm_slug)

        name = char_name.lower()
        url = self._format_url(
            f"profile/wow/character/{realm_slug}/{name}/collections/mounts"
        )

        return await self._request("GET", url, params=self._profile_params)

    async def get_playable_classes(self) -> list[dict[str, str]]:
        """Fetch all playable classes from the game.

        Returns:
            A list of dicts containing class information, or an empty list on failure.
        """
        logger.debug("Fetching playable classes")
        data = await self._get_static_data("playable-class")

        return data.get("classes", [])

    async def get_playable_races(self) -> list[dict[str, str]]:
        """Fetch all playable races from the game.

        Returns:
            A list of dicts containing race information, or an empty list on failure.
        """
        logger.debug("Fetching playable races")
        data = await self._get_static_data("playable-race")

        return data.get("races", [])

    async def close(self):
        """Close the underlying HTTP client session."""
        logger.debug("Closing HTTP client session")
        await self.client.aclose()
