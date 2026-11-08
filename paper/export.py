#!/usr/bin/env python3
"""Bundle publication code and only the input artifacts referenced by figure configs."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8*1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--data-only', action='store_true',
                        help='Export only ignored inputs/reference PNGs, for extraction into a Git clone')
    args = parser.parse_args()
    files = {}

    def add(path, target=None):
        path = path.resolve()
        if not path.is_relative_to(ROOT):
            raise ValueError(f'Input leaves project: {path}')
        if not path.is_file():
            raise FileNotFoundError(path)
        files[target or path.relative_to(ROOT).as_posix()] = path

    if not args.data_only:
        for folder in ('src', 'paper'):
            for path in (ROOT/folder).rglob('*'):
                if path.suffix in ('.py', '.json', '.md', '.txt') and '__pycache__' not in path.parts:
                    add(path)
        add(ROOT/'paper/HANDOFF.md', 'START_HERE.md')
    checkpoints = set()
    figures = []
    for config_path in sorted((ROOT/'paper/figures').glob('*.json')):
        config = json.loads(config_path.read_text())
        figures.append(config['figure'])
        for panel in config['panels'].values():
            source = panel['source']
            checkpoint = ROOT/'outputs'/source['system']
            if source.get('version'):
                checkpoint = checkpoint/'_versions'/source['version']
            checkpoint = checkpoint/source['workflow']/'artifacts'/source['route']/source['stage']
            checkpoints.add(checkpoint)
        for path in (ROOT/'outputs/paper'/config['figure']).glob('*.png'):
            prefix = 'outputs/paper-reference' if args.data_only else 'reference'
            add(path, f'{prefix}/{config["figure"]}/{path.name}')
    for checkpoint in sorted(checkpoints):
        manifest_path = checkpoint/'manifest.json'
        add(manifest_path)
        manifest = json.loads(manifest_path.read_text())
        for logical, size in manifest['artifacts'].items():
            path = (checkpoint/manifest.get('locations', {}).get(logical, logical)).resolve()
            add(path)
            if path.stat().st_size != size:
                raise ValueError(f'Input size changed: {path}')
            expected = manifest.get('sha256', {}).get(logical)
            if expected and digest(path) != expected:
                raise ValueError(f'Input digest changed: {path}')
    manifest = {'mode': 'data-only' if args.data_only else 'standalone',
                'figures': figures, 'checkpoints': len(checkpoints),
                'base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                'working_tree': subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True),
                'files': {name: {'bytes': path.stat().st_size, 'sha256': digest(path)}
                          for name, path in sorted(files.items())}}
    filename = 'paper-inputs.zip' if args.data_only else 'paper-handoff.zip'
    output = (args.output or ROOT/'outputs/handoff'/filename).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix('.zip.tmp')
    try:
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            prefix = '' if args.data_only else 'paper-handoff/'
            for name, path in sorted(files.items()):
                archive.write(path, prefix+name)
            manifest_name = 'outputs/handoff/INPUTS_MANIFEST.json' if args.data_only else prefix+'HANDOFF_MANIFEST.json'
            archive.writestr(manifest_name, json.dumps(manifest, indent=2, ensure_ascii=False)+'\n')
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    print(f'{output}\n{len(files)} files, {len(checkpoints)} input checkpoints, {output.stat().st_size/2**20:.1f} MiB')


if __name__ == '__main__':
    main()
