"""Deterministic ID ranking, with no experiment policy."""
import hashlib

def choose_ids(ids, n, seed, key):
    ids = sorted(set(ids))
    ranked = sorted(ids, key=lambda i: hashlib.sha256(f'{seed}:{key}:{i}'.encode()).digest())
    return ranked[:min(n, len(ranked))]
