"""Report selection, version isolation, metric provenance and PDF regression tests."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import pandas as pd

from embedding_analysis.artifacts import file_digest
from embedding_analysis.config import load_config
from embedding_analysis.publication.report import (
    ROOT, choose_version, grouped_jobs, metric_source, preset, render_report, source_paths)


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT/'paper/figures', self.root/'paper/figures')

    def test_default_report_has_four_grouped_pages(self):
        jobs = [(name,) for name in preset('cazy', 'esm1b')['panels']]
        groups = grouped_jobs(jobs)
        self.assertEqual([len(members) for _, _, members in groups], [3, 3, 3, 2])
        self.assertEqual([g[0] for g in groups], ['training', 'boundary', 'multilabel', 'metrics'])

    def test_nca_preset_pairs_figure5_routes_in_one_page(self):
        for system in ['cazy', 'peptidase']:
            config = preset(system, 'esm2-150m', kind='nca')
            panels = config['panels']
            self.assertEqual(panels['nca_direct']['source']['route'], 'esm2-150m__l2-frozen-nca')
            self.assertEqual(panels['nca_conditioned']['source']['route'], 'esm2-150m__l1-ft-ce__l2-frozen-nca')
            for spec in panels.values():
                self.assertEqual(spec['source']['system'], system)
                self.assertEqual(spec['kind'], 'overview_families')
                self.assertEqual(spec['selection']['top_family_fraction'], .15)
            groups = grouped_jobs([(name,) for name in panels])
            self.assertEqual(len(groups), 1)
            self.assertEqual(len(groups[0][2]), 2)

    def test_cazy_selection_matches_paper(self):
        config = preset('cazy', 'esm1b')
        self.assertEqual(len(config['panels']), 11)
        self.assertEqual(config['panels']['families_l2']['selection']['top_family_fraction'], .15)
        self.assertEqual(config['panels']['multilabel_l2']['selection']['combinations'], ['CBM|GH', 'CBM|PL'])
        self.assertEqual(config['panels']['ba']['selection']['combinations'],
                         ['CBM|GH', 'CBM|PL', 'AA|CBM', 'CBM|CE', 'GH|GT', 'CBM|GT'])
        self.assertEqual(config['panels']['binary_l0']['source']['route'], 'esm1b__l0-ft-ce')

    def test_peptidase_uses_own_combinations_at_every_level(self):
        config = preset('peptidase', 'esm1b')
        self.assertEqual(len(config['panels']), 11)
        for level in range(3):
            self.assertEqual(config['panels'][f'multilabel_l{level}']['selection']['combinations'], ['C|N', 'C|M'])
        self.assertEqual(config['panels']['ba']['selection']['combinations'], ['C|M', 'C|N', 'C|S', 'N|S', 'M|S', 'S|T'])
        self.assertEqual(config['panels']['binary_l0']['style']['legend_labels']['train'], 'Peptidase')

    def mark_sources(self, panels, version):
        for path in source_paths(self.root, 'cazy', version, panels):
            path.mkdir(parents=True, exist_ok=True)
            (path/'manifest.json').write_text('{}')

    def test_auto_version_and_ambiguity(self):
        panels = preset('cazy', 'esm2-150m')['panels']
        self.mark_sources(panels, 'esm2-150m')
        self.assertEqual(choose_version(self.root, 'cazy', panels, 'auto'), 'esm2-150m')
        self.mark_sources(panels, None)
        with self.assertRaisesRegex(ValueError, 'Multiple complete versions'):
            choose_version(self.root, 'cazy', panels, 'auto')
        self.assertIsNone(choose_version(self.root, 'cazy', panels, 'default'))

    def test_missing_sources_do_not_create_report(self):
        with self.assertRaisesRegex(ValueError, 'Missing workflow sources'):
            choose_version(self.root, 'peptidase', preset('peptidase', 'esm1b')['panels'], 'auto')
        self.assertFalse((self.root/'outputs').exists())

    def test_model_path_traversal_rejected(self):
        with self.assertRaises(ValueError):
            preset('cazy', '../esm1b')

    def write_metrics(self):
        spec = preset('cazy', 'esm1b')['panels']['silhouette']
        for i, route in enumerate(spec['selection']['routes']):
            path = self.root/'outputs/cazy/boundary/artifacts'/route/'metrics'
            path.mkdir(parents=True)
            csv = path/'samples.csv'
            pd.DataFrame({'sequence_id': ['a', 'b', 'c'], 'dataset_role': ['shuffled', 'idr', 'ood'],
                          'silhouette': [.1+i*.1, .2, .3]}).to_csv(csv, index=False)
            meta = {'config': {'system': 'cazy'}, 'experiment': 'boundary', 'route': route, 'stage': 'metrics',
                    'artifacts': {'samples.csv': csv.stat().st_size}, 'sha256': {'samples.csv': file_digest(csv)}}
            (path/'manifest.json').write_text(json.dumps(meta))
        return spec

    def test_metric_loading_needs_no_summary(self):
        spec = self.write_metrics()
        data, cfg, provenance = metric_source(spec, self.root, None)
        self.assertEqual(len(data), 9)
        self.assertEqual(list(dict.fromkeys(data.route)), spec['selection']['routes'])
        self.assertEqual(len(provenance['metric_sources']), 3)
        self.assertFalse((self.root/'outputs/cazy/boundary/artifacts/summary').exists())

    def test_metric_identity_and_tampering_rejected(self):
        spec = self.write_metrics()
        path = source_paths(self.root, 'cazy', None, {'silhouette': spec})[0]
        manifest = path/'manifest.json'
        meta = json.loads(manifest.read_text())
        meta['route'] = 'esm2__l0-ft-ce'
        manifest.write_text(json.dumps(meta))
        with self.assertRaisesRegex(ValueError, 'identity mismatch'):
            metric_source(spec, self.root, None)
        meta['route'] = spec['selection']['routes'][0]
        manifest.write_text(json.dumps(meta))
        csv = path/'samples.csv'
        csv.write_text(csv.read_text().replace('0.1', '0.9'))
        with self.assertRaisesRegex(ValueError, 'changed metric source'):
            metric_source(spec, self.root, None)

    def test_real_nca_pdf_has_both_routes_on_one_page(self):
        config = preset('cazy', 'esm1b', kind='nca')
        cfg = load_config(ROOT/'configs/cazy.json')
        data = pd.DataFrame({'sequence_id': ['a', 'b', 'c', 'd'],
                             'dataset_role': ['train']*4,
                             'class_label': ['GH', 'GH', 'GT', 'GT'],
                             'family_label': ['GH1', 'GH1', 'GT1', 'GT1'],
                             'x': [0, 1, 3, 4], 'y': [0, 1, 3, 4]})
        jobs = [(name, spec, config['style'], data, cfg, {'fixture': True})
                for name, spec in config['panels'].items()]
        path = render_report(config, jobs, 'cazy', 'esm1b', 'nca-test', self.root, dpi=40)
        from pypdf import PdfReader
        reader = PdfReader(path)
        self.assertEqual(len(reader.pages), 1)
        text = reader.pages[0].extract_text()
        self.assertIn('Direct L2 NCA', text)
        self.assertIn('L1-conditioned L2 NCA', text)
        self.assertEqual(path.name, 'cazy_esm1b_nca-test_nca.pdf')

    def test_real_pdf_subset_cache_and_names(self):
        config = preset('peptidase', 'esm1b')
        config['panels'] = {'binary_l0': config['panels']['binary_l0']}
        spec = config['panels']['binary_l0']
        cfg = load_config(ROOT/'configs/peptidase.json')
        data = pd.DataFrame({'sequence_id': ['a', 'b', 'c', 'd'],
                             'dataset_role': ['train', 'train', 'non_target_train', 'non_target_train'],
                             'x': [0, 1, 3, 4], 'y': [0, 1, 3, 4]})
        style = {**config['style'], **spec.get('style', {})}
        jobs = [('binary_l0', spec, style, data, cfg, {'fixture': True})]
        path = render_report(config, jobs, 'peptidase', 'esm1b', None, self.root, dpi=40)
        self.assertTrue(path.read_bytes().startswith(b'%PDF-'))
        from pypdf import PdfReader
        reader = PdfReader(path)
        self.assertEqual(len(reader.pages), 1)
        self.assertIn('Peptidase', reader.pages[0].extract_text())
        self.assertIn('peptidase_esm1b_default_', path.name)
        stamp = path.stat().st_mtime_ns
        render_report(config, jobs, 'peptidase', 'esm1b', None, self.root, dpi=40)
        self.assertEqual(stamp, path.stat().st_mtime_ns)


if __name__ == '__main__':
    unittest.main()
