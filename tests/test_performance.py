"""Regression checks for report values, missing bins and independent plot caches."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import numpy as np
import pandas as pd

from embedding_analysis.config import load_config
from embedding_analysis.artifacts import ready
from embedding_analysis.experiments.performance.tables import read_report, plotting_tables
from embedding_analysis.experiments.performance.workflow import main

ROOT = Path(__file__).resolve().parents[1]


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.cfg = load_config(ROOT/'configs/cazy.json')
        self.path = ROOT/self.cfg['performance']['report']

    def changed(self, before, after, cfg=None):
        cfg = cfg or self.cfg
        text = (ROOT/cfg['performance']['report']).read_text()
        self.assertIn(before, text)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'report.md'
            path.write_text(text.replace(before, after, 1))
            return read_report(path, cfg)

    def test_task_specific_baselines_and_unknown_family_exclusion(self):
        data = read_report(self.path, self.cfg)
        baseline = data[(data.method == 'esm2_1nn') & (data.metric == 'Macro-F1') & (data.section == 'overall')]
        self.assertEqual(baseline.value.tolist(), [96.80, 89.42, 66.67])
        self.assertEqual(baseline.total_samples.tolist(), [49830, 26409, 26409])
        self.assertEqual(baseline.included_samples.tolist(), [49830, 26409, 26407])

    def test_empty_peptidase_tail_remains_nan(self):
        cfg = load_config(ROOT/'configs/peptidase.json')
        data = read_report(ROOT/cfg['performance']['report'], cfg)
        tail = data[(data.section == 'bins') & (data.label == 'tail')]
        self.assertEqual(len(tail), 20)
        self.assertTrue(tail.value.isna().all())
        self.assertTrue((tail.test_samples == 0).all())
        rows = plotting_tables(data)['L2', 'bins']
        self.assertTrue(all(np.isnan(r['Macro-F1']) for r in rows if r['Bin'] == 'tail'))

    def test_wrong_system_rejected(self):
        cfg = load_config(ROOT/'configs/peptidase.json')
        with self.assertRaisesRegex(ValueError, 'system'):
            read_report(self.path, cfg)

    def test_missing_method_rejected(self):
        line = '| l0_ft_1nn | 99.00% | 98.99% | 98.99% | 98.99% | 99.00% | 99.81% | 99.78% |'
        with self.assertRaisesRegex(ValueError, 'Missing methods'):
            self.changed(line, '')

    def test_duplicate_metric_rejected(self):
        line = '| esm2_1nn | 96.81% | 96.93% | 96.71% | 96.80% | 96.81% | 99.55% | 99.57% |'
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.changed(line, line+'\n'+line)

    def test_invalid_score_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Invalid percentage'):
            self.changed('96.81%', '196.81%')
        with self.assertRaisesRegex(ValueError, 'N/A'):
            self.changed('96.81%', 'N/A')

    def test_support_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Counts differ'):
            self.changed('| GT | 15175 | esm2_1nn', '| GT | 15176 | esm2_1nn')

    def test_missing_class_rejected(self):
        text = self.path.read_text()
        lines = [line for line in text.splitlines() if not line.startswith('| AA |')]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'report.md';path.write_text('\n'.join(lines))
            with self.assertRaisesRegex(ValueError, 'classes'):
                read_report(path, self.cfg)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root/'configs').mkdir()
        shutil.copy(ROOT/'configs/defaults.json', self.root/'configs/defaults.json')
        self.config = self.root/'configs/cazy.json'
        cfg = json.loads((ROOT/'configs/cazy.json').read_text())
        cfg['plot'] = {'performance': {'dpi': 40}}
        self.config.write_text(json.dumps(cfg))
        self.report = self.root/cfg['performance']['report']
        self.report.parent.mkdir(parents=True)
        shutil.copy(ROOT/cfg['performance']['report'], self.report)
        record = self.root/cfg['performance']['source_manifest']
        shutil.copy(ROOT/cfg['performance']['source_manifest'], record)
        # No embeddings, metadata or prediction CSVs in this isolated project.

    def run_step(self, step, *args):
        with contextlib.redirect_stdout(io.StringIO()):
            return main([step, '--config', str(self.config), *args])

    def test_input_changes_refresh_cache_and_selected_plots_preserve_others(self):
        table = self.run_step('tables')
        old = json.loads((table/'manifest.json').read_text())['signature']
        stamp = (table/'manifest.json').stat().st_mtime_ns
        self.run_step('tables')
        self.assertEqual(stamp, (table/'manifest.json').stat().st_mtime_ns)
        self.run_step('plots', '--plots', '05_macro_f1_comparison', '04_level_2_nca_A_overall')
        folder = self.root/'outputs/cazy/performance/figures/summary'
        files = list(folder.iterdir())
        self.assertEqual(len(files), 2)
        self.assertTrue(all(p.suffix == '.png' and '_legend' not in p.stem for p in files))
        retained = folder/'05_macro_f1_comparison.png'
        retained_stamp = retained.stat().st_mtime_ns
        self.report.write_text(self.report.read_text().replace('66.67%', '66.68%'))
        self.run_step('tables')
        self.assertNotEqual(old, json.loads((table/'manifest.json').read_text())['signature'])
        self.run_step('plots', '--plots', '04_level_2_nca_A_overall')
        self.assertEqual(retained_stamp, retained.stat().st_mtime_ns)
        self.assertEqual(set(files), set(folder.iterdir()))
        data = pd.read_csv(self.root/'outputs/cazy/performance/tables/summary/metrics.csv')
        changed = data[(data.task == 'L2') & (data.section == 'overall') & (data.method == 'esm2_1nn') & (data.metric == 'Macro-F1')]
        self.assertEqual(changed.value.iloc[0], 66.68)
        self.assertTrue(ready(table))
        self.assertTrue(ready(table.parent/'plots/04_level_2_nca_A_overall'))

    def test_version_outputs_are_isolated(self):
        table = self.run_step('tables', '--version', 'review')
        self.assertIn('_versions/review/performance', str(table))
        self.run_step('plots', '--version', 'review', '--plots', '04_level_2_nca_A_overall')
        self.assertFalse((self.root/'outputs/cazy/performance').exists())
        self.assertTrue((self.root/'outputs/cazy/_versions/review/performance/figures/summary/04_level_2_nca_A_overall.png').is_file())
