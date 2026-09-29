"""CSV/sharded CSV/NPY adapters; algorithms receive aligned arrays and metadata."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd
from .config import local_path, spec_files


@dataclass
class Embedding:
    ids: np.ndarray
    values: np.ndarray

    def take(self, ids):
        index = pd.Index(self.ids).get_indexer(ids)
        if (index < 0).any():
            raise ValueError(f'{int((index < 0).sum())} requested IDs missing')
        return Embedding(np.asarray(ids, dtype=str), self.values[index])


def validate_ids(ids, context):
    series = pd.Series(ids, dtype='string')
    if series.isna().any() or series.eq('').any() or series.duplicated().any():
        raise ValueError(f'Missing/empty/duplicate IDs: {context}')
    return series.to_numpy(dtype=str)


def read_ids(cfg, spec):
    if spec['format'] == 'npy':
        if 'ids_reference' not in spec:
            raise ValueError('NPY input requires explicit ids_reference')
        files = [local_path(cfg, spec['ids_reference'])]
    else:
        files = spec_files(cfg, spec)
    ids = np.concatenate([pd.read_csv(p, header=None, usecols=[0], dtype=str)[0].to_numpy() for p in files])
    return validate_ids(ids, files)


def load_embedding(cfg, spec):
    files = spec_files(cfg, spec)
    if spec['format'] == 'npy':
        if len(files) != 1:
            raise ValueError('NPY adapter accepts one matrix')
        X = np.load(files[0], mmap_mode='r', allow_pickle=False)
        ids = read_ids(cfg, spec)
        if X.ndim != 2 or len(ids) != len(X):
            raise ValueError(f'NPY / reference ID row mismatch: {files[0]}')
        X = np.asarray(X, dtype=np.float32)
    elif spec['format'] == 'csv':
        frames = []
        for p in files:
            with p.open() as f:
                n = len(f.readline().rstrip().split(','))
            frames.append(pd.read_csv(p, header=None, dtype={0: str, **{i: np.float32 for i in range(1, n)}}))
        if len({f.shape[1] for f in frames}) != 1:
            raise ValueError('Inconsistent shard dimensions')
        frame = pd.concat(frames, ignore_index=True)
        ids = validate_ids(frame.iloc[:, 0], files)
        X = frame.iloc[:, 1:].to_numpy(dtype=np.float32)
    else:
        raise ValueError(f'Unsupported format {spec["format"]}')
    if not len(X) or not X.shape[1] or not np.isfinite(X).all():
        raise ValueError('Embedding must be nonempty and finite')
    return Embedding(ids, X)


def read_metadata(cfg, role, ids):
    m = cfg['metadata']
    df = pd.read_csv(local_path(cfg, m['files'][role]), sep='\t', dtype=str)
    df = df.rename(columns={m['id_column']: 'sequence_id', m['class_column']: 'class_label', m['family_column']: 'family_label'})
    validate_ids(df['sequence_id'], role)
    df = df.set_index('sequence_id').reindex(ids)
    if df[['class_label', 'family_label']].isna().any().any():
        raise ValueError(f'Missing metadata for {role}')
    for column in ['class_label', 'family_label']:
        df[column] = df[column].map(lambda s: '|'.join(sorted(set(x.strip() for x in s.split('|') if x.strip()))))
        if df[column].eq('').any():
            raise ValueError(f'Empty {column}')
    if role in ['train', 'unseen']:
        if df['class_label'].str.contains('|', regex=False).any() or df['family_label'].str.contains('|', regex=False).any():
            raise ValueError(f'{role} must have single class and family labels')
    df['dataset_role'] = role
    return df.reset_index()[['sequence_id', 'class_label', 'family_label', 'dataset_role']]


def inspect_inputs(cfg, deep=False):
    rows = []
    for route, info in cfg['routes'].items():
        for role, spec in info['datasets'].items():
            files = spec_files(cfg, spec)
            for p in files:
                if not p.is_file():
                    raise FileNotFoundError(p)
            if spec['format'] == 'npy':
                a = np.load(files[0], mmap_mode='r', allow_pickle=False)
                if a.ndim != 2:
                    raise ValueError(f'Expected matrix: {files[0]}')
                dims = {a.shape[1]}
                if not local_path(cfg, spec['ids_reference']).is_file():
                    raise FileNotFoundError(spec['ids_reference'])
            else:
                dims = set()
                for p in files:
                    with p.open() as f:
                        dims.add(len(f.readline().rstrip().split(',')) - 1)
            if dims != {info['dimensions']}:
                raise ValueError(f'Dimension mismatch {route}/{role}: {dims}')
            record = {'route': route, 'role': role, 'dimensions': info['dimensions'], 'files': len(files)}
            if deep:
                emb = load_embedding(cfg, spec)
                record['rows'] = len(emb.ids)
                if role in cfg['metadata']['files']:
                    read_metadata(cfg, role, emb.ids)
            rows.append(record)
    for p in cfg['metadata']['files'].values():
        if not local_path(cfg, p).is_file():
            raise FileNotFoundError(p)
    return rows
