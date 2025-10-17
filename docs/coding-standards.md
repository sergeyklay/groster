# Coding Standards

Requirements for consistent, maintainable code in the groster project.

## Python Standards

**Type System Requirements:**
- Type hints are **required** on all functions and class methods
- Use modern syntax (PEP 604/585): `list[str]` not `typing.List[str]`
- Avoid `Any` type - use specific types or protocols
- Return type `-> None` is optional for obvious cases (`__init__`, setters, etc.)
- Use `typing.Never` for functions that never return (always raise/exit)

**Code Style Requirements:**
- Line length: 88 characters maximum
- Function structure: Guard clauses first, happy path last
- Naming: Descriptive names, no abbreviations (`user_count` not `uc`)
- Comprehensions preferred over loops when readable
- Indentation: 4 spaces, never tabs

**Logging Requirements:**
- **Never** use `print()` for logging - use `logging` module
- **Never** use f-strings in logging calls - use `%` formatting
- Target senior Python developers - no obvious comments

**Docstring Requirements:**
- Use imperative voice: "Calculate discount" not "Calculates discount"
- One-line summary for trivial functions
- Google-style sections (Args, Returns, Raises) for non-trivial functions
- Do not duplicate types already in type hints

## Testing Standards

**Test Types:**
- **Unit tests**: `tests/unit/` - mock all I/O, fast, isolated
- **Integration tests**: `tests/integration/` - marked `@pytest.mark.integration`

**Test Quality Requirements:**
- **Always** use plain functions - class-based tests are prohibited
- Test names **must** follow pattern: `test_<subject>_<scenario>_<expected_outcome>`
- One logical scenario per test
- Understandable without comments
- 1:1 ratio between test files and implementation files

**Assertion Requirements:**
- Use plain `assert` for simple comparisons
- **Must** use `pytest.raises` with `match` parameter for exceptions
- Use domain-specific helpers when they improve diagnostics
- Arrange-Act-Assert pattern clearly separated

**Test Organization Requirements:**
- Use `@pytest.mark.parametrize` for data-driven testing
- Use pytest fixtures for setup/teardown
- All new features require tests
- Bug fixes require regression tests

## Import Organization

**Required structure:**
```python
# Standard library imports
import asyncio
from datetime import datetime
from pathlib import Path

# Third-party imports
import httpx
import pandas as pd

# First-party imports
from groster.services import make_guild_report
```

## Naming Conventions

- Classes: `CamelCase`
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private attributes: `_single_underscore`
