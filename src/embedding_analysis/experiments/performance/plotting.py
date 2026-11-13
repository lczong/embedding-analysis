"""Performance plotting adapted from Performance/src/performance_plots.py."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.colors import to_rgba
from matplotlib.patches import Patch
import numpy as np

# Physical dimensions in inches: score axes share both length and numeric range.
SCORE_AXIS_INCHES = 4.4
SCORE_LIMIT = 110
BAR_WIDTH_INCHES = .42
BAR_GAP_INCHES = .06
GROUP_GAP_INCHES = .60
BAR_MARGIN_INCHES = .30

METHODS = {
    'esm2_1nn': ('ESM2', '#858585'),
    'l0_ft_1nn': ('Level 0', '#59A14F'),
    'l1_ft_1nn': ('Level 1', '#4E79A7'),
    'l2_ft_1nn': ('Level 2', '#F28E2B'),
    'l2_nca_from_esm2_1nn': ('Direct L2 NCA', '#DF83B1'),
    'l2_nca_from_l1_ft_1nn': ('L1-conditioned L2 NCA', '#CA3E45'),
}


def value(row, key):
    return float(row[key])


def style(ax, title, horizontal=False):
    ax.set_title(title, loc='center', fontsize=12, fontweight='normal', pad=15)
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    for side in ('left', 'bottom'):
        ax.spines[side].set_color('black')
    ax.tick_params(length=4, width=.8, direction='out', colors='black', pad=6, labelsize=10)
    ax.set_axisbelow(True)
    ax.grid(False)
    if horizontal:
        ax.set_xlim(0, SCORE_LIMIT)
        ax.set_xticks(np.arange(0, 101, 20))
        ax.set_xlabel('Score (%)', labelpad=9)
    else:
        ax.set_ylim(0, SCORE_LIMIT)
        ax.set_yticks(np.arange(0, 101, 20))
        ax.set_ylabel('Score (%)', labelpad=9)


def bar_layout(method_count, group_count):
    group_width = method_count * BAR_WIDTH_INCHES + (method_count - 1) * BAR_GAP_INCHES
    axis_width = 2 * BAR_MARGIN_INCHES + group_count * group_width + (group_count - 1) * GROUP_GAP_INCHES
    centers = BAR_MARGIN_INCHES + group_width / 2 + np.arange(group_count) * (group_width + GROUP_GAP_INCHES)
    return axis_width, centers


def bars(ax, rows, methods, metrics, title):
    axis_width, x = bar_layout(len(methods), len(metrics))
    width = BAR_WIDTH_INCHES
    ax.set_xlim(0, axis_width)
    for index, method in enumerate(methods):
        row = next(row for row in rows if row['方法'] == method)
        scores = [value(row, key) for key in metrics]
        rects = ax.bar(x + (index - (len(methods) - 1) / 2) * (width + BAR_GAP_INCHES), scores, width,
                       color=to_rgba(METHODS[method][1], .5), edgecolor='black', linewidth=.8, zorder=3)
        ax.bar_label(rects, labels=[f'{score:.2f}' for score in scores],
                     padding=5, fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels([key.replace('AUPRC (AP)', 'AUPRC') for key in metrics])
    style(ax, title)


def dots(ax, groups, methods, title):
    """Paired horizontal points with separate value labels for close scores."""
    labels = []
    for index, (label, rows, metric) in enumerate(groups):
        labels.append(label)
        scores = [value(next(row for row in rows if row['方法'] == m), metric)
                  for m in methods]
        if all(np.isnan(scores)):
            ax.text(50, index, 'N/A — no test samples', ha='center', va='center',
                    fontsize=10, color='#727B84')
            continue
        positions = [index] * len(methods) if len(methods) == 2 else [index + (j - 1) * .22 for j in range(len(methods))]
        ax.plot(scores, positions, color='#C6CCD1', lw=2, zorder=2)
        for j, (method, score) in enumerate(zip(methods, scores)):
            ax.scatter(score, positions[j], s=62, color=METHODS[method][1],
                       edgecolors='white', linewidth=.8, zorder=4)
            offset = (0, 10 if j == 0 else -17) if len(methods) == 2 else (8, 0)
            ax.annotate(f'{score:.2f}', (score, positions[j]), xytext=offset,
                        textcoords='offset points', ha='center' if len(methods) == 2 else 'left',
                        va='center' if len(methods) > 2 else 'baseline', fontsize=9,
                        color=METHODS[method][1], fontweight='normal')
    ax.set_yticks(range(len(groups)))
    ax.set_yticklabels(labels)
    ax.set_ylim(len(groups) - .45, -.65)
    style(ax, title, horizontal=True)


def bin_groups(rows):
    groups = []
    ranges = {'head': '>100', 'body': '11–100', 'tail': '1–10'}
    for name in ('head', 'body', 'tail'):
        subset = [row for row in rows if row['Bin'] == name]
        first = subset[0]
        label = (f"{name.capitalize()} ({ranges[name]})\n{int(first['Test families']):,} families\n"
                 f"{int(first['Test samples']):,} samples")
        groups.append((label, subset, 'Macro-F1'))
    return groups


def legend_handles(methods, bar=True):
    if bar:
        return [Patch(facecolor=to_rgba(METHODS[m][1], .5), edgecolor='black',
                      linewidth=.8, label=METHODS[m][0]) for m in methods]
    return [Line2D([], [], color=METHODS[m][1], marker='o', linestyle='',
                   markersize=8, label=METHODS[m][0]) for m in methods]


def validate_geometry(fig, score_axis_inches=SCORE_AXIS_INCHES, width_scale=1.0):
    # Keep physical axes fixed; automatic layout would change scale across figures.
    fig.canvas.draw()
    ax = fig.axes[0]
    extent = ax.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
    horizontal = ax.get_xlabel() == 'Score (%)'
    score_length = extent.width if horizontal else extent.height
    assert np.isclose(score_length, score_axis_inches)
    assert np.allclose(ax.get_xlim() if horizontal else ax.get_ylim(), (0, SCORE_LIMIT))
    for patch in ax.patches:
        physical_width = patch.get_width() * extent.width / np.diff(ax.get_xlim())[0]
        assert np.isclose(physical_width, BAR_WIDTH_INCHES * width_scale)
        assert np.isclose(patch.get_facecolor()[3], .5)
        assert patch.get_edgecolor() == (0., 0., 0., 1.)
    if ax.patches:
        group_spacing = np.diff(ax.get_xticks()) * extent.width / np.diff(ax.get_xlim())[0]
        method_count = len(ax.patches) // len(ax.get_xticks())
        group_width = method_count * BAR_WIDTH_INCHES + (method_count - 1) * BAR_GAP_INCHES
        assert np.allclose(group_spacing - group_width * width_scale, GROUP_GAP_INCHES * width_scale)
        expected_width, _ = bar_layout(method_count, len(ax.get_xticks()))
        assert np.isclose(extent.width, expected_width * width_scale)
        # Verify the actual gaps between successive methods in each group.
        group_count = len(ax.get_xticks())
        ordered = sorted(ax.patches, key=lambda patch: patch.get_x())
        for group in range(group_count):
            for i in range(method_count - 1):
                first, second = ordered[group * method_count + i:group * method_count + i + 2]
                gap = second.get_x() - first.get_x() - first.get_width()
                assert np.isclose(gap, BAR_GAP_INCHES)

def new_figure(horizontal=False, method_count=2, group_count=2, compact=False):
    """Reserve label/legend space without altering the size of the score axis."""
    left = 2.5 if horizontal else .85
    width = SCORE_AXIS_INCHES if horizontal else bar_layout(method_count, group_count)[0]
    height = SCORE_AXIS_INCHES
    bottom, top, right = 1.25, .6, .5
    if compact:
        height, bottom, top = 2.0, .7, .425
    fig = plt.figure(figsize=(left + width + right, bottom + height + top))
    total_w, total_h = fig.get_size_inches()
    ax = fig.add_axes([left / total_w, bottom / total_h, width / total_w, height / total_h])
    return fig, ax


PLOTS = (
    '01_level_0', '02_level_1_A_overall', '02_level_1_B_per_class',
    '03_level_2_A_overall', '03_level_2_B_family_bins',
    '04_level_2_nca_A_overall', '04_level_2_nca_B_family_bins',
    '05_macro_f1_comparison',
)


def build_figure(tables, name):
    """Return reusable artists and geometry settings; no filesystem writes."""
    if name not in PLOTS:
        raise ValueError(f'Unknown performance plot: {name}')
    methods = ['esm2_1nn', 'l2_nca_from_esm2_1nn', 'l2_nca_from_l1_ft_1nn']
    geometry = {'score_axis_inches': SCORE_AXIS_INCHES, 'width_scale': 1.0}
    legend = {'fontsize': 10, 'columnspacing': 1.5, 'handlelength': 2., 'handletextpad': .5}
    if name == '05_macro_f1_comparison':
        fig, ax = new_figure(method_count=2, group_count=3, compact=True)
        fig.set_size_inches(fig.get_figwidth() * 2 / 3, fig.get_figheight())
        axis_width, centers = bar_layout(2, 3)
        ax.set_xlim(0, axis_width)
        for level, center in enumerate(centers):
            rows = tables[f'L{level}', 'overall']
            for j, method in enumerate(('esm2_1nn', f'l{level}_ft_1nn')):
                score = value(next(row for row in rows if row['方法'] == method), 'Macro-F1')
                rects = ax.bar(center + (j - .5) * (BAR_WIDTH_INCHES + BAR_GAP_INCHES),
                    score, BAR_WIDTH_INCHES, color=to_rgba(METHODS[method][1], .5),
                    edgecolor='black', linewidth=.8, zorder=3)
                ax.bar_label(rects, labels=[f'{score:.2f}'], padding=5, fontsize=7.5)
        ax.set_xticks(centers)
        ax.set_xticklabels(['Membership', 'Class', 'Family'])
        style(ax, 'Test set performance')
        ax.set_ylabel('Macro-F1 (%)', labelpad=4, fontsize=10)
        ax.tick_params(labelsize=9, pad=4)
        methods = ['esm2_1nn', 'l0_ft_1nn', 'l1_ft_1nn', 'l2_ft_1nn']
        geometry.update(score_axis_inches=2., width_scale=2 / 3)
        legend.update(ncol=4, fontsize=8, columnspacing=.8, handlelength=1.3)
    elif name == '04_level_2_nca_A_overall':
        fig, ax = new_figure(method_count=3, group_count=2, compact=True)
        width_scale = 3.9 / fig.get_figwidth()
        fig.set_size_inches(3.9, 3.125)
        position = ax.get_position()
        ax.set_position([position.x0, .85 / 3.125, position.width, 1.85 / 3.125])
        bars(ax, tables['L2', 'overall'], methods, ['Accuracy', 'Macro-F1'], 'Test set performance')
        for label in ax.texts:
            label.set_fontsize(7.5)
        ax.set_ylabel('Score (%)', labelpad=4, fontsize=10)
        ax.tick_params(labelsize=9, pad=4)
        geometry.update(score_axis_inches=1.85, width_scale=width_scale)
        legend.update(ncol=3, fontsize=6.5, columnspacing=.8, handlelength=1.3)
    elif name.endswith('_B_family_bins'):
        if name.startswith('03'):
            methods = ['esm2_1nn', 'l2_ft_1nn']
        fig, ax = new_figure(horizontal=True)
        dots(ax, bin_groups(tables['L2', 'bins']), methods, 'Family-bin Macro-F1')
    elif name == '02_level_1_B_per_class':
        methods = ['esm2_1nn', 'l1_ft_1nn']
        rows = tables['L1', 'classes']
        groups = []
        for label in dict.fromkeys(row['Class'] for row in rows):
            subset = [row for row in rows if row['Class'] == label]
            groups.append((f"{label}  (n = {int(subset[0]['Support']):,})", subset, 'F1'))
        fig, ax = new_figure(horizontal=True)
        dots(ax, groups, methods, 'Per-class F1')
    else:
        task = {'01_level_0': 'L0', '02_level_1_A_overall': 'L1'}.get(name, 'L2')
        if not name.startswith('04'):
            methods = ['esm2_1nn', f'{task.lower()}_ft_1nn']
        metrics = ['Accuracy', 'Macro-F1', 'AUROC', 'AUPRC (AP)'] if task == 'L0' else ['Accuracy', 'Macro-F1']
        fig, ax = new_figure(method_count=len(methods), group_count=len(metrics))
        bars(ax, tables[task, 'overall'], methods, metrics, 'Overall performance')
    legend.setdefault('ncol', 1 if len(methods) == 3 and fig.get_figwidth() < 6 else len(methods))
    return fig, ax, legend_handles(methods, bar=bool(ax.patches)), geometry, legend


def render(tables, name, destination, settings):
    """Export the original layout plus an optional separate one-row legend."""
    font = settings.get('font', 'Arial')
    font_manager.findfont(font, fallback_to_default=False)
    with plt.rc_context({'font.family': font, 'font.size': 11, 'pdf.fonttype': 42,
                         'ps.fonttype': 42, 'svg.fonttype': 'none', 'axes.grid': False}):
        fig, ax, handles, geometry, legend_options = build_figure(tables, name)
        try:
            if settings.get('legend_in_figure', True):
                fig.legend(handles=handles, loc='lower center', bbox_to_anchor=(.5, .015),
                           frameon=False, **legend_options)
            validate_geometry(fig, **geometry)
            for extension in settings['formats']:
                fig.savefig(destination / f'{name}.{extension}', dpi=settings['dpi'], facecolor='white')
        finally:
            plt.close(fig)
        if settings.get('separate_legend', False):
            legend_fig = plt.figure(figsize=(8, .6))
            try:
                options = {**legend_options, 'ncol': len(handles)}
                artist = legend_fig.legend(handles=handles, loc='center', frameon=False, **options)
                legend_fig.canvas.draw()
                bounds = artist.get_window_extent(legend_fig.canvas.get_renderer()).transformed(
                    legend_fig.dpi_scale_trans.inverted()).padded(.1)
                for extension in settings['formats']:
                    legend_fig.savefig(destination / f'{name}_legend.{extension}',
                                       dpi=settings['dpi'], facecolor='white', bbox_inches=bounds)
            finally:
                plt.close(legend_fig)
