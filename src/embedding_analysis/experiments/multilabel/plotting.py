"""Plots owned by multilabel; independent of other experiment plots."""
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

def plot_visualization(path, cfg, destination):
    path = Path(path)
    dest = Path(destination)
    df = pd.read_csv(path / 'coordinates.csv')
    scatter(df, 'class_label', dest / 'figures/classes', cfg, 'Train + multi-class')
    for combo in cfg['plot']['highlight_combinations']:
        parents = combo.split('|')
        subset = df.copy()
        subset['selection'] = np.where(subset.class_label.isin(parents + [combo]), subset.class_label, 'background')
        scatter(subset, 'selection', dest / 'figures' / ('combo_' + '_'.join(parents)), cfg, combo)

def plot_metrics(path, cfg, destination):
    path = Path(path)
    dest = Path(destination)
    scores = pd.read_csv(path / 'scores.csv')
    count = scores.groupby('class_label').size()
    scores = scores[scores.class_label.isin(count[count >= cfg['experiments']['multilabel']['min_combination_size']].index)]
    distributions(scores, 'ba_score', 'class_label', dest / 'figures/ba', cfg, 'Class barycentric alignment')



def plot_summary(path, cfg, destination):
    df=pd.read_csv(Path(path)/"summary.csv")
    if df.empty: return
    fig,ax=plt.subplots(figsize=(9,4))
    df.pivot_table(index='class_label',columns='route',values='mean',aggfunc='mean').plot.bar(ax=ax)
    ax.set_ylabel('mean');ax.legend(fontsize=6)
    save(fig,Path(destination)/'comparison',cfg)
