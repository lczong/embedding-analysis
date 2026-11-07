"""Artifact validation and output bookkeeping. Experiments own execution and exports."""
import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path
from .config import load_config, local_path
from .artifacts import code_hash, ready, run_context, write_json, artifact_file
from .output import system_root, stage_path, publish_target, indexes


def parser_for(description, steps):
    parser=argparse.ArgumentParser(description=description)
    parser.add_argument('step',choices=steps)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--route')
    parser.add_argument('--input',type=Path,help='Optional explicit upstream artifact directory')
    parser.add_argument('--method',choices=['tsne','umap'],default='tsne',help='Coordinate source for visualization')
    parser.add_argument('--version',help='Optional named output version within this system')
    return parser


class Artifacts:
    """One step owns a checkpoint and an explicit set of published files."""
    def __init__(self,parser,args,owner,table_patterns=(),table_names=None,figure_names=None):
        self.parser,self.args,self.owner=parser,args,owner
        self.cfg=load_config(args.config);self.route=args.route
        if args.version and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*',args.version):parser.error('Invalid version name')
        if self.route and self.route not in self.cfg['routes']:parser.error('Unknown route')
        self.root=system_root(self.cfg,args.version)
        self.source=self.upstream=None;self.extra={}
        self.table_patterns=table_patterns;self.table_names=table_names or {};self.figure_names=figure_names or {}
        self.method=args.method
        if args.input:
            initial=local_path(self.cfg,str(args.input))
            if not initial.is_relative_to(self.root):parser.error('Input must belong to the same system and output version')
            if (initial/'manifest.json').exists():
                meta=json.loads((initial/'manifest.json').read_text())
                self.route=self.route or meta.get('route')
                if args.step=='visualization':self.method=meta['stage']
        if not self.route and args.step not in ['sample','tables','plots']:parser.error('This step requires --route or --input with a route manifest')
        self.checkpoint=self.path(owner,self.route,args.step)
        self.dest=self.checkpoint
        self.old={};self.lock=None
        for var,name in [('MPLCONFIGDIR','matplotlib'),('NUMBA_CACHE_DIR','numba'),('XDG_CACHE_HOME','xdg')]:
            cache=local_path(self.cfg,'.cache/'+name);cache.mkdir(parents=True,exist_ok=True);os.environ.setdefault(var,str(cache))

    def path(self,owner,route,stage):
        return stage_path(self.root,owner,route,stage,self.method)

    def read(self,path,owner,stages):
        if path is None:
            stage=self.method if self.method in stages else stages[0]
            route=None if stage in ['sample','tables','plots'] else self.route
            source=self.path(owner,route,stage)
        else:source=local_path(self.cfg,str(path))
        if not source.is_relative_to(self.root):self.parser.error('Input must belong to the same system and output version')
        if source==self.checkpoint or source.is_relative_to(self.checkpoint) or self.checkpoint.is_relative_to(source):self.parser.error('Input and output must be separate non-nested directories')
        if not ready(source):self.parser.error(f'Incomplete upstream artifacts: {source}')
        meta=json.loads((source/'manifest.json').read_text())
        if meta['config']['system']!=self.cfg['system']:self.parser.error('Input system mismatch')
        if meta['experiment']!=owner or meta.get('stage') not in stages:self.parser.error(f'Expected {owner} artifacts from steps {stages}')
        return source,meta

    def input(self,owner,stages,roles=(),plotting=False):
        self.source,self.upstream=self.read(self.args.input,owner,stages)
        route=self.upstream['route']
        if self.route and self.route!=route:self.parser.error('Input route mismatch')
        self.route=route
        for role in roles:
            if not (self.source/f'{role}.npz').exists():self.parser.error(f'PCA artifacts lack {role}')
        if plotting:self.cfg={**self.upstream['config'],'_root':self.cfg['_root'],'plot':self.cfg['plot'],'class_colors':self.cfg['class_colors']}

    def raw_inputs(self):
        self.run_id,payload=run_context(self.cfg);self.extra['inputs']=payload['inputs']

    def release(self):
        if self.lock:fcntl.flock(self.lock,fcntl.LOCK_UN);self.lock.close();self.lock=None

    def cached(self):
        public={k:v for k,v in self.cfg.items() if not k.startswith('_')}
        self.payload={'config':public,'route':self.route,'experiment':self.owner,'stage':self.args.step,'upstream':self.upstream,'code_sha256':code_hash(),**self.extra}
        self.signature=hashlib.sha256(json.dumps(self.payload,sort_keys=True).encode()).hexdigest()
        self.checkpoint.parent.mkdir(parents=True,exist_ok=True)
        self.lock=(self.checkpoint.parent/('.'+self.checkpoint.name+'.lock')).open('a')
        try:fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:self.parser.error('This step is already running')
        manifest=self.checkpoint/'manifest.json'
        self.old=json.loads(manifest.read_text()) if manifest.exists() else {}
        if self.old.get('signature')==self.signature and ready(self.checkpoint):
            self.report('Cached');self.release();return True
        # Compute in a private workspace; retain the last complete result until success.
        self.dest=self.checkpoint.parent/('.'+self.checkpoint.name+'.work')
        if self.dest.exists():shutil.rmtree(self.dest)
        self.dest.mkdir()
        (self.dest/'run.log').write_text('Command: '+repr(sys.argv)+'\nSignature: '+self.signature+'\n')
        return False

    def report(self,status):
        print(f'{status}: {self.checkpoint}')
        for kind in ['figures','tables']:
            path=self.root/self.owner/kind/(self.route or 'summary')
            if path.exists():print(f'{kind}: {path.as_uri()}')
        if (self.root/self.owner/'figures/index.html').exists():print('Preview: '+(self.root/self.owner/'figures/index.html').as_uri())

    def finish(self):
        # prepare() may write a provisional manifest; only this final record is published.
        (self.dest/'manifest.json').unlink(missing_ok=True)
        with (self.dest/'run.log').open('a') as log:log.write('Completed successfully\n')
        files={};locations={};targets=set()
        for p in sorted(self.dest.rglob('*')):
            if not p.is_file():continue
            logical=p.relative_to(self.dest);size=p.stat().st_size
            target=publish_target(self.root,self.owner,self.route,self.args.step,logical,self.upstream.get('stage') if self.upstream else None,self.table_patterns,self.table_names,self.figure_names)
            if target:
                target.parent.mkdir(parents=True,exist_ok=True);os.replace(p,target)
            else:target=self.checkpoint/logical
            targets.add(target.resolve());files[str(logical)]=size
            locations[str(logical)]=os.path.relpath(target,self.checkpoint)
        for logical in self.old.get('artifacts',{}):
            old=artifact_file(self.checkpoint,logical)
            if old not in targets and not old.is_relative_to(self.checkpoint):old.unlink(missing_ok=True)
        if self.checkpoint.exists():shutil.rmtree(self.checkpoint)
        os.replace(self.dest,self.checkpoint);self.dest=self.checkpoint
        write_json(self.checkpoint/'manifest.json',{**self.payload,'signature':self.signature,'source':str(self.source) if self.source else None,'artifacts':files,'locations':locations})
        indexes(self.root);self.report('Completed');self.release()
        return self.checkpoint
