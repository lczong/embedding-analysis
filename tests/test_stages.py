import json
import importlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fixtures_builder import build_fixture
from embedding_analysis import pca
from embedding_analysis.experiments import ood, multilabel, unseen, overview, structure
from embedding_analysis.experiments.ood import workflow as ood_workflow
from embedding_analysis.experiments.multilabel import workflow as multilabel_workflow
from embedding_analysis.experiments.unseen import workflow as unseen_workflow
from embedding_analysis.experiments.overview import workflow as overview_workflow
from embedding_analysis.experiments.structure import workflow as structure_workflow
ENTRYPOINTS={"pca":pca.main,"ood":ood_workflow.main,"multilabel":multilabel_workflow.main,"unseen":unseen_workflow.main,"overview":overview_workflow.main,"structure":structure_workflow.main}



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
                    ENTRYPOINTS[exp](args)
                    return dest
                pca=run('pca','prepare'); sample=run('ood','sample')
                metrics={};coords={}
                for exp in ['ood','multilabel','unseen','structure']:
                    with patch('embedding_analysis.prepared.reduce_2d',side_effect=AssertionError('metrics ran reduction')):
                        metrics[exp]=run(exp,'metrics',pca,sample if exp=='ood' else None)
                    self.assertFalse(list(metrics[exp].rglob('coordinates.csv')))
                for exp in ['ood','multilabel','unseen','overview']:
                    for method in ['tsne','umap']:
                        with patch(f'embedding_analysis.experiments.{exp}.compute.compute_metrics',side_effect=AssertionError('reduction ran metrics'),create=True), patch('embedding_analysis.prepared.reduce_2d',side_effect=lambda X,*a:X[:,:2]) as reduce:
                            coords[exp]=run(exp,method,pca,sample if exp=='ood' else None)
                            self.assertTrue(reduce.called)
                            self.assertEqual(reduce.call_args.args[1],method)
                # Saved artifacts suffice after all raw inputs disappear.
                (root/'data').rename(root/'data-hidden')
                with patch('embedding_analysis.prepared.load_embedding',side_effect=AssertionError('plot read raw data')), patch('embedding_analysis.prepared.reduce_2d',side_effect=AssertionError('plot ran reduction')):
                    for exp,source in metrics.items():
                        dest=run(exp,'metric-plots',source)
                        self.assertTrue(list(dest.rglob('*.png')))
                    for exp,source in {**coords,'structure':metrics['structure']}.items():
                        dest=run(exp,'visualization',source)
                        self.assertTrue(list(dest.rglob('*.png')))
                for exp,source in metrics.items():
                    summary=importlib.import_module(f'embedding_analysis.experiments.{exp}.summary').main
                    table=root/'outputs'/'summary'/exp/'tables'
                    figures=root/'outputs'/'summary'/exp/'plots'
                    summary(['tables',*common,'--inputs',str(source),'--output',str(table)])
                    summary(['plots',*common,'--input',str(table),'--output',str(figures)])
                    self.assertTrue((table/'summary.csv').exists())
                    self.assertTrue(list(figures.glob('*.png')))
                with self.assertRaises(SystemExit):
                    ENTRYPOINTS['ood'](['metrics',*common,'--input',str(root/'absent'),'--output',str(root/'outputs/fail')])
                with self.assertRaises(SystemExit):
                    ENTRYPOINTS['multilabel'](['visualization',*common,'--input',str(metrics['multilabel']),'--output',str(root/'outputs/wrong')])
                # Stage cache survives absent raw inputs and never invokes upstream work.
                with patch('embedding_analysis.experiments.multilabel.compute.compute_metrics',side_effect=AssertionError('cache recomputed')):
                    run('multilabel','metrics',pca)
