"""Axes-based panel drawing; no file reads, figure creation or exports."""
from matplotlib.lines import Line2D

from ..experiments.overview.plotting import axis_indicator, selected_families


def draw_panel(ax, data, cfg, kind, selection, style, method):
    """Draw original coordinates and return legend handles and annotation details."""
    binary = kind == 'binary'
    column = 'dataset_role' if binary else 'class_label'
    options = cfg['plot'].get('binary' if binary else 'overview', {})
    if binary:
        groups = ['non_target_train', 'train']
        colors = {'non_target_train': '#888888', 'train': '#e6194b'}
        names = {'non_target_train': 'Non-CAZyme', 'train': 'CAZyme'}
        names.update(options.get('names', {}))
        labels = {'non_target_train': 'non-cazy', 'train': 'cazy'}
        labels.update(options.get('labels', {}))
        labels.update(style.get('legend_labels', {}))
    else:
        present = set(data.class_label)
        preferred = options.get('class_order', cfg['classes'])
        groups = [c for c in preferred if c in present] + sorted(present-set(preferred))
        colors = cfg['class_colors']
        names = labels = {c: c for c in groups}
    handles, counts = [], {}
    for group in groups:
        points = data[data[column] == group]
        if points.empty:
            continue
        counts[group] = len(points)
        ax.scatter(points.x, points.y, c=colors[group], s=style['point_size'],
                   alpha=style['point_alpha'], linewidths=0, edgecolors='white',
                   rasterized=style['rasterized'])
        handles.append(Line2D([], [], linestyle='none', marker='o',
                              color=colors[group], markersize=8,
                              label=f'{labels[group]} ({len(points):,})'))
    family = kind == 'overview_families'
    if family:
        fraction = selection.get('top_family_fraction', options.get('top_family_fraction', .15))
        if not 0 < fraction <= 1:
            raise ValueError('top_family_fraction must be in (0, 1]')
        annotations = selection.get('families', selected_families(data, groups, fraction))
        missing = set(annotations) - set(data.family_label)
        if missing:
            raise ValueError(f'Unknown annotation families: {sorted(missing)}')
        column = 'family_label'
    else:
        annotations = groups
    for group in annotations:
        points = data[data[column] == group]
        if points.empty:
            continue
        ax.annotate(group if family else names[group],
                xy=(float(points.x.median()), float(points.y.median())),
                xytext=style.get('annotation_offsets', {}).get(group, [0, 0]),
                textcoords='offset points',
                fontsize=style['family_fontsize'] if family else style['class_fontsize'],
                ha='center', va='center', zorder=10,
                bbox=dict(boxstyle='round,pad=0.15' if family else 'round,pad=0.3',
                          facecolor='white', edgecolor='none', alpha=.7 if family else .75))
    xy = data[['x', 'y']].to_numpy()
    lo, hi = xy.min(), xy.max()
    pad = (hi-lo)*.05 or 1
    ax.set(xlim=(lo-pad, hi+pad), ylim=(lo-pad, hi+pad), xticks=[], yticks=[])
    ax.set_aspect('equal', adjustable='box')
    for spine in ax.spines.values():
        spine.set_visible(False)
    axis_indicator(ax, {'tsne': 't-SNE', 'umap': 'UMAP'}[method])
    return handles, {'counts': counts, 'annotations': list(annotations)}
