import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fixtures_builder import build_fixture
from embedding_analysis.stages import main


class IndependentStages(unittest.TestCase):
    def test_independent_branches_and_plot_without_raw_data(self):
        for system in ['cazy', 'peptidase']:
            with self.subTest(system=system), tempfile.TemporaryDirectory() as td:
                root=Path(td); config=build_fixture(root, system)
                common=['--config',str(config)]
                def run(exp,step,source=None,sampling=None):
                    dest=root/'outputs'/'stages'/exp/step
                    args=[step,*common,'--output',str(dest)]
                    if source: args+=['--input',str(source)]
                    if sampling: args+=['--sampling',str(sampling)]
                    if exp=='pca': args+=['--route','esm2__l0-ft-ce']
                    main(exp,args)
                    return dest
                pca=run('pca','prepare'); sample=run('ood','sample')
                metrics={};coords={}
                for exp in ['ood','multilabel','unseen','structure']:
                    with patch('embedding_analysis.workflows.reduce_2d',side_effect=AssertionError('metrics ran reduction')):
                        metrics[exp]=run(exp,'metrics',pca,sample if exp=='ood' else None)
                    self.assertFalse(list(metrics[exp].rglob('coordinates.csv')))
                for exp in ['ood','multilabel','unseen','overview']:
                    for method in ['tsne','umap']:
                        with patch('embedding_analysis.workflows.compute_metrics',side_effect=AssertionError('reduction ran metrics')), patch('embedding_analysis.workflows.reduce_2d',side_effect=lambda X,*a:X[:,:2]) as reduce:
                            coords[exp]=run(exp,method,pca,sample if exp=='ood' else None)
                            self.assertTrue(reduce.called)
                            self.assertEqual(reduce.call_args.args[1],method)
                # Saved artifacts suffice after all raw inputs disappear.
                (root/'data').rename(root/'data-hidden')
                with patch('embedding_analysis.workflows.compute_metrics',side_effect=AssertionError('plot ran metrics')), patch('embedding_analysis.workflows.compute_coordinates',side_effect=AssertionError('plot ran reduction')):
                    for exp,source in metrics.items():
                        dest=run(exp,'metric-plots',source)
                        self.assertTrue(list(dest.rglob('*.png')))
                    for exp,source in {**coords,'structure':metrics['structure']}.items():
                        dest=run(exp,'visualization',source)
                        self.assertTrue(list(dest.rglob('*.png')))
                with self.assertRaises(SystemExit):
                    main('ood',['metrics',*common,'--input',str(root/'absent'),'--output',str(root/'outputs/fail')])
                with self.assertRaises(SystemExit):
                    main('multilabel',['visualization',*common,'--input',str(metrics['multilabel']),'--output',str(root/'outputs/wrong')])
                # Stage cache survives absent raw inputs and never invokes upstream work.
                with patch('embedding_analysis.workflows.compute_metrics',side_effect=AssertionError('cache recomputed')):
                    run('multilabel','metrics',pca)
