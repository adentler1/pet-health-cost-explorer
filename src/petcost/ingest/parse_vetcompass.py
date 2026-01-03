"""Parser for VetCompass data extracts.

VetCompass is a research project by the Royal Veterinary College (RVC)
that provides epidemiological data on companion animal health.

This module provides utilities for parsing VetCompass data when available.
The pipeline runs offline using seed data; this is for optional enrichment.

Data source: https://www.rvc.ac.uk/vetcompass
License: Academic use; aggregated data may be redistributable.
"""

from typing import Optional

import pandas as pd
from bs4 import BeautifulSoup

from petcost.logging_config import get_logger

logger = get_logger(__name__)


def parse_vetcompass_breed_table(html: str) -> pd.DataFrame:
    """
    Parse a VetCompass breed statistics HTML table.

    Args:
        html: HTML content containing breed statistics table

    Returns:
        DataFrame with parsed breed data

    Note:
        This is a template for parsing VetCompass HTML tables.
        Actual structure depends on the specific page/report.
    """
    soup = BeautifulSoup(html, "lxml")

    # Find tables with breed data
    tables = soup.find_all("table")
    if not tables:
        logger.warning("No tables found in HTML")
        return pd.DataFrame()

    # Try to find the main data table
    data_rows = []
    for table in tables:
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        if not headers:
            continue

        # Look for relevant headers
        relevant_headers = ["breed", "life expectancy", "prevalence", "n", "count"]
        if not any(h.lower() in " ".join(headers).lower() for h in relevant_headers):
            continue

        # Parse rows
        for row in table.find_all("tr")[1:]:  # Skip header row
            cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
            if cells:
                data_rows.append(dict(zip(headers, cells)))

    if not data_rows:
        logger.warning("No data rows found in tables")
        return pd.DataFrame()

    df = pd.DataFrame(data_rows)
    logger.info(f"Parsed {len(df)} rows from VetCompass HTML")
    return df


def parse_vetcompass_condition_prevalence(html: str) -> pd.DataFrame:
    """
    Parse condition prevalence data from VetCompass HTML.

    Args:
        html: HTML content containing prevalence data

    Returns:
        DataFrame with condition prevalence by breed
    """
    soup = BeautifulSoup(html, "lxml")

    data_rows = []
    tables = soup.find_all("table")

    for table in tables:
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        if not headers:
            continue

        for row in table.find_all("tr")[1:]:
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cells) == len(headers):
                row_data = dict(zip(headers, cells))
                data_rows.append(row_data)

    return pd.DataFrame(data_rows)


def normalize_breed_name(name: str, species: str = "dog") -> Optional[str]:
    """
    Normalize a breed name to our standard format.

    Args:
        name: Raw breed name
        species: Species (dog or cat)

    Returns:
        Normalized breed_id or None if not matched
    """
    # Mapping of common variations to standard breed_ids
    dog_mappings = {
        "labrador retriever": "dog_labrador",
        "labrador": "dog_labrador",
        "lab": "dog_labrador",
        "german shepherd dog": "dog_german_shepherd",
        "german shepherd": "dog_german_shepherd",
        "gsd": "dog_german_shepherd",
        "alsatian": "dog_german_shepherd",
        "golden retriever": "dog_golden_retriever",
        "golden": "dog_golden_retriever",
        "french bulldog": "dog_french_bulldog",
        "frenchie": "dog_french_bulldog",
        "bulldog": "dog_bulldog",
        "english bulldog": "dog_bulldog",
        "british bulldog": "dog_bulldog",
        "poodle": "dog_poodle",
        "standard poodle": "dog_poodle",
        "beagle": "dog_beagle",
        "rottweiler": "dog_rottweiler",
        "yorkshire terrier": "dog_yorkshire_terrier",
        "yorkie": "dog_yorkshire_terrier",
        "boxer": "dog_boxer",
        "dachshund": "dog_dachshund",
        "sausage dog": "dog_dachshund",
        "shih tzu": "dog_shih_tzu",
        "siberian husky": "dog_siberian_husky",
        "husky": "dog_siberian_husky",
        "cavalier king charles spaniel": "dog_cavalier_king_charles",
        "cavalier": "dog_cavalier_king_charles",
        "pug": "dog_pug",
        "border collie": "dog_border_collie",
        "collie": "dog_border_collie",
        "cocker spaniel": "dog_cocker_spaniel",
        "jack russell terrier": "dog_jack_russell",
        "jack russell": "dog_jack_russell",
        "jrt": "dog_jack_russell",
        "miniature schnauzer": "dog_miniature_schnauzer",
        "chihuahua": "dog_chihuahua",
        "crossbreed": "dog_crossbreed",
        "mixed breed": "dog_crossbreed",
        "mongrel": "dog_crossbreed",
    }

    cat_mappings = {
        "domestic shorthair": "cat_domestic_shorthair",
        "dsh": "cat_domestic_shorthair",
        "moggy": "cat_domestic_shorthair",
        "domestic longhair": "cat_domestic_longhair",
        "dlh": "cat_domestic_longhair",
        "british shorthair": "cat_british_shorthair",
        "bsh": "cat_british_shorthair",
        "maine coon": "cat_maine_coon",
        "ragdoll": "cat_ragdoll",
        "siamese": "cat_siamese",
        "persian": "cat_persian",
        "bengal": "cat_bengal",
        "russian blue": "cat_russian_blue",
        "abyssinian": "cat_abyssinian",
        "sphynx": "cat_sphynx",
        "scottish fold": "cat_scottish_fold",
        "burmese": "cat_burmese",
        "birman": "cat_birman",
        "norwegian forest cat": "cat_norwegian_forest",
        "norwegian forest": "cat_norwegian_forest",
    }

    normalized = name.lower().strip()

    if species.lower() == "dog":
        return dog_mappings.get(normalized)
    elif species.lower() == "cat":
        return cat_mappings.get(normalized)

    return None


def parse_life_expectancy_study(
    supplementary_csv: str,
) -> pd.DataFrame:
    """
    Parse life expectancy data from VetCompass study supplementary materials.

    Expected format matches Teng et al. 2022 Scientific Reports.

    Args:
        supplementary_csv: CSV content from study supplementary materials

    Returns:
        DataFrame with life expectancy data
    """
    from io import StringIO

    df = pd.read_csv(StringIO(supplementary_csv))

    # Standardize column names
    column_mapping = {
        "Breed": "breed_name",
        "breed": "breed_name",
        "Median life expectancy": "le_years",
        "median_life_expectancy": "le_years",
        "Lower CI": "le_low",
        "lower_ci": "le_low",
        "Upper CI": "le_high",
        "upper_ci": "le_high",
        "N": "sample_size",
        "n": "sample_size",
    }

    df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

    # Add breed_id by normalizing names
    if "breed_name" in df.columns:
        df["breed_id"] = df["breed_name"].apply(lambda x: normalize_breed_name(x, "dog"))

    logger.info(f"Parsed {len(df)} life expectancy records from supplementary data")
    return df
