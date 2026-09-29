#!/usr/bin/env python3
"""Validate configured inputs without running any experiment."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from embedding_analysis.config import load_config
from embedding_analysis.data import inspect_inputs

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--deep', action='store_true')
    args = parser.parse_args()
    print(json.dumps(inspect_inputs(load_config(args.config), deep=args.deep), indent=2))
