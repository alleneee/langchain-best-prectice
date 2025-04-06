# api/index.py
# Vercel entry point

import sys
import os
from pathlib import Path

# Add project root to the Python path
# This allows imports like 'from app.main import app'
project_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root))

# Set environment variable to indicate Vercel environment (optional)
os.environ['VERCEL'] = '1'

# Import the FastAPI app instance
# Make sure app.main correctly initializes the app
from app.main import app

# Optional: Add any Vercel-specific startup logic here if needed
# For example, initializing database connections if they differ in Vercel

# Vercel expects the ASGI app instance to be named 'app' 