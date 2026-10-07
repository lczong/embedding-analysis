"""multilabel input assembly and independent computations."""
import numpy as np
import pandas as pd
from ...prepared import load_prepared, coordinates
from ...artifacts import write_json
from .metrics import class_ba

def compute_metrics(cfg, prepared, path):
    settings = cfg['experiments']['multilabel']
    (train, mt) = load_prepared(prepared, 'train')
    (multi, mm) = load_prepared(prepared, 'multi')
    scores = class_ba(train.values, mt.class_label.to_numpy(), multi.values, mm.class_label.to_numpy())
    scores.insert(0, 'sequence_id', multi.ids)
    scores.to_csv(path / 'scores.csv', index=False)
    scores.groupby('class_label').ba_score.describe().reset_index().to_csv(path / 'summary.csv', index=False)

def compute_coordinates(cfg, prepared, path, method):
    (train, mt) = load_prepared(prepared, 'train')
    (multi, mm) = load_prepared(prepared, 'multi')
    coordinates(cfg, np.vstack([train.values, multi.values]), pd.concat([mt, mm]), method, path)

