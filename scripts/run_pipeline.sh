#!/bin/bash
# Build the Pet Health Cost Explorer database from seed data
# Usage: ./scripts/run_pipeline.sh [--rebuild]

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
echo -e "${BLUE}  Pet Health Cost Explorer - Build Pipeline     ${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

cd "$PROJECT_ROOT"

# Check for virtual environment
VENV_DIR="$PROJECT_ROOT/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}Error: Virtual environment not found at $VENV_DIR${NC}"
    echo -e "Please run ${BLUE}./scripts/setup_env.sh${NC} first."
    exit 1
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source "$VENV_DIR/bin/activate"

# Check if petcost is installed
if ! python -c "import petcost" 2>/dev/null; then
    echo -e "${RED}Error: petcost package not installed.${NC}"
    echo -e "Please run ${BLUE}./scripts/setup_env.sh${NC} to install dependencies."
    exit 1
fi

# Parse arguments
REBUILD=""
VERBOSE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --rebuild)
            REBUILD="--rebuild"
            echo -e "${YELLOW}Rebuild mode: Will drop all tables first.${NC}"
            shift
            ;;
        -v|--verbose)
            VERBOSE="--verbose"
            shift
            ;;
        *)
            echo -e "${RED}Unknown argument: $1${NC}"
            echo "Usage: $0 [--rebuild] [--verbose]"
            exit 1
            ;;
    esac
done

# Create data directory if needed
mkdir -p "$PROJECT_ROOT/data"
mkdir -p "$PROJECT_ROOT/logs"

# Run the pipeline
echo ""
echo -e "${YELLOW}Building database...${NC}"
echo ""

python -m petcost.pipeline.build_db $REBUILD $VERBOSE

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  Pipeline complete!                            ${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo -e "Database created at: ${BLUE}$PROJECT_ROOT/data/pet_insights.db${NC}"
echo ""
echo -e "Next step: Run the dashboard with:"
echo -e "  ${BLUE}./scripts/run_app.sh${NC}"
echo ""
