#!/usr/bin/env python3
"""Independent binary workflow entrypoint."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from embedding_analysis.experiments.binary.workflow import main

if __name__ == '__main__':
    main()
