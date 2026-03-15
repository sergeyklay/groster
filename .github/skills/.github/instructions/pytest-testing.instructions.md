---
description: Instructions for writing Python tests in the project
applyTo: 'tests/**/*.py'
---

# Testing Standards

You are writing tests for a Python project using pytest. Follow these standards strictly.

## Critical Rules (Always Apply)

1. **NEVER** perform real I/O in unit tests - mock all network, database, and file operations
2. **ALWAYS** use plain functions for tests - avoid class-based tests unless technically unavoidable
3. **ALWAYS** name tests using `test_<subject>_<scenario>_<expected_outcome>` pattern
4. **ALWAYS** use `pytest.raises` with `match` parameter for exception testing
5. **NEVER** put multiple logical assertions testing different scenarios in one test
6. **ALWAYS** use `mocker` fixture from pytest-mock instead of `unittest.mock` directly

## Test File Structure

When creating a new test file:

```python
"""Tests for module_name functionality."""

from __future__ import annotations

import pytest
# Standard library imports

# Third-party imports (pandas, etc.)

# Local imports - import the module under test


# Fixtures (if local to this file)


# Tests - grouped by function/class being tested
```

## Test Types and Scope

Unit tests MUST:
- Test a single function or component in complete isolation
- Mock ALL external I/O (network, database, filesystem)
- Execute in milliseconds, not seconds
- Live in the `tests/` directory mirroring the source structure

## Test Naming and Quality

ALWAYS use descriptive test names that explain the scenario without reading the code:

```python
# ✅ DO: Name describes subject, scenario, and expected outcome
def test_user_registration_with_invalid_email_raises_validation_error():
    """The docstring is optional when the name is fully descriptive."""
    invalid_email = "not-an-email"

    with pytest.raises(ValidationError, match="Invalid email format"):
        register_user(email=invalid_email, password="secure123")


# ✅ DO: Name makes the test self-documenting
def test_calculate_discount_with_premium_membership_returns_twenty_percent():
    user = User(membership="premium")

    discount = calculate_discount(user, base_price=100.0)

    assert discount == 20.0


# ❌ DON'T: Vague name requires reading implementation
def test_user():
    ...

# ❌ DON'T: Name doesn't indicate expected outcome
def test_registration():
    ...
```

**Why this matters:** Descriptive names make test failures immediately understandable in CI logs without digging into code.

## Arrange-Act-Assert Pattern

ALWAYS structure tests with clear visual separation between phases:

```python
# ✅ DO: Clear AAA structure with blank lines
def test_order_total_with_discount_code_applies_percentage():
    order = Order(items=[Item(price=100), Item(price=50)])
    discount_code = DiscountCode(percentage=10)

    total = order.calculate_total(discount_code=discount_code)

    assert total == 135.0  # 150 - 10%


# ❌ DON'T: Mixed phases, hard to follow
def test_order_total():
    order = Order(items=[Item(price=100)])
    assert order.items[0].price == 100  # Asserting during arrange
    order.add_item(Item(price=50))
    total = order.calculate_total(discount_code=DiscountCode(percentage=10))
    order.clear()  # Acting after assert
    assert total == 135.0
```

## Assertion Strategy

Use plain `assert` for simple comparisons - pytest provides rich diffs automatically:

```python
# ✅ DO: Simple assertions with clear messages
assert result == expected
assert user.is_active is True
assert len(items) == 3
assert "error" in message.lower()
```

Use domain-specific assertion helpers when they provide better diagnostics:

```python
# ✅ DO: Use pandas assertions for DataFrames
import pandas as pd
pd.testing.assert_frame_equal(result_df, expected_df)

# ✅ DO: Use numpy for array comparisons
import numpy as np
np.testing.assert_array_almost_equal(result, expected, decimal=5)

# ✅ DO: Use pytest.approx for floating point
assert result == pytest.approx(3.14159, rel=1e-5)
```

For exception testing, ALWAYS use `pytest.raises` with `match`:

```python
# ✅ DO: pytest.raises with regex match - validates exception type AND message
def test_divide_by_zero_raises_descriptive_error():
    with pytest.raises(ValueError, match=r"Cannot divide .* by zero"):
        divide(10, 0)


# ✅ DO: Capture exception for additional assertions if needed
def test_api_error_contains_status_code():
    with pytest.raises(APIError, match="Request failed") as exc_info:
        api_client.fetch("/invalid")

    assert exc_info.value.status_code == 404
    assert exc_info.value.endpoint == "/invalid"


# ❌ DON'T: Manual try/except - loses pytest's assertion introspection
def test_divide_by_zero_manual():
    try:
        divide(10, 0)
        assert False, "Expected ValueError"  # Easy to forget this line
    except ValueError as e:
        assert "divide by zero" in str(e)


# ❌ DON'T: pytest.raises without match - doesn't verify the right error occurred
def test_divide_by_zero_no_match():
    with pytest.raises(ValueError):  # Any ValueError passes, even wrong ones
        divide(10, 0)
```

