"""Standalone, axes-based paper panels. No NAE repository imports."""
import numpy as np
from matplotlib.patches import Rectangle

SPACES = ['esm2', 'esm2__l0-ft-ce', 'esm2__l1-ft-ce', 'esm2__l2-ft-ce',
          'esm2__l2-frozen-nca', 'esm2__l1-ft-ce__l2-frozen-nca']
LABELS = dict(zip(SPACES, ['ESM2', 'L0', 'L1', 'L2', 'Direct L2 NCA', 'L1-conditioned L2 NCA']))
COLORS = dict(zip(SPACES, ['#858585', '#59A14F', '#4E79A7', '#F28E2B', '#DF83B1', '#CA3E45']))


def spaces(group):
    return SPACES[:4] if group == 'four_spaces' else [SPACES[0], *SPACES[4:]]


def title(relation, dataset):
    labels = {'is_cazy': 'Membership', 'peptidase_membership': 'Membership',
              'cazy_class': 'Class', 'peptidase_class': 'Type',
              'cazy_family': 'Family', 'peptidase_family': 'Family',
              'membership_across_class': 'Membership across class',
              'class_across_family': 'Class across family'}
    text = labels[relation]
    return text.replace('class', 'type').replace('Class', 'Type') if dataset == 'peptidase' else text


def survival(ax, curves, stats, order, label, *, ylabel=True):
    fractions = []
    for space in order:
        c = curves.loc[curves.space.eq(space)].sort_values('x')
        s = stats.loc[stats.space.eq(space)].iloc[0]
        ax.step(c.x, c.fraction_ge_x, where='pre', color=COLORS[space], lw=1.8, alpha=.9, label=LABELS[space])
        ax.plot(1, s.full_score_fraction, 'o', color=COLORS[space], ms=4, clip_on=False)
        fractions.append(s.full_score_fraction)
    indices = np.argsort(-np.array(fractions), kind='stable')
    positions = []
    for i in indices:
        positions.append(min(fractions[i]/1.02, .93, positions[-1]-.12 if positions else .93))
    if positions[-1] < .06:
        positions = [p+.06-positions[-1] for p in positions]
    for i, pos in zip(indices, positions):
        name = LABELS[order[i]].replace('L1-conditioned L2 NCA', 'L1→NCA').replace('Direct L2 NCA', 'Direct NCA')
        ax.annotate(f'{name} {fractions[i]:.1%}', xy=(1, fractions[i]), xytext=(1.045, pos),
                    textcoords='axes fraction', va='center', fontsize=11, color='#222222', annotation_clip=False,
                    arrowprops=dict(arrowstyle='-', color=COLORS[order[i]], lw=.8, alpha=.7, shrinkA=4, shrinkB=3))
    ax.axvline(0, color='#888888', lw=.8, ls='--', zorder=0)
    ax.set(xlim=(-1, 1), ylim=(0, 1.02))
    ax.set_xticks([-1, -.5, 0, .5, 1])
    ax.set_yticks([0, .25, .5, .75, 1], ['0%', '25%', '50%', '75%', '100%'])
    ax.set_xlabel('Per-protein NAE', fontsize=13)
    if ylabel:
        ax.set_ylabel('Proteins with NAE ≥ x', fontsize=13)
    ax.set_title(label, fontsize=13)
    ax.tick_params(labelsize=12)
    ax.spines[['top', 'right']].set_visible(False)
    ax.grid(axis='y', alpha=.15)


