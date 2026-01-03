"""Database build pipeline for Pet Health Cost Explorer.

This module orchestrates the complete database build process:
1. Create schema
2. Load seed data
3. Run cost simulations
4. Update metadata
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from petcost.config import get_settings
from petcost.db import get_db, reset_db
from petcost.features.cost_model import CostSimulator
from petcost.ingest.sources import (
    load_seed_breeds,
    load_seed_cost_mapping,
    load_seed_got_historical,
    load_seed_life_expectancy,
    load_seed_risk_profiles,
)
from petcost.logging_config import get_logger
from petcost.schemas import create_schema, drop_all_tables, get_table_stats

logger = get_logger(__name__)


def load_breeds(db: object) -> int:
    """
    Load breed data into the database.

    Args:
        db: Database connection

    Returns:
        Number of rows inserted
    """
    logger.info("Loading breeds...")
    df = load_seed_breeds()

    # Select and rename columns for database
    df_insert = df[["species", "breed_id", "breed_name", "alt_names", "source"]]

    return db.insert_df(df_insert, "breeds", if_exists="append")


def load_life_expectancy(db: object) -> int:
    """
    Load life expectancy data into the database.

    Args:
        db: Database connection

    Returns:
        Number of rows inserted
    """
    logger.info("Loading life expectancy data...")
    df = load_seed_life_expectancy()

    # Select columns for database
    df_insert = df[
        ["breed_id", "sex", "country", "le_years", "le_low", "le_high", "source", "citation"]
    ]

    return db.insert_df(df_insert, "life_expectancy", if_exists="append")


def load_conditions_and_risks(db: object) -> tuple[int, int]:
    """
    Load conditions and risk profile data into the database.

    Args:
        db: Database connection

    Returns:
        Tuple of (conditions_inserted, risks_inserted)
    """
    logger.info("Loading conditions and risk profiles...")

    # Load risk profiles which contain condition references
    risks_df = load_seed_risk_profiles()

    # Load cost mapping which has condition details
    costs_df = load_seed_cost_mapping()

    # Extract unique conditions from cost mapping
    conditions_df = costs_df[["condition_id", "condition_name", "category"]].drop_duplicates()
    conditions_df = conditions_df.rename(columns={"condition_name": "name"})

    # Insert conditions
    conditions_inserted = db.insert_df(conditions_df, "conditions", if_exists="append")

    # Insert risk profiles
    risks_insert = risks_df[
        ["breed_id", "condition_id", "metric_type", "metric_value", "age_band", "source", "citation"]
    ]
    risks_inserted = db.insert_df(risks_insert, "breed_condition_risk", if_exists="append")

    return conditions_inserted, risks_inserted


def load_cost_assumptions(db: object) -> int:
    """
    Load cost assumption data into the database.

    Args:
        db: Database connection

    Returns:
        Number of rows inserted
    """
    logger.info("Loading cost assumptions...")
    df = load_seed_cost_mapping()

    # Select and rename columns for database
    df_insert = df[
        [
            "condition_id",
            "country",
            "cost_type",
            "cost_low",
            "cost_mid",
            "cost_high",
            "currency",
            "year",
            "source",
            "citation",
        ]
    ]

    return db.insert_df(df_insert, "cost_assumptions", if_exists="append")


def load_got_historical(db: object) -> int:
    """
    Load GOT historical fee data into the database.

    Args:
        db: Database connection

    Returns:
        Number of rows inserted
    """
    logger.info("Loading GOT historical data...")
    df = load_seed_got_historical()

    # Select columns for database
    df_insert = df[
        [
            "procedure_id",
            "procedure_name",
            "category",
            "species",
            "year",
            "got_version",
            "fee_1x",
            "fee_2x",
            "fee_3x",
            "currency",
            "source",
            "citation",
        ]
    ]

    return db.insert_df(df_insert, "got_historical", if_exists="append")


def run_cost_simulations(db: object) -> int:
    """
    Run cost simulations for all breeds.

    Args:
        db: Database connection

    Returns:
        Number of simulations run
    """
    logger.info("Running cost simulations...")

    # Get all breeds
    breeds = db.query_df("SELECT breed_id, species FROM breeds")

    if breeds.empty:
        logger.warning("No breeds found, skipping simulations")
        return 0

    settings = get_settings()
    simulator = CostSimulator(
        seed=settings.simulation_seed,
        iterations=settings.simulation_iterations,
    )

    simulations_run = 0

    logger.info(f"Found {len(breeds)} breeds to simulate")

    for _, row in breeds.iterrows():
        breed_id = row["breed_id"]
        logger.debug(f"Processing {breed_id}...")

        try:
            # Simulate annual costs (use middle year)
            # Life expectancy is universal (country='ALL'), so query accordingly
            # Note: country is normalized to uppercase in the database
            le_result = db.execute(
                """SELECT le_years FROM life_expectancy
                   WHERE breed_id = ? AND sex = 'all'
                   AND (country = ? OR country = 'ALL')
                   ORDER BY CASE WHEN country = ? THEN 1 ELSE 2 END LIMIT 1""",
                (breed_id, settings.default_country, settings.default_country),
            )

            logger.debug(f"  Life expectancy result for {breed_id}: {le_result}")

            if le_result:
                life_exp = le_result[0]["le_years"]
                mid_year = int(life_exp) // 2

                annual_result = simulator.simulate_annual_costs(
                    breed_id,
                    settings.default_country,
                    mid_year,
                )
                simulator.store_results(annual_result)
                simulations_run += 1

                # Simulate lifetime costs
                lifetime_result = simulator.simulate_lifetime_costs(
                    breed_id,
                    settings.default_country,
                )
                simulator.store_results(lifetime_result)
                simulations_run += 1

                logger.debug(f"Simulated {breed_id} ({settings.default_country}): annual P50={annual_result.p50:.0f}, lifetime P50={lifetime_result.p50:.0f}")

        except Exception as e:
            logger.error(f"Failed to simulate {breed_id}: {e}")

    logger.info(f"Completed {simulations_run} simulations")
    return simulations_run


def update_metadata(db: object) -> None:
    """
    Update metadata table with build information.

    Args:
        db: Database connection
    """
    logger.info("Updating metadata...")

    metadata = {
        "last_build": datetime.now().isoformat(),
        "build_version": "1.0.0",
        "data_version": "seed_v1",
        "simulation_seed": str(get_settings().simulation_seed),
        "simulation_iterations": str(get_settings().simulation_iterations),
    }

    for key, value in metadata.items():
        db.execute(
            "INSERT OR REPLACE INTO metadata (key, value, updated_at) VALUES (?, ?, ?)",
            (key, value, datetime.now().isoformat()),
        )


def build_database(rebuild: bool = False) -> dict[str, int]:
    """
    Build the complete database from seed data.

    Args:
        rebuild: If True, drop all tables first

    Returns:
        Dictionary with table statistics
    """
    logger.info("=" * 60)
    logger.info("Starting database build")
    logger.info("=" * 60)

    settings = get_settings()
    db_path = settings.database_path_absolute

    logger.info(f"Database path: {db_path}")
    logger.info(f"Seed data path: {settings.seed_data_path}")

    # Reset database connection
    db = reset_db()

    if rebuild:
        logger.info("Rebuild requested, dropping all tables...")
        drop_all_tables()

    # Create schema
    create_schema()

    # Load data
    breeds_count = load_breeds(db)
    logger.info(f"Loaded {breeds_count} breeds")

    le_count = load_life_expectancy(db)
    logger.info(f"Loaded {le_count} life expectancy records")

    conditions_count, risks_count = load_conditions_and_risks(db)
    logger.info(f"Loaded {conditions_count} conditions and {risks_count} risk profiles")

    costs_count = load_cost_assumptions(db)
    logger.info(f"Loaded {costs_count} cost assumptions")

    got_count = load_got_historical(db)
    logger.info(f"Loaded {got_count} GOT historical records")

    # Run simulations
    if settings.use_synthetic_costs:
        sim_count = run_cost_simulations(db)
        logger.info(f"Ran {sim_count} cost simulations")

    # Update metadata
    update_metadata(db)

    # Get final stats
    stats = get_table_stats()

    logger.info("=" * 60)
    logger.info("Database build complete!")
    logger.info("Table statistics:")
    for table, count in stats.items():
        logger.info(f"  {table}: {count} rows")
    logger.info("=" * 60)

    return stats


def main() -> int:
    """
    Main entry point for database build.

    Returns:
        Exit code (0 for success)
    """
    parser = argparse.ArgumentParser(
        description="Build the Pet Health Cost Explorer database"
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Drop all tables and rebuild from scratch",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    try:
        stats = build_database(rebuild=args.rebuild)
        print("\nDatabase build successful!")
        print(f"Total tables: {len(stats)}")
        print(f"Total rows: {sum(stats.values())}")
        return 0

    except Exception as e:
        logger.error(f"Database build failed: {e}")
        print(f"\nError: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
