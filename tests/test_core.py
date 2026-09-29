import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import silhouette_samples, silhouette_score, davies_bouldin_score, calinski_harabasz_score
from embedding_analysis.metrics import target_silhouette, class_ba, family_quality, family_centroids, centroid_structure
from embedding_analysis.sampling import choose_ids
from embedding_analysis.reduction import fit_pca
from embedding_analysis.data import load_embedding, read_metadata
from embedding_analysis.artifacts import ready, complete, run_context
from embedding_analysis.config import local_path


class MetricsRegression(unittest.TestCase):
    def test_family_metrics_against_frozen_legacy(self):
        fixture=json.loads((Path(__file__).parent/'fixtures/legacy_family_quality.json').read_text())
        X=np.asarray(fixture['X']);labels=np.asarray(fixture['labels']);old=fixture['expected']
        for chunk in [1,4,30]:
            table,overall=family_quality(X,labels,chunk)
            for key,col in [('per_family_silhouette','silhouette_mean'),('per_family_dbi','legacy_pairwise_dbi'),('per_family_dunn','dunn_cosine'),('per_family_intra_dist','intra_mean_euclidean'),('per_family_nearest_centroid','nearest_centroid_euclidean')]:
                np.testing.assert_allclose(table[col],[old[key][f] for f in table.family_label],rtol=1e-7,atol=1e-8)
            for col in ['ch_between','ch_within','ch_per_family']:
                np.testing.assert_allclose(table[col],[old['per_family_ch'][f][col] for f in table.family_label])
            self.assertAlmostEqual(overall['dunn_cosine'],old['global_dunn'])
            self.assertAlmostEqual(overall['silhouette_cosine'],silhouette_score(X,labels,metric='cosine'))
            self.assertAlmostEqual(overall['davies_bouldin_euclidean'],davies_bouldin_score(X,labels))
            self.assertAlmostEqual(overall['calinski_harabasz_euclidean'],calinski_harabasz_score(X,labels))

    def test_ood_matches_sklearn(self):
        rng=np.random.default_rng(3);reference=rng.normal(size=(15,4));target=rng.normal(2,1,size=(7,4))
        X=np.vstack([target,reference]);labels=[0]*len(target)+[1]*len(reference)
        for distance in ['euclidean','cosine']:
            expected=silhouette_samples(X,labels,metric=distance)[:len(target)]
            np.testing.assert_allclose(target_silhouette(target,reference,distance,2),expected,rtol=1e-7,atol=1e-8)

    def test_class_ba_and_invalid_cases(self):
        train=np.array([[-1.,0],[-1.,0],[1.,0],[1.,0]])
        result=class_ba(train,['A','A','B','B'],np.array([[0.,0],[1.,0],[2.,0],[0.,0],[0.,0]]),['A|B','A|B','B|A','A|C','A'])
        np.testing.assert_allclose(result.ba_score[:3],[1,0,-1])
        self.assertEqual(result.invalid_reason.iloc[3],'missing_class_centroid')
        self.assertEqual(result.invalid_reason.iloc[4],'not_multilabel')
        self.assertEqual(class_ba(np.zeros((2,2)),['A','B'],np.zeros((1,2)),['A|B']).invalid_reason.iloc[0],'degenerate_radius')

    def test_centroid_purity_excludes_self_with_ties(self):
        C=np.array([[0.,0],[0.,0],[5.,5],[5.,5]])
        result=centroid_structure(C,['A','A','B','B'],[1])
        self.assertEqual(result.iloc[0].value,1.)
        self.assertAlmostEqual(result[result.metric=='class_silhouette'].value.iloc[0],1.)

    def test_train_fit_pca_not_probe_fit(self):
        train=np.random.default_rng(5).normal(size=(20,6));probe=np.array([[100.,0,0,0,0,0]])
        model,X=fit_pca(train,3,42);before=model.named_steps['pca'].components_.copy()
        model.transform(probe)
        np.testing.assert_array_equal(before,model.named_steps['pca'].components_)
        self.assertEqual(X.shape,(20,3))

    def test_sampling_is_order_independent(self):
        ids=[str(i) for i in range(30)]
        self.assertEqual(choose_ids(ids,10,42,'ood'),choose_ids(ids[::-1],10,42,'ood'))
        self.assertNotEqual(choose_ids(ids,10,42,'ood'),choose_ids(ids,10,43,'ood'))


class InputIntegrity(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.cfg={'_root':str(self.root)}
    def tearDown(self):self.temp.cleanup()

    def test_npy_requires_and_preserves_reference_ids(self):
        X=np.arange(12).reshape(3,4);np.save(self.root/'x.npy',X)
        (self.root/'ids.csv').write_text('z,1\na,2\nx,3\n')
        spec={'format':'npy','path':'x.npy','ids_reference':'ids.csv'}
        result=load_embedding(self.cfg,spec)
        self.assertEqual(result.ids.tolist(),['z','a','x']);np.testing.assert_array_equal(result.values,X)
        (self.root/'ids.csv').write_text('z,1\na,2\n')
        with self.assertRaises(ValueError):load_embedding(self.cfg,spec)

    def test_csv_shards_duplicate_id_is_error(self):
        (self.root/'a.csv').write_text('a,1,2\nb,3,4\n');(self.root/'b.csv').write_text('a,5,6\n')
        with self.assertRaises(ValueError):load_embedding(self.cfg,{'format':'csv','paths':['a.csv','b.csv']})

    def test_metadata_missing_is_not_silently_dropped(self):
        (self.root/'m.tsv').write_text('id\tclass\tfamily\na\tA\tF\n')
        self.cfg['metadata']={'files':{'train':'m.tsv'},'id_column':'id','class_column':'class','family_column':'family'}
        with self.assertRaises(ValueError):read_metadata(self.cfg,'train',['a','b'])

    def test_local_path_rejects_external(self):
        with self.assertRaises(ValueError):local_path(self.cfg,'../external')

    def test_missing_artifact_invalidates_cache_but_replot_does_not(self):
        (self.root/'scores.csv').write_text('score\n1\n')
        (self.root/'figures').mkdir();(self.root/'figures/plot.png').write_bytes(b'old')
        complete(self.root,{'experiment':'test'})
        self.assertTrue(ready(self.root))
        (self.root/'figures/plot.png').write_bytes(b'new longer plot');self.assertTrue(ready(self.root))
        (self.root/'scores.csv').unlink();self.assertFalse(ready(self.root))


if __name__=='__main__':unittest.main()
