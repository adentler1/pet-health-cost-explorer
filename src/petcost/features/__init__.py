"""Feature computation modules for Pet Health Cost Explorer."""

from petcost.features.cost_model import CostSimulator, simulate_breed_costs
from petcost.features.inflation import (
    calculate_annual_inflation_rate,
    get_all_procedures_timeline,
    get_category_inflation,
    get_got_procedures,
    get_got_years,
    get_inflation_summary,
    get_procedure_history,
)
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
    "calculate_annual_inflation_rate",
    "get_all_procedures_timeline",
    "get_category_inflation",
    "get_got_procedures",
    "get_got_years",
    "get_inflation_summary",
    "get_procedure_history",
]
