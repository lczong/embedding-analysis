"""Explicit artifact-in/artifact-out stages. Never launch dependencies implicitly."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from .config import load_config, local_path
from .artifacts import code_hash, complete, ready, run_context, write_json

STEPS = {
    'pca': ['prepare'],
    'ood': ['sample', 'metrics', 'tsne', 'umap', 'visualization', 'metric-plots'],
    'multilabel': ['metrics', 'tsne', 'umap', 'visualization', 'metric-plots'],
    'overview': ['tsne', 'umap', 'visualization'],
    'unseen': ['metrics', 'tsne', 'umap', 'visualization', 'metric-plots'],
    'structure': ['metrics', 'visualization', 'metric-plots'],
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def main(experiment, argv=None):
    parser = argparse.ArgumentParser(description=f'Independent {experiment} stages; no automatic upstream execution')
    parser.add_argument('step', choices=STEPS[experiment])
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--route', help='Required for PCA; otherwise inherited from input manifest')
    parser.add_argument('--input', type=Path, help='Completed upstream artifact directory')
    parser.add_argument('--output', type=Path, required=True, help='Dedicated output directory for this step')
    parser.add_argument('--sampling', type=Path, help='OOD sample artifact directory, required for metrics/tsne/umap')
    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    for var, name in [('MPLCONFIGDIR', 'matplotlib'), ('NUMBA_CACHE_DIR', 'numba'), ('XDG_CACHE_HOME', 'xdg')]:
        cache = local_path(cfg, '.cache/'+name); cache.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault(var, str(cache))
    # Output paths are relative to the project root, including when invoked elsewhere.
    dest = local_path(cfg, str(args.output))
    output_root = local_path(cfg, cfg['output_root'])
    if dest == output_root or not dest.is_relative_to(output_root):
        parser.error('--output must be a dedicated subdirectory of configured output_root')
    route = args.route
    source = None
    upstream = None
    sampling = None
    if args.step not in ['prepare', 'sample']:
        if args.input is None: parser.error('This step requires --input; run the upstream step explicitly')
        source = local_path(cfg, str(args.input))
        if source == dest or source.is_relative_to(dest) or dest.is_relative_to(source):
            parser.error('Input and output directories must be separate, non-nested directories')
        if not ready(source): parser.error(f'Incomplete or missing upstream artifacts: {source}')
        upstream = json.loads((source/'manifest.json').read_text())
        if upstream['config']['system'] != cfg['system']: parser.error('Input system mismatch')
        if route and route != upstream['route']: parser.error('Input route mismatch')
        route = upstream['route']
        expected = 'preprocess' if args.step in ['metrics', 'tsne', 'umap'] else experiment
        if upstream['experiment'] != expected: parser.error(f'Expected {expected} input artifacts')
        if args.step in ['visualization', 'metric-plots']:
            required_step = 'metrics' if args.step == 'metric-plots' or experiment == 'structure' else None
            actual = upstream.get('stage')
            if required_step and actual != required_step: parser.error('This plot requires metrics artifacts')
            if required_step is None and actual not in ['tsne', 'umap']: parser.error('Visualization requires tsne or umap artifacts')
            # Preserve scientific settings from the actual producer; allow current plot styling.
            cfg = {**upstream['config'], '_root': cfg['_root'], 'plot': cfg['plot'], 'class_colors': cfg['class_colors']}
    if args.step == 'prepare' and route not in cfg['routes']: parser.error('PCA requires a valid --route')
    if experiment == 'ood' and args.step in ['metrics', 'tsne', 'umap']:
        if args.sampling is None: parser.error('OOD requires --sampling from the explicit sample step')
        sample_path = local_path(cfg, str(args.sampling))
        if not ready(sample_path): parser.error('Incomplete sampling artifacts')
        sm = json.loads((sample_path/'manifest.json').read_text())
        if sm.get('stage') != 'sample' or sm['config']['system'] != cfg['system']: parser.error('Sampling system/stage mismatch')
        sampling = json.loads((sample_path/'sampling.json').read_text())
    public = {k:v for k,v in cfg.items() if not k.startswith('_')}
    signature = {'config': public, 'route': route, 'experiment': experiment, 'stage': args.step,
                 'upstream': upstream, 'sampling': sampling, 'code_sha256': code_hash()}
    if args.step in ['prepare', 'sample']:
        run_id, payload = run_context(cfg)
        signature['inputs'] = payload['inputs']
    else:
        run_id, payload = digest(signature)[:16], {'config': public}
    signature_hash = digest(signature)
    if dest.exists() and any(dest.iterdir()):
        manifest = dest/'manifest.json'
        saved = json.loads(manifest.read_text()) if manifest.exists() else {}
        if saved.get('signature') == signature_hash and ready(dest):
            print(f'Cached: {dest}'); return dest
        parser.error(f'Output already contains different or incomplete artifacts; choose a new --output: {dest}')
    dest.mkdir(parents=True, exist_ok=True)
    from .workflows import prepare, compute_metrics, compute_coordinates
    if args.step == 'prepare':
        prepare(cfg, route, payload, destination=dest)
    elif args.step == 'sample':
        from .sampling import ood_manifest
        write_json(dest/'sampling.json', ood_manifest(cfg, run_id))
    elif args.step in ['metrics', 'tsne', 'umap']:
        from .workflows import REQUIRED
        for role in REQUIRED[experiment]:
            if not (source/f'{role}.npz').exists(): parser.error(f'PCA artifacts lack {role}')
        if args.step == 'metrics':
            compute_metrics(cfg, experiment, source, dest, sampling=sampling)
        else:
            compute_coordinates(cfg, experiment, source, dest, args.step, sampling=sampling)
    else:
        from .plotting import plot_metrics, plot_visualization
        plot = plot_metrics if args.step == 'metric-plots' else plot_visualization
        plot(source, experiment, cfg, destination=dest)
    complete(dest, {**payload, 'config': public, 'route': route,
                    'experiment': 'preprocess' if args.step == 'prepare' else experiment,
                    'stage': args.step, 'signature': signature_hash,
                    'source': str(source) if source else None, 'upstream': upstream})
    # Unlike computation manifests, plot-only manifests must track their figures.
    if args.step in ['visualization', 'metric-plots']:
        manifest = json.loads((dest/'manifest.json').read_text())
        manifest['artifacts'] = {str(p.relative_to(dest)): p.stat().st_size for p in dest.rglob('*') if p.is_file() and p.name != 'manifest.json'}
        write_json(dest/'manifest.json', manifest)
    print(dest)
    return dest
