"""Import physical NAE result snapshots and render their paper components."""
import argparse
import json
from pathlib import Path
import shutil

from ...artifacts import file_digest
from ...runtime import Artifacts
from .data import FILES, load_tables

ROOT = Path(__file__).resolve().parents[4]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['import', 'check', 'render'])
    parser.add_argument('--system', required=True, choices=['cazy', 'peptidase'])
    parser.add_argument('--source', type=Path, help='Standalone package directory, required only for import')
    args = parser.parse_args(argv)
    try:
        if args.command == 'import':
            if args.source is None:
                parser.error('import requires --source')
            source = args.source.resolve()
            load_tables(source/'inputs')
            inputs = [(source/'inputs'/name, Path(name)) for name in FILES]
            inputs += [(source/'panel_mapping.json', Path('panel_mapping.json'))]
            inputs += [(source/name, Path('source_code')/name) for name in ['plotting.py', 'render_panels.py', 'README.md', 'requirements.txt']]
            cli = argparse.Namespace(config=ROOT/f'configs/{args.system}.json', step='tables',
                                     route=None, input=None, method='tsne', version=None)
            job = Artifacts(parser, cli, 'nae')
            # No output component may be a symlink. Import reads source and writes real copies.
            for path in [job.checkpoint, *job.checkpoint.parents]:
                if path.is_symlink():
                    raise ValueError(f'NAE output must not be a symlink: {path}')
            job.extra['imported_inputs'] = [{'file': str(target), 'sha256': file_digest(path),
                                            'source': str(path), 'bytes': path.stat().st_size}
                                           for path, target in inputs]
            if job.cached():
                return
            for path, target in inputs:
                dest = job.dest/target
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, dest)
                if dest.is_symlink() or dest.stat().st_ino == path.stat().st_ino and dest.stat().st_dev == path.stat().st_dev:
                    raise ValueError('Expected independent physical input copy')
                if file_digest(dest) != file_digest(path):
                    raise ValueError('Imported file checksum mismatch')
            load_tables(job.dest)
            job.finish()
            return
        if args.source:
            parser.error('--source is used only during import')
        from ...publication.render import main as paper_main
        for path in sorted((ROOT/'paper/figures').glob('*.json')):
            config = json.loads(path.read_text())
            panels = [name for name, spec in config['panels'].items()
                      if spec['kind'].startswith('nae_') and spec['source']['system'] == args.system]
            if panels:
                paper_main([args.command, str(path), '--panel', *panels])
    except (ValueError, KeyError, OSError) as exc:
        parser.error(str(exc))
