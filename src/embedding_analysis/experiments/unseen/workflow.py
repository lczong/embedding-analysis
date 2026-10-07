"""unseen owns its CLI, dependencies and step execution."""
from ...runtime import Artifacts, parser_for


def main(argv=None):
    parser = parser_for('unseen independent workflow', ['metrics', 'tsne', 'umap', 'visualization', 'metric-plots'])
    args = parser.parse_args(argv)
    job = Artifacts(parser, args, 'unseen')
    if args.step in ['metrics', 'tsne', 'umap']:
        job.input('preprocess', ['prepare'], roles=['train', 'unseen'])
    elif args.step == 'visualization':
        job.input('unseen', ['tsne', 'umap'], plotting=True)
    elif args.step == 'metric-plots':
        job.input('unseen', ['metrics'], plotting=True)
    if job.cached(): return job.dest
    if args.step == 'metrics':
        from .compute import compute_metrics
        compute_metrics(job.cfg, job.source, job.dest)
    elif args.step in ['tsne', 'umap']:
        from .compute import compute_coordinates
        compute_coordinates(job.cfg, job.source, job.dest, args.step)
    elif args.step == 'visualization':
        from .plotting import plot_visualization
        plot_visualization(job.source, job.cfg, job.dest)
    elif args.step == 'metric-plots':
        from .plotting import plot_metrics
        plot_metrics(job.source, job.cfg, job.dest)
    return job.finish()
