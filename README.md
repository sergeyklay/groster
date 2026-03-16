# groster

[![CI](https://github.com/sergeyklay/groster/actions/workflows/ci.yml/badge.svg)](https://github.com/sergeyklay/groster/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/sergeyklay/groster/graph/badge.svg?token=t2SlaQow9Z)](https://codecov.io/gh/sergeyklay/groster)

CLI and Discord bot for World of Warcraft guild management. Fetches guild rosters via the Blizzard API, identifies alternate characters through achievement fingerprinting, and exposes the results through interactive Discord slash commands (`/whois`, `/alts`) and local CSV reports.

## Problem Statement

The Blizzard guild roster is a flat list of characters with no indication of which ones belong to the same player. Manually tracking mains and alts is tedious and error-prone, making it hard to understand the true size, composition, and activity of a guild.

groster automates this by analyzing account-wide achievement timestamps to group characters by player, then delivers the results where guild officers need them — directly in Discord.

## Technology Stack

- Language: Python 3.12+
- Data Processing: [pandas](https://pandas.pydata.org) — DataFrame merges for dashboard generation and CSV I/O
- HTTP Client: [httpx](https://www.python-httpx.org) — async Blizzard Battle.net API integration with OAuth 2.0
- Discord Bot: [aiohttp](https://docs.aiohttp.org) — lightweight webhook server with Ed25519 signature verification
- Configuration: [python-dotenv](https://pypi.org/project/python-dotenv/) — secure API credential management
- Linting: [ruff](https://docs.astral.sh/ruff/) — formatting, linting, and import sorting in one tool
- Dependency Management: [uv](https://docs.astral.sh/uv/) — fast, lockfile-based dependency resolution

## Documentation

- [Architecture](./docs/architecture.md) - Overview of the project's architecture and design decisions.
- [Getting Started (Localhost)](./docs/getting-started-localhost.md) - Guide for running groster locally with a Discord bot.
- [Docker](./docs/docker.md) - Running groster with Docker and Docker Compose.
- [Deploying a Local Server](./docs/deploy-local-server.md) - Guide for deploying groster on a local server with Cloudflare Tunnel and systemd.
- [Sending groster Logs to Grafana via Loki](./docs/logging-grafana-loki.md) - Instructions for configuring groster to send structured logs to Grafana Loki for monitoring and analysis.
- [Contributing](./CONTRIBUTING.md) - The project's contributing guidelines.

## License

This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for details.
