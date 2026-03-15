# groster

CLI + Discord bot that fetches WoW guild rosters via the Blizzard API and identifies alt characters through achievement fingerprinting. The non-obvious part: all data is generated locally (CSV files under `data/`), never committed, and always accessed through a repository abstraction.

## Commands

- Install deps: `uv sync --locked --all-packages --all-groups` (NOT `pip install` or `uv pip install`)
- Run tests: `make test` (NOT `pytest` — bare pytest skips coverage instrumentation)
- Quality gate: `make format lint test` (run before every commit)
- Python runtime: managed by `asdf` (version in `.tool-versions`). Run `asdf reshim python` after fresh installs or version changes.

## Gotchas

- `data/` is gitignored. CSV output files only exist after a roster update run — never assume they are present.
- `[project.dependencies]` in `pyproject.toml` must stay in **sorted alphabetical order** (see inline comment).
- Never use `print()` — use the `logging` module. Never use f-strings in log calls — use `%` formatting.
- `groster/commands/bot.py` reads env vars and creates a repository instance **at module level**. Importing it without `DISCORD_PUBLIC_KEY` set raises `ValueError` immediately.
- `uv run --frozen` is used everywhere — the lockfile is the source of truth for dependency resolution.

## Boundaries

### Always

- Enforce current coding standards on new and modified code; contain legacy code as-is.
- Route all data I/O through `RosterRepository` — never read/write CSVs directly in services or commands.
- Use plain test functions. Class-based tests are prohibited.
- Follow test naming: `test_<subject>_<scenario>_<expected_outcome>`.

### Ask first

- `constants.py` `FINGERPRINT_ACHIEVEMENT_IDS` — game-specific values chosen for alt detection accuracy.
- `ranks.py` default rank structure — guild-specific names and hierarchy.

### Never

- Edit files under `data/` — they are generated output, not source.
- Edit `uv.lock` manually — only change it via `uv` commands.
- Bypass the repository pattern to access data files directly.

## Reference docs

- `docs/coding-standards.md` — type hint requirements, docstring style, import ordering, test quality rules
- `docs/architecture.md` — data flow, alt detection algorithm, security model

---

Last updated: 2025-03-12

Maintained by: AI Agents under human supervision