**Why `match` matters:** Without it, your test passes even if the code raises the right exception type for the wrong reason.

## Test Organization

### File Structure Rules

- **1:1 mapping**: `src/module/service.py` → `tests/module/test_service.py`
- **All new features** require corresponding tests
- **All bug fixes** require regression tests that would have caught the bug

### Parametrized Tests

Use `@pytest.mark.parametrize` when testing the same logic with different inputs:

```python
# ✅ DO: Parametrize with descriptive IDs for clear test output
import pytest
import pandas as pd


@pytest.mark.parametrize(
    ("input_data", "expected_valid"),
    [
        pytest.param(
            pd.DataFrame({"id": [1, 2]}),
            True,
            id="valid_dataframe_with_ids",
        ),
        pytest.param(
            pd.DataFrame({"id": [1, None]}),
            False,
            id="invalid_dataframe_with_null_id",
        ),
        pytest.param(
            pd.DataFrame(),
            False,
            id="invalid_empty_dataframe",
        ),
    ],
)
def test_validate_data_checks_id_column(
    input_data: pd.DataFrame,
    expected_valid: bool,
):
    result = validate_data(input_data)

    assert result.is_valid is expected_valid


# ❌ DON'T: Multiple scenarios in one test - if one fails, you don't know which
def test_data_validation():
    result = validate_data(pd.DataFrame({"id": [1, 2]}))
    assert result.is_valid is True

    result = validate_data(pd.DataFrame({"id": [1, None]}))
    assert result.is_valid is False  # If this fails, the first case is untested

    result = validate_data(pd.DataFrame())
    assert result.is_valid is False
```

**Why parametrize:** Each parameter set runs as a separate test. If one fails, others still run, giving you complete information about what's broken.

### When NOT to Parametrize

Don't force parametrization when scenarios have different setup or assertions:

```python
# ❌ DON'T: Forced parametrization with conditional logic
@pytest.mark.parametrize("scenario", ["success", "failure", "timeout"])
def test_api_call(scenario, mocker):
    if scenario == "success":
        mocker.patch("module.api.call", return_value={"data": "ok"})
        result = fetch_data()
        assert result.success is True
    elif scenario == "failure":
        mocker.patch("module.api.call", side_effect=APIError("fail"))
        with pytest.raises(APIError):
            fetch_data()
    # ... more conditionals


# ✅ DO: Separate tests when scenarios differ significantly
def test_fetch_data_returns_parsed_response_on_success(mocker):
    mocker.patch("module.api.call", return_value={"data": "ok"})

    result = fetch_data()

    assert result.success is True
    assert result.data == "ok"


def test_fetch_data_raises_api_error_on_failure(mocker):
    mocker.patch("module.api.call", side_effect=APIError("Service unavailable"))

    with pytest.raises(APIError, match="Service unavailable"):
        fetch_data()
```

## Fixture Organization

### Placement Rules

**Put in `conftest.py` when:**
- Used by 2+ test modules
- Infrastructure (database mocks, API clients)
- Stable utilities unlikely to change

**Keep in test file when:**
- Only used by one module
- Domain-specific test data
- Likely to evolve with the feature

### Fixture Scope Selection

```python
# Function scope (default) - fresh instance per test
@pytest.fixture
def user():
    return User(name="test", email="test@example.com")


# Module scope - shared within a file, use for expensive setup
@pytest.fixture(scope="module")
def trained_model():
    return load_model("weights.pkl")


# Session scope - shared across entire test run, use sparingly
@pytest.fixture(scope="session")
def database_schema():
    return create_test_schema()
```

### Extracting Reusable Fixtures

ALWAYS extract repeated setup into fixtures:

```python
# ❌ DON'T: Duplicated setup across tests
def test_process_order_calculates_total():
    data = pd.DataFrame({"order_id": [1, 2], "item_id": [432, 878], "price": [10, 20]})
    result = process_order(data)
    assert result.total == 30


def test_process_order_validates_items():
    data = pd.DataFrame({"order_id": [1, 2], "item_id": [432, 878], "price": [10, 20]})
    result = process_order(data)
    assert result.items_valid is True


# ✅ DO: Reusable fixture eliminates duplication
@pytest.fixture
def sample_order_data():
    return pd.DataFrame({
        "order_id": [1, 2],
        "item_id": [432, 878],
        "price": [10, 20],
    })


def test_process_order_calculates_total(sample_order_data):
    result = process_order(sample_order_data)

    assert result.total == 30


def test_process_order_validates_items(sample_order_data):
    result = process_order(sample_order_data)

    assert result.items_valid is True
```

