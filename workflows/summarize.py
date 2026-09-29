#!/usr/bin/env python3
"""Aggregate explicit metrics artifacts, or plot saved summary tables."""
import argparse
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from embedding_analysis.config import load_config, local_path
from embedding_analysis.artifacts import ready, write_json


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=['tables','plots'])
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--input',type=Path,action='append',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv);cfg=load_config(args.config)
    dest=local_path(cfg,str(args.output));root=local_path(cfg,cfg['output_root'])
    if dest==root or not dest.is_relative_to(root): parser.error('Output must be a subdirectory of output_root')
    sources=[local_path(cfg,str(p)) for p in args.input]
    if any(p==dest or dest.is_relative_to(p) or p.is_relative_to(dest) for p in sources): parser.error('Separate input and output directories required')
    if dest.exists() and any(dest.iterdir()): parser.error('Choose an empty output directory')
    os.environ.setdefault('MPLCONFIGDIR',str(local_path(cfg,'.cache/matplotlib')))
    import pandas as pd
    tables={'ood':'summary.csv','multilabel':'summary.csv','unseen':'families.csv','structure':'metrics.csv'}
    if args.step=='tables':
        grouped={}
        for source in sources:
            if not ready(source): parser.error(f'Incomplete input: {source}')
            manifest=json.loads((source/'manifest.json').read_text());exp=manifest['experiment']
            if manifest.get('stage')!='metrics' or exp not in tables or manifest['config']['system']!=cfg['system']:
                parser.error('Inputs must be metrics artifacts from the configured system')
            frame=pd.read_csv(source/tables[exp]);frame.insert(0,'route',manifest['route'])
            grouped.setdefault(exp,[]).append(frame)
        dest.mkdir(parents=True,exist_ok=True)
        for exp,frames in grouped.items(): pd.concat(frames,ignore_index=True).to_csv(dest/f'{exp}.csv',index=False)
    else:
        if len(sources)!=1: parser.error('plots requires one summary directory')
        source=sources[0]
        manifest=json.loads((source/'summary.json').read_text())
        if manifest['step']!='tables' or manifest['system']!=cfg['system']: parser.error('Expected summary tables from this system')
        from embedding_analysis.plotting import save
        import matplotlib.pyplot as plt
        dest.mkdir(parents=True,exist_ok=True)
        for exp in tables:
            path=source/f'{exp}.csv'
            if not path.exists(): continue
            df=pd.read_csv(path)
            if df.empty: continue
            fig,ax=plt.subplots(figsize=(9,4))
            if exp=='structure':
                for route,g in df[df.metric=='knn_class_purity'].groupby('route'): ax.plot(g.k,g.value,marker='o',label=route)
                ax.set(xlabel='k',ylabel='Centroid class purity');ax.legend(fontsize=7)
            else:
                metric={'ood':'mean','multilabel':'mean','unseen':'silhouette_mean'}[exp]
                group={'ood':'dataset_role','multilabel':'class_label','unseen':'class_label'}[exp]
                df.pivot_table(index=group,columns='route',values=metric,aggfunc='mean').plot.bar(ax=ax)
                ax.set_ylabel(metric);ax.legend(fontsize=6)
            save(fig,dest/exp,cfg)
    write_json(dest/'summary.json',{'system':cfg['system'],'step':args.step,'inputs':[str(p) for p in sources]})
    print(dest)


if __name__=='__main__': main()
