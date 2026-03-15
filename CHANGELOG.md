# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] - Unreleased

### Added

- `InMemoryRosterRepository` for isolated unit testing without filesystem I/O.
- `seed_dashboard()` test helper on `InMemoryRosterRepository`.
- `in_memory_repo` pytest fixture in `tests/conftest.py`.
- `pytest-asyncio` test dependency with `asyncio_mode = "auto"`.
- Pull request template.
- Agentic framework: agent modes, coding instructions, prompts, and workflow skills.

### Changed

- Dependabot schedule changed from daily to weekly with labels.
- Updated CODEOWNERS.

## [0.5.0] - 2026-03-12

### Added

- Docker support: Dockerfile, `.dockerignore`, and image build CI test.
- Deployment guide for running groster on a local server.
- Grafana integration guide for sending logs via Loki.
- Discord bot command for interactive guild roster queries.
- `format_no_character_message()` helper for consistent user-facing messages.
- Getting started documentation.
- Missing achievements data file.

### Changed

- Restructured project layout and moved CSV repository into the `groster` package.
- Reworked `identify_alts()`, `fetch_roster_details()`, and profile link generation.
- Reworked constants and static data management.
- Refactored `bot.py` to streamline environment variable handling and application configuration.
- Refactored `register_commands` to use async context manager for HTTP client.
- Refactored `build_profile_links` to use locale mapping.
- Refactored character message formatting for clarity.
- Replaced `print()` calls in `summary_report` with `logging`.
- Reduced logging verbosity across multiple modules.
- Updated architecture diagram for accuracy.
- Bumped pandas to 3.0.x, pytest to 9.0.x, and other dependencies.

### Fixed

- Raise an error when unable to create a dashboard instead of silently failing.
- Fixed service name in image build test.
- Corrected coverage configuration.
- Corrected package namespace after restructuring.

## [0.4.0] - 2025-10-19

### Added

- CI workflow with GitHub Actions (lint, test, coverage via Codecov).
- Dependabot configuration for automated dependency updates.
- CODEOWNERS file.
- Auto-approve workflow for Dependabot PRs.

### Changed

- Prepared package for release distribution.
- Removed extra and debug dependencies.
- Reformatted codebase and removed code duplication.

## [0.3.0] - 2025-10-17

### Added

- Async Blizzard API client with `aiohttp`, replacing synchronous `requests`.
- `get_character_pets()` and `get_character_mounts()` API methods.
- Region-based host mappings and validation for Blizzard API.
- Rate-limit handling with backoff for 429/5xx responses.
- Data models layer.
- `data_path()` utility function for consistent file path resolution.
- Context manager support for the API client.
- Testing infrastructure with unit tests for client, services, and fingerprinting.
- Contributing guide, authors, and maintainers metadata.
- Coderabbit configuration for automated code review.

### Changed

- Migrated to fully asynchronous I/O for all API interactions.
- Improved error handling across file I/O, API calls, and concurrent operations.
- Added type hints to function arguments and return types throughout.
- Expanded docstrings for public API.
- Reduced verbose logging.

### Fixed

- Fixed `coroutine 'main' was never awaited` bug after async migration.
- Fixed inconsistent return types in API client methods.
- Fixed incorrect multi-variable assignment syntax.
- Fixed type safety issues and empty argument handling.
- Fail fast with a clear message when API credentials are missing.

### Removed

- Unused `requests` dependency.

## [0.2.0] - 2025-10-15

### Added

- Summary report generation for guild roster output.
- Character profile fetching and improved roster processing.
- Jaccard similarity threshold constant for alt detection tuning.

### Changed

- Refined alt identification logic using Jaccard similarity for better accuracy.
- Improved guild argument handling in CLI.

### Fixed

- Fixed UTC conversion before applying target timezone.
- Fixed output directory not created before write.
- Guarded against `None` values and removed unnecessary `int()` cast.
- Fixed variable name typo in alt calculation.
- Fixed exception handling and improved error logging.

## [0.1.0] - 2025-10-14

### Added

- Initial release.
- CLI tool to fetch WoW guild rosters via the Blizzard API.
- Achievement-based alt detection through fingerprinting.
- HTML dashboard generation.
- Region parameterization.
- `.env` support for API credentials.

[0.6.0]: https://github.com/sergeyklay/groster/compare/0.5.0...HEAD
[0.5.0]: https://github.com/sergeyklay/groster/compare/0.4.0...0.5.0
[0.4.0]: https://github.com/sergeyklay/groster/compare/0.3.0...0.4.0
[0.3.0]: https://github.com/sergeyklay/groster/compare/0.2.0...0.3.0
[0.2.0]: https://github.com/sergeyklay/groster/compare/0.1.0...0.2.0
[0.1.0]: https://github.com/sergeyklay/groster/releases/tag/0.1.0