### Factory Fixtures

Use factory fixtures when tests need variations of the same data:

```python
# ✅ DO: Factory fixture for flexible test data
@pytest.fixture
def make_user():
    """Factory to create users with custom attributes."""
    def _make_user(
        name: str = "Test User",
        email: str = "test@example.com",
        is_active: bool = True,
    ) -> User:
        return User(name=name, email=email, is_active=is_active)

    return _make_user


def test_inactive_user_cannot_login(make_user):
    user = make_user(is_active=False)

    result = attempt_login(user)

    assert result.success is False


def test_user_with_custom_email_receives_notification(make_user):
    user = make_user(email="custom@test.com")

    send_notification(user)

    assert notification_sent_to("custom@test.com")
```

## Mock and Patch Strategy

### Core Principles

1. **ALWAYS** use `mocker` fixture from pytest-mock (not `unittest.mock` directly)
2. **ALWAYS** use `autospec=True` to catch interface mismatches
3. **ONLY** mock external boundaries (I/O, APIs, databases) - never internal logic
4. **ALWAYS** patch where the object is used, not where it's defined

### Using the mocker Fixture

```python
# ✅ DO: Use mocker with autospec for type-safe mocking
def test_fetch_user_data_returns_formatted_response(mocker):
    # autospec ensures mock matches real function signature
    mock_api = mocker.patch(
        "myapp.services.user_service.api_client.get",
        autospec=True,
    )
    mock_api.return_value = {"id": 1, "name": "Alice"}

    result = fetch_user_data(user_id=1)

    assert result.name == "Alice"
    mock_api.assert_called_once_with("/users/1")


# ❌ DON'T: Use unittest.mock directly
from unittest.mock import patch

def test_fetch_user_data():
    with patch("myapp.services.api_client.get") as mock_api:  # Wrong module path!
        mock_api.return_value = {"id": 1, "name": "Alice"}
        result = fetch_user_data(user_id=1)  # Mock never called - real API hit!
```

### Patch Location Rule

Patch where the name is looked up, not where it's defined:

```python
# myapp/services/user_service.py
from myapp.clients import api_client  # api_client is imported HERE

def fetch_user(user_id: int):
    return api_client.get(f"/users/{user_id}")  # Lookup happens in user_service


# ✅ DO: Patch in the module that uses it
def test_fetch_user(mocker):
    mocker.patch("myapp.services.user_service.api_client.get")  # Correct!


# ❌ DON'T: Patch in the module that defines it
def test_fetch_user(mocker):
    mocker.patch("myapp.clients.api_client.get")  # Wrong - won't intercept!
```

### Multiple Mocks

Flatten nested context managers:

```python
# ✅ DO: Comma-separated context managers
def test_with_multiple_dependencies(mocker):
    mock_db = mocker.patch("module.database.connect", autospec=True)
    mock_cache = mocker.patch("module.cache.get", autospec=True)
    mock_api = mocker.patch("module.api.fetch", autospec=True)

    mock_db.return_value.query.return_value = [{"id": 1}]
    mock_cache.return_value = None
    mock_api.return_value = {"status": "ok"}

    result = process_request()

    assert result.success


# ❌ DON'T: Nested with blocks
def test_with_multiple_dependencies():
    with patch("module.database.connect"):
        with patch("module.cache.get"):
            with patch("module.api.fetch"):
                result = process_request()  # Deep nesting hurts readability
```

### Verifying Mock Calls

```python
# ✅ DO: Assert specific call arguments when they matter
def test_create_user_calls_api_with_correct_payload(mocker):
    mock_api = mocker.patch("module.api.post", autospec=True)
    mock_api.return_value = {"id": 123}

    create_user(name="Alice", email="alice@test.com")

    mock_api.assert_called_once_with(
        "/users",
        json={"name": "Alice", "email": "alice@test.com"},
    )


# ✅ DO: Use call_args for partial matching
def test_logger_includes_user_id(mocker):
    mock_logger = mocker.patch("module.logger.info", autospec=True)

    process_user(user_id=42)

    # Check that user_id appears somewhere in the log call
    call_args = mock_logger.call_args
    assert "42" in str(call_args)
```

## Resource Management in Tests

Unit tests **MUST NOT** perform real I/O. Always mock external boundaries.

### Fixture Cleanup

