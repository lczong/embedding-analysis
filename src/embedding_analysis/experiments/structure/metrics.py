"""Scientific metrics owned by structure."""
import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist
from sklearn.metrics import silhouette_score
from sklearn.neighbors import NearestNeighbors

def family_centroids(X, metadata, min_size=5):
    (rows, values) = ([], [])
    for (family, positions) in metadata.groupby('family_label', sort=True).indices.items():
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
    return (np.asarray(values), pd.DataFrame(rows))

def centroid_structure(C, labels, ks):
    labels = np.asarray(labels)
    if len(C) <= max(ks):
        raise ValueError(f'Need >{max(ks)} families for configured k; found {len(C)}')
    indices = NearestNeighbors(n_neighbors=max(ks) + 1, metric='euclidean').fit(C).kneighbors(C, return_distance=False)
    neighbors = np.stack([row[row != i][:max(ks)] for (i, row) in enumerate(indices)])
    rows = [{'metric': 'knn_class_purity', 'k': k, 'value': float((labels[neighbors[:, :k]] == labels[:, None]).mean())} for k in ks]
    n_labels = len(set(labels))
    sil = silhouette_score(C, labels, metric='euclidean') if 1 < n_labels < len(C) else np.nan
    distances = pdist(C, metric='euclidean')
    same = np.asarray([labels[i] == labels[j] for i in range(len(C)) for j in range(i + 1, len(C))])
    within = np.median(distances[same]) if same.any() else np.nan
    between = np.median(distances[~same]) if (~same).any() else np.nan
    ratio = between / within if within > 0 else np.nan
    rows += [{'metric': key, 'k': np.nan, 'value': value} for (key, value) in [('class_silhouette', sil), ('median_within_class', within), ('median_between_class', between), ('between_over_within', ratio)]]
    return pd.DataFrame(rows)

