#!/usr/bin/env python3
"""boundary cross-route summary entrypoint."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from embedding_analysis.experiments.boundary.summary import main
if __name__=='__main__': main()