Use `yield` fixtures to ensure proper cleanup:

```python
# ✅ DO: Cleanup with yield fixture
@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary config file, clean up after test."""
    config_file = tmp_path / "config.json"
    config_file.write_text('{"debug": true}')

    yield config_file  # Test runs here

    # Cleanup runs after test (even if test fails)
    if config_file.exists():
        config_file.unlink()


# ✅ DO: Use tmp_path for filesystem tests (auto-cleanup)
def test_export_writes_file(tmp_path):
    output_file = tmp_path / "output.csv"

    export_data(data, output_file)

    assert output_file.exists()
    assert output_file.read_text().startswith("id,name")
```

### Testing Pure Functions vs I/O

Separate pure logic from I/O for easier testing:

```python
# ✅ DO: Test pure transformation logic directly
def test_transform_data_adds_calculated_column():
    input_df = pd.DataFrame({"price": [100, 200], "quantity": [2, 3]})
    expected = pd.DataFrame({
        "price": [100, 200],
        "quantity": [2, 3],
        "total": [200, 600],
    })

    result = transform_data(input_df)

    pd.testing.assert_frame_equal(result, expected)


# ✅ DO: Mock I/O boundaries only
def test_load_and_transform_reads_from_database(mocker):
    mock_db = mocker.patch("module.database.query", autospec=True)
    mock_db.return_value = pd.DataFrame({"price": [100], "quantity": [2]})

    result = load_and_transform()

    assert "total" in result.columns
    mock_db.assert_called_once()
```

## Test Markers

Use markers to categorize and filter tests:

```python
# ✅ DO: Mark slow tests for optional exclusion
@pytest.mark.slow
def test_full_pipeline_end_to_end():
    """This test takes several seconds - skip in fast feedback loops."""
    ...


# ✅ DO: Skip with clear reason
@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Unix-specific path handling",
)
def test_symlink_resolution():
    ...


# ✅ DO: Mark expected failures
@pytest.mark.xfail(reason="Bug #123 - fix pending in next sprint")
def test_edge_case_currently_broken():
    ...
```

## Async Testing

When testing async code, use `pytest-asyncio`:

```python
import pytest


# ✅ DO: Use async test functions with pytest-asyncio
@pytest.mark.asyncio
async def test_fetch_user_returns_user_data(mocker):
    mock_client = mocker.patch("module.http_client.get", autospec=True)
    mock_client.return_value = {"id": 1, "name": "Alice"}

    result = await fetch_user(user_id=1)

    assert result.name == "Alice"


# ✅ DO: Async fixtures
@pytest.fixture
async def async_db_connection():
    conn = await create_connection()
    yield conn
    await conn.close()
```

## Test Commands

```bash
# Run all tests
uv run --frozen pytest ./tests

# Run specific file
uv run --frozen pytest -v ./tests/test_client.py

# Run specific test
uv run --frozen pytest -v ./tests/test_repo.py::test_clone_creates_directory

# Run excluding slow tests
uv run --frozen pytest -m "not slow"

# Run with verbose output
uv run --frozen pytest -v

# Run with coverage report
uv run --frozen pytest --cov=src --cov-report=term-missing

# Run failed tests from last run
uv run --frozen pytest --lf

# Stop on first failure
uv run --frozen pytest -x
```

## Common Mistakes to Avoid

### 1. Testing Implementation Instead of Behavior

```python
# ❌ DON'T: Test internal implementation details
def test_user_service_calls_repository_then_cache(mocker):
    mock_repo = mocker.patch("module.repo.get")
    mock_cache = mocker.patch("module.cache.set")

    get_user(1)

    # Brittle: test breaks if implementation changes order
    assert mock_repo.call_count == 1
    assert mock_cache.call_count == 1


# ✅ DO: Test observable behavior
def test_get_user_returns_user_with_correct_id(mocker):
    mocker.patch("module.repo.get", return_value=User(id=1, name="Alice"))

    result = get_user(1)

    assert result.id == 1
    assert result.name == "Alice"
```

### 2. Overly Broad Exception Handling

```python
# ❌ DON'T: Catch any exception
def test_invalid_input():
    with pytest.raises(Exception):  # Too broad!
        process(None)


# ✅ DO: Catch specific exception with message
def test_process_with_none_raises_value_error():
    with pytest.raises(ValueError, match="Input cannot be None"):
        process(None)
```

### 3. Shared Mutable State

```python
# ❌ DON'T: Mutable default in fixture
@pytest.fixture
def users(cache=[]):  # Shared across tests!
    cache.append(User())
    return cache


# ✅ DO: Fresh state per test
@pytest.fixture
def users():
    return [User()]
```
