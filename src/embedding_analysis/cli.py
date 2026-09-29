"""A single CLI for either system; no legacy scripts are executed."""
from pathlib import Path
import argparse
import json
import os
from .config import load_config, local_path


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['validate','prepare','run','plot','summarize'])
    p.add_argument('--config',required=True,type=Path)
    p.add_argument('--route',action='append',help='Repeat to select routes; default all configured routes')
    p.add_argument('--experiment',choices=['all','overview','ood','multilabel','unseen','structure'],default='all')
    p.add_argument('--force',action='store_true')
    p.add_argument('--no-plots',action='store_true')
    p.add_argument('--deep',action='store_true',help='Validate every row and metadata alignment')
    p.add_argument('--run-dir',type=Path,help='Saved experiment directory for plot-only')
    args=p.parse_args(argv)
    cfg=load_config(args.config)
    cache=Path(cfg['_root'])/'.cache'
    for var,suffix in [('MPLCONFIGDIR','matplotlib'),('NUMBA_CACHE_DIR','numba'),('XDG_CACHE_HOME','xdg')]:
        path=cache/suffix;path.mkdir(parents=True,exist_ok=True);os.environ.setdefault(var,str(path))
    from .data import inspect_inputs
    from .artifacts import run_context, complete, write_json
    from .workflows import REQUIRED, prepare, run_experiment
    from .plotting import plot_experiment
    if args.command=='plot':
        if not args.run_dir or args.experiment=='all': p.error('plot needs --run-dir and a single --experiment')
        dest=args.run_dir.resolve()
        if not dest.is_relative_to(local_path(cfg,cfg['output_root'])): p.error('run-dir must be inside configured output_root')
        manifest=json.loads((dest/'manifest.json').read_text())
        if manifest['config']['system']!=cfg['system'] or manifest['experiment']!=args.experiment:
            p.error('Saved experiment/system does not match request')
        # Scientific settings from the original run; current visual preferences may change.
        plotting_cfg={**manifest['config'],'plot':cfg['plot'],'class_colors':cfg['class_colors']}
        plot_experiment(dest,args.experiment,plotting_cfg)
        print(dest);return
    rows=inspect_inputs(cfg,deep=args.deep)
    if args.command=='validate':
        print(json.dumps({'system':cfg['system'],'routes':len(cfg['routes']),'datasets':rows},indent=2));return
    routes=args.route or list(cfg['routes'])
    unknown=set(routes)-cfg['routes'].keys()
    if unknown: p.error(f'Unknown routes: {sorted(unknown)}')
    run_id,payload=run_context(cfg)
    if args.command=='summarize':
        summarize(cfg,run_id);return
    records=[]
    for route in routes:
        print(f'[{cfg["system"]}] {route}',flush=True)
        if args.command=='prepare':
            print(prepare(cfg,route,run_id,payload,args.force));continue
        experiments=list(REQUIRED) if args.experiment=='all' else [args.experiment]
        if args.experiment!='all':
            missing=REQUIRED[args.experiment]-cfg['routes'][route]['datasets'].keys()
            if missing: p.error(f'{route}: missing {sorted(missing)} for {args.experiment}')
        if args.force: prepare(cfg,route,run_id,payload,force=True)
        for experiment in experiments:
            missing=REQUIRED[experiment]-cfg['routes'][route]['datasets'].keys()
            if missing:
                records.append({'route':route,'experiment':experiment,'status':'skipped','missing':sorted(missing)})
                print(f'  {experiment}: skipped, missing {sorted(missing)}',flush=True);continue
            print(f'  {experiment}',flush=True)
            dest=run_experiment(cfg,route,experiment,run_id,payload,args.force,not args.no_plots)
            records.append({'route':route,'experiment':experiment,'status':'complete','path':str(dest.relative_to(cfg['_root']))})
    report=local_path(cfg,cfg['output_root'])/cfg['system']/'_runs'/run_id/'report.json'
    # Merge partial-route executions rather than discarding previous records.
    if report.exists():
        previous=json.loads(report.read_text())['experiments']
        selected={(r['route'],r['experiment']) for r in records}
        records=[r for r in previous if (r['route'],r['experiment']) not in selected]+records
    write_json(report,{**payload,'run_id':run_id,'experiments':records})
    print(f'Run manifest: {report}')


def summarize(cfg,run_id):
    import pandas as pd
    from .plotting import save
    import matplotlib.pyplot as plt
    root=local_path(cfg,cfg['output_root'])/cfg['system']
    out=root/'_comparison'/run_id;out.mkdir(parents=True,exist_ok=True)
    for experiment,filename in [('ood','summary.csv'),('multilabel','summary.csv'),('unseen','families.csv'),('structure','metrics.csv')]:
        frames=[]
        for route in cfg['routes']:
            p=root/route/experiment/run_id/filename
            if p.exists():
                frame=pd.read_csv(p);frame.insert(0,'route',route);frames.append(frame)
        if not frames: continue
        df=pd.concat(frames,ignore_index=True);df.to_csv(out/f'{experiment}.csv',index=False)
        fig,ax=plt.subplots(figsize=(9,4))
        if experiment=='structure':
            for route,g in df[df.metric=='knn_class_purity'].groupby('route'):
                ax.plot(g.k,g.value,marker='o',label=route)
            ax.set(xlabel='k',ylabel='Centroid class purity');ax.legend(fontsize=7)
        else:
            metric={'ood':'mean','multilabel':'mean','unseen':'silhouette_mean'}[experiment]
            group={'ood':'dataset_role','multilabel':'class_label','unseen':'class_label'}[experiment]
            df.pivot_table(index=group,columns='route',values=metric,aggfunc='mean').plot.bar(ax=ax)
            ax.set_ylabel(metric);ax.legend(fontsize=6)
        save(fig,out/experiment,cfg)
    print(out)


if __name__=='__main__':
    main()
