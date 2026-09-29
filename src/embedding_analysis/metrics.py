"""Shared scientific definitions; no system-specific labels or paths."""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist
from sklearn.metrics import pairwise_distances, davies_bouldin_score, calinski_harabasz_score, silhouette_score
from sklearn.neighbors import NearestNeighbors


def target_silhouette(target, reference, metric='euclidean', chunk_size=512):
    """Exact binary silhouette for target rows only, matching the old fast path."""
    if len(target) < 2 or not len(reference):
        raise ValueError('Silhouette requires >=2 target rows and a nonempty reference')
    result = np.empty(len(target))
    for start in range(0, len(target), chunk_size):
        end = min(start + chunk_size, len(target))
        D = pairwise_distances(target[start:end], target, metric=metric)
        D[np.arange(end-start), np.arange(start, end)] = 0
        a = D.sum(axis=1) / (len(target) - 1)
        b = pairwise_distances(target[start:end], reference, metric=metric).mean(axis=1)
        denominator = np.maximum(a, b)
        result[start:end] = np.divide(b-a, denominator, out=np.zeros_like(b), where=denominator > 0)
    return result


def class_ba(train, train_classes, multi, multi_labels):
    centroids = {c: train[np.asarray(train_classes) == c].mean(axis=0) for c in sorted(set(train_classes))}
    rows = []
    for X, text in zip(multi, multi_labels):
        labels = sorted(set(text.split('|')))
        reason = ''
        score = np.nan
        if len(labels) < 2:
            reason = 'not_multilabel'
        elif any(c not in centroids for c in labels):
            reason = 'missing_class_centroid'
        else:
            C = np.asarray([centroids[c] for c in labels], dtype=float)
            barycenter = C.mean(axis=0)
            radius = np.linalg.norm(C - barycenter, axis=1).mean()
            if radius == 0:
                reason = 'degenerate_radius'
            else:
                score = 1 - np.linalg.norm(X - barycenter) / radius
        rows.append({'class_label': '|'.join(labels), 'ba_score': score, 'invalid_reason': reason})
    return pd.DataFrame(rows)


def family_centroids(X, metadata, min_size=5):
    rows, values = [], []
    for family, positions in metadata.groupby('family_label', sort=True).indices.items():
        block = metadata.iloc[positions]
        classes = block['class_label'].unique()
        if len(classes) != 1:
            raise ValueError(f'Family {family} spans classes')
        if len(positions) < min_size:
            continue
        rows.append({'family_label': family, 'class_label': classes[0], 'n_sequences': len(positions)})
        values.append(X[positions].mean(axis=0))
    if not rows:
        raise ValueError('No family survives minimum size')
    return np.asarray(values), pd.DataFrame(rows)


def centroid_structure(C, labels, ks):
    labels = np.asarray(labels)
    if len(C) <= max(ks):
        raise ValueError(f'Need >{max(ks)} families for configured k; found {len(C)}')
    indices = NearestNeighbors(n_neighbors=max(ks)+1, metric='euclidean').fit(C).kneighbors(C, return_distance=False)
    # Remove by index, not by position: coincident centroids can reorder self.
    neighbors = np.stack([row[row != i][:max(ks)] for i, row in enumerate(indices)])
    rows = [{'metric': 'knn_class_purity', 'k': k, 'value': float((labels[neighbors[:, :k]] == labels[:, None]).mean())} for k in ks]
    n_labels = len(set(labels))
    sil = silhouette_score(C, labels, metric='euclidean') if 1 < n_labels < len(C) else np.nan
    distances = pdist(C, metric='euclidean')
    same = np.asarray([labels[i] == labels[j] for i in range(len(C)) for j in range(i+1, len(C))])
    within = np.median(distances[same]) if same.any() else np.nan
    between = np.median(distances[~same]) if (~same).any() else np.nan
    ratio = between / within if within > 0 else np.nan
    rows += [{'metric': key, 'k': np.nan, 'value': value} for key, value in [('class_silhouette', sil), ('median_within_class', within), ('median_between_class', between), ('between_over_within', ratio)]]
    return pd.DataFrame(rows)


