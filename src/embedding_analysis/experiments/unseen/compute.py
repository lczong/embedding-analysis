"""unseen input assembly and independent computations."""
import numpy as np
import pandas as pd
from ...prepared import load_prepared, coordinates
from ...artifacts import write_json
from .metrics import family_quality
from .sampling import select_families

def compute_metrics(cfg, prepared, path):
    settings = cfg['experiments']['unseen']
    (train, mt) = load_prepared(prepared, 'train')
    (query, mq) = load_prepared(prepared, 'unseen')
    pcs = settings['n_pcs']
    if pcs > train.values.shape[1]:
        raise ValueError('Unseen n_pcs exceeds fitted PCA dimensions')
    family_tables = []
    global_rows = []
    selection = {}
    skipped = []
    for cls in cfg['classes']:
        t = mt[mt.class_label == cls]
        q = mq[mq.class_label == cls]
        tc = t.family_label.value_counts()
        qc = q.family_label.value_counts()
        candidates = tc[tc >= settings['min_family_size']].index.tolist()
        targets = qc[qc >= settings['min_family_size']].index.tolist()
        if not candidates or not targets:
            skipped.append({'class': cls, 'reason': 'no eligible train or unseen families'})
            continue
        chosen = select_families(candidates, settings['train_family_count'], cfg['seed'], cls)
        ti = t[t.family_label.isin(chosen)].index.to_numpy()
        qi = q[q.family_label.isin(targets)].index.to_numpy()
        meta = pd.concat([mt.loc[ti], mq.loc[qi]], ignore_index=True)
        if set(chosen).intersection(targets):
            raise ValueError('Unseen family appears in train')
        X = np.vstack([train.values[ti, :pcs], query.values[qi, :pcs]])
        out = path / cls
        out.mkdir(exist_ok=True)
        (fam, glob) = family_quality(X, meta.family_label.to_numpy(), settings['chunk_size'])
        fam.to_csv(out / 'joint_families.csv', index=False)
        unseen = fam[fam.family_label.isin(targets)].copy()
        unseen.insert(0, 'class_label', cls)
        family_tables.append(unseen)
        global_rows.append({'class_label': cls, 'context': 'joint_unseen_and_sampled_train', **glob})
        if len(chosen) >= 2:
            (tf, tg) = family_quality(train.values[ti, :pcs], mt.loc[ti, 'family_label'].to_numpy(), settings['chunk_size'])
            tf.to_csv(out / 'train_sample_families.csv', index=False)
            global_rows.append({'class_label': cls, 'context': 'sampled_train_only', **tg})
        selection[cls] = {'train_families': chosen, 'unseen_families': targets, 'train_count': len(ti), 'unseen_count': len(qi)}
    pd.concat(family_tables, ignore_index=True).to_csv(path / 'families.csv', index=False) if family_tables else pd.DataFrame(columns=['class_label', 'family_label']).to_csv(path / 'families.csv', index=False)
    pd.DataFrame(global_rows, columns=None if global_rows else ['class_label', 'context']).to_csv(path / 'global.csv', index=False)
    write_json(path / 'reference_families.json', selection)
    write_json(path / 'skipped_classes.json', skipped)

def compute_coordinates(cfg, prepared, path, method):
    (train, mt) = load_prepared(prepared, 'train')
    (query, mq) = load_prepared(prepared, 'unseen')
    settings = cfg['experiments']['unseen']
    pcs = settings['n_pcs']
    if pcs > train.values.shape[1]:
        raise ValueError('Unseen n_pcs exceeds fitted PCA dimensions')
    skipped = []
    for cls in cfg['classes']:
        t = mt[mt.class_label == cls]
        q = mq[mq.class_label == cls]
        counts = q.family_label.value_counts()
        targets = counts[counts >= settings['min_family_size']].index
        qi = q[q.family_label.isin(targets)].index.to_numpy()
        if not len(t) or not len(qi):
            skipped.append({'class': cls, 'reason': 'no train or eligible unseen families'})
            continue
        if set(t.family_label).intersection(targets):
            raise ValueError('Unseen family appears in train')
        out = path / cls
        out.mkdir(exist_ok=True)
        coordinates(cfg, np.vstack([train.values[t.index, :pcs], query.values[qi, :pcs]]), pd.concat([t, mq.loc[qi]]), method, out)
    write_json(path / 'skipped_visualization_classes.json', skipped)

