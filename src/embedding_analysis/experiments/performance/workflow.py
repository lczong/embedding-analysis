"""Independent tables/plots workflow for archived test-set performance."""
from pathlib import Path
import pandas as pd

from ...artifacts import artifact_file, file_digest
from ...config import local_path
from ...runtime import Artifacts, parser_for
from .tables import read_report, plotting_tables


def main(argv=None):
    parser = parser_for(__doc__, ['tables', 'plots'])
    parser.add_argument('--plots', nargs='+', help='Selected figure names (default: all eight)')
    args = parser.parse_args(argv)
    if args.route:
        parser.error('Performance reads one cross-route report; do not pass --route')
    if args.step == 'tables' and (args.plots or args.input):
        parser.error('tables reads the configured report, without --plots/--input')
    job = Artifacts(parser, args, 'performance', table_patterns=['metrics.csv'])
    try:
        settings = job.cfg['performance']
        if settings['base_model'] != 'esm2':
            raise ValueError('The imported performance report and method palette describe ESM2 only')
        if args.step == 'tables':
            report = local_path(job.cfg, settings['report'])
            source_record = local_path(job.cfg, settings['source_manifest'])
            job.extra['inputs'] = [{'path': str(p.relative_to(Path(job.cfg['_root']))),
                                    'bytes': p.stat().st_size, 'sha256': file_digest(p)}
                                   for p in (report, source_record)]
            data = read_report(report, job.cfg)
            if job.cached():
                return job.dest
            data.to_csv(job.dest/'metrics.csv', index=False)
            return job.finish()
        from .plotting import PLOTS, render
        names = args.plots or list(PLOTS)
        if len(set(names)) != len(names) or set(names) - set(PLOTS):
            parser.error(f'Select distinct plot names from: {", ".join(PLOTS)}')
        options = job.cfg['plot']['performance']
        if not options['formats'] or set(options['formats']) - {'png', 'pdf', 'svg'}:
            parser.error('Performance formats must be png, pdf and/or svg')
        # Each figure has a checkpoint so selection never deletes other figures.
        destinations = []
        for name in names:
            current = Artifacts(parser, args, 'performance')
            current.checkpoint = current.path('performance', None, 'plots') / name
            current.dest = current.checkpoint
            current.input('performance', ['tables'], plotting=True)
            current.extra['selected_plot'] = name
            current.extra['plot_options'] = options
            if current.cached():
                destinations.append(current.dest)
                continue
            data = pd.read_csv(artifact_file(current.source, 'metrics.csv'))
            render(plotting_tables(data), name, current.dest, options)
            destinations.append(current.finish())
        return destinations
    except (KeyError, ValueError, OSError) as exc:
        parser.error(str(exc))