def matrix(ax, frame, order, relations, dataset):
    values = frame.pivot(index='space', columns='relation', values='mean_nae').loc[order, relations].to_numpy()
    low, high = np.floor(values.min()*20)/20, np.ceil(values.max()*20)/20
    if low == high:
        low, high = low-.05, high+.05
    im = ax.imshow(values, cmap='viridis_r', vmin=low, vmax=high, aspect='auto')
    for j in range(len(relations)):
        winner = np.argmax(values[:, j])
        for i in range(len(order)):
            rgba = im.cmap(im.norm(values[i, j]))
            lum = np.dot(rgba[:3], [.2126, .7152, .0722])
            ax.text(j, i, f'{values[i,j]:.3f}', ha='center', va='center', fontsize=21,
                    fontweight='bold' if i == winner else 'normal', color='white' if lum < .52 else '#222222')
        ax.add_patch(Rectangle((j-.45, winner-.45), .9, .9, fill=False, edgecolor='#FFD54F', lw=3))
        ax.plot(j+.30, winner-.30, '*', ms=13, markerfacecolor='#FFD54F', markeredgecolor='#222222', markeredgewidth=.6)
    ax.set_xticks(range(len(relations)), [title(r, dataset).replace(' across ', '\nacross ') for r in relations], fontsize=15)
    ax.set_yticks(range(len(order)), [LABELS[s].replace('Direct L2 NCA', 'Direct L2\nNCA').replace('L1-conditioned L2 NCA', 'L1-conditioned\nL2 NCA') for s in order], fontsize=17)
    ax.xaxis.tick_top()
    ax.tick_params(length=0, pad=10)
    ax.set_xticks(np.arange(-.5, len(relations), 1), minor=True)
    ax.set_yticks(np.arange(-.5, len(order), 1), minor=True)
    ax.grid(which='minor', color='white', lw=3)
    ax.tick_params(which='minor', length=0)
    ax.spines[:].set_visible(False)
    return im


def build_figure(data, cfg, spec, style):
    """Layouts adapted from the copied standalone render_panels.py."""
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from .data import select
    system = spec['source']['system']
    selection = spec['selection']
    select(data, system, selection)
    group = selection['space_group']
    order = spaces(group)
    parts = selection['parts']
    def subset(name, analysis, relations):
        frame = data[name]
        return frame.loc[frame.dataset.eq(system) & frame.space_group.eq(group) &
                         frame.analysis.eq(analysis) & frame.relation.isin(relations)]
    if spec['kind'] == 'nae_survival':
        relations = [(p['analysis'], r) for p in parts for r in p['relations']]
        panel_width = float(style.get('survival_panel_width', 4.6))
        panel_height = float(style.get('survival_height', 4.2))
        if panel_width <= 0 or panel_height <= 0:
            raise ValueError('NAE survival dimensions must be positive')
        fig, axes = plt.subplots(1, len(relations),
                                 figsize=(panel_width*len(relations), panel_height), squeeze=False)
        for j, (analysis, relation) in enumerate(relations):
            survival(axes[0, j], subset('curves', analysis, [relation]), subset('stats', analysis, [relation]),
                     order, title(relation, system), ylabel=j == 0)
        fig.tight_layout(w_pad=1.3)
        handles = [Line2D([], [], color=COLORS[s], lw=1.8, label=LABELS[s]) for s in order]
        ax = axes[0, 0]
    else:
        if len(parts) != 1:
            raise ValueError('Each NAE matrix component requires one analysis')
        relations = parts[0]['relations']
        left = 2.2 if group == 'esm2_vs_nca' else .85
        cell_width = float(style.get('matrix_cell_width', 1.65))
        cell_height = float(style.get('matrix_cell_height', 1.0))
        if cell_width <= 0 or cell_height <= 0:
            raise ValueError('NAE matrix cell dimensions must be positive')
        gw, gh = cell_width*len(relations), cell_height*len(order)
        width, height = left+gw+.25, gh+2.4
        fig = plt.figure(figsize=(width, height))
        ax = fig.add_axes([left/width, 1.4/height, gw/width, gh/height])
        im = matrix(ax, subset('means', parts[0]['analysis'], relations), order, relations, system)
        cax = fig.add_axes([left/width, .93/height, gw/width, .18/height])
        cb = fig.colorbar(im, cax=cax, orientation='horizontal')
        cb.ax.tick_params(labelsize=13)
        cb.set_label('Mean NAE', fontsize=15)
        cb.outline.set_visible(False)
        handles = []
    return fig, ax, handles, {'space_group': group, 'parts': parts, 'k': 50,
                              'cohort': 'train', 'size_inches': fig.get_size_inches().tolist()}
