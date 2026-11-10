"""Configuration, local outputs, and explicitly allowed linked inputs."""
from __future__ import annotations
import copy
import json
import os
import re
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
    if not re.fullmatch(r'[A-Za-z0-9_-]+', cfg['system']):
        raise ValueError('Invalid system name')
    for route, info in cfg['routes'].items():
        if not re.fullmatch(r'(?:esm1b|esm2(?:-(?:650m|150m|35m))?)(?:__pool-(?:cls|residue_mean))?(?:__l[012]-(?:ft|frozen)-(?:ce|nca))*', route):
            raise ValueError(f'Invalid route: {route}')
        if 'train' not in info['datasets']:
            raise ValueError(f'{route} requires train input')
    if cfg['preprocessing']['normalize'] != 'l2':
        raise ValueError('Phase 1 requires L2 normalization')
    if cfg['preprocessing']['fit_on'] != 'train':
        raise ValueError('Phase 1 only supports train-fit PCA')
    cfg['_config_path'] = str(path)
    cfg['_root'] = str(path.parent.parent)
    return cfg


def local_path(cfg, relative):
    root = Path(cfg['_root']).resolve()
    result = (root / relative).resolve()
    if not result.is_relative_to(root):
        raise ValueError(f'Path leaves project: {relative}')
    return result


def input_path(cfg, relative):
    """Keep project-local input names while allowing declared symlink targets.

    Output paths must continue to use local_path, which forbids external targets.
    """
    root = Path(cfg['_root']).resolve()
    path = Path(os.path.abspath(root / relative))
    if not path.is_relative_to(root):
        raise ValueError(f'Input path leaves project: {relative}')
    target = path.resolve()
    allowed = [Path(p).resolve() for p in cfg.get('external_embedding_roots', [])]
    if not target.is_relative_to(root):
        if not path.is_relative_to(root / 'data') or not any(target.is_relative_to(p) for p in allowed):
            raise ValueError(f'Input target is not allowed: {relative}')
    return path


def dataset_spec(cfg, route, role):
    return cfg['routes'][route]['datasets'][role]


def spec_files(cfg, spec):
    return [input_path(cfg, p) for p in spec.get('paths', [spec.get('path')]) if p]
