"""Centroid summaries contain both k-dependent and scalar metrics."""
import unittest
import pandas as pd

from embedding_analysis.publication.figures import selected_purity


class CentroidSelectionTests(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame([
            ('a', 'knn_class_purity', 1, .7),
            ('a', 'knn_class_purity', 3, .6),
            ('b', 'knn_class_purity', 1, .9),
            ('b', 'knn_class_purity', 3, .8),
            ('a', 'class_silhouette', float('nan'), -.1),
        ], columns=['route', 'metric', 'k', 'value'])
        self.selection = {'routes': ['b', 'a']}

    def test_scalar_metrics_excluded_and_order_preserved(self):
        result = selected_purity(self.data, self.selection)
        self.assertEqual(result.route.tolist(), ['b', 'b', 'a', 'a'])
        self.assertEqual(len(result), 4)

    def test_missing_route_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Missing'):
            selected_purity(self.data, {'routes': ['absent']})

    def test_inconsistent_k_rejected(self):
        with self.assertRaisesRegex(ValueError, 'same k'):
            selected_purity(self.data.drop(index=3), self.selection)

    def test_duplicate_k_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            selected_purity(pd.concat([self.data, self.data.iloc[:1]]), self.selection)

    def test_invalid_purity_rejected(self):
        self.data.loc[0, 'value'] = 1.1
        with self.assertRaisesRegex(ValueError, 'Invalid'):
            selected_purity(self.data, self.selection)
