"""Compose selected experiment views without running upstream computation."""
import numpy as np

from ..config import merge


def selected_performance(data, selection):
    from ..experiments.performance.tables import METHODS_BY_TASK
    name = selection['plot']
    if name == '05_macro_f1_comparison':
        expected = {(task, method, 'Macro-F1') for task in ('L0', 'L1', 'L2')
                    for method in ('esm2_1nn', f'{task.lower()}_ft_1nn')}
    elif name == '04_level_2_nca_A_overall':
        expected = {('L2', method, metric) for method in METHODS_BY_TASK['L2']
                    if method != 'l2_ft_1nn' for metric in ('Accuracy', 'Macro-F1')}
    else:
        raise ValueError(f'Unsupported performance panel: {name}')
    required = {'task', 'section', 'method', 'metric', 'value', 'route', 'label'}
    if not required <= set(data.columns):
        raise ValueError('Missing performance columns')
    selected = data[(data.section == 'overall') &
                    data.apply(lambda r: (r.task, r.method, r.metric) in expected, axis=1)].copy()
    if set(zip(selected.task, selected.method, selected.metric)) != expected:
        raise ValueError('Missing required performance metrics')
    if selected.duplicated(['task', 'method', 'metric']).any():
        raise ValueError('Duplicate performance metrics')
    if not np.isfinite(selected.value).all() or not selected.value.between(0, 100).all():
        raise ValueError('Invalid performance percentages')
    return selected


def selected_purity(data, selection):
    required = {'route', 'metric', 'k', 'value'}
    if not required <= set(data.columns):
        raise ValueError('Missing centroid summary columns')
    routes = selection['routes']
    if not routes or len(set(routes)) != len(routes):
        raise ValueError('Select distinct, nonempty routes')
    selected = data[(data.metric == 'knn_class_purity') & data.route.isin(routes)].copy()
    if set(routes) != set(selected.route):
        raise ValueError('Missing centroid purity routes')
    if selected.duplicated(['route', 'k']).any():
        raise ValueError('Duplicate centroid route/k values')
    if not np.isfinite(selected[['k', 'value']].to_numpy()).all():
        raise ValueError('Nonfinite centroid purity values')
    if not selected.value.between(0, 1).all() or (selected.k < 1).any() or (selected.k % 1 != 0).any():
        raise ValueError('Invalid centroid purity values or k')
    if len({tuple(sorted(g.k)) for _, g in selected.groupby('route')}) != 1:
        raise ValueError('Centroid routes must use the same k values')
    return selected.set_index('route').loc[routes].reset_index()


def selected_samples(data, selection, value):
    routes = selection['routes']
    if not routes or len(set(routes)) != len(routes):
        raise ValueError('Select distinct, nonempty routes')
    missing = set(routes) - set(data.route)
    if missing:
        raise ValueError(f'Missing routes: {sorted(missing)}')
    selected = data[data.route.isin(routes)].copy()
    if value == 'ba_score':
        combos = selection['combinations']
        if not combos or len(set(combos)) != len(combos):
            raise ValueError('Select distinct, nonempty combinations')
        selected = selected[selected.class_label.isin(combos)]
        selected = selected[np.isfinite(selected[value])]
        for route in routes:
            for combo in combos:
                if not ((selected.route == route) & (selected.class_label == combo)).any():
                    raise ValueError(f'Missing valid BA samples: {route}/{combo}')
    else:
        for route in routes:
            for role in ('shuffled', 'idr', 'ood'):
                if not ((selected.route == route) & (selected.dataset_role == role)).any():
                    raise ValueError(f'Missing silhouette samples: {route}/{role}')
    # Preserve explicit route order, retaining every sample within each route.
    return selected.set_index('route').loc[routes].reset_index()


def multilabel_figure(data, cfg, selection, style, method):
    from ..experiments.multilabel.spatial import density, draw_view
    combos = selection['combinations']
    if not combos or set(combos) - set(data.class_label):
        raise ValueError('Selected multilabel combinations are missing')
    options = cfg['plot']['multilabel']
    parents = {c for combo in combos for c in combo.split('|')}
    order = options.get('class_order', cfg['classes'])
    categories = [c for c in order if c in parents and c in set(data.class_label)] + combos
    palette = {**cfg['class_colors'], **options.get('combo_colors', {})}
    if set(categories)-set(palette):
        raise ValueError('Missing colors for selected combinations')
    xy = data[['x', 'y']].to_numpy()
    span = np.ptp(xy, axis=0).max()*1.1
    center = (xy.min(axis=0)+xy.max(axis=0))/2
    bounds = [(c-span/2, c+span/2) for c in center]
    curves, skipped = {}, []
    for category in categories:
        group = data[data.class_label == category]
        for dimension, column in enumerate(('x', 'y')):
            curve, reason = density(group[column].to_numpy(), np.linspace(*bounds[dimension], 400),
                                    options.get('kde_min_samples', 10))
            curves[(category, dimension)] = curve
            if reason:skipped.append({'category': category, 'dimension': column, 'reason': reason})
    effective = merge(cfg, {'plot': {'multilabel': {'figsize': style['size_inches']}}})
    fig, ax, handles = draw_view(data, categories, combos, palette, curves, bounds, effective,
                                 None, method, return_artists=True)
    return fig, ax, handles, {'combinations': combos, 'categories': categories,
        'counts': {c: int((data.class_label == c).sum()) for c in categories}, 'kde_skipped': skipped}


