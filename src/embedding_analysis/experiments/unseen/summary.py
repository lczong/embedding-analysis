"""Experiment-owned cross-route tables and comparison plots."""
import argparse
import json
from pathlib import Path
import pandas as pd
from ...runtime import Artifacts, parser_for
from ...config import local_path
from ...artifacts import ready, write_json


def main(argv=None):
    parser=parser_for('Cross-route summary', ['tables','plots'])
    parser.add_argument('--inputs', type=Path, nargs='+', help='Metric directories for tables')
    args=parser.parse_args(argv)
    job=Artifacts(parser,args,'unseen')
    if args.step=='tables':
        if not args.inputs: parser.error('tables requires --inputs')
        frames=[]; manifests=[]
        for path in args.inputs:
            source,meta=job.read(path,'unseen',['metrics'])
            frame=pd.read_csv(source/'families.csv')
            frame.insert(0,'route',meta['route']); frames.append(frame); manifests.append(meta)
        job.extra['metric_inputs']=manifests
        if job.cached(): return job.dest
        pd.concat(frames,ignore_index=True).to_csv(job.dest/'summary.csv',index=False)
    else:
        job.input('unseen',['tables'],plotting=True)
        if job.cached(): return job.dest
        from .plotting import plot_summary
        plot_summary(job.source,job.cfg,job.dest)
    return job.finish()
