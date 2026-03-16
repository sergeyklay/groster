import difflib
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from aiohttp import web
from dotenv import load_dotenv
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

from groster.repository import CsvRosterRepository, RosterRepository

load_dotenv()

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
    suggestions: list[str] | None = None,
) -> str:
    """Build a 'character not found' message for Discord."""
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

    suggestion_message = ""
    if suggestions:
        names = ", ".join(f"**{name}**" for name in suggestions)
        suggestion_message = f"\nDid you mean: {names}?"

    return (
        f"{mention}character **{character_name}** not found in guild roster. "
        "Please check the character name and try again. "
        "If the character name is correct, please contact the server administrator."
        f"{modified_message}{suggestion_message}"
    )


def format_character_info(
    char_info: dict[str, Any] | None,
    character_name: str,
    modified_at: datetime | None,
    user_id: str | None,
    region: str = "eu",
) -> str:
    """Format character information for a Discord message.

    Args:
        char_info: Character data dict, or None if not found.
        character_name: The name the user searched for.
        modified_at: Last roster update timestamp.
        user_id: Discord user ID for mention, or None.
        region: Game region identifier (e.g., 'eu', 'us').

    Returns:
        Formatted string ready to send as Discord message content.
    """
    if not char_info:
        return _format_no_character_message(
            character_name,
            modified_at,
            user_id,
        )

    region_tag = region.upper()

    # Format main character
    main_emoji = get_class_emoji(char_info["class"])
    response = "**Main:**\n"
    response += f"{main_emoji} **{char_info['name']}** — {char_info['class']}\n"
    response += f"Realm: {char_info['realm']} ({region_tag})\n"
    response += f"iLvl: {char_info['ilvl']}\n"
    response += f"Last Login: {char_info['last_login']}\n"

    # Format alts if any
    if char_info.get("alts"):
        response += "\n**Alts:**\n"
        for alt in char_info["alts"]:
            alt_emoji = get_class_emoji(alt["class"])
            response += f"{alt_emoji} **{alt['name']}** — {alt['class']}\n"
            response += f"Realm: {alt['realm']} ({region_tag})\n"
            response += f"iLvl: {alt['ilvl']}\n"
            response += f"Last Login: {alt['last_login']}\n\n"

    return response.strip()


def _utf16_len(s: str) -> int:
    """Return string length as counted by Discord (UTF-16 code units)."""
    return len(s.encode("utf-16-le")) // 2


def format_alts_embed(
    alts_data: list[tuple[str, str, int]],
) -> dict[str, Any]:
    """Build a Discord embed dict for the /alts response.

    Args:
        alts_data: List of (main_name, class_name, alt_count) tuples.

    Returns:
        Embed dict with title, description, footer, and color.
    """
    # Discord documents 4096 but the exact counting method is unspecified.
    # 3900 leaves headroom for encoding differences (emoji surrogate pairs).
    max_description = 3900
    total_mains = len(alts_data)
    total_alts = sum(c for _, _, c in alts_data)
    total_characters = total_mains + total_alts

    description = ""
    for i, (main_name, class_name, alt_count) in enumerate(alts_data):
        emoji = get_class_emoji(class_name)
        label = "alt" if alt_count == 1 else "alts"
        line = f"{emoji} **{main_name}** \u2014 {alt_count} {label}\n"
        remaining = total_mains - i
        suffix = f"\n\u2026 and {remaining} more mains"
        if len(description) + len(line) + len(suffix) > max_description:
            description += suffix
            break
        description += line

    footer_text = (
        f"{total_mains} mains \u00b7 {total_alts} alts"
        f" \u00b7 {total_characters} total characters"
    )

    return {
        "title": "Guild Alt Summary",
        "description": description,
        "color": 0x00AAFF,
        "footer": {"text": footer_text},
    }


async def _handle_alts(
    repo: RosterRepository,
    region: str,
    realm: str,
    guild: str,
) -> web.Response:
    """Handle the /alts slash command.

    Args:
        repo: Repository instance for data lookup.
        region: Bot region.
        realm: Bot realm.
        guild: Bot guild.

    Returns:
        aiohttp JSON response with type 4 containing alt summary embed.
    """
    try:
        alts_data = await repo.get_alts_per_main(region, realm, guild)

        if alts_data is None:
            return web.json_response(
                {
                    "type": 4,
                    "data": {
                        "content": (
                            "Guild roster data is not available yet. "
                            "Please ask the server administrator "
                            "to run a roster update."
                        ),
                        "flags": 64,
                    },
                }
            )

        embed = format_alts_embed(alts_data)
        return web.json_response(
            {
                "type": 4,
                "data": {
                    "embeds": [embed],
                    "flags": 64,
                },
            }
        )
    except Exception:
        logger.exception("Error retrieving alt summary")
        return web.json_response(
            {
                "type": 4,
                "data": {
                    "content": ("An error occurred while retrieving the alt summary."),
                    "flags": 64,
                },
            }
        )


