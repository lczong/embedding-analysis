"""Artifact validation and output bookkeeping. No experiment registry or execution."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from .config import load_config, local_path
from .artifacts import code_hash, complete, ready, run_context, write_json


def parser_for(description, steps):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('step', choices=steps)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--route')
    parser.add_argument('--input', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    return parser


class Artifacts:
    """An experiment explicitly requests validation, caching and completion."""
    def __init__(self, parser, args, owner):
        self.parser, self.args, self.owner = parser, args, owner
        self.cfg = load_config(args.config)
        self.route = args.route
        self.source = self.upstream = None
        self.extra = {}
        for var, name in [('MPLCONFIGDIR','matplotlib'), ('NUMBA_CACHE_DIR','numba'), ('XDG_CACHE_HOME','xdg')]:
            cache = local_path(self.cfg, '.cache/'+name); cache.mkdir(parents=True, exist_ok=True)
            os.environ.setdefault(var, str(cache))
        self.dest = local_path(self.cfg, str(args.output))
        root = local_path(self.cfg, self.cfg['output_root'])
        if self.dest == root or not self.dest.is_relative_to(root):
            parser.error('Output must be a dedicated subdirectory of output_root')

    def read(self, path, owner, stages):
        if path is None: self.parser.error('This step requires an explicit upstream directory')
        source = local_path(self.cfg, str(path))
        if source == self.dest or source.is_relative_to(self.dest) or self.dest.is_relative_to(source):
            self.parser.error('Input and output must be separate non-nested directories')
        if not ready(source): self.parser.error(f'Incomplete upstream artifacts: {source}')
        meta = json.loads((source/'manifest.json').read_text())
        if meta['config']['system'] != self.cfg['system']: self.parser.error('Input system mismatch')
        if meta['experiment'] != owner or meta.get('stage') not in stages:
            self.parser.error(f'Expected {owner} artifacts from steps {stages}')
        return source, meta

    def input(self, owner, stages, roles=(), plotting=False):
        self.source, self.upstream = self.read(self.args.input, owner, stages)
        route = self.upstream['route']
        if self.route and self.route != route: self.parser.error('Input route mismatch')
        self.route = route
        for role in roles:
            if not (self.source/f'{role}.npz').exists(): self.parser.error(f'PCA artifacts lack {role}')
        if plotting:
            self.cfg = {**self.upstream['config'], '_root': self.cfg['_root'],
                        'plot': self.cfg['plot'], 'class_colors': self.cfg['class_colors']}

    def raw_inputs(self):
        self.run_id, payload = run_context(self.cfg)
        self.extra['inputs'] = payload['inputs']

    def cached(self):
        public = {k:v for k,v in self.cfg.items() if not k.startswith('_')}
        self.payload = {'config': public, 'route': self.route, 'experiment': self.owner,
                        'stage': self.args.step, 'upstream': self.upstream,
                        'code_sha256': code_hash(), **self.extra}
        self.signature = hashlib.sha256(json.dumps(self.payload, sort_keys=True).encode()).hexdigest()
        if self.dest.exists() and any(self.dest.iterdir()):
            manifest = self.dest/'manifest.json'
            saved = json.loads(manifest.read_text()) if manifest.exists() else {}
            if saved.get('signature') == self.signature and ready(self.dest):
                print(f'Cached: {self.dest}'); return True
            self.parser.error(f'Output is occupied by different or incomplete artifacts: {self.dest}')
        self.dest.mkdir(parents=True, exist_ok=True)
        return False

    def finish(self):
        complete(self.dest, {**self.payload, 'signature': self.signature,
                            'source': str(self.source) if self.source else None})
        # All stage artifacts, including figures, participate in completion checks.
        meta = json.loads((self.dest/'manifest.json').read_text())
        meta['artifacts'] = {str(p.relative_to(self.dest)): p.stat().st_size
                             for p in self.dest.rglob('*') if p.is_file() and p.name != 'manifest.json'}
        write_json(self.dest/'manifest.json', meta)
        print(self.dest)
        return self.dest
