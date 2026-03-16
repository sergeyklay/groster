# groster

CLI + Discord bot that fetches WoW guild rosters via the Blizzard API and identifies alt characters through achievement fingerprinting. The non-obvious part: all data is generated locally (CSV files under `data/`), never committed, and always accessed through a repository abstraction.

## Commands

- Install deps: `uv sync --locked --all-packages --all-groups` (NOT `pip install` or `uv pip install`)
- Run tests: `make test` (NOT `pytest` — bare pytest skips coverage instrumentation)
- Quality gate: `make format lint test` (run before every commit)
- Python runtime: managed by `asdf` (version in `.tool-versions`). Run `asdf reshim python` after fresh installs or version changes.
- Deploy: `docker compose down --remove-orphans && docker build --no-cache . && docker compose up -d` — always use `--no-cache` to avoid stale `COPY` layers.

## Gotchas

- `data/` is gitignored. CSV output files only exist after a roster update run — never assume they are present.
- `[project.dependencies]` in `pyproject.toml` must stay in **sorted alphabetical order** (see inline comment).
- Never use `print()` — use the `logging` module. Never use f-strings in log calls — use `%` formatting.
- `groster/commands/bot.py` reads env vars and creates a repository instance **at module level**. Importing it without `DISCORD_PUBLIC_KEY` set raises `ValueError` immediately. Tests must `os.environ.setdefault("DISCORD_PUBLIC_KEY", "0" * 64)` before importing from this module.
- `uv run --frozen` is used everywhere — the lockfile is the source of truth for dependency resolution.
- `register_commands()` in `discord.py` uses **bulk PUT overwrite**. Adding a new slash command requires listing it alongside all existing commands in the payload array — omitting one deletes it from Discord.
- Discord enforces the embed description limit in **UTF-8 bytes**, not Unicode code points or UTF-16 units. Each class emoji (supplementary-plane, e.g. 💀) is 4 UTF-8 bytes but 1 Python char; the utf8/py ratio for this guild is ~1.23. Use `_utf8_len()` (UTF-8 byte counting) in the truncation guard; 3900 bytes leaves ~196 bytes of headroom below the 4096-byte limit.
- `scripts/` is excluded from Ruff linting (in `pyproject.toml` `extend-exclude`). Throwaway scripts there won't block CI but also won't be checked.

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

Last updated: 2026-03-16

Maintained by: AI Agents under human supervision
