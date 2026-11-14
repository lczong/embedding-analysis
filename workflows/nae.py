#!/usr/bin/env python3
"""Import, check or render the standalone NAE paper panels."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from embedding_analysis.experiments.nae.workflow import main
if __name__ == '__main__':
    main()
