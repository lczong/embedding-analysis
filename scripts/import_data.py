#!/usr/bin/env python3
"""One-time import only; runtime code never reads either legacy project."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[1]


def sample_digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        h.update(f.read(1024 * 1024))
        if path.stat().st_size > 1024 * 1024:
            f.seek(max(0, path.stat().st_size - 1024 * 1024))
            h.update(f.read())
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root', type=Path, required=True, help='Directory containing the two legacy projects')
    p.add_argument('--verify-full', action='store_true', help='Byte-compare every imported file (slow)')
    args = p.parse_args()
    records = []
    for system, legacy in [('cazy', 'normpca100'), ('peptidase', 'normpca100-peptidase')]:
        cfg = json.loads((PROJECT / 'configs' / f'{system}.json').read_text())
        paths = set(cfg['metadata']['files'].values())
        for route in cfg['routes'].values():
            for spec in route['datasets'].values():
                paths.update(spec.get('paths', [spec.get('path')]))
                if 'ids_reference' in spec:
                    paths.add(spec['ids_reference'])
        for rel in sorted(paths):
            source = args.source_root / legacy / Path(rel).relative_to(f'data/{system}')
            dest = PROJECT / rel
            if not source.is_file():
                raise FileNotFoundError(source)
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                if sys.platform == 'darwin':
                    subprocess.run(['/bin/cp', '-c', str(source), str(dest)], check=True)
                else:
                    shutil.copy2(source, dest)
            if dest.is_symlink() or (source.stat().st_dev, source.stat().st_ino) == (dest.stat().st_dev, dest.stat().st_ino):
                raise ValueError(f'Expected independent copy: {dest}')
            if source.stat().st_size != dest.stat().st_size or sample_digest(source) != sample_digest(dest):
                raise ValueError(f'Copy verification failed: {dest}')
            if args.verify_full:
                subprocess.run(['cmp', '-s', str(source), str(dest)], check=True)
            records.append({'path': rel, 'source': str(source.resolve()), 'bytes': dest.stat().st_size,
                            'sample_sha256': sample_digest(dest), 'full_byte_compare': args.verify_full})
        print(f'{system}: imported configured files', flush=True)
    (PROJECT / 'data/import_manifest.json').write_text(json.dumps(records, indent=2) + '\n')
    print(f'{len(records)} files; {sum(r["bytes"] for r in records) / 1024**3:.2f} GiB logical size')


if __name__ == '__main__':
    main()
