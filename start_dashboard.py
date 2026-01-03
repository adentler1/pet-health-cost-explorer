#!/usr/bin/env python3
"""
Pet Health Cost Explorer - Dashboard Launcher
Run this script to start the web dashboard
"""

import os
import subprocess
import sys
from pathlib import Path

# Get project root
PROJECT_ROOT = Path(__file__).parent

# Check if virtual environment exists
venv_path = PROJECT_ROOT / ".venv"
if not venv_path.exists():
    print("❌ Virtual environment not found!")
    print("")
    print("Please run setup first:")
    print("  ./scripts/setup_env.sh")
    print("")
    sys.exit(1)

# Check if database exists
db_path = PROJECT_ROOT / "data" / "pet_insights.db"
if not db_path.exists():
    print("❌ Database not found!")
    print("")
    print("Please build the database first:")
    print("  ./scripts/run_pipeline.sh")
    print("")
    sys.exit(1)

print("=" * 50)
print("  Pet Health Cost Explorer - Starting...")
print("=" * 50)
print("")
print("✅ Environment ready")
print("")
print("Starting dashboard on port 8502...")
print("")
print("🌐 Dashboard will be available at:")
print("   Local:   http://localhost:8502")
print("")
print("Press Ctrl+C to stop the server.")
print("")
print("=" * 50)
print("")

# Determine the Python executable from the virtual environment
if sys.platform == "win32":
    python_exe = venv_path / "Scripts" / "python.exe"
else:
    python_exe = venv_path / "bin" / "python"

# Start Streamlit using the venv Python
streamlit_cmd = [
    str(python_exe),
    "-m",
    "streamlit",
    "run",
    str(PROJECT_ROOT / "src" / "petcost" / "app" / "streamlit_app.py"),
    "--server.port=8502",
    "--server.headless=true",
    "--browser.gatherUsageStats=false",
]

try:
    subprocess.run(streamlit_cmd, cwd=PROJECT_ROOT, check=True)
except KeyboardInterrupt:
    print("\n\n✅ Dashboard stopped.")
    sys.exit(0)
except subprocess.CalledProcessError as e:
    print(f"\n❌ Error starting dashboard: {e}")
    sys.exit(1)
