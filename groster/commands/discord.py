import logging

import httpx

from groster.http_client import DEFAULT_USER_AGENT

logger = logging.getLogger(__name__)


async def register_commands(
    app_id: str,
    guild_id: str,
    bot_token: str,
    max_retries: int = 5,
    timeout: int = 10,
):
    """Register Discord commands."""
    logger.info("Registering Discord commands...")

    try:
        url = f"https://discord.com/api/v10/applications/{app_id}/guilds/{guild_id}/commands"

        payload = {
            "name": "whois",
            "description": "Get information about a player.",
            "options": [
                {
                    "name": "player",
                    "description": "The player to get information about.",
                    "type": 3,
                    "required": True,
                }
            ],
            "type": 1,
        }

        headers = {"Authorization": f"Bot {bot_token}"}

        transport = httpx.AsyncHTTPTransport(retries=max_retries)
        client = httpx.AsyncClient(
            transport=transport,
            timeout=timeout,
            headers={
                "User-Agent": DEFAULT_USER_AGENT,
                "Accept": "application/json",
            },
        )

        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        logger.info("Discord commands registered successfully")
        logger.debug("Response: %s", response.json())

        return response.json()
    except httpx.HTTPError as e:
        logger.exception("Failed to register Discord commands")
        raise RuntimeError("Failed to register Discord commands") from e
