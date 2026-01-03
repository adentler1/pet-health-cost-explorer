.PHONY: setup build run test clean lint format help

# Default target
.DEFAULT_GOAL := help

# Python interpreter
PYTHON := .venv/bin/python
PIP := .venv/bin/pip
STREAMLIT := .venv/bin/streamlit
PYTEST := .venv/bin/pytest

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Pet Health Cost Explorer$(NC)"
	@echo "========================"
	@echo ""
	@echo "$(GREEN)Available commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}'

setup: ## Create virtual environment and install dependencies
	@echo "$(BLUE)Creating virtual environment...$(NC)"
	python3 -m venv .venv
	@echo "$(BLUE)Installing dependencies...$(NC)"
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	@echo "$(GREEN)Setup complete!$(NC)"
	@echo "Run 'source .venv/bin/activate' to activate the environment"

build: ## Build the SQLite database from seed data
	@echo "$(BLUE)Building database...$(NC)"
	$(PYTHON) -m petcost.pipeline.build_db
	@echo "$(GREEN)Database built successfully!$(NC)"

rebuild: ## Rebuild the database from scratch
	@echo "$(BLUE)Rebuilding database...$(NC)"
	$(PYTHON) -m petcost.pipeline.build_db --rebuild
	@echo "$(GREEN)Database rebuilt successfully!$(NC)"

run: ## Run the Streamlit dashboard
	@echo "$(BLUE)Starting dashboard...$(NC)"
	$(STREAMLIT) run src/petcost/app/streamlit_app.py --server.port 8501

test: ## Run unit tests
	@echo "$(BLUE)Running tests...$(NC)"
	$(PYTEST) tests/ -v

test-cov: ## Run tests with coverage
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	$(PYTEST) tests/ -v --cov=src/petcost --cov-report=html --cov-report=term

lint: ## Run linting checks
	@echo "$(BLUE)Running linter...$(NC)"
	.venv/bin/ruff check src/ tests/
	.venv/bin/mypy src/

format: ## Format code
	@echo "$(BLUE)Formatting code...$(NC)"
	.venv/bin/ruff format src/ tests/
	.venv/bin/ruff check --fix src/ tests/

clean: ## Clean generated files
	@echo "$(BLUE)Cleaning up...$(NC)"
	rm -rf .venv/
	rm -rf data/pet_insights.db
	rm -rf logs/*.log
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf *.egg-info/
	rm -rf src/*.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)Clean complete!$(NC)"

clean-db: ## Remove only the database (preserves environment)
	@echo "$(BLUE)Removing database...$(NC)"
	rm -f data/pet_insights.db
	@echo "$(GREEN)Database removed!$(NC)"

all: setup build test ## Full setup: create env, build db, run tests
	@echo "$(GREEN)All steps completed!$(NC)"
