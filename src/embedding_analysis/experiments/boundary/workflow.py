"""boundary owns its CLI, dependencies and step execution."""
from ...runtime import Artifacts, parser_for


def main(argv=None):
    parser = parser_for('boundary independent workflow', ['sample', 'metrics', 'tsne', 'umap', 'visualization', 'metric-plots'])
    from pathlib import Path
    parser.add_argument('--sampling', type=Path)
    args = parser.parse_args(argv)
    job = Artifacts(parser, args, 'boundary')
    if args.step == 'sample':
        from .sampling import boundary_manifest
        from ...artifacts import write_json
        job.raw_inputs()
        if job.cached(): return job.dest
        write_json(job.dest/'sampling.json', boundary_manifest(job.cfg, job.run_id))
        return job.finish()
    if args.step in ['metrics', 'tsne', 'umap']:
        job.input('preprocess', ['prepare'], roles=['train', 'ood', 'shuffled', 'idr'])
        import json
        sample_path, sample_meta = job.read(args.sampling, 'boundary', ['sample'])
        sampling = json.loads((sample_path/'sampling.json').read_text())
        job.extra['sampling'] = sampling
    elif args.step == 'visualization':
        job.input('boundary', ['tsne', 'umap'], plotting=True)
    elif args.step == 'metric-plots':
        job.input('boundary', ['metrics'], plotting=True)
    if job.cached(): return job.dest
    if args.step == 'metrics':
        from .compute import compute_metrics
        compute_metrics(job.cfg, job.source, job.dest, sampling)
    elif args.step in ['tsne', 'umap']:
        from .compute import compute_coordinates
        compute_coordinates(job.cfg, job.source, job.dest, args.step, sampling)
    elif args.step == 'visualization':
        from .plotting import plot_visualization
        plot_visualization(job.source, job.cfg, job.dest)
    elif args.step == 'metric-plots':
        from .plotting import plot_metrics
        plot_metrics(job.source, job.cfg, job.dest)
    return job.finish()
