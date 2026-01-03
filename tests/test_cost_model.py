"""Tests for the synthetic cost model."""

import os
import sys
from pathlib import Path

import numpy as np
import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


class TestCostSimulator:
    """Tests for CostSimulator class."""

    @pytest.fixture
    def simulator(self):
        """Create a cost simulator for testing."""
        from petcost.features.cost_model import CostSimulator

        # Use fixed seed for reproducibility
        return CostSimulator(seed=42, iterations=1000)

    def test_simulator_initialization(self, simulator) -> None:
        """Test simulator initializes correctly."""
        assert simulator.seed == 42
        assert simulator.iterations == 1000
        assert simulator.rng is not None

    def test_reproducibility(self) -> None:
        """Test that same seed produces same results."""
        from petcost.features.cost_model import CostSimulator

        sim1 = CostSimulator(seed=42, iterations=100)
        sim2 = CostSimulator(seed=42, iterations=100)

        # Sample from same distribution
        samples1 = sim1._sample_condition_cost(100, 200, 500, 100)
        samples2 = sim2._sample_condition_cost(100, 200, 500, 100)

        np.testing.assert_array_equal(samples1, samples2)

    def test_different_seeds_produce_different_results(self) -> None:
        """Test that different seeds produce different results."""
        from petcost.features.cost_model import CostSimulator

        sim1 = CostSimulator(seed=42, iterations=100)
        sim2 = CostSimulator(seed=123, iterations=100)

        samples1 = sim1._sample_condition_cost(100, 200, 500, 100)
        samples2 = sim2._sample_condition_cost(100, 200, 500, 100)

        # Should not be equal
        assert not np.array_equal(samples1, samples2)


class TestCostSampling:
    """Tests for cost sampling functions."""

    @pytest.fixture
    def simulator(self):
        """Create a cost simulator for testing."""
        from petcost.features.cost_model import CostSimulator

        return CostSimulator(seed=42, iterations=1000)

    def test_sample_condition_cost_shape(self, simulator) -> None:
        """Test sample_condition_cost returns correct shape."""
        samples = simulator._sample_condition_cost(100, 200, 500, 100)
        assert samples.shape == (100,)

    def test_sample_condition_cost_bounds(self, simulator) -> None:
        """Test sampled costs are within bounds."""
        samples = simulator._sample_condition_cost(100, 200, 500, 1000)

        assert samples.min() >= 100
        assert samples.max() <= 500

    def test_sample_condition_cost_distribution(self, simulator) -> None:
        """Test sampled costs follow expected distribution."""
        samples = simulator._sample_condition_cost(100, 200, 500, 10000)

        # Mode should be around 200 (the middle value)
        # Mean of triangular distribution = (a + b + c) / 3
        expected_mean = (100 + 200 + 500) / 3
        actual_mean = samples.mean()

        # Allow 10% tolerance
        assert abs(actual_mean - expected_mean) / expected_mean < 0.1


class TestConditionOccurrence:
    """Tests for condition occurrence simulation."""

    @pytest.fixture
    def simulator(self):
        """Create a cost simulator for testing."""
        from petcost.features.cost_model import CostSimulator

        return CostSimulator(seed=42, iterations=5000)

    def test_simulate_occurrence_shape(self, simulator) -> None:
        """Test occurrence simulation returns correct shape."""
        occurrences = simulator._simulate_condition_occurrence(
            prevalence=0.1,
            years=10,
            age_band="all",
            n_simulations=100,
        )

        assert occurrences.shape == (100, 10)

    def test_simulate_occurrence_low_prevalence(self, simulator) -> None:
        """Test low prevalence produces few occurrences."""
        occurrences = simulator._simulate_condition_occurrence(
            prevalence=0.01,
            years=10,
            age_band="all",
            n_simulations=1000,
        )

        # With 1% lifetime prevalence over 10 years,
        # should have low occurrence rate
        occurrence_rate = occurrences.any(axis=1).mean()
        assert occurrence_rate < 0.05

    def test_simulate_occurrence_high_prevalence(self, simulator) -> None:
        """Test high prevalence produces many occurrences."""
        occurrences = simulator._simulate_condition_occurrence(
            prevalence=0.9,
            years=10,
            age_band="all",
            n_simulations=1000,
        )

        # With 90% lifetime prevalence, most simulations should have occurrence
        occurrence_rate = occurrences.any(axis=1).mean()
        assert occurrence_rate > 0.8