def build_figure(data, cfg, spec, style):
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from .panels import draw_panel
    kind, selection = spec['kind'], spec.get('selection', {})
    method = {'tsne': 't-SNE', 'umap': 'UMAP'}.get(spec['source']['stage'])
    if kind.startswith('nae_'):
        from ..experiments.nae.plotting import build_figure as nae_figure
        return nae_figure(data, cfg, spec, style)
    if kind == 'multilabel_combos':
        return multilabel_figure(data, cfg, selection, style, method)
    if kind == 'performance':
        from ..experiments.performance.plotting import build_figure as performance_figure, validate_geometry
        from ..experiments.performance.tables import plotting_tables
        selected = selected_performance(data, selection)
        with plt.rc_context({'font.size': 11}):
            fig, ax, handles, geometry, _ = performance_figure(plotting_tables(selected), selection['plot'])
        try:
            validate_geometry(fig, **geometry)
            return fig, ax, handles, {'plot': selection['plot'], 'rows': len(selected),
                'metrics': selected[['task', 'method', 'metric', 'value']].to_dict('records'),
                'size_inches': fig.get_size_inches().tolist()}
        except Exception:
            plt.close(fig)
            raise
    fig = plt.figure(figsize=style['size_inches'])
    ax = fig.add_axes(style['axes_rect'])
    try:
        if kind == 'centroid_purity':
            from ..experiments.centroid.plotting import draw_purity_compact
            selected = selected_purity(data, selection)
            effective = merge(cfg, {'plot': {'centroid': {
                'route_labels': style.get('route_labels', {}),
                'route_colors': style.get('route_colors', {})}}})
            handles = draw_purity_compact(ax, selected, effective)
            details = {'routes': selection['routes'], 'rows': len(selected),
                       'ks': sorted(selected.k.unique().tolist()), 'ylim': list(ax.get_ylim())}
        elif kind == 'boundary_balanced':
            from ..experiments.boundary.plotting import (
                background, foreground, contour, darken, labels, COLORS, TARGETS, axis_indicator)
            options = cfg['plot']['boundary']
            names = labels(cfg)
            train = data[data.dataset_role == 'train']
            background(ax, train, options, lighten=True)
            handles = [Patch(facecolor=COLORS['train'], label=names['train']+' density')]
            for role in TARGETS:
                group = data[data.dataset_role == role]
                foreground(ax, group, role, options)
                contour(ax, group[['x', 'y']].to_numpy(), darken(COLORS[role], .7),
                        options.get('contour_percentile', 90))
                handles.append(ax.scatter([], [], c=COLORS[role], s=50, edgecolors='white',
                                          linewidths=.25, label=names[role]))
            ax.set_aspect('equal', adjustable='datalim')
            ax.axis('off');axis_indicator(ax, method)
            details = {'counts': data.dataset_role.value_counts().to_dict(),
                       'contour_percentile': options.get('contour_percentile', 90)}
        elif kind == 'boundary_silhouette':
            from ..experiments.boundary.plotting import boxplot
            selected = selected_samples(data, selection, 'silhouette')
            _, _, handles = boxplot(selected, cfg, None, ax=ax, return_artists=True)
            route_labels = style.get('route_labels', {})
            ax.set_xticklabels([route_labels.get(r, r.removeprefix('esm2__'))
                                for r in selection['routes']], fontsize=12)
            details = {'routes': selection['routes'], 'rows': len(selected),
                       'counts': selected.groupby(['route', 'dataset_role']).size().unstack().to_dict('index')}
        elif kind == 'multilabel_ba':
            from ..experiments.multilabel.plotting import draw_summary
            selected = selected_samples(data, selection, 'ba_score')
            _, _, handles = draw_summary(selected, selection['routes'], selection['combinations'],
                                         cfg, None, ax=ax, return_artists=True)
            from ..experiments.boundary.plotting import darken
            from matplotlib.colors import to_hex
            for route, handle in zip(selection['routes'], handles):
                handle.set_label(style.get('route_labels', {}).get(route, handle.get_label()))
                handle.set_edgecolor(darken(to_hex(handle.get_facecolor()), .6))
                handle.set_linewidth(1)
            details = {'routes': selection['routes'], 'combinations': selection['combinations'],
                       'rows': len(selected),
                       'counts': selected.groupby(['route', 'class_label']).size().unstack().to_dict('index')}
        else:
            handles, details = draw_panel(ax, data, cfg, kind, selection, style, spec['source']['stage'])
        return fig, ax, handles, details
    except Exception:
        plt.close(fig)
        raise