def family_quality(X, labels, chunk_size=256):
    """Legacy Exp3 joint-context metrics, bounded-memory exact pairwise reductions.

    Silhouette and Dunn: cosine. DBI global: sklearn Euclidean definition.
    Per-family legacy DBI: average pairwise Euclidean scatter (explicitly named).
    """
    X = np.asarray(X, dtype=np.float64)
    labels = np.asarray(labels)
    names, codes, counts = np.unique(labels, return_inverse=True, return_counts=True)
    if len(names) < 2 or len(names) >= len(X):
        raise ValueError('Family metrics need 2..N-1 families')
    order = np.argsort(codes, kind='stable')
    starts = np.r_[0, np.cumsum(counts)[:-1]]
    C = np.stack([X[codes == i].mean(axis=0) for i in range(len(names))])
    sil = np.empty(len(X)); max_intra = np.zeros(len(names)); min_inter = np.full(len(names), np.inf)
    for start in range(0, len(X), chunk_size):
        end = min(start+chunk_size, len(X))
        D = pairwise_distances(X[start:end], X[order], metric='cosine')
        means = np.add.reduceat(D, starts, axis=1) / counts[None, :]
        for local, global_i in enumerate(range(start, end)):
            c = codes[global_i]
            own = codes[order] == c
            # Explicit diagonal zero preserves sklearn convention.
            D[local, np.flatnonzero(order == global_i)[0]] = 0
            a = D[local, own].sum() / (counts[c]-1) if counts[c] > 1 else 0
            means[local, c] = np.inf
            b = means[local].min()
            sil[global_i] = (b-a)/max(a,b) if counts[c] > 1 and max(a,b) > 0 else 0
            max_intra[c] = max(max_intra[c], D[local, own].max())
            min_inter[c] = min(min_inter[c], D[local, ~own].min())
    scatter = np.zeros(len(names))
    for c in range(len(names)):
        points = X[codes == c]
        if len(points) > 1:
            total = 0.
            for start in range(0, len(points), chunk_size):
                D = pairwise_distances(points[start:start+chunk_size], points, metric='euclidean')
                n = len(D); D[np.arange(n), np.arange(start, start+n)] = 0
                total += D.sum()
            scatter[c] = total / (len(points)*(len(points)-1))
    center_dist = pairwise_distances(C, metric='euclidean')
    global_mean = X.mean(axis=0)
    rows = []
    for i, name in enumerate(names):
        mask = codes == i
        good = center_dist[i] > 0
        good[i] = False
        ratios = (scatter[i] + scatter[good]) / center_dist[i, good]
        others = np.arange(len(names)) != i
        between = len(X[mask]) * np.sum((C[i]-global_mean)**2)
        within = np.sum((X[mask]-C[i])**2)
        rows.append({'family_label': name, 'n_sequences': int(counts[i]), 'silhouette_mean': float(sil[mask].mean()),
                     'dunn_cosine': float(min_inter[i]/max_intra[i]) if max_intra[i] > 0 else np.nan,
                     'legacy_pairwise_dbi': float(ratios.max()) if len(ratios) else 0.,
                     'ch_between': between, 'ch_within': within,
                     'ch_per_family': between / (within/max(counts[i]-1,1)) if within else np.nan,
                     'intra_mean_euclidean': scatter[i], 'nearest_centroid_euclidean': float(center_dist[i, others].min())})
    overall = {'n_sequences': len(X), 'n_families': len(names), 'silhouette_cosine': float(sil.mean()),
               'dunn_cosine': float(min_inter.min()/max_intra.max()) if max_intra.max() else np.nan,
               'davies_bouldin_euclidean': float(davies_bouldin_score(X, labels)),
               'calinski_harabasz_euclidean': float(calinski_harabasz_score(X, labels))}
    return pd.DataFrame(rows), overall
