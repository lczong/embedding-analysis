"""Validate exact NAE curve/summary exports without changing their cohorts."""
import json
import numpy as np
import pandas as pd

FILES = ('survival_curves.csv.gz', 'survival_stats.csv', 'mean_matrices.csv', 'provenance.json')
KEYS = ['dataset', 'space_group', 'analysis', 'relation', 'space', 'k']


def load_tables(directory):
    curves = pd.read_csv(directory/FILES[0], float_precision='round_trip')
    stats = pd.read_csv(directory/FILES[1], float_precision='round_trip')
    means = pd.read_csv(directory/FILES[2], float_precision='round_trip')
    provenance = json.loads((directory/FILES[3]).read_text())
    if (provenance.get('metric_version'), provenance.get('k'), provenance.get('cohort'),
            provenance.get('membership')) != ('nae_v2_attainable_excess', 50, 'train', 'both_positive'):
        raise ValueError('Unsupported NAE metric/cohort/filter definition')
    for frame, values in [(curves, ['x', 'fraction_ge_x']), (stats, ['n', 'full_score_fraction']),
                          (means, ['mean_nae', 'n_common'])]:
        if not set(KEYS+values) <= set(frame) or frame.empty:
            raise ValueError('Missing NAE columns or empty table')
        if frame[KEYS+values].isna().any().any() or not np.isfinite(frame[values].to_numpy()).all():
            raise ValueError('Missing or nonfinite NAE data')
        if not frame.k.eq(50).all():
            raise ValueError('Expected NAE k=50')
        if frame.duplicated(KEYS+(['x'] if frame is curves else [])).any():
            raise ValueError('Duplicate NAE records')
    expected = set()
    from .plotting import spaces
    for dataset in ('cazy', 'peptidase'):
        standard = ['is_cazy', 'cazy_class', 'cazy_family'] if dataset == 'cazy' else ['peptidase_membership', 'peptidase_class', 'peptidase_family']
        for group in ('four_spaces', 'esm2_vs_nca'):
            for analysis, relations in [('standard', standard if group == 'four_spaces' else standard[-1:]),
                                         ('transition', ['membership_across_class', 'class_across_family'] if group == 'four_spaces' else ['class_across_family'])]:
                expected.update((dataset, group, analysis, r, s, 50) for r in relations for s in spaces(group))
    for frame in (curves, stats, means):
        if set(frame[KEYS].itertuples(index=False, name=None)) != expected:
            raise ValueError('Missing or unexpected NAE spaces/relations')
    indexed = stats.set_index(KEYS)
    for key, curve in curves.groupby(KEYS, sort=False):
        curve = curve.sort_values('x')
        y = curve.fraction_ge_x.to_numpy()
        if not np.all((y >= 0) & (y <= 1)) or (np.diff(y) > 1e-12).any():
            raise ValueError('Invalid inclusive survival curve')
        if not {-1., 1.} <= set(curve.x):
            raise ValueError('Missing survival boundaries')
        end = curve.loc[curve.x.eq(1), 'fraction_ge_x'].iloc[0]
        if not np.isclose(end, indexed.loc[key, 'full_score_fraction'], atol=1e-12, rtol=0):
            raise ValueError('Survival endpoint disagrees with full-score fraction')
    for frame, count, group_keys in [(stats, 'n', KEYS[:4]), (means, 'n_common', KEYS[:3])]:
        if 'common_ids_sha256' not in frame or not frame.common_ids_sha256.str.fullmatch(r'[a-f0-9]{64}').all():
            raise ValueError('Missing or invalid common-ID hashes')
        if (frame[count] <= 0).any() or (frame[count] % 1 != 0).any():
            raise ValueError('Invalid cohort size')
        for _, group in frame.groupby(group_keys):
            if group[count].nunique() != 1 or group.common_ids_sha256.nunique() != 1:
                raise ValueError('Inconsistent cohort within NAE comparison')
    return {'curves': curves, 'stats': stats, 'means': means}


def select(data, system, selection):
    group = selection['space_group']
    from .plotting import spaces
    if group not in ('four_spaces', 'esm2_vs_nca'):
        raise ValueError('Unknown NAE space group')
    parts = selection['parts']
    if not parts:
        raise ValueError('Select NAE relations')
    for part in parts:
        relations = part['relations']
        if not relations or len(set(relations)) != len(relations):
            raise ValueError('Select distinct NAE relations')
        for frame in data.values():
            rows = frame[(frame.dataset == system) & (frame.space_group == group) &
                         (frame.analysis == part['analysis']) & frame.relation.isin(relations)]
            if set(zip(rows.relation, rows.space)) != {(r, s) for r in relations for s in spaces(group)}:
                raise ValueError('Missing selected NAE relation/space')
    return data
