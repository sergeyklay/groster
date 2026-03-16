# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.6.0] - 2026-03-16

### Added

- Incremental roster updates: `groster update` now diffs the current guild roster against the previous run and only re-fetches achievement, pet, and mount data for new or changed members, reducing Blizzard API calls by ~75% on typical runs. Member profiles (ilvl, last login) are always refreshed to keep Discord data current.
- `--force` flag on the `update` command to bypass the incremental cache and perform a full refresh.
- `diff_roster_members()` pure function for comparing current Blizzard roster members against previously saved records.
- `get_roster_details()`, `save_character_achievements()`, and `get_member_fingerprints()` methods on `RosterRepository` for incremental state persistence.
- Per-character `achievements.json` cache files under `data/{region}/{realm}/{charname}/` for fingerprint reuse across runs.
- `/alts` slash command that displays every guild main with their alt count in an ephemeral Discord embed, sorted by alt count descending.
- `format_alts_embed()` helper that builds a Discord embed dict with automatic truncation at the 4096-character description limit.
- `get_alts_per_main()` method on `RosterRepository` for per-main alt count aggregation from the dashboard.
- Discord autocomplete for the `/whois` command — typing a partial name shows matching character suggestions.
- Fuzzy "Did you mean?" suggestions when `/whois` finds no exact match, powered by `difflib.get_close_matches()`.
- `search_character_names()` method on `RosterRepository` for prefix-based character name lookup.
- `build_dashboard()` and `get_alt_summary()` methods on `RosterRepository`.
- `InMemoryRosterRepository` with async test support via `pytest-asyncio`.
- Pull request template.
- Agentic framework: agent modes, coding instructions, prompts, and workflow skills.

### Changed

- `identify_alts()` returns a 5-tuple (was 4-tuple) — the new fifth element is `fingerprint_cache` containing only freshly fetched fingerprint data for persistence.
- `fetch_roster_details()` accepts an optional `cached_records` keyword argument to skip API calls for unchanged members.
- `_get_roster_details()` in `commands/roster.py` returns `(roster_data, cached_profile_records)` to thread incremental state through the orchestration layer.
- `register_commands()` switched from single POST to bulk PUT (`PUT .../commands`) so all guild slash commands are registered atomically.
- `/whois` command handler extracted into `_handle_whois()` helper to reduce `interactions_handler()` complexity.
- `_format_no_character_message()` accepts optional `suggestions` parameter for fuzzy match results.
- Dashboard generation and alt summary logic moved behind `RosterRepository`; `summary_report()` accepts a repository instance instead of reading CSVs directly.
- Dependabot schedule changed from daily to weekly with labels.

### Fixed

- `US/Eastern` timezone in tests replaced with IANA canonical `America/New_York`.

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

[Unreleased]: https://github.com/sergeyklay/groster/compare/0.6.0...HEAD
[0.6.0]: https://github.com/sergeyklay/groster/compare/0..0...0.6.0
[0.5.0]: https://github.com/sergeyklay/groster/compare/0.4.0...0.5.0
[0.4.0]: https://github.com/sergeyklay/groster/compare/0.3.0...0.4.0
[0.3.0]: https://github.com/sergeyklay/groster/compare/0.2.0...0.3.0
[0.2.0]: https://github.com/sergeyklay/groster/compare/0.1.0...0.2.0
[0.1.0]: https://github.com/sergeyklay/groster/releases/tag/0.1.0
