"""Saved ID manifests are shared by metrics, plots and routes within a system."""
import hashlib
import numpy as np
from .data import read_ids
from .config import local_path
from .artifacts import write_json
import json


def choose_ids(ids, n, seed, key):
    ids = sorted(set(ids))
    # Hash ranking is independent of file order and other groups' sample sizes.
    ranked = sorted(ids, key=lambda i: hashlib.sha256(f'{seed}:{key}:{i}'.encode()).digest())
    return ranked[:min(n, len(ranked))]


def ood_manifest(cfg, run_id):
    path = local_path(cfg, cfg['output_root']) / cfg['system'] / '_sampling' / run_id / 'ood.json'
    if path.exists(): return json.loads(path.read_text())
    result = {}
    for role in ['ood', 'shuffled', 'idr']:
        sets = {route:set(read_ids(cfg, info['datasets'][role])) for route, info in cfg['routes'].items() if role in info['datasets']}
        if not sets:
            raise ValueError(f'No inputs for {role}')
        common = set.intersection(*sets.values())
        if len(common) < 2:
            raise ValueError(f'{role} has fewer than 2 common IDs across routes')
        ids = choose_ids(common, cfg['experiments']['ood']['target_size'], cfg['seed'], role)
        result[role] = {'ids': ids, 'requested':cfg['experiments']['ood']['target_size'], 'actual':len(ids),
                        'common_count':len(common), 'source_counts':{r:len(v) for r,v in sets.items()}}
    write_json(path, result)
    return result


def select_families(families, n, seed, class_label):
    return choose_ids(families, n, seed, 'families:'+class_label)
