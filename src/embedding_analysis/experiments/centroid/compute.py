"""centroid input assembly and independent computations."""
import numpy as np
import pandas as pd
from ...prepared import load_prepared, coordinates
from ...artifacts import write_json
from .metrics import family_centroids, centroid_metrics

def compute_metrics(cfg, prepared, path):
    settings = cfg['experiments']['centroid']
    (train, mt) = load_prepared(prepared, 'train')
    (C, meta) = family_centroids(train.values, mt, settings['min_family_size'])
    centroid_metrics(C, meta.class_label.to_numpy(), settings['ks']).to_csv(path / 'metrics.csv', index=False)
    pd.concat([meta, pd.DataFrame(C, columns=[f'PC{i + 1}' for i in range(C.shape[1])])], axis=1).to_csv(path / 'centroids.csv', index=False)

