"""Scientific metrics owned by multilabel."""
import numpy as np
import pandas as pd

def class_ba(train, train_classes, multi, multi_labels):
    centroids = {c: train[np.asarray(train_classes) == c].mean(axis=0) for c in sorted(set(train_classes))}
    rows = []
    for (X, text) in zip(multi, multi_labels):
        labels = sorted(set(text.split('|')))
        reason = ''
        score = np.nan
        if len(labels) < 2:
            reason = 'not_multilabel'
        elif any((c not in centroids for c in labels)):
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

