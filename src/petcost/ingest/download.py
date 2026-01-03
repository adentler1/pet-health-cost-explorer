"""Optional data downloading utilities for Pet Health Cost Explorer.

This module provides utilities for downloading public data from external sources.
All functionality is optional - the pipeline runs entirely offline using seed data.
"""

from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests
from requests.exceptions import RequestException

from petcost.logging_config import get_logger

logger = get_logger(__name__)

# Default timeout for HTTP requests (seconds)
DEFAULT_TIMEOUT = 30

# User agent for requests
USER_AGENT = "PetHealthCostExplorer/0.1.0 (https://github.com/pet-health/explorer)"


class DownloadError(Exception):
    """Exception raised when a download fails."""

    pass


def download_file(
    url: str,
    output_path: Path,
    timeout: int = DEFAULT_TIMEOUT,
    overwrite: bool = False,
) -> Path:
    """
    Download a file from a URL.

    Args:
        url: URL to download from
        output_path: Path to save the file
        timeout: Request timeout in seconds
        overwrite: Whether to overwrite existing files

    Returns:
        Path to the downloaded file

    Raises:
        DownloadError: If download fails
    """
    if output_path.exists() and not overwrite:
        logger.info(f"File already exists, skipping: {output_path}")
        return output_path

    # Validate URL
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise DownloadError(f"Invalid URL scheme: {parsed.scheme}")

    logger.info(f"Downloading {url} to {output_path}")

    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
            stream=True,
        )
        response.raise_for_status()

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to file
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info(f"Downloaded {output_path.stat().st_size} bytes")
        return output_path

    except RequestException as e:
        raise DownloadError(f"Failed to download {url}: {e}") from e


def fetch_html(
    url: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """
    Fetch HTML content from a URL.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds

    Returns:
        HTML content as string

    Raises:
        DownloadError: If fetch fails
    """
    logger.info(f"Fetching HTML from {url}")

    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        return response.text

    except RequestException as e:
        raise DownloadError(f"Failed to fetch {url}: {e}") from e


class DataSourceRegistry:
    """Registry of available external data sources."""

    # Known public data sources (URLs may change)
    SOURCES = {
        "vetcompass_life_expectancy": {
            "name": "VetCompass Life Expectancy Study",
            "url": "https://www.nature.com/articles/s41598-022-10341-6",
            "type": "publication",
            "license": "CC BY 4.0",
            "notes": "Supplementary data available via DOI",
        },
        "pdsa_paw_report": {
            "name": "PDSA PAW Report",
            "url": "https://www.pdsa.org.uk/what-we-do/pdsa-animal-wellbeing-report",
            "type": "report",
            "license": "Public domain",
            "notes": "Annual report with pet ownership statistics",
        },
        "agria_breed_profiles": {
            "name": "Agria Pet Insurance Breed Profiles",
            "url": "https://www.agria.se/hund/",
            "type": "web",
            "license": "Public domain",
            "notes": "Swedish insurer with public breed statistics",
        },
        "bva_fee_survey": {
            "name": "BVA Fee Survey",
            "url": "https://www.bva.co.uk/",
            "type": "report",
            "license": "Restricted",
            "notes": "Member-only access; use published summaries",
        },
    }

    @classmethod
    def list_sources(cls) -> list[dict]:
        """
        List all available data sources.

        Returns:
            List of source dictionaries
        """
        return list(cls.SOURCES.values())

    @classmethod
    def get_source(cls, source_id: str) -> Optional[dict]:
        """
        Get information about a specific source.

        Args:
            source_id: Source identifier

        Returns:
            Source information or None if not found
        """
        return cls.SOURCES.get(source_id)


def check_source_availability(source_id: str, timeout: int = 10) -> bool:
    """
    Check if a data source URL is accessible.

    Args:
        source_id: Source identifier from DataSourceRegistry
        timeout: Request timeout in seconds

    Returns:
        True if source is accessible
    """
    source = DataSourceRegistry.get_source(source_id)
    if not source:
        logger.warning(f"Unknown source: {source_id}")
        return False

    try:
        response = requests.head(
            source["url"],
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
        )
        is_available = response.status_code < 400
        logger.info(f"Source {source_id}: {'available' if is_available else 'unavailable'}")
        return is_available
    except RequestException:
        logger.warning(f"Source {source_id}: unavailable (connection error)")
        return False