async def _handle_autocomplete(
    data: dict[str, Any],
    repo: RosterRepository,
    region: str,
    realm: str,
    guild: str,
) -> web.Response:
    """Handle Discord autocomplete interaction (type 4).

    Args:
        data: Parsed interaction JSON body.
        repo: Repository instance for name lookup.
        region: Bot region.
        realm: Bot realm.
        guild: Bot guild.

    Returns:
        aiohttp JSON response with type 8 and choices array.
    """
    options = data.get("data", {}).get("options", [])
    focused_value = ""
    for option in options:
        if option.get("focused"):
            focused_value = option.get("value", "")
            break

    logger.debug("Autocomplete focused value: %s", focused_value)

    names = await repo.search_character_names(focused_value, region, realm, guild)
    choices = [{"name": name[:100], "value": name} for name in names]
    return web.json_response({"type": 8, "data": {"choices": choices}})


async def _handle_whois(
    data: dict[str, Any],
    repo: RosterRepository,
    region: str,
    realm: str,
    guild: str,
    user_id: str | None,
) -> web.Response:
    """Handle the /whois slash command.

    Args:
        data: Parsed interaction JSON body.
        repo: Repository instance for character lookup.
        region: Bot region.
        realm: Bot realm.
        guild: Bot guild.
        user_id: Discord user ID for mention, or None.

    Returns:
        aiohttp JSON response with type 4 containing character info.
    """
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
            character_name, region, realm, guild
        )

        if not char_info:
            all_names = await repo.search_character_names(
                "", region, realm, guild, limit=200
            )
            lower_names = [n.lower() for n in all_names]
            lower_matches = difflib.get_close_matches(
                character_name.lower(), lower_names, n=3, cutoff=0.6
            )
            suggestions = [all_names[lower_names.index(m)] for m in lower_matches]
            return web.json_response(
                {
                    "type": 4,
                    "data": {
                        "content": _format_no_character_message(
                            character_name,
                            modified_at,
                            user_id,
                            suggestions=suggestions,
                        )
                    },
                }
            )

        response_content = format_character_info(
            char_info,
            character_name,
            modified_at,
            user_id,
            region=region,
        )

        return web.json_response(
            {
                "type": 4,
                "data": {"content": response_content},
            }
        )
    except Exception:
        logger.exception("Error getting character info")
        error_message = "An error occurred while retrieving character information."
        return web.json_response(
            {
                "type": 4,
                "data": {"content": error_message},
            }
        )


async def interactions_handler(request: web.Request):
    signature = request.headers.get("X-Signature-Ed25519")
    timestamp = request.headers.get("X-Signature-Timestamp")

    if not signature or not timestamp:
        return web.Response(text="Missing headers", status=401)

    body = await request.read()

    try:
        request.app["verify_key"].verify(
            timestamp.encode() + body,
            bytes.fromhex(signature),
        )
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
            return await _handle_whois(
                data,
                request.app["repo"],
                request.app["bot_region"],
                request.app["bot_realm"],
                request.app["bot_guild"],
                user_id,
            )
        if command_name == "alts":
            return await _handle_alts(
                request.app["repo"],
                request.app["bot_region"],
                request.app["bot_realm"],
                request.app["bot_guild"],
            )

    # Autocomplete
    if interaction_type == 4:
        logger.info("Received autocomplete interaction")
        return await _handle_autocomplete(
            data,
            request.app["repo"],
            request.app["bot_region"],
            request.app["bot_realm"],
            request.app["bot_guild"],
        )

    return web.Response(text="Unhandled interaction type", status=400)


def _create_app() -> web.Application:
    """Create and configure the aiohttp application.

    Reads configuration from environment variables and validates
    that required values are present.

    Raises:
        ValueError: If DISCORD_PUBLIC_KEY is not set.
    """
    public_key = os.getenv("DISCORD_PUBLIC_KEY")
    if not public_key:
        raise ValueError("DISCORD_PUBLIC_KEY not found in environment variables")

    base_path = Path(
        os.getenv("GROSTER_DATA_PATH", Path.cwd() / "data"),
    )

    app = web.Application()
    app["verify_key"] = VerifyKey(bytes.fromhex(public_key))
    app["repo"] = CsvRosterRepository(base_path=base_path)
    app["bot_region"] = os.getenv("WOW_REGION", "eu")
    app["bot_realm"] = os.getenv("WOW_REALM", "terokkar")
    app["bot_guild"] = os.getenv(
        "WOW_GUILD",
        "darq-side-of-the-moon",
    )
    app.router.add_post("/api/interactions", interactions_handler)
    return app


def run_bot(host: str, port: int) -> None:
    """Main entry point for the bot application."""
    app = _create_app()

    logger.info("Starting aiohttp server on http://%s:%d", host, port)
    web.run_app(app, host=host, port=port)
