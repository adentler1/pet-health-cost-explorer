"""Synthetic cost model for Pet Health Cost Explorer.

This module implements a Monte Carlo simulation for estimating veterinary
costs when real claims data is unavailable.

IMPORTANT: All results from this model are ESTIMATES based on:
- Published veterinary fee schedules
- Epidemiological prevalence data
- Assumptions about condition recurrence and treatment patterns

Results should be clearly labeled as "Estimated" in any user-facing output.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats

from petcost.config import get_settings
from petcost.db import get_db
from petcost.logging_config import get_logger

logger = get_logger(__name__)

# Model version for tracking
MODEL_VERSION = "synthetic_v1.0"


@dataclass
class CostAssumption:
    """Cost assumption for a condition."""

    condition_id: str
    condition_name: str
    category: str
    cost_type: str
    cost_low: float
    cost_mid: float
    cost_high: float
    currency: str


@dataclass
class SimulationResult:
    """Result of a cost simulation."""

    breed_id: str
    country: str
    age_start: int
    age_end: int
    p10: float
    p50: float
    p90: float
    mean: float
    std: float
    model_version: str
    is_synthetic: bool
    iterations: int


class CostSimulator:
    """Monte Carlo simulator for pet health costs."""

    def __init__(
        self,
        seed: Optional[int] = None,
        iterations: Optional[int] = None,
    ) -> None:
        """
        Initialize the cost simulator.

        Args:
            seed: Random seed for reproducibility
            iterations: Number of Monte Carlo iterations
        """
        settings = get_settings()
        self.seed = seed or settings.simulation_seed
        self.iterations = iterations or settings.simulation_iterations
        self.rng = np.random.default_rng(self.seed)
        self.db = get_db()

        logger.info(f"CostSimulator initialized with seed={self.seed}, iterations={self.iterations}")

    def _get_breed_risks(self, breed_id: str) -> pd.DataFrame:
        """Get risk profile for a breed."""
        query = """
            SELECT
                bcr.condition_id,
                c.name as condition_name,
                c.category,
                bcr.metric_value as prevalence,
                bcr.age_band
            FROM breed_condition_risk bcr
            JOIN conditions c ON bcr.condition_id = c.condition_id
            WHERE bcr.breed_id = ?
              AND bcr.metric_type = 'prevalence'
        """
        return self.db.query_df(query, (breed_id,))

    def _get_cost_assumptions(self, country: str) -> pd.DataFrame:
        """Get cost assumptions for a country."""
        query = """
            SELECT
                ca.condition_id,
                c.name as condition_name,
                c.category,
                ca.cost_type,
                ca.cost_low,
                ca.cost_mid,
                ca.cost_high,
                ca.currency
            FROM cost_assumptions ca
            JOIN conditions c ON ca.condition_id = c.condition_id
            WHERE ca.country = ?
        """
        return self.db.query_df(query, (country,))

    def _get_life_expectancy(self, breed_id: str, country: str) -> float:
        """Get life expectancy for a breed.

        Life expectancy data is universal (country='ALL'), but this function
        accepts a country parameter for backwards compatibility.
        Note: country is normalized to uppercase in the database.
        """
        query = """
            SELECT le_years
            FROM life_expectancy
            WHERE breed_id = ?
              AND (country = ? OR country = 'ALL')
              AND sex = 'all'
            ORDER BY
              CASE WHEN country = ? THEN 1 ELSE 2 END
            LIMIT 1
        """
        results = self.db.execute(query, (breed_id, country, country))
        if results:
            return results[0]["le_years"]
        return 12.0  # Default fallback

    def _sample_condition_cost(
        self,
        cost_low: float,
        cost_mid: float,
        cost_high: float,
        n_samples: int = 1,
    ) -> np.ndarray:
        """
        Sample costs from a triangular distribution.

        Args:
            cost_low: Minimum cost (10th percentile)
            cost_mid: Modal cost (most likely)
            cost_high: Maximum cost (90th percentile)
            n_samples: Number of samples

        Returns:
            Array of sampled costs
        """
        # Use triangular distribution with mode at cost_mid
        # Adjust mode position within [0, 1] range
        if cost_high <= cost_low:
            return np.full(n_samples, cost_mid)

        mode_position = (cost_mid - cost_low) / (cost_high - cost_low)
        mode_position = np.clip(mode_position, 0.01, 0.99)

        samples = self.rng.triangular(
            left=cost_low,
            mode=cost_mid,
            right=cost_high,
            size=n_samples,
        )
        return samples

    def _simulate_condition_occurrence(
        self,
        prevalence: float,
        years: int,
        age_band: str,
        n_simulations: int,
    ) -> np.ndarray:
        """
        Simulate whether a condition occurs in each year.

        Args:
            prevalence: Lifetime prevalence
            years: Number of years to simulate
            age_band: Age band for the condition
            n_simulations: Number of simulation paths

        Returns:
            Boolean array (n_simulations, years) of condition occurrences
        """
        # Convert lifetime prevalence to annual probability
        # Using: 1 - (1-p)^n = lifetime_prevalence
        # So: annual_prob ≈ 1 - (1 - lifetime_prevalence)^(1/n)
        if prevalence >= 1.0:
            annual_prob = 0.99
        elif prevalence <= 0:
            annual_prob = 0.0
        else:
            # Approximate annual probability
            annual_prob = 1 - (1 - prevalence) ** (1 / years)

        # Adjust for age band
        age_weights = self._get_age_weights(age_band, years)

        # Generate occurrence matrix
        occurrences = np.zeros((n_simulations, years), dtype=bool)
        for year in range(years):
            adjusted_prob = annual_prob * age_weights[year]
            occurrences[:, year] = self.rng.random(n_simulations) < adjusted_prob

        return occurrences

    def _get_age_weights(self, age_band: str, years: int) -> np.ndarray:
        """
        Get age-based probability weights.

        Args:
            age_band: Condition age band
            years: Number of years

        Returns:
            Array of weights for each year
        """
        weights = np.ones(years)

        if age_band == "puppy":
            # Higher risk in first 2 years
            weights[:2] = 2.0
            weights[2:] = 0.2
        elif age_band == "junior":
            # Higher risk in years 1-3
            weights[:1] = 0.5
            weights[1:4] = 1.5
            weights[4:] = 0.5
        elif age_band == "senior":
            # Higher risk in later years
            senior_start = max(years // 2, 5)
            weights[:senior_start] = 0.3
            weights[senior_start:] = 2.0
        # 'adult' and 'all' keep uniform weights

        # Normalize
        weights = weights / weights.mean()
        return weights

    def simulate_annual_costs(
        self,
        breed_id: str,
        country: str = "UK",
        year: int = 0,
    ) -> SimulationResult:
        """
        Simulate annual veterinary costs for a breed.

        Args:
            breed_id: Breed identifier
            country: Country code
            year: Age of pet (0-indexed)

        Returns:
            SimulationResult with cost distribution
        """
        risks = self._get_breed_risks(breed_id)
        costs = self._get_cost_assumptions(country)
        life_exp = self._get_life_expectancy(breed_id, country)

        if risks.empty or costs.empty:
            logger.warning(f"Insufficient data for {breed_id}/{country}")
            return SimulationResult(
                breed_id=breed_id,
                country=country,
                age_start=year,
                age_end=year + 1,
                p10=0.0,
                p50=0.0,
                p90=0.0,
                mean=0.0,
                std=0.0,
                model_version=MODEL_VERSION,
                is_synthetic=True,
                iterations=self.iterations,
            )

        # Merge risks with costs
        merged = risks.merge(costs, on="condition_id", how="inner", suffixes=("", "_cost"))

        if merged.empty:
            logger.warning(f"No cost data for conditions affecting {breed_id}")
            return SimulationResult(
                breed_id=breed_id,
                country=country,
                age_start=year,
                age_end=year + 1,
                p10=0.0,
                p50=0.0,
                p90=0.0,
                mean=0.0,
                std=0.0,
                model_version=MODEL_VERSION,
                is_synthetic=True,
                iterations=self.iterations,
            )

        # Simulate costs for each condition
        total_costs = np.zeros(self.iterations)

        for _, row in merged.iterrows():
            # Simulate occurrence
            occurrences = self._simulate_condition_occurrence(
                prevalence=row["prevalence"],
                years=int(life_exp),
                age_band=row["age_band"],
                n_simulations=self.iterations,
            )

            # Check if condition occurs in target year
            year_idx = min(year, occurrences.shape[1] - 1)
            occurs = occurrences[:, year_idx]

            # Sample costs for occurrences
            if occurs.any():
                sampled_costs = self._sample_condition_cost(
                    cost_low=row["cost_low"],
                    cost_mid=row["cost_mid"],
                    cost_high=row["cost_high"],
                    n_samples=self.iterations,
                )
                total_costs += occurs * sampled_costs

        # Calculate percentiles
        p10 = float(np.percentile(total_costs, 10))
        p50 = float(np.percentile(total_costs, 50))
        p90 = float(np.percentile(total_costs, 90))
        mean = float(np.mean(total_costs))
        std = float(np.std(total_costs))

        return SimulationResult(
            breed_id=breed_id,
            country=country,
            age_start=year,
            age_end=year + 1,
            p10=round(p10, 2),
            p50=round(p50, 2),
            p90=round(p90, 2),
            mean=round(mean, 2),
            std=round(std, 2),
            model_version=MODEL_VERSION,
            is_synthetic=True,
            iterations=self.iterations,
        )

    def simulate_lifetime_costs(
        self,
        breed_id: str,
        country: str = "UK",
    ) -> SimulationResult:
        """
        Simulate total lifetime veterinary costs for a breed.

        Args:
            breed_id: Breed identifier
            country: Country code

        Returns:
            SimulationResult with lifetime cost distribution
        """
        risks = self._get_breed_risks(breed_id)
        costs = self._get_cost_assumptions(country)
        life_exp = self._get_life_expectancy(breed_id, country)
        years = int(np.ceil(life_exp))

        if risks.empty or costs.empty:
            logger.warning(f"Insufficient data for lifetime simulation: {breed_id}/{country}")
            return SimulationResult(
                breed_id=breed_id,
                country=country,
                age_start=0,
                age_end=years,
                p10=0.0,
                p50=0.0,
                p90=0.0,
                mean=0.0,
                std=0.0,
                model_version=MODEL_VERSION,
                is_synthetic=True,
                iterations=self.iterations,
            )

        # Merge risks with costs
        merged = risks.merge(costs, on="condition_id", how="inner", suffixes=("", "_cost"))

        if merged.empty:
            return SimulationResult(
                breed_id=breed_id,
                country=country,
                age_start=0,
                age_end=years,
                p10=0.0,
                p50=0.0,
                p90=0.0,
                mean=0.0,
                std=0.0,
                model_version=MODEL_VERSION,
                is_synthetic=True,
                iterations=self.iterations,
            )

        # Simulate lifetime costs
        total_costs = np.zeros(self.iterations)

        for _, row in merged.iterrows():
            # Simulate occurrence across lifetime
            occurrences = self._simulate_condition_occurrence(
                prevalence=row["prevalence"],
                years=years,
                age_band=row["age_band"],
                n_simulations=self.iterations,
            )

            # Count occurrences and sample costs
            n_occurrences = occurrences.sum(axis=1)

            # For chronic/management conditions, cost applies each year
            if row["cost_type"] == "annual_management":
                for sim_idx in range(self.iterations):
                    if n_occurrences[sim_idx] > 0:
                        # Once diagnosed, annual cost applies for remaining life
                        first_occurrence = np.argmax(occurrences[sim_idx])
                        years_with_condition = years - first_occurrence
                        annual_cost = self._sample_condition_cost(
                            row["cost_low"],
                            row["cost_mid"],
                            row["cost_high"],
                            n_samples=1,
                        )[0]
                        total_costs[sim_idx] += annual_cost * years_with_condition
            else:
                # One-time treatment cost per occurrence
                for sim_idx in range(self.iterations):
                    if n_occurrences[sim_idx] > 0:
                        treatment_cost = self._sample_condition_cost(
                            row["cost_low"],
                            row["cost_mid"],
                            row["cost_high"],
                            n_samples=1,
                        )[0]
                        total_costs[sim_idx] += treatment_cost * min(n_occurrences[sim_idx], 3)

        # Calculate percentiles
        p10 = float(np.percentile(total_costs, 10))
        p50 = float(np.percentile(total_costs, 50))
        p90 = float(np.percentile(total_costs, 90))
        mean = float(np.mean(total_costs))
        std = float(np.std(total_costs))

        return SimulationResult(
            breed_id=breed_id,
            country=country,
            age_start=0,
            age_end=years,
            p10=round(p10, 2),
            p50=round(p50, 2),
            p90=round(p90, 2),
            mean=round(mean, 2),
            std=round(std, 2),
            model_version=MODEL_VERSION,
            is_synthetic=True,
            iterations=self.iterations,
        )

    def store_results(self, result: SimulationResult) -> None:
        """
        Store simulation results in the database.

        Args:
            result: SimulationResult to store
        """
        query = """
            INSERT OR REPLACE INTO simulated_costs
            (breed_id, country, age_start, age_end, p10, p50, p90, mean, std,
             model_version, is_synthetic, generated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.db.execute(
            query,
            (
                result.breed_id,
                result.country,
                result.age_start,
                result.age_end,
                result.p10,
                result.p50,
                result.p90,
                result.mean,
                result.std,
                result.model_version,
                result.is_synthetic,
                datetime.now().isoformat(),
            ),
        )
        logger.debug(f"Stored simulation result for {result.breed_id}")


def simulate_breed_costs(
    breed_id: str,
    country: str = "UK",
    store: bool = True,
) -> dict[str, SimulationResult]:
    """
    Run full cost simulation for a breed (annual + lifetime).

    Args:
        breed_id: Breed identifier
        country: Country code
        store: Whether to store results in database

    Returns:
        Dictionary with 'annual' and 'lifetime' SimulationResults
    """
    simulator = CostSimulator()

    # Get life expectancy for simulation
    le = simulator._get_life_expectancy(breed_id, country)
    years = int(np.ceil(le))

    results = {}

    # Simulate annual costs for each year
    annual_results = []
    for year in range(years):
        annual = simulator.simulate_annual_costs(breed_id, country, year)
        annual_results.append(annual)
        if store:
            simulator.store_results(annual)

    # Use middle year as representative annual cost
    mid_year = years // 2
    results["annual"] = annual_results[mid_year] if annual_results else None

    # Simulate lifetime costs
    lifetime = simulator.simulate_lifetime_costs(breed_id, country)
    if store:
        simulator.store_results(lifetime)
    results["lifetime"] = lifetime

    logger.info(f"Simulated costs for {breed_id}: lifetime P50=£{lifetime.p50:,.0f}")

    return results


def get_stored_costs(
    breed_id: str,
    country: str = "UK",
) -> Optional[dict]:
    """
    Retrieve stored cost simulation results.

    Args:
        breed_id: Breed identifier
        country: Country code

    Returns:
        Dictionary with stored results or None if not found
    """
    db = get_db()

    query = """
        SELECT *
        FROM simulated_costs
        WHERE breed_id = ?
          AND country = ?
        ORDER BY age_end - age_start DESC
    """

    results = db.execute(query, (breed_id, country))

    if not results:
        return None

    output = {"annual": None, "lifetime": None}

    for row in results:
        duration = row["age_end"] - row["age_start"]
        if duration == 1 and output["annual"] is None:
            output["annual"] = dict(row)
        elif duration > 1:
            output["lifetime"] = dict(row)

    return output
