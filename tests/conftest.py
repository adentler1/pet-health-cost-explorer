"""Pytest configuration and fixtures for Pet Health Cost Explorer tests."""

import os
import sys
from pathlib import Path

import pytest

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


@pytest.fixture(scope="session")
def project_root_path() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def seed_data_path(project_root_path: Path) -> Path:
    """Get the seed data directory."""
    return project_root_path / "data" / "seed"


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment variables after each test."""
    original_env = os.environ.copy()
    yield
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def temp_database(tmp_path: Path):
    """Create a temporary database for testing."""
    from petcost.db import DatabaseConnection

    db_path = tmp_path / "test_db.sqlite"
    db = DatabaseConnection(db_path)
    return db


@pytest.fixture
def populated_database(tmp_path: Path):
    """Create a fully populated database for testing."""
    import os

    from petcost.config import reload_settings
    from petcost.db import get_db, reset_db
    from petcost.pipeline.build_db import build_database

    # Set environment variables for test database
    db_path = tmp_path / "test_pet_insights.db"
    os.environ["DATABASE_PATH"] = str(db_path)
    os.environ["SIMULATION_ITERATIONS"] = "100"
    os.environ["LOG_LEVEL"] = "WARNING"

    reload_settings()
    reset_db()

    # Build the database
    build_database(rebuild=True)

    yield get_db()

    # Cleanup is handled by reset_environment fixture
