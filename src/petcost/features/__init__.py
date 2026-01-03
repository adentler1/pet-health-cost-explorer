"""Feature computation modules for Pet Health Cost Explorer."""

from petcost.features.cost_model import CostSimulator, simulate_breed_costs
from petcost.features.life_expectancy import (
    get_breed_life_expectancy,
    get_life_expectancy_comparison,
)
from petcost.features.risk_profiles import (
    get_breed_risk_summary,
    get_top_conditions_by_breed,
)

__all__ = [
    "get_breed_life_expectancy",
    "get_life_expectancy_comparison",
    "get_breed_risk_summary",
    "get_top_conditions_by_breed",
    "CostSimulator",
    "simulate_breed_costs",
]
