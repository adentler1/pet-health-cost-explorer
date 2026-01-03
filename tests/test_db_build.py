"""Tests for database build pipeline."""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


class TestSeedDataLoading:
    """Tests for seed data loading functions."""

    def test_load_seed_breeds(self) -> None:
        """Test loading breed seed data."""
        from petcost.ingest.sources import load_seed_breeds

        df = load_seed_breeds()

        # Check required columns
        assert "species" in df.columns
        assert "breed_id" in df.columns
        assert "breed_name" in df.columns
        assert "source" in df.columns

        # Check we have data
        assert len(df) > 0

        # Check species values are valid
        assert set(df["species"].unique()).issubset({"dog", "cat"})

        # Check we have both dogs and cats
        assert "dog" in df["species"].values
        assert "cat" in df["species"].values

    def test_load_seed_life_expectancy(self) -> None:
        """Test loading life expectancy seed data."""
        from petcost.ingest.sources import load_seed_life_expectancy

        df = load_seed_life_expectancy()

        # Check required columns
        assert "breed_id" in df.columns
        assert "sex" in df.columns
        assert "country" in df.columns
        assert "le_years" in df.columns

        # Check we have data
        assert len(df) > 0

        # Check numeric values are reasonable
        assert df["le_years"].min() > 0
        assert df["le_years"].max() < 25

        # Check sex values are valid
        assert set(df["sex"].unique()).issubset({"male", "female", "all"})

    def test_load_seed_risk_profiles(self) -> None:
        """Test loading risk profile seed data."""
        from petcost.ingest.sources import load_seed_risk_profiles

        df = load_seed_risk_profiles()

        # Check required columns
        assert "breed_id" in df.columns
        assert "condition_id" in df.columns
        assert "metric_type" in df.columns
        assert "metric_value" in df.columns

        # Check we have data
        assert len(df) > 0

        # Check metric values are valid (prevalence should be 0-1)
        prevalence_df = df[df["metric_type"] == "prevalence"]
        assert prevalence_df["metric_value"].min() >= 0
        assert prevalence_df["metric_value"].max() <= 1

    def test_load_seed_cost_mapping(self) -> None:
        """Test loading cost mapping seed data."""
        from petcost.ingest.sources import load_seed_cost_mapping

        df = load_seed_cost_mapping()

        # Check required columns
        assert "condition_id" in df.columns
        assert "cost_low" in df.columns
        assert "cost_mid" in df.columns
        assert "cost_high" in df.columns
        assert "currency" in df.columns

        # Check we have data
        assert len(df) > 0

        # Check cost ordering makes sense
        assert (df["cost_low"] <= df["cost_mid"]).all()
        assert (df["cost_mid"] <= df["cost_high"]).all()

    def test_validate_seed_data(self) -> None:
        """Test seed data validation."""
        from petcost.ingest.sources import validate_seed_data

        results = validate_seed_data()

        # All seed files should be valid
        assert results["seed_breeds.csv"] is True
        assert results["seed_life_expectancy.csv"] is True
        assert results["seed_risk_profiles.csv"] is True
        assert results["seed_cost_mapping.csv"] is True


class TestDatabaseOperations:
    """Tests for database operations."""

    @pytest.fixture
    def temp_db(self, tmp_path: Path):
        """Create a temporary database for testing."""
        from petcost.db import DatabaseConnection

        db_path = tmp_path / "test_pet_insights.db"
        db = DatabaseConnection(db_path)
        return db

    def test_database_connection(self, temp_db) -> None:
        """Test database connection works."""
        with temp_db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1

    def test_create_table(self, temp_db) -> None:
        """Test table creation."""
        temp_db.execute_script(
            """
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
            """
        )

        assert temp_db.table_exists("test_table")

    def test_insert_and_query(self, temp_db) -> None:
        """Test data insertion and querying."""
        temp_db.execute_script(
            """
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
            """
        )

        temp_db.execute(
            "INSERT INTO test_table (id, name) VALUES (?, ?)",
            (1, "test"),
        )

        results = temp_db.execute("SELECT * FROM test_table WHERE id = ?", (1,))
        assert len(results) == 1
        assert results[0]["name"] == "test"


