"""Publication selections must preserve samples and fail on absent comparisons."""
import unittest
import pandas as pd

from embedding_analysis.publication.figures import selected_samples


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame([
            {'route': r, 'class_label': c, 'ba_score': v, 'sequence_id': f'{c}-{v}'}
            for r in ('esm2', 'esm2__l0-ft-ce')
            for c in ('CBM|GH', 'CBM|PL', 'AA|CBM') for v in (0., -1., 1.)])

    def test_selection_preserves_values_and_explicit_route_order(self):
        selection = {'routes': ['esm2__l0-ft-ce', 'esm2'], 'combinations': ['CBM|PL', 'CBM|GH']}
        result = selected_samples(self.data, selection, 'ba_score')
        self.assertEqual(result.route.drop_duplicates().tolist(), selection['routes'])
        self.assertEqual(set(result.class_label), set(selection['combinations']))
        self.assertEqual(len(result), 12)
        self.assertEqual(sorted(result.ba_score), [-1.]*4 + [0.]*4 + [1.]*4)

    def test_missing_combination_in_one_route_fails(self):
        data = self.data[~((self.data.route == 'esm2') & (self.data.class_label == 'CBM|PL'))]
        with self.assertRaisesRegex(ValueError, 'Missing valid BA samples'):
            selected_samples(data, {'routes': ['esm2', 'esm2__l0-ft-ce'],
                                   'combinations': ['CBM|PL']}, 'ba_score')

    def test_invalid_scores_not_counted_as_observations(self):
        self.data.loc[0, 'ba_score'] = float('nan')
        selected = selected_samples(self.data, {'routes': ['esm2'], 'combinations': ['CBM|GH']}, 'ba_score')
        self.assertEqual(len(selected), 2)

    def test_incomplete_boundary_role_fails(self):
        data = pd.DataFrame({'route': ['esm2']*2, 'dataset_role': ['ood', 'idr'], 'silhouette': [.1, .2]})
        with self.assertRaisesRegex(ValueError, 'Missing silhouette samples'):
            selected_samples(data, {'routes': ['esm2']}, 'silhouette')
