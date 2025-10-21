"""Test configuration."""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def mock_openai_key(monkeypatch):
    """Mock OpenAI API key."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")


@pytest.fixture
def mock_db_url(monkeypatch):
    """Mock database URL."""
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
