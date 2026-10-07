"""overview owns its CLI, dependencies and step execution."""
from ...runtime import Artifacts, parser_for


def main(argv=None):
    parser = parser_for('overview independent workflow', ['tsne', 'umap', 'visualization'])
    args = parser.parse_args(argv)
    job = Artifacts(parser, args, 'overview')
    if args.step in ['tsne', 'umap']:
        job.input('preprocess', ['prepare'], roles=['train'])
    elif args.step == 'visualization':
        job.input('overview', ['tsne', 'umap'], plotting=True)
    if job.cached(): return job.dest
    if args.step in ['tsne', 'umap']:
        from .compute import compute_coordinates
        compute_coordinates(job.cfg, job.source, job.dest, args.step)
    elif args.step == 'visualization':
        from .plotting import plot_visualization
        plot_visualization(job.source, job.cfg, job.dest)
    return job.finish()