class TestSchemaCreation:
    """Tests for schema creation."""

    @pytest.fixture
    def temp_db_with_schema(self, tmp_path: Path):
        """Create a temporary database with schema."""
        import os

        from petcost.db import DatabaseConnection, reset_db

        # Set environment variable for database path
        db_path = tmp_path / "test_pet_insights.db"
        os.environ["DATABASE_PATH"] = str(db_path)

        # Reset and create fresh connection
        from petcost.config import reload_settings

        reload_settings()
        db = reset_db()

        # Create schema
        from petcost.schemas import create_schema

        create_schema()

        yield db

        # Cleanup
        if "DATABASE_PATH" in os.environ:
            del os.environ["DATABASE_PATH"]

    def test_breeds_table_exists(self, temp_db_with_schema) -> None:
        """Test breeds table is created."""
        assert temp_db_with_schema.table_exists("breeds")

    def test_life_expectancy_table_exists(self, temp_db_with_schema) -> None:
        """Test life_expectancy table is created."""
        assert temp_db_with_schema.table_exists("life_expectancy")

    def test_conditions_table_exists(self, temp_db_with_schema) -> None:
        """Test conditions table is created."""
        assert temp_db_with_schema.table_exists("conditions")

    def test_breed_condition_risk_table_exists(self, temp_db_with_schema) -> None:
        """Test breed_condition_risk table is created."""
        assert temp_db_with_schema.table_exists("breed_condition_risk")

    def test_cost_assumptions_table_exists(self, temp_db_with_schema) -> None:
        """Test cost_assumptions table is created."""
        assert temp_db_with_schema.table_exists("cost_assumptions")

    def test_simulated_costs_table_exists(self, temp_db_with_schema) -> None:
        """Test simulated_costs table is created."""
        assert temp_db_with_schema.table_exists("simulated_costs")


class TestFullPipelineBuild:
    """Integration tests for full pipeline build."""

    @pytest.fixture
    def built_database(self, tmp_path: Path):
        """Build a complete database for testing."""
        import os

        from petcost.config import reload_settings
        from petcost.db import reset_db
        from petcost.pipeline.build_db import build_database

        # Set environment variable for database path
        db_path = tmp_path / "test_pet_insights.db"
        os.environ["DATABASE_PATH"] = str(db_path)

        # Reduce simulation iterations for faster tests
        os.environ["SIMULATION_ITERATIONS"] = "100"

        reload_settings()
        reset_db()

        # Build database
        stats = build_database(rebuild=True)

        yield stats

        # Cleanup
        if "DATABASE_PATH" in os.environ:
            del os.environ["DATABASE_PATH"]
        if "SIMULATION_ITERATIONS" in os.environ:
            del os.environ["SIMULATION_ITERATIONS"]

    def test_breeds_loaded(self, built_database) -> None:
        """Test breeds are loaded."""
        assert built_database["breeds"] > 0

    def test_life_expectancy_loaded(self, built_database) -> None:
        """Test life expectancy data is loaded."""
        assert built_database["life_expectancy"] > 0

    def test_conditions_loaded(self, built_database) -> None:
        """Test conditions are loaded."""
        assert built_database["conditions"] > 0

    def test_breed_condition_risk_loaded(self, built_database) -> None:
        """Test breed condition risks are loaded."""
        assert built_database["breed_condition_risk"] > 0

    def test_cost_assumptions_loaded(self, built_database) -> None:
        """Test cost assumptions are loaded."""
        assert built_database["cost_assumptions"] > 0

    def test_simulated_costs_generated(self, built_database) -> None:
        """Test simulated costs are generated."""
        assert built_database["simulated_costs"] > 0
