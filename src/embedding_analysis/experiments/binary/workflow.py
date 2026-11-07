"""Independent binary overview steps."""
from ...runtime import Artifacts, parser_for

def main(argv=None):
    parser=parser_for('Binary train overview', ['pca','tsne','umap','visualization'])
    args=parser.parse_args(argv)
    job=Artifacts(parser,args,'binary')
    if args.step=='pca':
        if args.route not in job.cfg['routes']:parser.error('pca requires a configured --route')
        if 'non_target_train' not in job.cfg['routes'][args.route]['datasets']:parser.error('Route has no non_target_train embedding')
        job.raw_inputs()
        job.extra['fit_on']=['train','non_target_train']
    elif args.step in ['tsne','umap']:job.input('binary',['pca'])
    else:job.input('binary',['tsne','umap'],plotting=True)
    if job.cached():return job.dest
    if args.step=='pca':
        from .compute import prepare
        prepare(job.cfg,job.route,job.dest)
    elif args.step in ['tsne','umap']:
        from .compute import compute_coordinates
        compute_coordinates(job.cfg,job.source,job.dest,args.step)
    else:
        from .plotting import plot_visualization
        plot_visualization(job.source,job.cfg,job.dest)
    return job.finish()
