import asyncio
import logging
import os

import click
from dotenv import load_dotenv

from groster.commands import register_commands, run_bot, update_roster
from groster.constants import SUPPORTED_REGIONS
from groster.logging import setup_logging

logger = logging.getLogger(__name__)


BANNER = r"""

                                      █████
                                     ▒▒███
  ███████ ████████   ██████   █████  ███████    ██████  ████████
 ███▒▒███▒▒███▒▒███ ███▒▒███ ███▒▒  ▒▒▒███▒    ███▒▒███▒▒███▒▒███
▒███ ▒███ ▒███ ▒▒▒ ▒███ ▒███▒▒█████   ▒███    ▒███████  ▒███ ▒▒▒
▒███ ▒███ ▒███     ▒███ ▒███ ▒▒▒▒███  ▒███ ███▒███▒▒▒   ▒███
▒▒███████ █████    ▒▒██████  ██████   ▒▒█████ ▒▒██████  █████
 ▒▒▒▒▒███▒▒▒▒▒      ▒▒▒▒▒▒  ▒▒▒▒▒▒     ▒▒▒▒▒   ▒▒▒▒▒▒  ▒▒▒▒▒
 ███ ▒███
▒▒██████
 ▒▒▒▒▒▒

"""


class RichGroup(click.Group):
    """Custom Click group that displays a banner before the help text."""

    def format_help(self, ctx, formatter):
        """Writes the help into the formatter if it exists.

        This method is called by Click when the help text is requested.
        """
        click.secho(BANNER, nl=False)
        super().format_help(ctx, formatter)


def get_version() -> str:
    """Get version info."""
    from groster import __version__

    return __version__


def get_copyright() -> str:
    """Get copyright info."""
    from groster import __copyright__

    return __copyright__


@click.group(
    cls=RichGroup,
    help="A tool to fetch and process World of Warcraft guild rosters.",
)
@click.version_option(
    version=get_version(),
    prog_name="groster",
    message="%(prog)s %(version)s\n"
    + get_copyright()
    + "\n"
    + "This is free software; see the source for copying conditions.  There is NO\n"
    + "warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug logging, including HTTP request/response details.",
)
@click.pass_context
def cli(ctx: click.Context, debug: bool) -> None:
    """Entrypoint for groster CLI."""
    load_dotenv()
    setup_logging(debug)

    ctx.ensure_object(dict)
    ctx.obj["DEBUG"] = debug


@cli.command()
@click.option(
    "--region",
    default=lambda: os.getenv("WOW_REGION", "eu"),
    type=click.Choice(SUPPORTED_REGIONS),
    show_default=True,
    help="The region for the API request (e.g., 'eu').",
)
@click.option(
    "--realm",
    default=lambda: os.getenv("WOW_REALM"),
    required=os.getenv("WOW_REALM") is None,
    help="The slug of the realm (e.g., 'terokkar').",
)
@click.option(
    "--guild",
    default=lambda: os.getenv("WOW_GUILD"),
    required=os.getenv("WOW_GUILD") is None,
    help="The slug of the guild (e.g., 'darq-side-of-the-moon').",
)
@click.option(
    "--locale",
    default="en_US",
    show_default=True,
    help="The locale for the API request (e.g., 'en_US').",
)
@click.pass_context
def update(
    ctx: click.Context,
    region: str,
    realm: str,
    guild: str,
    locale: str,
) -> None:
    """Fetch and process a WoW guild roster from the Battle.net API."""
    logger.info("Starting update for %s@%s.%s...", guild, realm, region)
    try:
        asyncio.run(update_roster(region, realm, guild, locale))
    except Exception as e:
        logger.exception("Update failed")
        click.echo(f"Update failed: {e}", err=True)


@cli.command()
@click.option(
    "--host",
    default=lambda: os.getenv("GROSTER_HOST", "127.0.0.1"),
    show_default="env: GROSTER_HOST or 127.0.0.1",
    help="Host address for the bot server.",
)
@click.option(
    "--port",
    type=int,
    default=lambda: int(os.getenv("GROSTER_PORT", "5000")),
    show_default="env: GROSTER_PORT or 5000",
    help="Port for the bot server.",
)
def serve(host: str, port: int):
    """Run the Discord bot server."""
    logger.info("Starting server on %s:%d...", host, port)
    try:
        run_bot(host=host, port=port)
    except Exception as e:
        logger.exception("Server failed")
        click.echo(f"Server failed: {e}", err=True)


@cli.command()
@click.option(
    "--app-id",
    default=lambda: os.getenv("DISCORD_APP_ID"),
    required=os.getenv("DISCORD_APP_ID") is None,
    help="The ID of the Discord application.",
)
@click.option(
    "--guild-id",
    default=lambda: os.getenv("DISCORD_GUILD_ID"),
    required=os.getenv("DISCORD_GUILD_ID") is None,
    help="The ID of the Discord guild.",
)
@click.option(
    "--bot-token",
    default=lambda: os.getenv("DISCORD_BOT_TOKEN"),
    required=os.getenv("DISCORD_BOT_TOKEN") is None,
    help="The token of the Discord bot.",
)
def register(app_id: str, guild_id: str, bot_token: str):
    """Register Discord commands."""
    logger.info("Registering Discord commands...")
    try:
        asyncio.run(register_commands(app_id, guild_id, bot_token))
    except Exception as e:
        logger.exception("Commands failed")
        click.echo(f"Commands failed: {e}", err=True)


def main(args: list[str] | None = None) -> int:
    try:
        cli.main(args=args, standalone_mode=False)
        return 0
    except click.exceptions.NoSuchOption:
        # Handle case where no option is provided
        click.echo("No such option. Use --help for more information.", err=True)
        return 2
    except click.exceptions.Abort:
        # Handle keyboard interrupts gracefully
        click.echo("Operation aborted by user")
        return 130  # Standard exit code for SIGINT
    except click.exceptions.Exit as e:
        # Handle normal exit
        return e.exit_code
    except Exception as exc:  # pylint: disable=broad-exception-caught
        # Handle unexpected errors
        logger.error(exc, exc_info=True)
        return 1
