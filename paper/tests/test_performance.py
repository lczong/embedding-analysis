"""Performance paper panels keep task-specific baselines and exact selections."""
import json
from pathlib import Path
import unittest

from embedding_analysis.config import load_config
from embedding_analysis.experiments.performance.tables import read_report
from embedding_analysis.publication.figures import selected_performance, build_figure

ROOT = Path(__file__).resolve().parents[2]


class PerformancePanelTests(unittest.TestCase):
    def setUp(self):
        self.cfg = load_config(ROOT/'configs/cazy.json')
        self.data = read_report(ROOT/self.cfg['performance']['report'], self.cfg)

    def test_three_tasks_keep_distinct_esm2_baselines(self):
        data = selected_performance(self.data, {'plot': '05_macro_f1_comparison'})
        self.assertEqual(len(data), 6)
        self.assertEqual(data[data.method == 'esm2_1nn'].value.tolist(), [96.80, 89.42, 66.67])

    def test_nca_selection_excludes_ft_and_bins(self):
        data = selected_performance(self.data, {'plot': '04_level_2_nca_A_overall'})
        self.assertEqual(len(data), 6)
        self.assertEqual(set(data.section), {'overall'})
        self.assertNotIn('l2_ft_1nn', set(data.method))

    def test_missing_and_duplicate_metrics_fail(self):
        import pandas as pd
        selected = selected_performance(self.data, {'plot': '05_macro_f1_comparison'})
        with self.assertRaisesRegex(ValueError, 'Missing required'):
            selected_performance(selected.iloc[1:], {'plot': '05_macro_f1_comparison'})
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            selected_performance(pd.concat([selected, selected.iloc[:1]]), {'plot': '05_macro_f1_comparison'})

    def test_four_panel_mappings_and_artists(self):
        import matplotlib.pyplot as plt
        from embedding_analysis.config import merge
        for num, panel, system, plot in [
            (2, 'f', 'cazy', '05_macro_f1_comparison'),
            (4, 'e', 'peptidase', '05_macro_f1_comparison'),
            (5, 'e', 'cazy', '04_level_2_nca_A_overall'),
            (5, 'k', 'peptidase', '04_level_2_nca_A_overall'),
        ]:
            config = json.loads((ROOT/f'paper/figures/figure{num}.json').read_text())
            spec = config['panels'][panel]
            self.assertEqual(spec['source']['system'], system)
            self.assertEqual(spec['selection']['plot'], plot)
            cfg = load_config(ROOT/f'configs/{system}.json')
            data = read_report(ROOT/cfg['performance']['report'], cfg)
            fig, ax, handles, details = build_figure(data, cfg, spec, merge(config['style'], spec['style']))
            try:
                self.assertEqual(len(ax.patches), 6)
                self.assertEqual(ax.get_title(), 'Test set performance')
                self.assertEqual(len(handles), 4 if plot.startswith('05') else 3)
                self.assertFalse(fig.legends)
                self.assertEqual(details['rows'], 6)
                self.assertAlmostEqual(fig.get_figwidth(), 3.9)
            finally:
                plt.close(fig)