class TestAgeWeights:
    """Tests for age-based probability weights."""

    @pytest.fixture
    def simulator(self):
        """Create a cost simulator for testing."""
        from petcost.features.cost_model import CostSimulator

        return CostSimulator(seed=42, iterations=1000)

    def test_age_weights_all_uniform(self, simulator) -> None:
        """Test 'all' age band produces uniform weights."""
        weights = simulator._get_age_weights("all", 10)

        # Should be normalized around 1.0
        assert len(weights) == 10
        np.testing.assert_almost_equal(weights.mean(), 1.0, decimal=5)

    def test_age_weights_puppy_early_weighted(self, simulator) -> None:
        """Test 'puppy' age band weights early years higher."""
        weights = simulator._get_age_weights("puppy", 10)

        # Early years should have higher weights
        assert weights[0] > weights[5]
        assert weights[1] > weights[5]

    def test_age_weights_senior_late_weighted(self, simulator) -> None:
        """Test 'senior' age band weights later years higher."""
        weights = simulator._get_age_weights("senior", 12)

        # Later years should have higher weights
        assert weights[-1] > weights[0]
        assert weights[-2] > weights[0]


class TestSimulationResults:
    """Tests for simulation result structure."""

    @pytest.fixture
    def built_database(self, tmp_path: Path):
        """Build a minimal database for testing."""
        import os

        from petcost.config import reload_settings
        from petcost.db import reset_db
        from petcost.pipeline.build_db import build_database

        # Set environment variable for database path
        db_path = tmp_path / "test_pet_insights.db"
        os.environ["DATABASE_PATH"] = str(db_path)
        os.environ["SIMULATION_ITERATIONS"] = "100"

        reload_settings()
        reset_db()

        build_database(rebuild=True)

        yield

        # Cleanup
        if "DATABASE_PATH" in os.environ:
            del os.environ["DATABASE_PATH"]
        if "SIMULATION_ITERATIONS" in os.environ:
            del os.environ["SIMULATION_ITERATIONS"]

    def test_simulation_result_structure(self, built_database) -> None:
        """Test simulation result has correct structure."""
        from petcost.features.cost_model import CostSimulator

        simulator = CostSimulator(seed=42, iterations=100)
        result = simulator.simulate_annual_costs("dog_labrador", "UK", 5)

        assert hasattr(result, "breed_id")
        assert hasattr(result, "country")
        assert hasattr(result, "p10")
        assert hasattr(result, "p50")
        assert hasattr(result, "p90")
        assert hasattr(result, "mean")
        assert hasattr(result, "std")
        assert hasattr(result, "model_version")
        assert hasattr(result, "is_synthetic")

    def test_simulation_percentiles_ordered(self, built_database) -> None:
        """Test simulation percentiles are in correct order."""
        from petcost.features.cost_model import CostSimulator

        simulator = CostSimulator(seed=42, iterations=100)
        result = simulator.simulate_annual_costs("dog_labrador", "UK", 5)

        assert result.p10 <= result.p50
        assert result.p50 <= result.p90

    def test_lifetime_costs_greater_than_annual(self, built_database) -> None:
        """Test lifetime costs are greater than single year costs."""
        from petcost.features.cost_model import CostSimulator

        simulator = CostSimulator(seed=42, iterations=100)
        annual = simulator.simulate_annual_costs("dog_labrador", "UK", 5)
        lifetime = simulator.simulate_lifetime_costs("dog_labrador", "UK")

        # Lifetime should be substantially greater than single year
        assert lifetime.p50 > annual.p50

    def test_is_synthetic_flag(self, built_database) -> None:
        """Test is_synthetic flag is set correctly."""
        from petcost.features.cost_model import CostSimulator

        simulator = CostSimulator(seed=42, iterations=100)
        result = simulator.simulate_annual_costs("dog_labrador", "UK", 5)

        assert result.is_synthetic is True


class TestModelVersion:
    """Tests for model versioning."""

    def test_model_version_set(self) -> None:
        """Test MODEL_VERSION is defined."""
        from petcost.features.cost_model import MODEL_VERSION

        assert MODEL_VERSION is not None
        assert isinstance(MODEL_VERSION, str)
        assert len(MODEL_VERSION) > 0

    def test_model_version_in_results(self, tmp_path: Path) -> None:
        """Test model version is included in results."""
        import os

        from petcost.config import reload_settings
        from petcost.db import reset_db
        from petcost.features.cost_model import MODEL_VERSION, CostSimulator
        from petcost.pipeline.build_db import build_database

        # Set environment variable for database path
        db_path = tmp_path / "test_pet_insights.db"
        os.environ["DATABASE_PATH"] = str(db_path)
        os.environ["SIMULATION_ITERATIONS"] = "100"

        reload_settings()
        reset_db()
        build_database(rebuild=True)

        simulator = CostSimulator(seed=42, iterations=100)
        result = simulator.simulate_annual_costs("dog_labrador", "UK", 5)

        assert result.model_version == MODEL_VERSION

        # Cleanup
        del os.environ["DATABASE_PATH"]
        del os.environ["SIMULATION_ITERATIONS"]
