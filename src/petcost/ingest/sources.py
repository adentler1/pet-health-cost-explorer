"""Seed data loading functions for Pet Health Cost Explorer."""

from pathlib import Path
from typing import Optional

import pandas as pd

from petcost.config import get_settings
from petcost.logging_config import get_logger

logger = get_logger(__name__)


def _get_seed_path(filename: str, seed_dir: Optional[Path] = None) -> Path:
    """
    Get the full path to a seed data file.

    Args:
        filename: Name of the seed file
        seed_dir: Optional custom seed directory

    Returns:
        Path to the seed file
    """
    if seed_dir is None:
        settings = get_settings()
        seed_dir = settings.seed_data_path
    return seed_dir / filename


def load_seed_breeds(seed_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Load breed seed data from CSV.

    Args:
        seed_dir: Optional custom seed directory

    Returns:
        DataFrame with breed data
    """
    filepath = _get_seed_path("seed_breeds.csv", seed_dir)
    logger.info(f"Loading breeds from {filepath}")

    df = pd.read_csv(filepath)

    # Validate required columns
    required_cols = ["species", "breed_id", "breed_name", "source"]
    missing = set(required_cols) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in breeds CSV: {missing}")

    # Clean data
    df["species"] = df["species"].str.lower().str.strip()
    df["breed_id"] = df["breed_id"].str.lower().str.strip()
    df["breed_name"] = df["breed_name"].str.strip()
    df["alt_names"] = df["alt_names"].fillna("")

    logger.info(f"Loaded {len(df)} breeds ({df['species'].value_counts().to_dict()})")
    return df


def load_seed_life_expectancy(seed_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Load life expectancy seed data from CSV.

    Args:
        seed_dir: Optional custom seed directory

    Returns:
        DataFrame with life expectancy data
    """
    filepath = _get_seed_path("seed_life_expectancy.csv", seed_dir)
    logger.info(f"Loading life expectancy from {filepath}")

    df = pd.read_csv(filepath)

    # Validate required columns
    required_cols = ["breed_id", "sex", "country", "le_years", "source"]
    missing = set(required_cols) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in life expectancy CSV: {missing}")

    # Clean data
    df["breed_id"] = df["breed_id"].str.lower().str.strip()
    df["sex"] = df["sex"].str.lower().str.strip()
    df["country"] = df["country"].str.upper().str.strip()

    # Ensure numeric columns are float
    df["le_years"] = pd.to_numeric(df["le_years"], errors="coerce")
    df["le_low"] = pd.to_numeric(df["le_low"], errors="coerce")
    df["le_high"] = pd.to_numeric(df["le_high"], errors="coerce")

    logger.info(f"Loaded {len(df)} life expectancy records")
    return df


def load_seed_risk_profiles(seed_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Load risk profile seed data from CSV.

    Args:
        seed_dir: Optional custom seed directory

    Returns:
        DataFrame with risk profile data
    """
    filepath = _get_seed_path("seed_risk_profiles.csv", seed_dir)
    logger.info(f"Loading risk profiles from {filepath}")

    df = pd.read_csv(filepath)

    # Validate required columns
    required_cols = ["breed_id", "condition_id", "metric_type", "metric_value", "source"]
    missing = set(required_cols) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in risk profiles CSV: {missing}")

    # Clean data
    df["breed_id"] = df["breed_id"].str.lower().str.strip()
    df["condition_id"] = df["condition_id"].str.lower().str.strip()
    df["metric_type"] = df["metric_type"].str.lower().str.strip()
    df["age_band"] = df["age_band"].str.lower().str.strip()

    # Ensure metric_value is float
    df["metric_value"] = pd.to_numeric(df["metric_value"], errors="coerce")

    logger.info(f"Loaded {len(df)} risk profile records")
    return df


def load_seed_cost_mapping(seed_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Load cost mapping seed data from CSV.

    Args:
        seed_dir: Optional custom seed directory

    Returns:
        DataFrame with cost mapping data
    """
    filepath = _get_seed_path("seed_cost_mapping.csv", seed_dir)
    logger.info(f"Loading cost mapping from {filepath}")

    df = pd.read_csv(filepath)

    # Validate required columns
    required_cols = [
        "condition_id",
        "condition_name",
        "category",
        "country",
        "cost_type",
        "cost_low",
        "cost_mid",
        "cost_high",
        "currency",
        "year",
        "source",
    ]
    missing = set(required_cols) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in cost mapping CSV: {missing}")

    # Clean data
    df["condition_id"] = df["condition_id"].str.lower().str.strip()
    df["condition_name"] = df["condition_name"].str.strip()
    df["category"] = df["category"].str.lower().str.strip()
    df["country"] = df["country"].str.upper().str.strip()
    df["cost_type"] = df["cost_type"].str.lower().str.strip()
    df["currency"] = df["currency"].str.upper().str.strip()

    # Ensure numeric columns are float
    for col in ["cost_low", "cost_mid", "cost_high"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype(int)

    logger.info(f"Loaded {len(df)} cost mapping records")
    return df


def load_seed_got_historical(seed_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Load GOT historical fee data from CSV.

    Args:
        seed_dir: Optional custom seed directory

    Returns:
        DataFrame with GOT historical data
    """
    filepath = _get_seed_path("seed_got_historical.csv", seed_dir)
    logger.info(f"Loading GOT historical data from {filepath}")

    df = pd.read_csv(filepath)

    # Validate required columns
    required_cols = [
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
    ]
    missing = set(required_cols) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in GOT historical CSV: {missing}")

    # Clean data
    df["procedure_id"] = df["procedure_id"].str.lower().str.strip()
    df["procedure_name"] = df["procedure_name"].str.strip()
    df["category"] = df["category"].str.lower().str.strip()
    df["species"] = df["species"].str.lower().str.strip()
    df["got_version"] = df["got_version"].str.strip()
    df["currency"] = df["currency"].str.upper().str.strip()

    # Ensure numeric columns
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype(int)
    for col in ["fee_1x", "fee_2x", "fee_3x"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    logger.info(f"Loaded {len(df)} GOT historical records ({df['year'].nunique()} years)")
    return df


def validate_seed_data(seed_dir: Optional[Path] = None) -> dict[str, bool]:
    """
    Validate that all required seed data files exist and are valid.

    Args:
        seed_dir: Optional custom seed directory

    Returns:
        Dictionary mapping file names to validation status
    """
    results = {}

    try:
        load_seed_breeds(seed_dir)
        results["seed_breeds.csv"] = True
    except Exception as e:
        logger.error(f"Failed to load breeds: {e}")
        results["seed_breeds.csv"] = False

    try:
        load_seed_life_expectancy(seed_dir)
        results["seed_life_expectancy.csv"] = True
    except Exception as e:
        logger.error(f"Failed to load life expectancy: {e}")
        results["seed_life_expectancy.csv"] = False

    try:
        load_seed_risk_profiles(seed_dir)
        results["seed_risk_profiles.csv"] = True
    except Exception as e:
        logger.error(f"Failed to load risk profiles: {e}")
        results["seed_risk_profiles.csv"] = False

    try:
        load_seed_cost_mapping(seed_dir)
        results["seed_cost_mapping.csv"] = True
    except Exception as e:
        logger.error(f"Failed to load cost mapping: {e}")
        results["seed_cost_mapping.csv"] = False

    return results
