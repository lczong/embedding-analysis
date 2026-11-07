"""Shared PCA preparation and prepared-array I/O."""
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from .artifacts import complete
from .data import Embedding, load_embedding, read_metadata
from .reduction import fit_pca, reduce_2d

def prepare(cfg, route, payload, destination):
    path = Path(destination)
    path.mkdir(parents=True, exist_ok=True)
    (path / 'manifest.json').unlink(missing_ok=True)
    datasets = cfg['routes'][route]['datasets']
    train = load_embedding(cfg, datasets['train'])
    train_ids = set(train.ids)
    (pipe, X) = fit_pca(train.values, cfg['preprocessing']['n_components'], cfg['seed'])
    joblib.dump(pipe, path / 'pca_model.joblib')
    np.savez(path / 'train.npz', ids=train.ids, values=X)
    read_metadata(cfg, 'train', train.ids).to_csv(path / 'train.metadata.csv', index=False)
    expected = train.values.shape[1]
    del train, X
    for (role, spec) in datasets.items():
        if role in ['train', 'non_target_train']:
            continue
        data = load_embedding(cfg, spec)
        if data.values.shape[1] != expected:
            raise ValueError(f'{route}/{role}: incompatible feature dimension')
        if role in ['unseen', 'multi'] and train_ids.intersection(data.ids):
            raise ValueError(f'{role} overlaps train sequence IDs')
        projected = pipe.transform(data.values).astype(np.float32)
        np.savez(path / f'{role}.npz', ids=data.ids, values=projected)
        if role in cfg['metadata']['files']:
            read_metadata(cfg, role, data.ids).to_csv(path / f'{role}.metadata.csv', index=False)
    evr = pipe.named_steps['pca'].explained_variance_ratio_
    pd.DataFrame({'component': np.arange(1, len(evr) + 1), 'explained_variance': evr, 'cumulative': evr.cumsum()}).to_csv(path / 'explained_variance.csv', index=False)
    complete(path, {**payload, 'route': route, 'experiment': 'preprocess', 'fit_on': 'train'})
    return path

def load_prepared(path, role):
    with np.load(path / f'{role}.npz', allow_pickle=False) as z:
        data = Embedding(z['ids'], z['values'])
    p = path / f'{role}.metadata.csv'
    meta = pd.read_csv(p, dtype=str) if p.exists() else pd.DataFrame({'sequence_id': data.ids, 'dataset_role': role})
    if meta.sequence_id.tolist() != data.ids.tolist():
        raise ValueError('Prepared metadata order mismatch')
    return (data, meta)

def coordinates(cfg, X, meta, method, path):
    xy = reduce_2d(X, method, cfg['reduction'][method], cfg['seed'])
    out = meta.reset_index(drop=True).copy()
    out['x'] = xy[:, 0]
    out['y'] = xy[:, 1]
    out.to_csv(path / 'coordinates.csv', index=False)

