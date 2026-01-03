#!/bin/bash
# Run the Pet Health Cost Explorer Streamlit dashboard
# Usage: ./scripts/run_app.sh [--port PORT]

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

# Default port
PORT=8502

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        -p)
            PORT="$2"
            shift 2
            ;;
        *)
            echo -e "${RED}Unknown argument: $1${NC}"
            echo "Usage: $0 [--port PORT]"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Pet Health Cost Explorer - Dashboard          ${NC}"
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

# Check if database exists
DB_PATH="$PROJECT_ROOT/data/pet_insights.db"
if [ ! -f "$DB_PATH" ]; then
    echo -e "${YELLOW}Warning: Database not found at $DB_PATH${NC}"
    echo -e "Building database from seed data..."
    echo ""
    python -m petcost.pipeline.build_db
    echo ""
fi

# Check if streamlit is available
if ! command -v streamlit &> /dev/null; then
    echo -e "${RED}Error: Streamlit not found.${NC}"
    echo -e "Please run ${BLUE}./scripts/setup_env.sh${NC} to install dependencies."
    exit 1
fi

echo -e "${GREEN}Starting dashboard on port $PORT...${NC}"
echo ""
echo -e "Dashboard will be available at: ${BLUE}http://localhost:$PORT${NC}"
echo ""
echo -e "Press ${YELLOW}Ctrl+C${NC} to stop the server."
echo ""

# Run Streamlit
streamlit run "$PROJECT_ROOT/src/petcost/app/streamlit_app.py" \
    --server.port "$PORT" \
    --server.headless true \
    --browser.gatherUsageStats false
