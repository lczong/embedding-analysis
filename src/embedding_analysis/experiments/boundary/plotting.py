"""Plots owned by boundary; independent of other experiment plots."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde
ROLE_COLORS={'train': '#76B7B2', 'ood': '#E15759', 'shuffled': '#4E79A7', 'idr': '#B07AA1'}

def save(fig, stem, cfg):
    stem = Path(stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    for ext in cfg['plot']['formats']:
        fig.savefig(stem.with_suffix('.' + ext), dpi=cfg['plot']['dpi'], bbox_inches='tight')
    plt.close(fig)

def distributions(df, value, group, stem, cfg, title):
    valid = df[np.isfinite(df[value])]
    (fig, ax) = plt.subplots(figsize=(max(6, valid[group].nunique() * 0.6), 4))
    groups = list(valid.groupby(group, sort=True))
    if groups:
        ax.boxplot([g[value].to_numpy() for (_, g) in groups], tick_labels=[str(k) for (k, _) in groups], showfliers=False)
    else:
        ax.text(0.5, 0.5, 'No finite scores', ha='center', transform=ax.transAxes)
    ax.set(ylabel=value, title=title)
    ax.tick_params(axis='x', labelrotation=45)
    save(fig, stem, cfg)

def density(df, stem, cfg):
    (fig, ax) = plt.subplots(figsize=(7, 6))
    train = df[df.dataset_role == 'train']
    ax.hexbin(train.x, train.y, gridsize=65, mincnt=1, cmap='Greys', vmin=0, linewidths=0, rasterized=True)
    ax.scatter([], [], marker='h', color='#777777', label=cfg['role_labels']['train'])
    for role in ['ood', 'shuffled', 'idr']:
        group = df[df.dataset_role == role]
        ax.scatter(group.x, group.y, s=3, alpha=0.4, color=ROLE_COLORS[role], label=cfg['role_labels'][role], rasterized=True)
        pts = group[['x', 'y']].to_numpy().T
        if len(group) >= 3 and np.linalg.matrix_rank(np.cov(pts)) == 2:
            kde = gaussian_kde(pts)
            threshold = np.percentile(kde(pts), 90)
            (gx, gy) = np.meshgrid(np.linspace(group.x.min(), group.x.max(), 90), np.linspace(group.y.min(), group.y.max(), 90))
            z = kde(np.vstack([gx.ravel(), gy.ravel()])).reshape(gx.shape)
            if z.min() < threshold < z.max():
                ax.contour(gx, gy, z, levels=[threshold], colors=[ROLE_COLORS[role]], linewidths=1)
    ax.legend(markerscale=3, frameon=False)
    ax.set(title='OOD populations', aspect='equal')
    ax.set_xticks([])
    ax.set_yticks([])
    save(fig, stem, cfg)

def plot_visualization(path, cfg, destination):
    path = Path(path)
    dest = Path(destination)
    density(pd.read_csv(path / 'coordinates.csv'), dest / 'figures/density', cfg)

def plot_metrics(path, cfg, destination):
    path = Path(path)
    dest = Path(destination)
    distributions(pd.read_csv(path / 'samples.csv'), 'silhouette', 'dataset_role', dest / 'figures/silhouette', cfg, 'OOD silhouette')



def plot_summary(path, cfg, destination):
    df=pd.read_csv(Path(path)/"summary.csv")
    if df.empty: return
    fig,ax=plt.subplots(figsize=(9,4))
    df.pivot_table(index='dataset_role',columns='route',values='mean',aggfunc='mean').plot.bar(ax=ax)
    ax.set_ylabel('mean');ax.legend(fontsize=6)
    save(fig,Path(destination)/'comparison',cfg)
