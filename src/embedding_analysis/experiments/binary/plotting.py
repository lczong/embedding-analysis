#!/usr/bin/env python3
"""Binary t-SNE plot — cazy vs non-cazy.

Reads the tSNE results CSV produced by compute_tsne_2d.py (columns
sequence_id, label, tsne_x, tsne_y; label in {cazy, non-cazy}). Style mirrors
plot_class.py.
"""
from __future__ import annotations
from ...legend import top_legend

import argparse
from pathlib import Path
from typing import Tuple, Optional

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.family'] = 'Arial'

# Color & draw order — non-cazy goes first as background, cazy on top.
COLORS = {'non-cazy': '#888888', 'cazy': '#e6194b'}
LABEL_ORDER = ['non-cazy', 'cazy']
# Display names for on-plot text annotations
DISPLAY_NAMES = {'cazy': 'CAZyme', 'non-cazy': 'Non-CAZyme'}
ANNOT_FONTSIZE = 25
ANNOT_BBOX = dict(boxstyle='round,pad=0.3', facecolor='white',
                  edgecolor='none', alpha=0.75)


def add_tsne_axis_indicator(ax, ox: float = 0.04, oy: float = 0.04,
                            L: float = 0.14, fontsize: int = 11):
    """Lower-left t-SNE-x / t-SNE-y arrow pair in axes-fraction coordinates."""
    arrow_kw = dict(arrowstyle="->", color="black", lw=1.0,
                    mutation_scale=14, shrinkA=0, shrinkB=0)
    ax.annotate("", xy=(ox + L, oy), xytext=(ox, oy),
                xycoords="axes fraction", arrowprops=arrow_kw, zorder=1000)
    ax.annotate("", xy=(ox, oy + L), xytext=(ox, oy),
                xycoords="axes fraction", arrowprops=arrow_kw, zorder=1000)
    ax.text(ox + L + 0.01, oy, "t-SNE-x", transform=ax.transAxes,
            ha="left", va="center", fontsize=fontsize, zorder=1000)
    ax.text(ox, oy + L + 0.01, "t-SNE-y", transform=ax.transAxes,
            ha="center", va="bottom", rotation=90, fontsize=fontsize, zorder=1000)

# Style knobs (match plot_class.py)
POINT_SIZE         = 6
POINT_ALPHA        = 0.4
POINT_EDGECOLOR    = 'white'
POINT_LINEWIDTH    = 0
LEGEND_FONTSIZE    = 14
LEGEND_MARKERSCALE = 3
AXIS_PADDING       = 0.05


def compute_axis_limits(embeddings: np.ndarray,
                        axis_limit: Optional[float] = None) -> Tuple[float, float]:
    if axis_limit is not None:
        return -axis_limit, axis_limit
    lo = min(embeddings[:, 0].min(), embeddings[:, 1].min())
    hi = max(embeddings[:, 0].max(), embeddings[:, 1].max())
    pad = (hi - lo) * AXIS_PADDING
    return lo - pad, hi + pad


def plot_visualization(source, cfg, destination):
    import json
    options=cfg['plot'].get('binary',{})
    plt.rcParams['font.family']=options.get('font','Arial')
    df=pd.read_csv(source/'coordinates.csv').rename(columns={'x':'tsne_x','y':'tsne_y','dataset_role':'label'})
    df['label']=df['label'].map({'train':'cazy','non_target_train':'non-cazy'})
    if df['label'].isna().any():raise ValueError('Unexpected binary role')
    method=json.loads((source/'manifest.json').read_text())['stage']
    args=argparse.Namespace(figsize=[12,10],dpi=options.get('dpi',300),axis_limit=None,output=destination/'figures'/f"{cfg['system']}_vs_non{cfg['system']}.png")
    unexpected = set(df['label'].unique()) - {'cazy', 'non-cazy'}
    assert not unexpected, f"unexpected labels in tSNE CSV: {sorted(unexpected)}"

    embeddings = df[['tsne_x', 'tsne_y']].to_numpy()
    labels = df['label'].to_numpy()
    lo, hi = compute_axis_limits(embeddings, axis_limit=args.axis_limit)

    fig, ax = plt.subplots(figsize=tuple(args.figsize), constrained_layout=True)

    annotation_positions = []
    for label in LABEL_ORDER:
        mask = (labels == label)
        n = int(mask.sum())
        if n == 0:
            continue
        ax.scatter(
            embeddings[mask, 0], embeddings[mask, 1],
            c=[COLORS[label]],
            s=POINT_SIZE, alpha=POINT_ALPHA,
            edgecolors=POINT_EDGECOLOR, linewidths=POINT_LINEWIDTH,
            label=f"{options.get('labels',{}).get({'cazy':'train','non-cazy':'non_target_train'}[label],label)} ({n:,})",
            marker='o',
        )
        cx = float(np.median(embeddings[mask, 0]))
        cy = float(np.median(embeddings[mask, 1]))
        annotation_positions.append((options.get('names',{}).get({'cazy':'train','non-cazy':'non_target_train'}[label],DISPLAY_NAMES[label]), cx, cy))

    for name, cx, cy in annotation_positions:
        ax.text(
            cx, cy, name,
            fontsize=ANNOT_FONTSIZE, color='black',
            ha='center', va='center',
            bbox=ANNOT_BBOX, zorder=10,
        )

    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_aspect('equal', adjustable='box')
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    add_tsne_axis_indicator(ax)
    if method=="umap":
        for text in ax.texts:text.set_text(text.get_text().replace("t-SNE","UMAP"))

    top_legend(ax,cfg)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    for extension in cfg['plot']['formats']:
        output=args.output.with_suffix('.'+extension)
        fig.savefig(output,dpi=args.dpi,bbox_inches='tight')
        print(f"saved: {output}")
    plt.close(fig)
