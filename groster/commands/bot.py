import json
import logging
import os
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

from aiohttp import web
from dotenv import load_dotenv
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

from groster.repository import CsvRosterRepository, RosterRepository

load_dotenv()

PUBLIC_KEY = os.getenv("DISCORD_PUBLIC_KEY")
if not PUBLIC_KEY:
    raise ValueError("DISCORD_PUBLIC_KEY not found in environment variables")
verify_key = VerifyKey(bytes.fromhex(PUBLIC_KEY))


BOT_REGION = os.getenv("WOW_REGION", "eu")
BOT_REALM = os.getenv("WOW_REALM", "terokkar")
BOT_GUILD = os.getenv("WOW_GUILD", "darq-side-of-the-moon")

base_path = Path(os.getenv("GROSTER_DATA_PATH", Path.cwd() / "data"))
repo: RosterRepository = CsvRosterRepository(base_path=base_path)

logger = logging.getLogger(__name__)


def get_class_emoji(class_name: str) -> str:
    """Get emoji for class names."""
    class_emojis = {
        "Death Knight": "💀",
        "Demon Hunter": "😈",
        "Druid": "🌿",
        "Evoker": "🐉",
        "Hunter": "🏹",
        "Mage": "🧙",
        "Monk": "🥋",
        "Paladin": "⚔️",
        "Priest": "🩸",
        "Rogue": "🗡️",
        "Shaman": "⚡",
        "Warlock": "🔥",
        "Warrior": "🛡️",
    }
    return class_emojis.get(class_name, "⚔️")


def _format_no_character_message(
    character_name: str,
    modified_at: datetime | None,
    user_id: str | None,
) -> str:
    mention = f"<@{user_id}>, " if user_id else ""
    if modified_at:
        formatted_date = modified_at.strftime("%Y-%m-%d %H:%M:%S")
        modified_message = f" Last date of guild roster update was {formatted_date}."

        # Check if last date of roster update was more that 1 day ago
        if modified_at < datetime.now() - timedelta(days=1):
            modified_message += (
                " The guild roster is outdated. Please contact the server "
                "administrator to update the guild roster."
            )
    else:
        modified_message = ""
    return (
        f"{mention}character **{character_name}** not found in guild roster. "
        "Please check the character name and try again. "
        "If the character name is correct, please contact the server administrator."
        f"{modified_message}"
    )


def format_character_info(
    char_info: dict[str, Any],
    character_name: str,
    modified_at: datetime | None,
    user_id: str | None,
) -> str:
    """Format character information for Discord."""
    if not char_info:
        return _format_no_character_message(character_name, modified_at, user_id)

    # Format main character
    main_emoji = get_class_emoji(char_info["class"])
    response = "**Main:**\n"
    response += f"{main_emoji} **{char_info['name']}** — {char_info['class']}\n"
    response += f"Realm: {char_info['realm']} (EU)\n"
    response += f"iLvl: {char_info['ilvl']}\n"
    response += f"Last Login: {char_info['last_login']}\n"

    # Format alts if any
    if char_info.get("alts"):
        response += "\n**Alts:**\n"
        for alt in char_info["alts"]:
            alt_emoji = get_class_emoji(alt["class"])
            response += f"{alt_emoji} **{alt['name']}** — {alt['class']}\n"
            response += f"Realm: {alt['realm']} (EU)\n"
            response += f"iLvl: {alt['ilvl']}\n"
            response += f"Last Login: {alt['last_login']}\n\n"

    return response.strip()


async def interactions_handler(request: web.Request):
    signature = request.headers.get("X-Signature-Ed25519")
    timestamp = request.headers.get("X-Signature-Timestamp")

    if not signature or not timestamp:
        return web.Response(text="Missing headers", status=401)

    body = await request.read()

    try:
        verify_key.verify(timestamp.encode() + body, bytes.fromhex(signature))
    except BadSignatureError:
        logger.warning("Invalid request signature")
        return web.Response(text="Invalid request signature", status=401)

    data = json.loads(body)

    interaction_type = data.get("type")
    invoking_user = data.get("member", {}).get("user", {})
    user_id = invoking_user.get("id", 0)

    logger.info("Invoking user: %s (%s)", invoking_user.get("global_name"), user_id)

    # Discord PING
    if interaction_type == 1:
        logger.info("Received PING from Discord, responding with PONG.")
        return web.json_response({"type": 1})

    # Command
    if interaction_type == 2:
        command_name = data.get("data", {}).get("name")
        logger.info("Received command: /%s", command_name)

        if command_name == "ping":
            return web.json_response(
                {
                    "type": 4,
                    "data": {"content": "pong"},
                }
            )
        if command_name == "whois":
            character_name = data.get("data", {}).get("options", [{}])[0].get("value")
            logger.info("Received character name: %s", character_name)

            if not character_name:
                logger.warning("No character name provided")
                return web.json_response(
                    {
                        "type": 4,
                        "data": {"content": "Please provide a character name."},
                    }
                )

            try:
                char_info, modified_at = await repo.get_character_info_by_name(
                    character_name, BOT_REGION, BOT_REALM, BOT_GUILD
                )

                if not char_info:
                    return web.json_response(
                        {
                            "type": 4,
                            "data": {
                                "content": _format_no_character_message(
                                    character_name,
                                    modified_at,
                                    user_id,
                                )
                            },
                        }
                    )

                response_content = format_character_info(
                    char_info, character_name, modified_at, user_id
                )

                return web.json_response(
                    {
                        "type": 4,
                        "data": {"content": response_content},
                    }
                )
            except Exception:
                logger.exception("Error getting character info")
                error_message = (
                    "An error occurred while retrieving character information."
                )
                return web.json_response(
                    {
                        "type": 4,
                        "data": {"content": error_message},
                    }
                )

    return web.Response(text="Unhandled interaction type", status=400)


@lru_cache(maxsize=1)
def _create_app() -> web.Application:
    """Create aiohttp application."""
    app = web.Application()
    app.router.add_post("/api/interactions", interactions_handler)
    return app


def run_bot(host: str, port: int) -> None:
    """Main entry point for the bot application."""

    app = _create_app()

    logger.info("Starting aiohttp server on http://%s:%d", host, port)
    web.run_app(app, host=host, port=port)
