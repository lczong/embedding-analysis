"""Shared train-fit PCA and separate visualization reductions."""
import numpy as np
from sklearn.decomposition import PCA
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import Normalizer


def fit_pca(X, n_components, seed):
    if n_components > min(X.shape):
        raise ValueError(f'PCA {n_components} exceeds matrix shape {X.shape}')
    pipe = Pipeline([('l2norm', Normalizer(norm='l2')), ('pca', PCA(n_components=n_components, random_state=seed))])
    coordinates = pipe.fit_transform(X).astype(np.float32)
    return pipe, coordinates


def reduce_2d(X, method, options, seed):
    if len(X) < 4:
        raise ValueError('Visualization needs >=4 rows')
    if method == 'tsne':
        import openTSNE
        if options['perplexity'] >= len(X):
            raise ValueError('t-SNE perplexity must be smaller than sample count')
        affinity = openTSNE.affinity.PerplexityBasedNN(X, perplexity=options['perplexity'], n_jobs=options['n_jobs'], random_state=seed)
        init = openTSNE.initialization.pca(X, random_state=seed)
        embedding = openTSNE.TSNEEmbedding(init, affinity, n_jobs=options['n_jobs'], random_state=seed)
        embedding.optimize(n_iter=options['n_iter_early'], exaggeration=12, momentum=.5, inplace=True)
        embedding.optimize(n_iter=options['n_iter_main'], exaggeration=1, momentum=.8, inplace=True)
        return np.asarray(embedding)
    if method == 'umap':
        import umap
        if options['n_neighbors'] >= len(X):
            raise ValueError('UMAP n_neighbors must be smaller than sample count')
        return umap.UMAP(n_components=2, random_state=seed, **options).fit_transform(X)
    raise ValueError(f'Unsupported reduction {method}')
