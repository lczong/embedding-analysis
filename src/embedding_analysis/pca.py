"""Shared PCA entrypoint, independent of downstream experiments."""
from .runtime import Artifacts, parser_for
from .prepared import prepare


def main(argv=None):
    parser = parser_for('Fit train PCA and transform configured datasets', ['prepare'])
    args = parser.parse_args(argv)
    job = Artifacts(parser, args, 'preprocess')
    if args.route not in job.cfg['routes']: parser.error('PCA requires a valid --route')
    job.raw_inputs()
    if job.cached(): return job.dest
    prepare(job.cfg, job.route, job.payload, job.dest)
    return job.finish()
