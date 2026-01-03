#!/bin/bash
# Pet Health Cost Explorer - Dashboard Launcher
# Run this script to start the web dashboard

set -e

cd "$(dirname "$0")"

echo "================================================"
echo "  Pet Health Cost Explorer - Starting...       "
echo "================================================"
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found!"
    echo ""
    echo "Please run setup first:"
    echo "  ./scripts/setup_env.sh"
    echo ""
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Check if database exists
if [ ! -f "data/pet_insights.db" ]; then
    echo "❌ Database not found!"
    echo ""
    echo "Please build the database first:"
    echo "  ./scripts/run_pipeline.sh"
    echo ""
    exit 1
fi

echo "✅ Environment ready"
echo ""
echo "Starting dashboard on port 8502..."
echo ""
echo "🌐 Dashboard will be available at:"
echo "   Local:   http://localhost:8502"
echo "   Network: http://$(hostname -I | awk '{print $1}'):8502"
echo ""
echo "Press Ctrl+C to stop the server."
echo ""
echo "================================================"
echo ""

# Start Streamlit
streamlit run src/petcost/app/streamlit_app.py \
    --server.port=8502 \
    --server.headless=true \
    --browser.gatherUsageStats=false
