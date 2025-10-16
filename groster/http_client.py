import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# TODO: Use project version from pyproject.toml
DEFAULT_USER_AGENT = "groster/0.3.0"
"""Default user agent for the Blizzard API."""


class BlizzardAPIClient:
    """A HTTP client for the Blizzard Battle.net API."""

    def __init__(
        self,
        region: str,
        client_id: str,
        client_secret: str,
        locale: str = "en_US",
        timeout: int = 10,
        max_retries: int = 3,
    ):
        if not all([region, client_id, client_secret]):
            raise ValueError("Region, client ID, and client secret must be provided")

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

        transport = httpx.AsyncHTTPTransport(
            retries=max_retries,
        )

        self.client = httpx.AsyncClient(
            transport=transport,
            timeout=timeout,
            headers={"User-Agent": DEFAULT_USER_AGENT},
        )

    def _format_url(self, path: str) -> str:
        """Formats the URL for the Blizzard Battle.net API."""
        path = path.lstrip("/")
        return f"https://{self.region}.api.blizzard.com/{path}"

    async def _get_access_token(self) -> str:
        """Fetche or renews the OAuth access token."""
        if self._api_token and time.time() < self._token_expires_at:
            return self._api_token

        url = "https://oauth.battle.net/token"
        data = {"grant_type": "client_credentials"}
        auth = (self.client_id, self.client_secret)

        logger.info("Requesting new access token from Battle.net")
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

            logger.info("Access token successfully obtained")
            return self._api_token
        except httpx.HTTPError as e:
            logger.error("Failed to obtain access token: %s", e)
            raise

    async def _request(self, method: str, url: str, **kwargs) -> dict[str, Any]:
        """Make a HTTP request to the Blizzard API."""
        token = await self._get_access_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"

        try:
            response = await self.client.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.warning(
                "API request to %s failed with status %d: %s",
                e.request.url,
                e.response.status_code,
                e.response.text,
            )
        except httpx.RequestError as e:
            logger.warning("API request to %s failed: %s", e.request.url, e)

        return {}  # Return empty dict on failure

    async def _get_static_data(self, data_key: str) -> dict:
        logger.info("Fetching %s data ...", data_key)

        path = f"data/wow/{data_key}/index"
        url = self._format_url(path)
        return await self._request("GET", url, params=self._static_params)

    async def get_guild_roster(self, realm_slug: str, guild_slug: str) -> dict:
        logger.info("Fetching guild roster ...")
        url = self._format_url(f"data/wow/guild/{realm_slug}/{guild_slug}/roster")

        return await self._request("GET", url, params=self._profile_params)

    async def get_character_profile(self, realm_slug: str, char_name: str) -> dict:
        logger.info("Fetching character profile ...")

        name = char_name.lower()
        url = self._format_url(f"profile/wow/character/{realm_slug}/{name}")

        return await self._request("GET", url, params=self._profile_params)

    async def get_character_achievements(self, realm_slug: str, char_name: str) -> dict:
        logger.info("Fetching character achievements ...")

        name = char_name.lower()
        url = self._format_url(
            f"profile/wow/character/{realm_slug}/{name}/achievements"
        )

        return await self._request("GET", url, params=self._profile_params)

    async def get_playable_classes(self) -> dict:
        logger.info("Fetching playable classes ...")

        data = await self._get_static_data("playable-class")

        return data.get("classes", {})

    async def get_playable_races(self) -> dict:
        logger.info("Fetching playable races ...")

        data = await self._get_static_data("playable-race")

        return data.get("races", {})

    async def close(self):
        """Close the underlying HTTP client session."""
        logger.debug("Closing HTTP client session ...")
        await self.client.aclose()
