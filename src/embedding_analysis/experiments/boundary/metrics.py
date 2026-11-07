"""Scientific metrics owned by boundary."""
import numpy as np
import pandas as pd
from sklearn.metrics import pairwise_distances

def target_silhouette(target, reference, metric='euclidean', chunk_size=512):
    """Exact binary silhouette for target rows only, matching the old fast path."""
    if len(target) < 2 or not len(reference):
        raise ValueError('Silhouette requires >=2 target rows and a nonempty reference')
    result = np.empty(len(target))
    for start in range(0, len(target), chunk_size):
        end = min(start + chunk_size, len(target))
        D = pairwise_distances(target[start:end], target, metric=metric)
        D[np.arange(end - start), np.arange(start, end)] = 0
        a = D.sum(axis=1) / (len(target) - 1)
        b = pairwise_distances(target[start:end], reference, metric=metric).mean(axis=1)
        denominator = np.maximum(a, b)
        result[start:end] = np.divide(b - a, denominator, out=np.zeros_like(b), where=denominator > 0)
    return result

