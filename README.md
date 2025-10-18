# groster

A tool for fetching and processing a World of Warcraft guild roster via the official Blizzard API. Its primary feature is to identify and group alternate characters (_alts_) with their main characters based on shared account-wide data.

## Problem Statement

The standard guild roster from the Blizzard presents a flat list of characters without indicating which ones belong to the same player. Manually tracking mains and alts is tedious and error-prone, making it difficult to understand the true size and composition of a guild's player base.

This tool automates the process by programmatically analyzing character data to uncover these player-character relationships, providing a clear and accurate overview of the guild roster.

## Technology Stack

- Language: Python 3.12+
- Data Processing: [pandas](https://pandas.pydata.org) - Data processing, analysis and manipulation
- HTTP Requests: [httpx](https://www.python-httpx.org) - For all interactions with the Blizzard Battle.net REST API
- Configuration: [python-dotenv](https://pypi.org/project/python-dotenv/) - For managing API credentials securely
- Linting: [ruff](https://docs.astral.sh/ruff/) - As an all-in-one tool for code linting and formatting, ensuring high code quality
- Dependency Management: [uv](https://docs.astral.sh/uv/) - The project's required tool for Python dependency management.

## Documentation

- [Coding Standards](./docs/coding-standards.md) - The project's coding standards and guidelines.
- [Contributing](./CONTRIBUTING.md) - The project's contributing guidelines.

## License

This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for details.
