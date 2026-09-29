#!/usr/bin/env python3
"""Run from a checkout without an editable install."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from embedding_analysis.cli import main
if __name__ == "__main__":
    main()
