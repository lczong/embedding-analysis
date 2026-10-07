"""overview input assembly and independent computations."""
import numpy as np
import pandas as pd
from ...prepared import load_prepared, coordinates
from ...artifacts import write_json

def compute_coordinates(cfg, prepared, path, method):
    (train, mt) = load_prepared(prepared, 'train')
    coordinates(cfg, train.values, mt, method, path)

