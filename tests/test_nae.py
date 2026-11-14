"""Scientific invariants of imported NAE summaries, independent of local outputs."""
import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from embedding_analysis.experiments.nae.data import load_tables
from embedding_analysis.experiments.nae.plotting import spaces, title


class NaeTablesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        curves, stats, means = [], [], []
        for ds in ('cazy', 'peptidase'):
            standard = ['is_cazy', 'cazy_class', 'cazy_family'] if ds == 'cazy' else ['peptidase_membership', 'peptidase_class', 'peptidase_family']
            for group in ('four_spaces', 'esm2_vs_nca'):
                for analysis, relations in [('standard', standard if group == 'four_spaces' else standard[-1:]),
                        ('transition', ['membership_across_class', 'class_across_family'] if group == 'four_spaces' else ['class_across_family'])]:
                    for relation in relations:
                        for space in spaces(group):
                            key = dict(dataset=ds, space_group=group, analysis=analysis, relation=relation, space=space, k=50)
                            curves.extend(dict(key, x=x, fraction_ge_x=y) for x, y in [(-2, 1), (-1, .8), (0, .6), (1, .2)])
                            stats.append(dict(key, n=10, full_score_fraction=.2, common_ids_sha256='a'*64))
                            # Matrix and survival cohorts may differ; negative means must survive import.
                            means.append(dict(key, n_common=5, mean_nae=-1.2, common_ids_sha256='b'*64))
        self.curves, self.stats, self.means = map(pd.DataFrame, (curves, stats, means))
        (self.root/'provenance.json').write_text(json.dumps(dict(metric_version='nae_v2_attainable_excess', k=50, cohort='train', membership='both_positive')))

    def load(self):
        self.curves.to_csv(self.root/'survival_curves.csv.gz', index=False)
        self.stats.to_csv(self.root/'survival_stats.csv', index=False)
        self.means.to_csv(self.root/'mean_matrices.csv', index=False)
        return load_tables(self.root)

    def test_preserves_negative_values_and_distinct_cohorts(self):
        data = self.load()
        self.assertEqual(len(data['means']), 52)
        self.assertEqual(data['curves'].x.min(), -2)
        self.assertTrue(data['means'].mean_nae.eq(-1.2).all())
        self.assertEqual(title('class_across_family', 'peptidase'), 'Type across family')

    def test_missing_space_rejected(self):
        self.means = self.means.iloc[1:]
        with self.assertRaisesRegex(ValueError, 'spaces/relations'):
            self.load()

    def test_endpoint_mismatch_rejected(self):
        self.stats.loc[0, 'full_score_fraction'] = .3
        with self.assertRaisesRegex(ValueError, 'endpoint'):
            self.load()

    def test_nonmonotonic_curve_rejected(self):
        self.curves.loc[2, 'fraction_ge_x'] = .9
        with self.assertRaisesRegex(ValueError, 'survival curve'):
            self.load()

    def test_matrix_cohort_must_match_across_relations(self):
        self.means.loc[0, 'common_ids_sha256'] = 'c'*64
        with self.assertRaisesRegex(ValueError, 'cohort'):
            self.load()


if __name__ == '__main__':
    unittest.main()
