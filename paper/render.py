#!/usr/bin/env python3
"""Render selected publication panels from completed experiment artifacts."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from embedding_analysis.publication.render import main

if __name__ == '__main__':
    main()
