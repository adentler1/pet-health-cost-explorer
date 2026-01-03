"""Risk profile feature computations for Pet Health Cost Explorer."""

from typing import Literal, Optional

import pandas as pd

from petcost.db import get_db
from petcost.logging_config import get_logger

logger = get_logger(__name__)


def get_breed_risk_summary(
    breed_id: str,
    age_band: Literal["puppy", "junior", "adult", "senior", "all"] = "all",
) -> dict:
    """
    Get a summary of health risks for a specific breed.

    Args:
        breed_id: Breed identifier
        age_band: Age band filter

    Returns:
        Dictionary with risk summary
    """
    db = get_db()

    query = """
        SELECT
            bcr.breed_id,
            b.breed_name,
            b.species,
            bcr.condition_id,
            c.name as condition_name,
            c.category,
            bcr.metric_type,
            bcr.metric_value,
            bcr.age_band,
            bcr.source
        FROM breed_condition_risk bcr
        JOIN breeds b ON bcr.breed_id = b.breed_id
        JOIN conditions c ON bcr.condition_id = c.condition_id
        WHERE bcr.breed_id = ?
          AND bcr.age_band = ?
        ORDER BY bcr.metric_value DESC
    """

    df = db.query_df(query, (breed_id, age_band))

    if df.empty:
        # Try with 'all' age band as fallback
        if age_band != "all":
            df = db.query_df(query, (breed_id, "all"))

    if df.empty:
        logger.warning(f"No risk data for {breed_id}/{age_band}")
        return {
            "breed_id": breed_id,
            "breed_name": None,
            "species": None,
            "condition_count": 0,
            "conditions": [],
            "categories": {},
        }

    # Group by category
    category_counts = df.groupby("category").size().to_dict()

    conditions = []
    for _, row in df.iterrows():
        conditions.append({
            "condition_id": row["condition_id"],
            "condition_name": row["condition_name"],
            "category": row["category"],
            "metric_type": row["metric_type"],
            "metric_value": row["metric_value"],
            "risk_level": _classify_risk_level(row["metric_value"], row["metric_type"]),
        })

    return {
        "breed_id": breed_id,
        "breed_name": df.iloc[0]["breed_name"],
        "species": df.iloc[0]["species"],
        "condition_count": len(conditions),
        "conditions": conditions,
        "categories": category_counts,
        "highest_risk": conditions[0] if conditions else None,
    }


def _classify_risk_level(
    value: float,
    metric_type: str,
) -> Literal["low", "moderate", "high", "very_high"]:
    """
    Classify a risk metric into a human-readable level.

    Args:
        value: Metric value
        metric_type: Type of metric (prevalence, odds_ratio, etc.)

    Returns:
        Risk level classification
    """
    if metric_type == "prevalence":
        if value >= 0.20:
            return "very_high"
        elif value >= 0.10:
            return "high"
        elif value >= 0.05:
            return "moderate"
        else:
            return "low"
    elif metric_type in ("odds_ratio", "relative_risk"):
        if value >= 3.0:
            return "very_high"
        elif value >= 2.0:
            return "high"
        elif value >= 1.5:
            return "moderate"
        else:
            return "low"
    else:
        # Default classification
        if value >= 0.15:
            return "high"
        elif value >= 0.08:
            return "moderate"
        else:
            return "low"


def get_top_conditions_by_breed(
    breed_id: str,
    limit: int = 5,
    age_band: str = "all",
) -> list[dict]:
    """
    Get the top health conditions for a breed by risk.

    Args:
        breed_id: Breed identifier
        limit: Maximum number of conditions to return
        age_band: Age band filter

    Returns:
        List of top conditions with risk data
    """
    db = get_db()

    query = """
        SELECT
            bcr.condition_id,
            c.name as condition_name,
            c.category,
            bcr.metric_type,
            bcr.metric_value,
            bcr.source
        FROM breed_condition_risk bcr
        JOIN conditions c ON bcr.condition_id = c.condition_id
        WHERE bcr.breed_id = ?
          AND bcr.age_band = ?
        ORDER BY bcr.metric_value DESC
        LIMIT ?
    """

    results = db.execute(query, (breed_id, age_band, limit))

    conditions = []
    for row in results:
        conditions.append({
            "condition_id": row["condition_id"],
            "condition_name": row["condition_name"],
            "category": row["category"],
            "metric_type": row["metric_type"],
            "metric_value": row["metric_value"],
            "prevalence_percent": round(row["metric_value"] * 100, 1) if row["metric_type"] == "prevalence" else None,
            "risk_level": _classify_risk_level(row["metric_value"], row["metric_type"]),
            "source": row["source"],
        })

    return conditions


