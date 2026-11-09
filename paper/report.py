#!/usr/bin/env python3
"""Create a model-specific review PDF from completed workflow artifacts."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from embedding_analysis.publication.report import main

if __name__ == '__main__':
    main()
