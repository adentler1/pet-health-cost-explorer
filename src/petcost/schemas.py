"""SQLite schema definitions for Pet Health Cost Explorer."""

from petcost.db import get_db
from petcost.logging_config import get_logger

logger = get_logger(__name__)

# SQL schema for all tables
SCHEMA_SQL = """
-- Breeds table: stores all dog and cat breeds
CREATE TABLE IF NOT EXISTS breeds (
    breed_id TEXT PRIMARY KEY,
    species TEXT NOT NULL CHECK(species IN ('dog', 'cat')),
    breed_name TEXT NOT NULL,
    alt_names TEXT,  -- Comma-separated alternative names
    source TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for species lookups
CREATE INDEX IF NOT EXISTS idx_breeds_species ON breeds(species);

-- Life expectancy table: breed-specific life expectancy data
CREATE TABLE IF NOT EXISTS life_expectancy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    breed_id TEXT NOT NULL,
    sex TEXT NOT NULL CHECK(sex IN ('male', 'female', 'all')),
    country TEXT NOT NULL,
    le_years REAL NOT NULL,  -- Median life expectancy
    le_low REAL,             -- Lower confidence bound
    le_high REAL,            -- Upper confidence bound
    source TEXT NOT NULL,
    citation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (breed_id) REFERENCES breeds(breed_id),
    UNIQUE(breed_id, sex, country)
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_life_expectancy_breed ON life_expectancy(breed_id);
CREATE INDEX IF NOT EXISTS idx_life_expectancy_country ON life_expectancy(country);

-- Conditions table: catalog of health conditions
CREATE TABLE IF NOT EXISTS conditions (
    condition_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for category lookups
CREATE INDEX IF NOT EXISTS idx_conditions_category ON conditions(category);

-- Breed condition risk table: links breeds to their condition risks
CREATE TABLE IF NOT EXISTS breed_condition_risk (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    breed_id TEXT NOT NULL,
    condition_id TEXT NOT NULL,
    metric_type TEXT NOT NULL CHECK(metric_type IN ('prevalence', 'incidence', 'odds_ratio', 'relative_risk')),
    metric_value REAL NOT NULL,
    age_band TEXT NOT NULL CHECK(age_band IN ('puppy', 'junior', 'adult', 'senior', 'all')),
    source TEXT NOT NULL,
    citation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (breed_id) REFERENCES breeds(breed_id),
    FOREIGN KEY (condition_id) REFERENCES conditions(condition_id),
    UNIQUE(breed_id, condition_id, metric_type, age_band)
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_breed_condition_risk_breed ON breed_condition_risk(breed_id);
CREATE INDEX IF NOT EXISTS idx_breed_condition_risk_condition ON breed_condition_risk(condition_id);

-- Cost assumptions table: cost data for conditions
CREATE TABLE IF NOT EXISTS cost_assumptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    condition_id TEXT NOT NULL,
    country TEXT NOT NULL,
    cost_type TEXT NOT NULL CHECK(cost_type IN ('treatment', 'annual_management', 'diagnosis', 'surgery')),
    cost_low REAL NOT NULL,
    cost_mid REAL NOT NULL,
    cost_high REAL NOT NULL,
    currency TEXT NOT NULL,
    year INTEGER NOT NULL,
    source TEXT NOT NULL,
    citation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (condition_id) REFERENCES conditions(condition_id),
    UNIQUE(condition_id, country, cost_type)
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_cost_assumptions_condition ON cost_assumptions(condition_id);
CREATE INDEX IF NOT EXISTS idx_cost_assumptions_country ON cost_assumptions(country);

-- Simulated costs table: Monte Carlo simulation results
CREATE TABLE IF NOT EXISTS simulated_costs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    breed_id TEXT NOT NULL,
    country TEXT NOT NULL,
    age_start INTEGER NOT NULL,
    age_end INTEGER NOT NULL,
    p10 REAL NOT NULL,          -- 10th percentile
    p50 REAL NOT NULL,          -- Median (50th percentile)
    p90 REAL NOT NULL,          -- 90th percentile
    mean REAL NOT NULL,         -- Mean cost
    std REAL NOT NULL,          -- Standard deviation
    model_version TEXT NOT NULL,
    is_synthetic BOOLEAN NOT NULL DEFAULT 1,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (breed_id) REFERENCES breeds(breed_id),
    UNIQUE(breed_id, country, age_start, age_end, model_version)
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_simulated_costs_breed ON simulated_costs(breed_id);
CREATE INDEX IF NOT EXISTS idx_simulated_costs_country ON simulated_costs(country);

-- Metadata table: store information about data updates
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- GOT Historical table: German veterinary fee schedule history for inflation analysis
CREATE TABLE IF NOT EXISTS got_historical (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    procedure_id TEXT NOT NULL,
    procedure_name TEXT NOT NULL,
    category TEXT NOT NULL,
    species TEXT NOT NULL CHECK(species IN ('dog', 'cat', 'all')),
    year INTEGER NOT NULL,
    got_version TEXT NOT NULL,
    fee_1x REAL NOT NULL,           -- Base fee (1-facher Satz)
    fee_2x REAL NOT NULL,           -- Double fee (2-facher Satz)
    fee_3x REAL NOT NULL,           -- Triple fee (3-facher Satz)
    currency TEXT NOT NULL DEFAULT 'EUR',
    source TEXT NOT NULL,
    citation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(procedure_id, species, year)
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_got_historical_procedure ON got_historical(procedure_id);
CREATE INDEX IF NOT EXISTS idx_got_historical_year ON got_historical(year);
CREATE INDEX IF NOT EXISTS idx_got_historical_species ON got_historical(species);
"""


def create_schema() -> None:
    """Create all database tables."""
    db = get_db()
    logger.info("Creating database schema...")
    db.execute_script(SCHEMA_SQL)
    logger.info("Schema created successfully")


def drop_all_tables() -> None:
    """Drop all tables in the database."""
    db = get_db()
    logger.warning("Dropping all tables...")
    db.drop_all_tables()
    logger.info("All tables dropped")


def get_table_stats() -> dict[str, int]:
    """
    Get row counts for all tables.

    Returns:
        Dictionary mapping table names to row counts
    """
    db = get_db()
    tables = [
        "breeds",
        "life_expectancy",
        "conditions",
        "breed_condition_risk",
        "cost_assumptions",
        "simulated_costs",
        "got_historical",
        "metadata",
    ]
    stats = {}
    for table in tables:
        if db.table_exists(table):
            stats[table] = db.get_table_count(table)
        else:
            stats[table] = 0
    return stats


def verify_schema() -> bool:
    """
    Verify that all required tables exist.

    Returns:
        True if all tables exist
    """
    db = get_db()
    required_tables = [
        "breeds",
        "life_expectancy",
        "conditions",
        "breed_condition_risk",
        "cost_assumptions",
        "simulated_costs",
    ]
    for table in required_tables:
        if not db.table_exists(table):
            logger.error(f"Missing table: {table}")
            return False
    return True
