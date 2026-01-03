"""Parser for Agria Pet Insurance breed profiles.

Agria is a Swedish pet insurance company that publishes breed-specific
health statistics and risk profiles on their website.

This module provides utilities for parsing Agria data when available.
The pipeline runs offline using seed data; this is for optional enrichment.

Data source: https://www.agria.se/
License: Public domain for aggregate statistics.
"""

from typing import Optional

import pandas as pd
from bs4 import BeautifulSoup

from petcost.logging_config import get_logger

logger = get_logger(__name__)


def parse_agria_breed_page(html: str) -> dict:
    """
    Parse a single Agria breed profile page.

    Args:
        html: HTML content of breed profile page

    Returns:
        Dictionary with breed health information
    """
    soup = BeautifulSoup(html, "lxml")

    breed_data = {
        "breed_name": None,
        "common_conditions": [],
        "life_expectancy": None,
        "insurance_claims_rate": None,
    }

    # Try to extract breed name from heading
    h1 = soup.find("h1")
    if h1:
        breed_data["breed_name"] = h1.get_text(strip=True)

    # Look for condition lists
    condition_sections = soup.find_all(["ul", "ol"])
    for section in condition_sections:
        items = section.find_all("li")
        for item in items:
            text = item.get_text(strip=True).lower()
            # Check if this looks like a health condition
            condition_keywords = [
                "dysplasia",
                "disease",
                "disorder",
                "syndrome",
                "condition",
                "problem",
            ]
            if any(kw in text for kw in condition_keywords):
                breed_data["common_conditions"].append(item.get_text(strip=True))

    return breed_data


def parse_agria_statistics_table(html: str) -> pd.DataFrame:
    """
    Parse Agria breed statistics table.

    Args:
        html: HTML content containing statistics table

    Returns:
        DataFrame with breed statistics
    """
    soup = BeautifulSoup(html, "lxml")

    data_rows = []
    tables = soup.find_all("table")

    for table in tables:
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        if not headers:
            # Try first row as headers
            first_row = table.find("tr")
            if first_row:
                headers = [td.get_text(strip=True) for td in first_row.find_all(["td", "th"])]

        if not headers:
            continue

        for row in table.find_all("tr")[1:]:
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cells) == len(headers):
                data_rows.append(dict(zip(headers, cells)))

    df = pd.DataFrame(data_rows)
    logger.info(f"Parsed {len(df)} rows from Agria statistics table")
    return df


def convert_sek_to_gbp(amount_sek: float, rate: float = 0.074) -> float:
    """
    Convert Swedish Krona to British Pounds.

    Args:
        amount_sek: Amount in SEK
        rate: Exchange rate (SEK to GBP), default approximate rate

    Returns:
        Amount in GBP
    """
    return amount_sek * rate


def normalize_swedish_breed_name(name: str) -> Optional[str]:
    """
    Normalize Swedish breed names to English equivalents.

    Args:
        name: Swedish breed name

    Returns:
        Normalized breed_id or None if not matched
    """
    # Swedish to English breed name mapping
    swedish_mappings = {
        "labrador retriever": "dog_labrador",
        "schäfer": "dog_german_shepherd",
        "tysk schäfer": "dog_german_shepherd",
        "golden retriever": "dog_golden_retriever",
        "fransk bulldogg": "dog_french_bulldog",
        "engelsk bulldogg": "dog_bulldog",
        "pudel": "dog_poodle",
        "beagle": "dog_beagle",
        "rottweiler": "dog_rottweiler",
        "yorkshireterrier": "dog_yorkshire_terrier",
        "boxer": "dog_boxer",
        "tax": "dog_dachshund",
        "shih tzu": "dog_shih_tzu",
        "sibirisk husky": "dog_siberian_husky",
        "cavalier king charles spaniel": "dog_cavalier_king_charles",
        "mops": "dog_pug",
        "border collie": "dog_border_collie",
        "cocker spaniel": "dog_cocker_spaniel",
        "jack russell terrier": "dog_jack_russell",
        "dvärgschnauzer": "dog_miniature_schnauzer",
        "chihuahua": "dog_chihuahua",
        "blandrashund": "dog_crossbreed",
        # Cats
        "huskatt": "cat_domestic_shorthair",
        "brittiskt korthår": "cat_british_shorthair",
        "maine coon": "cat_maine_coon",
        "ragdoll": "cat_ragdoll",
        "siames": "cat_siamese",
        "perser": "cat_persian",
        "bengal": "cat_bengal",
        "rysk blå": "cat_russian_blue",
        "abessinier": "cat_abyssinian",
        "sphynx": "cat_sphynx",
        "scottish fold": "cat_scottish_fold",
        "burma": "cat_burmese",
        "helig birma": "cat_birman",
        "norsk skogkatt": "cat_norwegian_forest",
    }

    normalized = name.lower().strip()
    return swedish_mappings.get(normalized)


def parse_condition_prevalence_data(html: str) -> pd.DataFrame:
    """
    Parse condition prevalence data from Agria reports.

    Args:
        html: HTML content containing prevalence data

    Returns:
        DataFrame with condition prevalence information
    """
    soup = BeautifulSoup(html, "lxml")

    prevalence_data = []

    # Look for data in various formats
    tables = soup.find_all("table")
    for table in tables:
        headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]

        # Look for tables with condition data
        if not any(
            kw in " ".join(headers)
            for kw in ["condition", "diagnosis", "claim", "prevalence"]
        ):
            continue

        for row in table.find_all("tr")[1:]:
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cells) >= 2:
                prevalence_data.append(
                    {
                        "condition": cells[0],
                        "value": cells[1] if len(cells) > 1 else None,
                        "unit": cells[2] if len(cells) > 2 else None,
                    }
                )

    df = pd.DataFrame(prevalence_data)
    logger.info(f"Parsed {len(df)} condition prevalence records from Agria data")
    return df


def estimate_regional_cost_adjustment(
    base_cost_gbp: float,
    source_country: str,
    target_country: str,
) -> float:
    """
    Estimate cost adjustment between regions.

    Args:
        base_cost_gbp: Base cost in GBP
        source_country: Source country code
        target_country: Target country code

    Returns:
        Adjusted cost in GBP

    Note:
        These are rough multipliers based on published veterinary
        fee comparisons. Actual costs vary significantly.
    """
    # Regional cost multipliers relative to UK
    cost_multipliers = {
        "UK": 1.0,
        "SE": 0.85,  # Sweden slightly lower
        "DE": 0.90,  # Germany slightly lower
        "US": 1.50,  # US significantly higher
        "AU": 1.20,  # Australia higher
        "FR": 0.95,  # France similar
    }

    source_mult = cost_multipliers.get(source_country.upper(), 1.0)
    target_mult = cost_multipliers.get(target_country.upper(), 1.0)

    # Convert from source to UK, then to target
    return base_cost_gbp / source_mult * target_mult
