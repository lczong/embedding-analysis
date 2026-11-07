"""boundary input assembly and independent computations."""
import numpy as np
import pandas as pd
from ...prepared import load_prepared, coordinates
from ...artifacts import write_json
from .metrics import target_silhouette

def compute_metrics(cfg, prepared, path, sampling):
    settings = cfg['experiments']['boundary']
    (train, mt) = load_prepared(prepared, 'train')
    manifest = sampling
    write_json(path / 'sampling.json', manifest)
    samples = []
    for role in ['ood', 'shuffled', 'idr']:
        (target, _) = load_prepared(prepared, role)
        target = target.take(manifest[role]['ids'])
        scores = target_silhouette(target.values, train.values, settings['distance'], settings['chunk_size'])
        samples.append(pd.DataFrame({'sequence_id': target.ids, 'dataset_role': role, 'silhouette': scores}))
    frame = pd.concat(samples, ignore_index=True)
    frame.to_csv(path / 'samples.csv', index=False)
    frame.groupby('dataset_role').silhouette.agg(['count', 'mean', 'median', 'std', 'min', 'max']).reset_index().to_csv(path / 'summary.csv', index=False)

def compute_coordinates(cfg, prepared, path, method, sampling):
    (train, mt) = load_prepared(prepared, 'train')
    manifest = sampling
    write_json(path / 'sampling.json', manifest)
    matrices = [train.values]
    metas = [mt[['sequence_id', 'dataset_role']]]
    for role in ['ood', 'shuffled', 'idr']:
        (target, _) = load_prepared(prepared, role)
        target = target.take(manifest[role]['ids'])
        matrices.append(target.values)
        metas.append(pd.DataFrame({'sequence_id': target.ids, 'dataset_role': role}))
    coordinates(cfg, np.vstack(matrices), pd.concat(metas), method, path)