def compare_breed_risks(
    breed_id_1: str,
    breed_id_2: str,
    age_band: str = "all",
) -> pd.DataFrame:
    """
    Compare health risks between two breeds.

    Args:
        breed_id_1: First breed identifier
        breed_id_2: Second breed identifier
        age_band: Age band filter

    Returns:
        DataFrame with risk comparison
    """
    db = get_db()

    query = """
        SELECT
            bcr.condition_id,
            c.name as condition_name,
            c.category,
            bcr.breed_id,
            b.breed_name,
            bcr.metric_value
        FROM breed_condition_risk bcr
        JOIN conditions c ON bcr.condition_id = c.condition_id
        JOIN breeds b ON bcr.breed_id = b.breed_id
        WHERE bcr.breed_id IN (?, ?)
          AND bcr.age_band = ?
          AND bcr.metric_type = 'prevalence'
    """

    df = db.query_df(query, (breed_id_1, breed_id_2, age_band))

    if df.empty:
        return df

    # Pivot to compare side by side
    pivot = df.pivot_table(
        index=["condition_id", "condition_name", "category"],
        columns="breed_name",
        values="metric_value",
        aggfunc="first",
    ).reset_index()

    return pivot


def get_breeds_by_condition(
    condition_id: str,
    min_prevalence: float = 0.0,
    age_band: str = "all",
) -> pd.DataFrame:
    """
    Get all breeds affected by a specific condition.

    Args:
        condition_id: Condition identifier
        min_prevalence: Minimum prevalence threshold
        age_band: Age band filter

    Returns:
        DataFrame with breeds and their risk levels
    """
    db = get_db()

    query = """
        SELECT
            bcr.breed_id,
            b.breed_name,
            b.species,
            bcr.metric_value as prevalence,
            bcr.source
        FROM breed_condition_risk bcr
        JOIN breeds b ON bcr.breed_id = b.breed_id
        WHERE bcr.condition_id = ?
          AND bcr.age_band = ?
          AND bcr.metric_type = 'prevalence'
          AND bcr.metric_value >= ?
        ORDER BY bcr.metric_value DESC
    """

    return db.query_df(query, (condition_id, age_band, min_prevalence))


def get_condition_categories() -> list[str]:
    """
    Get all unique condition categories.

    Returns:
        List of category names
    """
    db = get_db()

    query = "SELECT DISTINCT category FROM conditions ORDER BY category"
    results = db.execute(query)

    return [row["category"] for row in results]


def get_breeds_by_risk_category(
    species: Literal["dog", "cat"],
    category: str,
    min_total_prevalence: float = 0.10,
) -> pd.DataFrame:
    """
    Get breeds with highest total risk in a specific category.

    Args:
        species: Species filter
        category: Condition category
        min_total_prevalence: Minimum sum of prevalences

    Returns:
        DataFrame with breeds and total category risk
    """
    db = get_db()

    query = """
        SELECT
            b.breed_id,
            b.breed_name,
            SUM(bcr.metric_value) as total_prevalence,
            COUNT(*) as condition_count
        FROM breed_condition_risk bcr
        JOIN breeds b ON bcr.breed_id = b.breed_id
        JOIN conditions c ON bcr.condition_id = c.condition_id
        WHERE b.species = ?
          AND c.category = ?
          AND bcr.metric_type = 'prevalence'
          AND bcr.age_band = 'all'
        GROUP BY b.breed_id, b.breed_name
        HAVING SUM(bcr.metric_value) >= ?
        ORDER BY total_prevalence DESC
    """

    return db.query_df(query, (species, category, min_total_prevalence))


def get_overall_breed_risk_score(
    breed_id: str,
) -> Optional[dict]:
    """
    Calculate an overall risk score for a breed.

    The score is based on the sum of all prevalences weighted by
    condition severity (approximated by typical treatment cost).

    Args:
        breed_id: Breed identifier

    Returns:
        Dictionary with risk score data or None if no data
    """
    db = get_db()

    query = """
        SELECT
            bcr.breed_id,
            b.breed_name,
            b.species,
            SUM(bcr.metric_value) as sum_prevalence,
            AVG(bcr.metric_value) as avg_prevalence,
            COUNT(*) as condition_count,
            MAX(bcr.metric_value) as max_prevalence
        FROM breed_condition_risk bcr
        JOIN breeds b ON bcr.breed_id = b.breed_id
        WHERE bcr.breed_id = ?
          AND bcr.metric_type = 'prevalence'
          AND bcr.age_band = 'all'
        GROUP BY bcr.breed_id, b.breed_name, b.species
    """

    results = db.execute(query, (breed_id,))

    if not results:
        return None

    row = results[0]

    # Calculate a normalized risk score (0-100)
    # Based on sum of prevalences, capped at reasonable maximum
    raw_score = row["sum_prevalence"] * 100
    normalized_score = min(100, raw_score)

    return {
        "breed_id": row["breed_id"],
        "breed_name": row["breed_name"],
        "species": row["species"],
        "risk_score": round(normalized_score, 1),
        "sum_prevalence": round(row["sum_prevalence"], 3),
        "avg_prevalence": round(row["avg_prevalence"], 3),
        "condition_count": row["condition_count"],
        "max_prevalence": round(row["max_prevalence"], 3),
        "risk_category": _classify_overall_risk(normalized_score),
    }


def _classify_overall_risk(score: float) -> str:
    """Classify overall risk score into category."""
    if score >= 70:
        return "High Risk"
    elif score >= 40:
        return "Moderate Risk"
    elif score >= 20:
        return "Low-Moderate Risk"
    else:
        return "Low Risk"
