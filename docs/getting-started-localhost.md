# Running groster locally with a Discord bot

This guide walks you through the full process of running groster on your local machine, exposing it to the internet with Cloudflare Tunnel, and connecting it to Discord so your guild can use the `/whois` command. By the end, you'll have a working Discord bot that looks up WoW characters and shows their main/alt relationships.

> **Prefer Docker?** If you want to run groster in a container instead of installing Python locally, see the [Docker guide](docker.md). The rest of this guide covers the local development setup.

## What you'll need

Before you start, make sure you have:

- **Python 3.12+** installed (groster uses `asdf` for version management; the pinned version lives in `.tool-versions`)
- **uv** installed as the Python package manager ([installation guide](https://docs.astral.sh/uv/getting-started/installation/))
- A **Blizzard Battle.net developer account** with a client ID and secret ([developer portal](https://develop.battle.net/))
- A **Discord developer account** with an application and bot token ([developer portal](https://discord.com/developers/applications))
- `cloudflared` installed on your machine (covered below)

## Step 1: clone the repository and install dependencies

Start by cloning the repository and installing all project dependencies:

```bash
git clone https://github.com/sergeyklay/groster.git
cd groster
uv sync --locked --all-packages --all-groups
```

The `uv sync --locked` command reads from the lockfile and installs the exact dependency versions the project was tested against. Don't use `pip install` or `uv pip install` here; the lockfile is the source of truth for dependency resolution.

If you're using `asdf` for Python version management, run `asdf reshim python` after fresh installs or version changes.

## Step 2: configure environment variables

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Open `.env` in your editor and add the following values:

```ini
BLIZZARD_CLIENT_ID="your-blizzard-client-id"
BLIZZARD_CLIENT_SECRET="your-blizzard-client-secret"

DISCORD_APP_ID="your-discord-application-id"
DISCORD_PUBLIC_KEY="your-discord-public-key"
DISCORD_BOT_TOKEN="your-discord-bot-token"
DISCORD_GUILD_ID="your-discord-server-id"

WOW_REGION="eu"
WOW_REALM="terokkar"
WOW_GUILD="darq-side-of-the-moon"
```

Where to find each value:

- **Blizzard credentials**: go to the [Blizzard Developer Portal](https://develop.battle.net/), create or select your API client, and copy the Client ID and Client Secret.
- **Discord application ID and public key**: go to the [Discord Developer Portal](https://discord.com/developers/applications), select your application, and look at the "General Information" page. The Application ID and Public Key are both listed there.
- **Discord bot token**: in the same portal, go to the "Bot" section of your application and click "Reset Token" to generate a new one. Copy it immediately because Discord only shows it once.
- **Discord guild (server) ID**: enable Developer Mode in Discord (Settings > App Settings > Advanced > Developer Mode). Then right-click your server name in the sidebar and select "Copy Server ID".
- **WoW settings**: adjust `WOW_REGION`, `WOW_REALM`, and `WOW_GUILD` to match your guild. Use slug format for realm and guild names (lowercase, hyphens instead of spaces).

## Step 3: fetch the guild roster

Before the bot can answer questions, it needs roster data. Run the update command:

```bash
uv run --frozen groster update
```

This contacts the Blizzard API, downloads your guild's roster and achievement data, processes alt relationships, and writes CSV files into the `data/` directory. The process can take a few minutes depending on guild size because it fetches individual character profiles and achievements.

You can also pass options directly instead of relying on environment variables:

```bash
uv run --frozen groster update --region eu --realm terokkar --guild darq-side-of-the-moon
```

After the update finishes, you should see several CSV files in `data/`:

```bash
ls data/
```

The dashboard CSV contains the consolidated view with all character information, alt groupings, and profile links.

## Step 4: start the bot server

Launch the bot's HTTP server:

```bash
uv run --frozen groster serve
```

By default, the server binds to `127.0.0.1:5000`. You can change the host and port:

```bash
uv run --frozen groster serve --host 0.0.0.0 --port 8080
```

The server exposes a single endpoint at `POST /api/interactions` that handles Discord's interaction webhook requests. Leave this terminal running; you'll need it for the next steps.

## Step 5: install `cloudflared` and expose your local server

Discord needs to reach your bot over the public internet. Since you're running locally, you need a tunnel that forwards public HTTPS traffic to your local server. Cloudflare Tunnel does this with a single command, no account required for quick tunnels.

### Installing `cloudflared`

**Linux (Debian/Ubuntu):**

```bash
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb
```

**macOS:**

```bash
brew install cloudflared
```

**Windows:**

```powershell
winget install --id Cloudflare.cloudflared
```

Verify the installation:

```bash
cloudflared --version
```

### Starting a quick tunnel

Open a second terminal (keep the bot server running in the first one) and run:

```bash
cloudflared tunnel --url http://localhost:5000
```

The port in this command **must match** the port your bot server is running on. If you started the server on a different port (for example, `--port 8888`), use that same port here:

```bash
cloudflared tunnel --url http://localhost:8888
```

A mismatched port is the most common cause of `502 Bad Gateway` errors from the tunnel.

After a few seconds, `cloudflared` prints a public URL that looks like this:

```
https://random-words-here.trycloudflare.com
```

Copy this URL. You'll paste it into Discord in the next step.

Quick tunnels are free and require no Cloudflare account. They generate a new random subdomain each time you restart `cloudflared`. That means you'll need to update the Discord endpoint URL every time you restart the tunnel. For persistent tunnels with a stable domain, see the [Cloudflare Tunnel documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/create-local-tunnel/).

## Step 6: configure the Discord interactions endpoint URL

Now you need to tell Discord where to send interaction events (slash command invocations) for your bot.

1. Open the [Discord Developer Portal](https://discord.com/developers/applications).
2. Select your application from the list.
3. Click **General Information** in the left sidebar.
4. Find the **Interactions Endpoint URL** field.
5. Paste your full tunnel URL with the API path appended:

   ```
   https://random-words-here.trycloudflare.com/api/interactions
   ```

6. Click **Save Changes**.

When you save, Discord sends a `PING` request to your endpoint. Your bot must be running and reachable through the tunnel for this to succeed. If the save fails, check that:

- The bot server is running (`uv run --frozen groster serve`).
- The `cloudflared` tunnel is active and pointing to the correct local port. If you started the server with `--port 8888`, the tunnel command should use `http://localhost:8888` too.
- The URL ends with `/api/interactions` (not the base domain alone).
- The `DISCORD_PUBLIC_KEY` in your `.env` matches the Public Key shown on the General Information page.

Once saved, Discord confirms the endpoint is valid. Your bot is now connected.

## Step 7: register the slash command

The bot needs to register its `/whois` slash command with Discord. Run this once (or whenever you change the command definition):

```bash
uv run --frozen groster register
```

This sends a request to the Discord API to create the `/whois` command in your server. After registration, the command appears in the Discord command picker within a few minutes. Guild-scoped commands can take up to an hour to propagate.

## Step 8: test the bot in Discord

Open Discord, navigate to a channel in your server, and type:

```
/whois player:CharacterName
```

Replace `CharacterName` with an actual character name from your guild roster. The bot responds with the character's information: class, realm, item level, last login date, and a list of alts if any were detected.

If the character isn't found, the bot tells you so and shows when the roster was last updated.

A note on testing: don't try to open the tunnel URL in a browser or send a `GET` request to it. The `/api/interactions` endpoint only accepts `POST` requests with Discord's specific payload format. A browser visit returns an error; that's expected. The way to test is through the `/whois` command inside Discord.

## Common commands reference

| Command                            | What it does                                         |
| ---------------------------------- | ---------------------------------------------------- |
| `uv run --frozen groster update`   | Fetch and process the guild roster from Blizzard API |
| `uv run --frozen groster serve`    | Start the Discord bot HTTP server                    |
| `uv run --frozen groster register` | Register slash commands with Discord                 |
| `make test`                        | Run all tests with coverage                          |
| `make format`                      | Format source code                                   |
| `make lint`                        | Run linters                                          |
| `make format lint test`            | Full quality gate (run before commits)               |

## Troubleshooting

### "DISCORD_PUBLIC_KEY not found in environment variables"

The bot reads `DISCORD_PUBLIC_KEY` at import time. Make sure your `.env` file exists in the project root and contains the correct value. If you're running from a different directory, set the variable in your shell before running the command.

### Discord says "Interaction failed"

Check the terminal where `groster serve` is running. The server logs every incoming request and any errors. Common causes:

- The roster data hasn't been fetched yet. Run `uv run --frozen groster update` first.
- The `cloudflared` tunnel URL has changed (happens on restart). Update the Interactions Endpoint URL in the Discord Developer Portal.
- The character name has a typo or doesn't exist in the guild roster.

### `cloudflared` tunnel URL changed

Quick tunnels generate a new URL every time you restart `cloudflared`. After restarting, copy the new URL and update the Interactions Endpoint URL in the Discord Developer Portal. Append `/api/interactions` to the new URL.

### Roster data is outdated

Run `uv run --frozen groster update` again to pull fresh data from the Blizzard API. The bot uses CSV files in `data/`, and those files only update when you run this command.

### Debug mode

Pass `--debug` to get detailed HTTP request/response logs:

```bash
uv run --frozen groster --debug serve
uv run --frozen groster --debug update
```

This is helpful when diagnosing Blizzard API authentication issues or Discord webhook problems.
