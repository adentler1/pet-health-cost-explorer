#!/bin/bash
# Setup script for Pet Health Cost Explorer
# Creates a virtual environment and installs dependencies

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Pet Health Cost Explorer - Environment Setup  ${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

cd "$PROJECT_ROOT"

# Check Python version
echo -e "${YELLOW}Checking Python version...${NC}"
PYTHON_CMD=""

# Try python3 first, then python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}Error: Python not found. Please install Python 3.10 or higher.${NC}"
    exit 1
fi

# Check Python version is 3.10+
PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 10 ]); then
    echo -e "${RED}Error: Python 3.10 or higher is required. Found: Python $PYTHON_VERSION${NC}"
    exit 1
fi

echo -e "${GREEN}Found Python $PYTHON_VERSION${NC}"
echo ""

# Create virtual environment
VENV_DIR="$PROJECT_ROOT/.venv"

if [ -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Virtual environment already exists at $VENV_DIR${NC}"
    read -p "Do you want to recreate it? (y/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Removing existing virtual environment...${NC}"
        rm -rf "$VENV_DIR"
    else
        echo -e "${YELLOW}Using existing virtual environment.${NC}"
    fi
fi

if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    $PYTHON_CMD -m venv "$VENV_DIR"
    echo -e "${GREEN}Virtual environment created at $VENV_DIR${NC}"
fi

echo ""

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo -e "${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip --quiet

# Install dependencies
echo ""
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -e ".[dev]" --quiet

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  Environment setup complete!                   ${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo -e "To activate the environment, run:"
echo -e "  ${BLUE}source .venv/bin/activate${NC}"
echo ""
echo -e "Next steps:"
echo -e "  1. Build the database: ${BLUE}./scripts/run_pipeline.sh${NC}"
echo -e "  2. Run the dashboard:  ${BLUE}./scripts/run_app.sh${NC}"
echo ""

# Copy .env.example to .env if it doesn't exist
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    if [ -f "$PROJECT_ROOT/.env.example" ]; then
        echo -e "${YELLOW}Creating .env file from .env.example...${NC}"
        cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
        echo -e "${GREEN}Created .env file. Edit it to customize settings.${NC}"
    fi
fi

# Create logs directory
mkdir -p "$PROJECT_ROOT/logs"

echo -e "${GREEN}Setup complete!${NC}"
