"""Plots owned by structure; independent of other experiment plots."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def save(fig, stem, cfg):
    stem = Path(stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    for ext in cfg['plot']['formats']:
        fig.savefig(stem.with_suffix('.' + ext), dpi=cfg['plot']['dpi'], bbox_inches='tight')
    plt.close(fig)

def plot_visualization(path, cfg, destination):
    path = Path(path)
    dest = Path(destination)
    c = pd.read_csv(path / 'centroids.csv')
    pc = [x for x in c if x.startswith('PC')]
    from scipy.spatial.distance import squareform, pdist
    order = c.sort_values(['class_label', 'family_label']).index
    D = squareform(pdist(c.loc[order, pc].to_numpy()))
    (fig, ax) = plt.subplots(figsize=(6, 5))
    im = ax.imshow(D, cmap='viridis', rasterized=True)
    fig.colorbar(im, ax=ax, label='Euclidean distance')
    ax.set(title='Family centroid distances', xlabel='Families ordered by class', ylabel='Families ordered by class')
    save(fig, dest / 'figures/centroid_distances', cfg)

def plot_metrics(path, cfg, destination):
    path = Path(path)
    dest = Path(destination)
    df = pd.read_csv(path / 'metrics.csv')
    knn = df[df.metric == 'knn_class_purity']
    (fig, ax) = plt.subplots(figsize=(6, 4))
    ax.plot(knn.k, knn.value, marker='o')
    ax.set(xlabel='k', ylabel='Family centroid class purity', ylim=(0, 1))
    save(fig, dest / 'figures/knn_class_purity', cfg)



def plot_summary(path, cfg, destination):
    df=pd.read_csv(Path(path)/"summary.csv")
    if df.empty: return
    fig,ax=plt.subplots(figsize=(9,4))
    for route,g in df[df.metric=='knn_class_purity'].groupby('route'):
        ax.plot(g.k,g.value,marker='o',label=route)
    ax.set(xlabel='k',ylabel='Centroid class purity');ax.legend(fontsize=7)
    save(fig,Path(destination)/'comparison',cfg)
