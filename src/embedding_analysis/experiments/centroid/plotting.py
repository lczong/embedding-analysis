"""Centroid plots adapted from the legacy metrics/ plotting scripts."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from scipy.spatial.distance import squareform, pdist
from ...artifacts import artifact_file


def options(cfg):
    return cfg['plot'].get('centroid', {})


def route_style(route, cfg, index=0):
    settings = options(cfg)
    if route == 'esm2':
        label, color = 'ESM2', '#777777'
    elif route.endswith('__l1-ft-ce__l2-frozen-nca'):
        label, color = 'L1-conditioned L2 NCA', '#CA3E45'
    elif route.endswith('__l2-frozen-nca'):
        label, color = 'Direct L2 NCA', '#DF83B1'
    else:
        label = route
        color = plt.rcParams['axes.prop_cycle'].by_key()['color'][index % 10]
    return settings.get('route_labels', {}).get(route, label), settings.get('route_colors', {}).get(route, color)


def save(fig, stem, cfg):
    stem = Path(stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    for ext in cfg['plot']['formats']:
        fig.savefig(stem.with_suffix('.'+ext), dpi=options(cfg).get('dpi', 300), bbox_inches='tight')
    plt.close(fig)


def plot_visualization(path, cfg, destination):
    path = Path(path)
    c = pd.read_csv(artifact_file(path, 'centroids.csv'))
    pc = [x for x in c if x.startswith('PC')]
    preferred = options(cfg).get('class_order', cfg['plot'].get('overview', {}).get('class_order', cfg['classes']))
    present = set(c.class_label)
    classes = [x for x in preferred if x in present] + sorted(present-set(preferred))
    rank = {name: i for i, name in enumerate(classes)}
    order = sorted(range(len(c)), key=lambda i: (rank[c.iloc[i].class_label], c.iloc[i].family_label))
    ordered = c.iloc[order]
    labels = ordered.class_label.to_numpy()
    families = ordered.family_label.to_numpy()
    distances = squareform(pdist(ordered[pc].to_numpy(), metric='euclidean'))
    band = np.array([matplotlib.colors.to_rgb(cfg['class_colors'][name]) for name in labels])
    route = json.loads((path/'manifest.json').read_text())['route']
    label, _ = route_style(route, cfg)
    n = len(c)
    with plt.rc_context({'font.family': options(cfg).get('font', 'Arial')}):
        fig = plt.figure(figsize=options(cfg).get('heatmap_figsize', [11, 11]))
        grid = fig.add_gridspec(2, 3, width_ratios=[.035, 1, .04], height_ratios=[.035, 1],
                                left=.10, right=.90, bottom=.10, top=.86, wspace=.045, hspace=.02)
        ax = fig.add_subplot(grid[1, 1])
        top = fig.add_subplot(grid[0, 1])
        left = fig.add_subplot(grid[1, 0])
        colorbar = fig.add_subplot(grid[1, 2])
        image = ax.imshow(distances, cmap='viridis_r', aspect='auto', interpolation='nearest', rasterized=True)
        top.imshow(band[None, :, :], aspect='auto', interpolation='nearest')
        left.imshow(band[:, None, :], aspect='auto', interpolation='nearest')
        top.set(xticks=[], yticks=[])
        left.set_xticks([])
        for panel in [top, left]:
            for spine in panel.spines.values():spine.set_visible(False)
        for boundary in np.flatnonzero(labels[1:] != labels[:-1])+1:
            ax.axhline(boundary-.5, color='white', lw=.8, alpha=.7)
            ax.axvline(boundary-.5, color='white', lw=.8, alpha=.7)
        keep = np.arange(0, n, max(1, int(np.ceil(n/60))))
        ax.set_xticks(keep, families[keep], rotation=90, fontsize=6)
        ax.set_yticks([])
        left.set_yticks(keep, families[keep], fontsize=6)
        ax.set_xlabel('Families ordered by class', fontsize=11)
        left.set_ylabel('Families ordered by class', fontsize=11)
        cb = fig.colorbar(image, cax=colorbar)
        cb.set_label(f'Euclidean distance in PCA-{len(pc)}', fontsize=10)
        cb.ax.tick_params(labelsize=9)
        fig.suptitle(f'{label}: pairwise family-centroid distance (N={n} families)', fontsize=13, y=.96)
        fig.legend(handles=[Patch(facecolor=cfg['class_colors'][name], label=name) for name in classes],
                   loc='upper center', bbox_to_anchor=(.5, .925), ncol=len(classes), frameon=False, fontsize=11)
        save(fig, Path(destination)/'figures/centroid_distances', cfg)


def purity_plot(df, cfg, stem):
    name = {'cazy': 'CAZy', 'peptidase': 'MEROPS'}.get(cfg['system'], cfg['system'])
    with plt.rc_context({'font.family': options(cfg).get('font', 'Arial')}):
        fig, ax = plt.subplots(figsize=options(cfg).get('purity_figsize', [7, 5]))
        for index, (route, group) in enumerate(df[df.metric == 'knn_class_purity'].groupby('route', sort=False)):
            group = group.sort_values('k')
            label, color = route_style(route, cfg, index)
            ax.plot(group.k, group.value, marker='o', linewidth=2.2, color=color, label=label)
        ax.set_xlabel(f'k (# nearest {name} family centroids)', fontsize=12)
        ax.set_ylabel(f'{name} class purity', fontsize=12)
        ax.set_title(f'{name} family-centroid kNN class purity', fontsize=13)
        ax.set_xticks(sorted(df.loc[df.metric == 'knn_class_purity', 'k'].dropna().unique()))
        ax.set_ylim(0, 1)
        ax.grid(False)
        ax.legend(fontsize=12, frameon=True, facecolor='white', edgecolor='#CCCCCC')
        for spine in ax.spines.values():
            spine.set_color('#999999')
            spine.set_linewidth(1)
        save(fig, stem, cfg)


def draw_purity_compact(ax, df, cfg):
    """Draw compact purity curves on supplied axes, without a legend."""
    data = df.loc[df.metric == 'knn_class_purity']
    markers = ['o', 's', '^', 'D']
    for index, (route, group) in enumerate(data.groupby('route', sort=False)):
        group = group.sort_values('k')
        label, color = route_style(route, cfg, index)
        marker = ('^' if route.endswith('__l1-ft-ce__l2-frozen-nca') else
                  's' if route.endswith('__l2-frozen-nca') else
                  'o' if route == 'esm2' else markers[index % len(markers)])
        ax.plot(group.k, group.value, marker=marker,
                markersize=7, linewidth=2, color=color, label=label,
                markeredgecolor='white', markeredgewidth=.6)
    ax.set_xlabel('Number of nearest family centroids (k)', fontsize=12, labelpad=9)
    ax.set_ylabel('Class purity', fontsize=12, labelpad=9)
    ax.set_xticks(sorted(data.k.dropna().unique()))
    lower = min(.55, float(data.value.min()) - .03)
    ax.set_ylim(lower, 1.02)
    ax.set_yticks(np.arange(np.ceil(lower * 10) / 10, 1.01, .1))
    ax.tick_params(labelsize=11, direction='out')
    ax.spines[['top', 'right']].set_visible(False)
    for side in ['left', 'bottom']:
        ax.spines[side].set_color('#777777')
    ax.grid(axis='y', color='#EAEAEA', linewidth=.6)
    ax.set_axisbelow(True)
    return ax.get_legend_handles_labels()[0]


def purity_plot_compact(df, cfg, stem):
    """Alternative publication layout; keep the full-range workflow plot intact."""
    data = df.loc[df.metric == 'knn_class_purity']
    with plt.rc_context({'font.family': options(cfg).get('font', 'Arial'),
                         'svg.fonttype': 'none', 'pdf.fonttype': 42}):
        fig, ax = plt.subplots(figsize=(6.4, 4.6))
        draw_purity_compact(ax, data, cfg)
        handles, labels = ax.get_legend_handles_labels()
        save(fig, stem, cfg)
        legend_fig = plt.figure(figsize=(8.2, .45))
        legend_fig.legend(handles, labels, loc='center', ncol=len(labels),
                          frameon=False, fontsize=10.5, handlelength=2.3,
                          columnspacing=1.8)
        save(legend_fig, str(stem) + '_legend', cfg)


def plot_metrics(path, cfg, destination):
    path = Path(path)
    df = pd.read_csv(artifact_file(path, 'metrics.csv'))
    df['route'] = json.loads((path/'manifest.json').read_text())['route']
    purity_plot(df, cfg, Path(destination)/'figures/knn_class_purity')


def plot_summary(path, cfg, destination):
    df = pd.read_csv(artifact_file(Path(path), 'summary.csv'))
    if not df.empty:purity_plot(df, cfg, Path(destination)/'comparison')
