"""Inflation analysis for German veterinary fees (GOT)."""

from typing import Literal, Optional

import pandas as pd

from petcost.db import get_db
from petcost.logging_config import get_logger

logger = get_logger(__name__)


def get_got_procedures() -> list[dict]:
    """
    Get list of all procedures tracked in GOT historical data.

    Returns:
        List of procedure dictionaries with id, name, and category
    """
    db = get_db()
    results = db.execute(
        """
        SELECT DISTINCT procedure_id, procedure_name, category
        FROM got_historical
        ORDER BY category, procedure_name
        """
    )
    return [dict(r) for r in results] if results else []


def get_got_years() -> list[int]:
    """
    Get list of years available in GOT historical data.

    Returns:
        List of years in ascending order
    """
    db = get_db()
    results = db.execute(
        "SELECT DISTINCT year FROM got_historical ORDER BY year"
    )
    return [r["year"] for r in results] if results else []


def get_procedure_history(
    procedure_id: str,
    species: Literal["dog", "cat", "all"] = "dog",
) -> pd.DataFrame:
    """
    Get historical fee data for a specific procedure.

    Args:
        procedure_id: Procedure identifier
        species: Species filter (dog, cat, or all)

    Returns:
        DataFrame with year-by-year fee data
    """
    db = get_db()

    query = """
        SELECT
            year,
            got_version,
            fee_1x,
            fee_2x,
            fee_3x,
            yearly_inflation_pct,
            procedure_name,
            category,
            source
        FROM got_historical
        WHERE procedure_id = ?
          AND species = ?
        ORDER BY year
    """

    df = db.query_df(query, (procedure_id, species))

    if df.empty:
        logger.warning(f"No GOT data for procedure {procedure_id}/{species}")
        return df

    # Calculate cumulative change from baseline
    df["cumulative_change_pct"] = ((df["fee_1x"] / df["fee_1x"].iloc[0]) - 1) * 100

    return df


def get_inflation_summary(
    species: Literal["dog", "cat"] = "dog",
    base_year: int = 1999,
    compare_year: int = 2022,
) -> pd.DataFrame:
    """
    Get inflation summary comparing two years across all procedures.

    Args:
        species: Species to analyze
        base_year: Starting year for comparison
        compare_year: Ending year for comparison

    Returns:
        DataFrame with inflation data for each procedure
    """
    db = get_db()

    query = """
        SELECT
            g1.procedure_id,
            g1.procedure_name,
            g1.category,
            g1.fee_1x as fee_base,
            g2.fee_1x as fee_compare,
            ((g2.fee_1x - g1.fee_1x) / g1.fee_1x * 100) as change_pct
        FROM got_historical g1
        JOIN got_historical g2
            ON g1.procedure_id = g2.procedure_id
            AND g1.species = g2.species
        WHERE g1.species = ?
          AND g1.year = ?
          AND g2.year = ?
        ORDER BY change_pct DESC
    """

    df = db.query_df(query, (species, base_year, compare_year))

    if df.empty:
        logger.warning(f"No inflation data for {species} {base_year}-{compare_year}")

    return df


def get_category_inflation(
    species: Literal["dog", "cat"] = "dog",
) -> pd.DataFrame:
    """
    Get average inflation by procedure category.

    Args:
        species: Species to analyze

    Returns:
        DataFrame with category-level inflation statistics
    """
    db = get_db()

    query = """
        WITH yearly_data AS (
            SELECT
                category,
                year,
                AVG(fee_1x) as avg_fee
            FROM got_historical
            WHERE species = ?
            GROUP BY category, year
        ),
        inflation_calc AS (
            SELECT
                y1.category,
                y1.avg_fee as fee_1999,
                y2.avg_fee as fee_2022,
                ((y2.avg_fee - y1.avg_fee) / y1.avg_fee * 100) as total_inflation
            FROM yearly_data y1
            JOIN yearly_data y2 ON y1.category = y2.category
            WHERE y1.year = 1999 AND y2.year = 2022
        )
        SELECT * FROM inflation_calc
        ORDER BY total_inflation DESC
    """

    return db.query_df(query, (species,))


def get_all_procedures_timeline(
    species: Literal["dog", "cat"] = "dog",
) -> pd.DataFrame:
    """
    Get fee timeline for all procedures (for visualization).

    Args:
        species: Species to analyze

    Returns:
        DataFrame with procedure fees over time
    """
    db = get_db()

    query = """
        SELECT
            procedure_id,
            procedure_name,
            category,
            year,
            fee_1x,
            fee_2x,
            fee_3x
        FROM got_historical
        WHERE species = ?
        ORDER BY procedure_id, year
    """

    return db.query_df(query, (species,))


def calculate_annual_inflation_rate(
    species: Literal["dog", "cat"] = "dog",
    start_year: int = 1999,
    end_year: int = 2022,
) -> dict:
    """
    Calculate compound annual growth rate (CAGR) for veterinary fees.

    Args:
        species: Species to analyze
        start_year: Starting year
        end_year: Ending year

    Returns:
        Dictionary with inflation statistics
    """
    db = get_db()

    query = """
        SELECT
            year,
            AVG(fee_1x) as avg_fee
        FROM got_historical
        WHERE species = ?
          AND year IN (?, ?)
        GROUP BY year
        ORDER BY year
    """

    results = db.execute(query, (species, start_year, end_year))

    if len(results) < 2:
        return {"cagr": None, "total_change": None, "years": 0}

    fee_start = results[0]["avg_fee"]
    fee_end = results[1]["avg_fee"]
    years = end_year - start_year

    # CAGR formula: (end/start)^(1/years) - 1
    cagr = ((fee_end / fee_start) ** (1 / years) - 1) * 100
    total_change = ((fee_end / fee_start) - 1) * 100

    return {
        "cagr": round(cagr, 2),
        "total_change": round(total_change, 1),
        "years": years,
        "fee_start": round(fee_start, 2),
        "fee_end": round(fee_end, 2),
        "start_year": start_year,
        "end_year": end_year,
    }


def get_got_version_changes() -> pd.DataFrame:
    """
    Get summary of GOT version changes and their impact.

    Returns:
        DataFrame with GOT version information
    """
    db = get_db()

    query = """
        SELECT
            got_version,
            MIN(year) as year,
            COUNT(DISTINCT procedure_id) as procedures_affected,
            AVG(fee_1x) as avg_fee,
            source
        FROM got_historical
        GROUP BY got_version
        ORDER BY year
    """

    return db.query_df(query)
