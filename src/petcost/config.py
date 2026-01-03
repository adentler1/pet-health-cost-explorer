"""Configuration management for Pet Health Cost Explorer."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Data sources
    use_synthetic_costs: bool = Field(
        default=True,
        description="Use synthetic cost model (true) or real claims data (false)",
    )
    default_country: str = Field(
        default="UK",
        description="Default country/region for cost estimates",
    )
    default_currency: str = Field(
        default="GBP",
        description="Currency for cost display",
    )

    # Database
    database_path: str = Field(
        default="data/pet_insights.db",
        description="Path to SQLite database (relative to project root)",
    )

    # Simulation settings
    simulation_seed: int = Field(
        default=42,
        description="Random seed for reproducible Monte Carlo simulations",
    )
    simulation_iterations: int = Field(
        default=10000,
        description="Number of Monte Carlo iterations for cost estimation",
    )

    # Cost model parameters
    cost_inflation_rate: float = Field(
        default=0.05,
        description="Annual cost inflation rate (decimal)",
    )
    cost_base_year: int = Field(
        default=2024,
        description="Base year for cost data",
    )

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Log level",
    )
    log_file: str = Field(
        default="logs/petcost.log",
        description="Log file path (relative to project root)",
    )

    # Dashboard
    streamlit_port: int = Field(
        default=8501,
        description="Streamlit server port",
    )
    dashboard_debug: bool = Field(
        default=False,
        description="Enable debug mode in dashboard",
    )

    @property
    def project_root(self) -> Path:
        """Get the project root directory."""
        # Navigate up from src/petcost to project root
        current_file = Path(__file__).resolve()
        return current_file.parent.parent.parent

    @property
    def database_path_absolute(self) -> Path:
        """Get absolute path to the database."""
        return self.project_root / self.database_path

    @property
    def log_file_absolute(self) -> Path:
        """Get absolute path to the log file."""
        return self.project_root / self.log_file

    @property
    def seed_data_path(self) -> Path:
        """Get path to seed data directory."""
        return self.project_root / "data" / "seed"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings


def reload_settings() -> Settings:
    """Reload settings from environment."""
    global settings
    settings = Settings()
    return settings
