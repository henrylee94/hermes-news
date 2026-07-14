#!/usr/bin/env python3
"""Simple wrapper: run the daily news pipeline."""
import sys, os
from pathlib import Path

# Resolve pipeline relative to this script
PIPELINE = Path(__file__).resolve().parent / "news_pipeline.py"
os.execvp(sys.executable, [sys.executable, str(PIPELINE), "daily"] + sys.argv[1:])
