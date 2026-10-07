"""structure owns its CLI, dependencies and step execution."""
from ...runtime import Artifacts, parser_for


def main(argv=None):
    parser = parser_for('structure independent workflow', ['metrics', 'visualization', 'metric-plots'])
    args = parser.parse_args(argv)
    job = Artifacts(parser, args, 'structure')
    if args.step in ['metrics']:
        job.input('preprocess', ['prepare'], roles=['train'])
    elif args.step == 'visualization':
        job.input('structure', ['metrics'], plotting=True)
    elif args.step == 'metric-plots':
        job.input('structure', ['metrics'], plotting=True)
    if job.cached(): return job.dest
    if args.step == 'metrics':
        from .compute import compute_metrics
        compute_metrics(job.cfg, job.source, job.dest)
    elif args.step == 'visualization':
        from .plotting import plot_visualization
        plot_visualization(job.source, job.cfg, job.dest)
    elif args.step == 'metric-plots':
        from .plotting import plot_metrics
        plot_metrics(job.source, job.cfg, job.dest)
    return job.finish()
