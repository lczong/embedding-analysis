"""Configuration and strictly local path resolution."""
from __future__ import annotations
import copy
import json
from pathlib import Path


def merge(base, override):
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def load_config(path):
    path = Path(path).resolve()
    spec = json.loads(path.read_text())
    defaults = path.parent / spec.pop('defaults', 'defaults.json')
    cfg = merge(json.loads(defaults.read_text()) if defaults.exists() else {}, spec)
    if not cfg.get('system') or not cfg.get('routes'):
        raise ValueError('Config needs system and routes')
    if cfg['preprocessing']['fit_on'] != 'train':
        raise ValueError('Phase 1 only supports train-fit PCA')
    if cfg['experiments']['multilabel']['label_level'] != 'class':
        raise ValueError('BA is class-level only')
    cfg['_config_path'] = str(path)
    cfg['_root'] = str(path.parent.parent)
    return cfg


def local_path(cfg, relative):
    root = Path(cfg['_root']).resolve()
    result = (root / relative).resolve()
    if not result.is_relative_to(root):
        raise ValueError(f'Path leaves project: {relative}')
    return result


def dataset_spec(cfg, route, role):
    return cfg['routes'][route]['datasets'][role]


def spec_files(cfg, spec):
    return [local_path(cfg, p) for p in spec.get('paths', [spec.get('path')]) if p]
