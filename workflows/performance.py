#!/usr/bin/env python3
"""Render archived performance reports independently of embedding workflows."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from embedding_analysis.experiments.performance.workflow import main

if __name__ == '__main__':
    main()
