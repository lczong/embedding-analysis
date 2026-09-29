import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
from embedding_analysis.config import load_config
from embedding_analysis.artifacts import run_context, ready
from embedding_analysis.cli import main
from embedding_analysis.workflows import run_experiment

PROJECT=Path(__file__).resolve().parents[1]


def build_fixture(root,system='cazy',full_routes=2):
    (root/'configs').mkdir(parents=True)
    cfg=json.loads((PROJECT/'configs'/f'{system}.json').read_text())
    defaults=json.loads((PROJECT/'configs/defaults.json').read_text())
    defaults['preprocessing']['n_components']=3
    defaults['experiments']['unseen'].update(n_pcs=3,min_family_size=2,train_family_count=2)
    defaults['experiments']['structure'].update(min_family_size=2,ks=[1,3])
    defaults['experiments']['ood']['target_size']=5
    defaults['experiments']['multilabel']['min_combination_size']=2
    defaults['reduction']['tsne'].update(perplexity=3,n_iter_early=15,n_iter_main=20)
    defaults['reduction']['umap'].update(n_neighbors=3)
    cfg['classes']=cfg['classes'][:2];cfg['routes']={};cfg['plot']['highlight_combinations']=[]
    cols=cfg['metadata'];rng=np.random.default_rng(123)
    labels={};values={};ids={}
    for role in ['train','unseen','multi','ood','shuffled','idr']:
        rows=[];vectors=[]
        if role in ['train','unseen']:
            for ci,cls in enumerate(cfg['classes']):
                for family in range(3 if role=='train' else 2):
                    for i in range(4):
                        rows.append([f'{role}_{ci}_{family}_{i}',cls,f'{role}_{ci}_{family}'])
                        center=np.zeros(6);center[ci]=4;center[2+family]=2
                        vectors.append(center+rng.normal(0,.2,6))
        else:
            for i in range(8):
                rows.append([f'{role}_{i}','|'.join(cfg['classes']),f'm_{i}'])
                vectors.append(rng.normal(size=6))
        labels[role]=rows;values[role]=np.asarray(vectors);ids[role]=[r[0] for r in rows]
    for role in ['train','unseen','multi']:
        p=root/cfg['metadata']['files'][role];p.parent.mkdir(parents=True,exist_ok=True)
        pd.DataFrame(labels[role],columns=[cols['id_column'],cols['class_column'],cols['family_column']]).to_csv(p,sep='\t',index=False)
    routes=['esm2__l0-ft-ce','esm2__l2-frozen-nca','esm2__l1-ft-ce__l2-frozen-nca']
    for ri,route in enumerate(routes):
        roles=['train','unseen','multi','ood','shuffled','idr'] if ri<full_routes else ['train']
        datasets={}
        for role in roles:
            rel=f'data/{system}/{route}/{role}.csv';p=root/rel;p.parent.mkdir(parents=True,exist_ok=True)
            frame=pd.DataFrame(values[role]+ri*.02);frame.insert(0,'id',ids[role]);frame.to_csv(p,index=False,header=False)
            datasets[role]={'format':'csv','path':rel}
        cfg['routes'][route]={'dimensions':6,'datasets':datasets}
    (root/'configs/defaults.json').write_text(json.dumps(defaults))
    p=root/'configs'/f'{system}.json';p.write_text(json.dumps(cfg));return p


class SharedWorkflows(unittest.TestCase):
    def test_both_systems_all_workflows_and_skip_report(self):
        for system in ['cazy','peptidase']:
            with self.subTest(system=system),tempfile.TemporaryDirectory() as td:
                p=build_fixture(Path(td),system)
                with patch('embedding_analysis.workflows.reduce_2d',side_effect=lambda X,*a:X[:,:2]):
                    main(['run','--config',str(p),'--no-plots'])
                cfg=load_config(p);runid,payload=run_context(cfg)
                report=json.loads((Path(td)/'outputs'/system/'_runs'/runid/'report.json').read_text())
                self.assertEqual(sum(r['status']=='complete' for r in report['experiments']),12)
                self.assertEqual(sum(r['status']=='skipped' for r in report['experiments']),3)
                routes=list(cfg['routes'])
                m=[]
                for route in routes[:2]:
                    path=Path(td)/'outputs'/system/route/'ood'/runid
                    m.append(json.loads((path/'sampling.json').read_text()))
                    self.assertTrue(ready(path))
                self.assertEqual(m[0],m[1])
                with patch('embedding_analysis.workflows.compute',side_effect=AssertionError('cache not used')):
                    run_experiment(cfg,routes[0],'ood',runid,payload,plot=False)
                cfg['experiments']['ood']['target_size']=4
                self.assertNotEqual(runid,run_context(cfg)[0])
                with self.assertRaises(SystemExit):
                    main(['run','--config',str(p),'--route',routes[-1],'--experiment','ood','--no-plots'])


if __name__=='__main__':unittest.main()
