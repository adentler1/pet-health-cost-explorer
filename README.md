# Pet Health Cost Explorer

A local web dashboard for exploring pet health costs, life expectancy, and breed-specific health risks for dogs and cats.

## Project Purpose

This tool helps pet owners, veterinarians, and insurance professionals understand:
- **Life expectancy** estimates by breed (with uncertainty ranges)
- **Breed-specific health risks** (top conditions affecting each breed)
- **Expected veterinary costs** using public data and transparent synthetic modeling
- **Cost distributions** (P10/P50/P90) for annual and lifetime expenses

## Data Sources and Limitations

### Primary Data Sources

| Source | Data Type | Status | License |
|--------|-----------|--------|---------|
| VetCompass (RVC) | Life expectancy, breed risks | Aggregated from publications | Academic use |
| Agria Pet Insurance (Sweden) | Breed risk profiles | Public reports | Public domain |
| PDSA PAW Report (UK) | Average vet costs (UK) | Annual survey | Public domain |
| BVA Fee Surveys | Procedure costs (UK) | Published ranges | Public domain |
| German GOT Fee Schedule | Veterinary costs (Germany) | Official fee schedule | Public domain |

### Coverage

- **75 breeds total**: 51 dog breeds, 24 cat breeds
- **Generic/Mixed breed categories**: Reference data for typical and crossbreed pets
- **Life expectancy**: Universal data from 2024 VetCompass studies (country-independent)
- **Cost estimates**: Available for UK (GBP) and Germany (EUR)

### Limitations

1. **Geographic Coverage**: Life expectancy data is universal; costs available for UK and Germany
2. **Cost Data**: True claims microdata is proprietary; we use a **synthetic cost model**
3. **Breed Coverage**: Some rare breeds may have limited data
4. **Temporal**: Costs are indexed to 2024; historical data may be outdated

### Synthetic Cost Model

When real claims data is unavailable (the default case), costs are estimated using:
- Published veterinary fee schedules
- Condition prevalence from epidemiological studies
- Monte Carlo simulation with documented assumptions

**All synthetic results are clearly labeled as "Estimated" in the dashboard.**

## Environment Setup

### Prerequisites

- Python 3.10+ installed
- No other dependencies required

### Quick Start

```bash
# 1. Create and activate the virtual environment
./scripts/setup_env.sh

# 2. Build the SQLite database from seed data
./scripts/run_pipeline.sh

# 3. Launch the dashboard (choose one):

# Option A: Simple launcher script (recommended)
./start_dashboard.sh

# Option B: Python launcher
./start_dashboard.py

# Option C: Use the scripts directory
./scripts/run_app.sh
```

The dashboard will be available at **http://localhost:8502**

### Manual Setup (if scripts don't work)

```bash
# Create virtual environment
python3 -m venv .venv

# Activate (Linux/Mac)
source .venv/bin/activate

# Activate (Windows)
# .venv\Scripts\activate

# Install dependencies
pip install -e .

# Build database
python -m petcost.pipeline.build_db

# Run dashboard
streamlit run src/petcost/app/streamlit_app.py
```

## How to Rebuild the Database

```bash
# Full rebuild (drops existing data)
./scripts/run_pipeline.sh --rebuild

# Or manually:
source .venv/bin/activate
python -m petcost.pipeline.build_db --rebuild
```

## Project Structure

```
pet-health-cost-explorer/
├── README.md                 # This file
├── pyproject.toml            # Python package configuration
├── .env.example              # Environment variable template
├── Makefile                  # Common commands
├── data/
│   ├── seed/                 # Curated public data (versioned)
│   │   ├── seed_breeds.csv
│   │   ├── seed_life_expectancy.csv
│   │   ├── seed_risk_profiles.csv
│   │   └── seed_cost_mapping.csv
│   └── pet_insights.db       # Generated SQLite database
├── src/petcost/              # Main package
│   ├── config.py             # Configuration management
│   ├── logging_config.py     # Logging setup
│   ├── db.py                 # Database connection
│   ├── schemas.py            # SQLite schema definitions
│   ├── ingest/               # Data ingestion modules
│   ├── features/             # Feature computation
│   ├── pipeline/             # Data pipeline
│   └── app/                  # Streamlit dashboard
├── scripts/                  # Shell scripts
├── tests/                    # Unit tests
└── logs/                     # Log files (gitignored)
```

## Extending with Insurer Claims Data

The system is designed to integrate real claims data when available:

### Interface Requirements

To add a new claims data source, implement the `ClaimsDataSource` protocol:

```python
from typing import Protocol
from pandas import DataFrame

class ClaimsDataSource(Protocol):
    """Protocol for claims data integration."""

    def get_claims_by_breed(
        self,
        breed_id: str,
        country: str,
        year_start: int,
        year_end: int
    ) -> DataFrame:
        """Return claims data with columns: claim_date, condition_id, cost_gbp."""
        ...

    def get_aggregate_costs(
        self,
        breed_id: str,
        country: str
    ) -> dict[str, float]:
        """Return P10, P50, P90 annual costs from real data."""
        ...
```

### Integration Steps

1. Create a new module in `src/petcost/ingest/` implementing the protocol
2. Set `USE_SYNTHETIC_COSTS = false` in `.env`
3. Configure data source credentials in `.env`
4. Rebuild the database with `./scripts/run_pipeline.sh --rebuild`

### Data Requirements

Real claims data should include:
- Anonymized claim records
- Condition/diagnosis codes (mapped to our `conditions` table)
- Claim amounts in local currency
- Breed identification
- Pet age at claim

## Configuration

Copy `.env.example` to `.env` and adjust as needed:

```bash
cp .env.example .env
```

Key settings:
- `USE_SYNTHETIC_COSTS`: Set to `false` when real data is available
- `DEFAULT_COUNTRY`: Default region for cost estimates (default: UK)
- `SIMULATION_SEED`: Random seed for reproducibility (default: 42)
- `LOG_LEVEL`: Logging verbosity (default: INFO)

## Running Tests

```bash
source .venv/bin/activate
pytest tests/ -v
```

## License

This project is for educational and research purposes. Data sources retain their original licenses.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Ensure all tests pass
4. Submit a pull request

## Changelog

### v0.1.0 (2024-01)
- Initial release
- UK dog and cat breeds
- Synthetic cost model
- Streamlit dashboard
