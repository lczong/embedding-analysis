"""Regression checks for backbone routes and linked-input path boundaries."""
import json
from pathlib import Path
import tempfile
import unittest

from embedding_analysis.config import input_path, load_config, local_path, spec_files
from embedding_analysis.artifacts import input_fingerprints


class LinkedInputTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.root = base / 'project'
        self.source = base / 'source'
        self.source.mkdir()
        (self.root / 'data').mkdir(parents=True)
        (self.source / 'embedding.csv').write_text('protein1,1,2\n')
        (self.root / 'data' / 'linked').symlink_to(self.source, target_is_directory=True)
        self.relative = 'data/linked/embedding.csv'
        self.cfg = {'_root': str(self.root), 'external_embedding_roots': [str(self.source)]}

    def test_declared_link_preserves_local_name_and_fingerprints(self):
        spec = {'path': self.relative, 'format': 'csv'}
        path = spec_files(self.cfg, spec)[0]
        self.assertEqual(path, self.root / self.relative)
        self.assertEqual(path.read_text(), 'protein1,1,2\n')
        self.cfg.update(metadata={'files': {}}, routes={'esm1b__l0-ft-ce': {'datasets': {'train': spec}}})
        records = input_fingerprints(self.cfg)
        self.assertEqual(records[0]['path'], self.relative)

    def test_undeclared_target_rejected(self):
        self.cfg.pop('external_embedding_roots')
        with self.assertRaises(ValueError):
            input_path(self.cfg, self.relative)

    def test_direct_external_path_rejected(self):
        with self.assertRaises(ValueError):
            input_path(self.cfg, str(self.source / 'embedding.csv'))
        with self.assertRaises(ValueError):
            input_path(self.cfg, '../source/embedding.csv')

    def test_output_links_remain_rejected(self):
        with self.assertRaises(ValueError):
            local_path(self.cfg, self.relative)
        (self.root / 'outputs').symlink_to(self.source, target_is_directory=True)
        with self.assertRaises(ValueError):
            input_path(self.cfg, 'outputs/embedding.csv')

    def test_allowlist_does_not_accept_sibling_prefix(self):
        other = self.source.with_name('source-other')
        other.mkdir()
        (other / 'embedding.csv').write_text('protein1,1,2\n')
        (self.root / 'data' / 'other').symlink_to(other, target_is_directory=True)
        with self.assertRaises(ValueError):
            input_path(self.cfg, 'data/other/embedding.csv')


class RouteTests(unittest.TestCase):
    def test_repository_configs(self):
        root = Path(__file__).resolve().parents[1]
        for name in ['cazy', 'peptidase', 'cazy_backbones']:
            cfg = load_config(root / 'configs' / (name + '.json'))
            self.assertTrue(cfg['routes'])
        self.assertEqual(len(cfg['routes']), 9)
        self.assertEqual({r['dimensions'] for r in cfg['routes'].values()}, {1280, 640, 480})

    def test_invalid_route_rejected(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'config.json'
            cfg = load_config(root / 'configs/cazy_backbones.json')
            cfg['routes'] = {'../esm1b__l0-ft-ce': next(iter(cfg['routes'].values()))}
            path.write_text(json.dumps(cfg))
            with self.assertRaisesRegex(ValueError, 'Invalid route'):
                load_config(path)


if __name__ == '__main__':
    unittest.main()
