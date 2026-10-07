"""Plots owned by overview; independent of other experiment plots."""
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

def colors(labels, cfg):
    unique = sorted(set(labels))
    cmap = plt.get_cmap('tab20' if len(unique) <= 20 else 'hsv')
    return {v: cfg['class_colors'].get(v, cmap(i if len(unique) <= 20 else i / len(unique))) for (i, v) in enumerate(unique)}

def scatter(df, column, stem, cfg, title='', background_train=False):
    (fig, ax) = plt.subplots(figsize=(7, 6))
    foreground = df
    if background_train:
        bg = df[df.dataset_role == 'train']
        ax.scatter(bg.x, bg.y, c='#cccccc', s=cfg['plot']['point_size'], alpha=0.15, rasterized=True)
        foreground = df[df.dataset_role != 'train']
    palette = colors(foreground[column], cfg)
    for (label, group) in foreground.groupby(column, sort=True):
        ax.scatter(group.x, group.y, s=cfg['plot']['point_size'], color=palette[label], label=label, alpha=0.6, rasterized=True)
    if len(palette) <= 25:
        ax.legend(markerscale=3, fontsize=8, frameon=False, loc='best')
    ax.set(title=title, xlabel='Dimension 1', ylabel='Dimension 2', aspect='equal')
    ax.set_xticks([])
    ax.set_yticks([])
    save(fig, stem, cfg)

def plot_visualization(path, cfg, destination):
    path = Path(path)
    dest = Path(destination)
    df = pd.read_csv(path / 'coordinates.csv', dtype={'sequence_id': str})
    scatter(df, 'class_label', dest / 'figures/classes', cfg, 'Training classes')
    scatter(df, 'family_label', dest / 'figures/families', cfg, 'Training families')

