from ...legend import top_legend
from ...artifacts import artifact_file
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

from .spatial import plot_visualization

def plot_metrics(path, cfg, destination):
    path = Path(path)
    dest = Path(destination)
    scores = pd.read_csv(artifact_file(path, 'scores.csv'))
    count = scores.groupby('class_label').size()
    scores = scores[scores.class_label.isin(count[count >= cfg['experiments']['multilabel']['min_combination_size']].index)]
    distributions(scores, 'ba_score', 'class_label', dest / 'figures/ba', cfg, 'Class barycentric alignment')



def plot_summary(path, cfg, destination):
    df=pd.read_csv(artifact_file(Path(path), 'summary.csv'))
    if df.empty: return
    fig,ax=plt.subplots(figsize=(9,4))
    df.pivot_table(index='class_label',columns='route',values='mean',aggfunc='mean').plot.bar(ax=ax)
    ax.set_ylabel('mean');top_legend(ax,cfg)
    save(fig,Path(destination)/'comparison',cfg)
