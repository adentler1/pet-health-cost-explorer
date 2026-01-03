"""Life expectancy feature computations for Pet Health Cost Explorer."""

from typing import Literal, Optional

import pandas as pd

from petcost.db import get_db
from petcost.logging_config import get_logger

logger = get_logger(__name__)


def get_breed_life_expectancy(
    breed_id: str,
    sex: Literal["male", "female", "all"] = "all",
    country: str = "UK",
) -> Optional[dict]:
    """
    Get life expectancy data for a specific breed.

    Life expectancy data is universal (country='ALL') but this function
    accepts a country parameter for backwards compatibility.
    Note: country is normalized to uppercase in the database.

    Args:
        breed_id: Breed identifier
        sex: Sex filter (male, female, or all)
        country: Country code (optional, data is country-independent)

    Returns:
        Dictionary with life expectancy data or None if not found
    """
    db = get_db()

    query = """
        SELECT
            le.breed_id,
            b.breed_name,
            b.species,
            le.sex,
            le.country,
            le.le_years,
            le.le_low,
            le.le_high,
            le.source,
            le.citation
        FROM life_expectancy le
        JOIN breeds b ON le.breed_id = b.breed_id
        WHERE le.breed_id = ?
          AND le.sex = ?
          AND (le.country = ? OR le.country = 'ALL')
        ORDER BY
          CASE WHEN le.country = ? THEN 1 ELSE 2 END
        LIMIT 1
    """

    results = db.execute(query, (breed_id, sex, country, country))

    if not results:
        logger.warning(f"No life expectancy data for {breed_id}/{sex}/{country}")
        return None

    row = results[0]
    return {
        "breed_id": row["breed_id"],
        "breed_name": row["breed_name"],
        "species": row["species"],
        "sex": row["sex"],
        "country": row["country"],
        "le_years": row["le_years"],
        "le_low": row["le_low"],
        "le_high": row["le_high"],
        "uncertainty_range": row["le_high"] - row["le_low"] if row["le_high"] and row["le_low"] else None,
        "source": row["source"],
        "citation": row["citation"],
    }


def get_life_expectancy_comparison(
    species: Literal["dog", "cat"],
    country: str = "UK",
    sex: Literal["male", "female", "all"] = "all",
) -> pd.DataFrame:
    """
    Get life expectancy comparison for all breeds of a species.

    Life expectancy data is universal (country='ALL') but this function
    accepts a country parameter for backwards compatibility.

    Args:
        species: Species to compare (dog or cat)
        country: Country code (optional, data is country-independent)
        sex: Sex filter

    Returns:
        DataFrame with life expectancy data for all breeds
    """
    db = get_db()

    query = """
        SELECT
            le.breed_id,
            b.breed_name,
            le.le_years,
            le.le_low,
            le.le_high,
            le.source
        FROM life_expectancy le
        JOIN breeds b ON le.breed_id = b.breed_id
        WHERE b.species = ?
          AND (le.country = ? OR le.country = 'ALL')
          AND le.sex = ?
        GROUP BY le.breed_id
        HAVING le.country = CASE
            WHEN MAX(CASE WHEN le.country = ? THEN 1 ELSE 0 END) = 1 THEN ?
            ELSE 'ALL'
        END
        ORDER BY le.le_years DESC
    """

    df = db.query_df(query, (species, country, sex, country, country))

    if df.empty:
        logger.warning(f"No life expectancy data for {species}/{country}/{sex}")
        return df

    # Add uncertainty column
    df["uncertainty"] = df["le_high"] - df["le_low"]

    logger.info(f"Retrieved life expectancy for {len(df)} {species} breeds")
    return df


def get_species_average_life_expectancy(
    species: Literal["dog", "cat"],
    country: str = "UK",
) -> dict:
    """
    Get average life expectancy statistics for a species.

    Life expectancy data is universal (country='ALL') but this function
    accepts a country parameter for backwards compatibility.

    Args:
        species: Species (dog or cat)
        country: Country code (optional, data is country-independent)

    Returns:
        Dictionary with average statistics
    """
    db = get_db()

    query = """
        SELECT
            AVG(le.le_years) as avg_le,
            MIN(le.le_years) as min_le,
            MAX(le.le_years) as max_le,
            COUNT(DISTINCT le.breed_id) as breed_count
        FROM life_expectancy le
        JOIN breeds b ON le.breed_id = b.breed_id
        WHERE b.species = ?
          AND (le.country = ? OR le.country = 'ALL')
          AND le.sex = 'all'
    """

    results = db.execute(query, (species, country))

    if not results or results[0]["avg_le"] is None:
        return {
            "species": species,
            "country": country,
            "avg_le": None,
            "min_le": None,
            "max_le": None,
            "breed_count": 0,
        }

    row = results[0]
    return {
        "species": species,
        "country": country,
        "avg_le": round(row["avg_le"], 1),
        "min_le": row["min_le"],
        "max_le": row["max_le"],
        "breed_count": row["breed_count"],
    }


def get_breeds_by_life_expectancy_range(
    species: Literal["dog", "cat"],
    min_years: float,
    max_years: float,
    country: str = "UK",
) -> pd.DataFrame:
    """
    Get breeds within a life expectancy range.

    Life expectancy data is universal (country='ALL') but this function
    accepts a country parameter for backwards compatibility.

    Args:
        species: Species (dog or cat)
        min_years: Minimum life expectancy
        max_years: Maximum life expectancy
        country: Country code (optional, data is country-independent)

    Returns:
        DataFrame with matching breeds
    """
    db = get_db()

    query = """
        SELECT
            le.breed_id,
            b.breed_name,
            le.le_years,
            le.le_low,
            le.le_high
        FROM life_expectancy le
        JOIN breeds b ON le.breed_id = b.breed_id
        WHERE b.species = ?
          AND (le.country = ? OR le.country = 'ALL')
          AND le.sex = 'all'
          AND le.le_years >= ?
          AND le.le_years <= ?
        GROUP BY le.breed_id
        HAVING le.country = CASE
            WHEN MAX(CASE WHEN le.country = ? THEN 1 ELSE 0 END) = 1 THEN ?
            ELSE 'ALL'
        END
        ORDER BY le.le_years DESC
    """

    return db.query_df(query, (species, country, min_years, max_years, country, country))


def compare_breed_to_species_average(
    breed_id: str,
    country: str = "UK",
) -> Optional[dict]:
    """
    Compare a breed's life expectancy to the species average.

    Args:
        breed_id: Breed identifier
        country: Country code

    Returns:
        Dictionary with comparison data or None if not found
    """
    breed_data = get_breed_life_expectancy(breed_id, "all", country)
    if not breed_data:
        return None

    species = breed_data["species"]
    species_avg = get_species_average_life_expectancy(species, country)

    if species_avg["avg_le"] is None:
        return None

    difference = breed_data["le_years"] - species_avg["avg_le"]
    percentage_diff = (difference / species_avg["avg_le"]) * 100

    return {
        "breed_id": breed_id,
        "breed_name": breed_data["breed_name"],
        "breed_le": breed_data["le_years"],
        "species_avg_le": species_avg["avg_le"],
        "difference_years": round(difference, 1),
        "difference_percent": round(percentage_diff, 1),
        "is_above_average": difference > 0,
    }
