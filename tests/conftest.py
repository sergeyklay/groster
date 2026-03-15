import pytest

from groster.repository import InMemoryRosterRepository


@pytest.fixture
def in_memory_repo() -> InMemoryRosterRepository:
    """Provide a fresh, empty InMemoryRosterRepository instance."""
    return InMemoryRosterRepository()
