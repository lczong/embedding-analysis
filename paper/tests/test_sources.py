"""Check provenance boundaries using small, independent source artifacts."""
import json
from pathlib import Path
import tempfile
import unittest

from embedding_analysis.artifacts import file_digest
from embedding_analysis.publication.render import resolve_source


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root/'outputs/cazy/overview/artifacts/esm2/tsne'
        self.path.mkdir(parents=True)
        self.csv = self.path/'coordinates.csv'
        self.csv.write_text('sequence_id,dataset_role,class_label,family_label,x,y\na,train,GH,GH1,0,1\nb,train,GH,GH1,1,0\n')
        self.meta = {'config': {'system': 'cazy'}, 'experiment': 'overview',
                     'route': 'esm2', 'stage': 'tsne',
                     'artifacts': {'coordinates.csv': self.csv.stat().st_size},
                     'sha256': {'coordinates.csv': file_digest(self.csv)}}
        self.save()
        self.spec = {'kind': 'overview_classes', 'source': {'system': 'cazy',
                     'workflow': 'overview', 'route': 'esm2', 'stage': 'tsne'}}

    def save(self):
        (self.path/'manifest.json').write_text(json.dumps(self.meta))

    def test_valid_source(self):
        data, _, record = resolve_source(self.spec, self.root)
        self.assertEqual(data.sequence_id.tolist(), ['a', 'b'])
        self.assertEqual(record['coordinates_sha256'], file_digest(self.csv))

    def test_same_size_tampering_is_rejected(self):
        self.csv.write_text(self.csv.read_text().replace('0,1', '0,2'))
        with self.assertRaisesRegex(ValueError, 'changed source'):
            resolve_source(self.spec, self.root)

    def test_wrong_route_in_manifest_is_rejected(self):
        self.meta['route'] = 'esm2__l0-ft-ce'
        self.save()
        with self.assertRaisesRegex(ValueError, 'identity mismatch'):
            resolve_source(self.spec, self.root)

    def test_locked_source_is_rejected(self):
        self.spec['source']['coordinates_sha256'] = 'old-digest'
        with self.assertRaisesRegex(ValueError, 'Locked coordinates'):
            resolve_source(self.spec, self.root)

    def test_duplicate_ids_are_rejected(self):
        self.csv.write_text(self.csv.read_text().replace('b,train', 'a,train'))
        self.meta['sha256']['coordinates.csv'] = file_digest(self.csv)
        self.save()
        with self.assertRaisesRegex(ValueError, 'duplicate IDs'):
            resolve_source(self.spec, self.root)

    def test_missing_source_does_not_create_outputs(self):
        self.spec['source']['route'] = 'absent'
        with self.assertRaisesRegex(ValueError, 'Missing source'):
            resolve_source(self.spec, self.root)
        self.assertFalse((self.root/'outputs/paper').exists())
