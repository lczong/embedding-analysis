#!/usr/bin/env python3
"""Run all phase-1 workflows on small real-data subsets, without modifying originals."""
from pathlib import Path
import json
import os
import sys
import copy
PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/'src'))
os.environ.setdefault('MPLCONFIGDIR',str(PROJECT/'.cache/matplotlib'))
os.environ.setdefault('NUMBA_CACHE_DIR',str(PROJECT/'.cache/numba'))
os.environ.setdefault('XDG_CACHE_HOME',str(PROJECT/'.cache/xdg'))
os.environ.setdefault('LOKY_MAX_CPU_COUNT','1')
import numpy as np
import pandas as pd
from embedding_analysis.config import load_config,local_path,spec_files
from embedding_analysis.data import read_ids,load_embedding,read_metadata
from embedding_analysis.cli import main


def extract_csv(cfg,spec,wanted,dest):
    frames=[];remaining=set(wanted)
    for p in spec_files(cfg,spec):
        with p.open() as f:n=len(f.readline().rstrip().split(','))
        for chunk in pd.read_csv(p,header=None,dtype={0:str,**{i:np.float32 for i in range(1,n)}},chunksize=4096):
            found=chunk[chunk[0].isin(remaining)]
            if len(found):frames.append(found);remaining.difference_update(found[0])
            if not remaining:break
        if not remaining:break
    if remaining:raise ValueError(f'Missing smoke IDs: {len(remaining)}')
    df=pd.concat(frames).set_index(0).loc[wanted].reset_index()
    dest.parent.mkdir(parents=True,exist_ok=True);df.to_csv(dest,index=False,header=False)


def main_smoke():
    for system,classes in [('cazy',['CBM','GH']),('peptidase',['C','M'])]:
        original=load_config(PROJECT/'configs'/f'{system}.json')
        smoke=PROJECT/'outputs/smoke'/system
        if (smoke/'configs'/f'{system}.json').exists():
            config_path=smoke/'configs'/f'{system}.json'
        else:
            (smoke/'configs').mkdir(parents=True,exist_ok=True)
            cfg={k:copy.deepcopy(v) for k,v in original.items() if not k.startswith('_')}
            cfg['classes']=classes;cfg['routes']={};cfg['plot']['highlight_combinations']=['|'.join(classes)]
            cfg['plot']['formats']=['png'];cfg['plot']['dpi']=100
            cfg['preprocessing']['n_components']=5
            cfg['experiments']['unseen'].update(n_pcs=5,min_family_size=2,train_family_count=3)
            cfg['experiments']['structure'].update(min_family_size=2,ks=[1,3])
            cfg['experiments']['ood']['target_size']=8
            cfg['experiments']['multilabel']['min_combination_size']=2
            cfg['reduction']['tsne'].update(perplexity=5,n_iter_early=50,n_iter_main=100)
            cfg['reduction']['umap'].update(n_neighbors=5)
            route='esm2__l2-frozen-nca';datasets={}
            for role,spec in original['routes'][route]['datasets'].items():
                if role in ['train','unseen','multi']:
                    m=original['metadata'];full=pd.read_csv(local_path(original,m['files'][role]),sep='\t',dtype=str)
                    cls_col=m['class_column'];fam_col=m['family_column'];id_col=m['id_column']
                    if role=='multi':
                        subset=full[full[cls_col].map(lambda x:set(x.split('|'))==set(classes))].head(8)
                    else:
                        pieces=[]
                        for cls in classes:
                            group=full[full[cls_col]==cls];counts=group[fam_col].value_counts()
                            families=sorted(counts[counts>=4].index)[:3 if role=='train' else 2]
                            pieces += [group[group[fam_col]==family].head(4) for family in families]
                        subset=pd.concat(pieces)
                    wanted=subset[id_col].tolist()
                    if not wanted:raise ValueError(f'No real smoke input for {system}/{role}')
                    mp=smoke/cfg['metadata']['files'][role];mp.parent.mkdir(parents=True,exist_ok=True);subset.to_csv(mp,sep='\t',index=False)
                else:
                    wanted=pd.read_csv(spec_files(original,spec)[0],header=None,usecols=[0],dtype=str,nrows=8)[0].tolist()
                rel=f'data/{system}/embeddings/{route}/{role}.csv'
                extract_csv(original,spec,wanted,smoke/rel)
                datasets[role]={'format':'csv','path':rel}
                print(f'Smoke subset: {system}/{role}: {len(wanted)} rows',flush=True)
            cfg['routes'][route]={'dimensions':256,'datasets':datasets}
            config_path=smoke/'configs'/f'{system}.json';config_path.write_text(json.dumps(cfg,indent=2)+'\n')
        main(['validate','--config',str(config_path),'--deep'])
        main(['run','--config',str(config_path)])
        main(['summarize','--config',str(config_path)])


if __name__=='__main__':main_smoke()
