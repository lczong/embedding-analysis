"""Content-aware run directories; metadata is written only after success."""
from pathlib import Path
import hashlib
import json
import numpy as np
from .config import local_path, spec_files


def write_json(path, obj):
    def default(x):
        if isinstance(x, np.generic): return x.item()
        if isinstance(x, Path): return str(x)
        raise TypeError(type(x).__name__)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=default) + '\n')
    tmp.replace(path)


def code_hash():
    h = hashlib.sha256()
    for p in sorted(Path(__file__).parent.rglob('*.py')):
        h.update(str(p.relative_to(Path(__file__).parent)).encode()); h.update(p.read_bytes())
    return h.hexdigest()


def input_fingerprints(cfg):
    paths = set(cfg['metadata']['files'].values())
    for route in cfg['routes'].values():
        for spec in route['datasets'].values():
            paths.update(str(p.relative_to(Path(cfg['_root']))) for p in spec_files(cfg, spec))
            if 'ids_reference' in spec: paths.add(spec['ids_reference'])
    result = []
    for relative in sorted(paths):
        p = local_path(cfg, relative); st = p.stat()
        # Include edge content to catch common replacements; full-file hashing is not implied.
        h = hashlib.sha256()
        with p.open('rb') as f:
            h.update(f.read(4096))
            if st.st_size > 4096:
                f.seek(max(0, st.st_size-4096)); h.update(f.read())
        result.append({'path': relative, 'size': st.st_size, 'mtime_ns': st.st_mtime_ns, 'edge_sha256': h.hexdigest()})
    return result


def run_context(cfg):
    public = {k:v for k,v in cfg.items() if not k.startswith('_')}
    payload = {'config': public, 'inputs': input_fingerprints(cfg), 'code_sha256': code_hash()}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
    return digest, payload


def complete(path, payload):
    files = {str(p.relative_to(path)):p.stat().st_size for p in path.rglob('*') if p.is_file() and p.name != 'manifest.json' and 'figures' not in p.relative_to(path).parts}
    write_json(path/'manifest.json', {**payload, 'artifacts': files})


def artifact_file(path, logical):
    """Resolve a logical result name through its step manifest."""
    path=Path(path)
    manifest=path/'manifest.json'
    if not manifest.exists():return path/logical
    data=json.loads(manifest.read_text())
    target=(path/data.get('locations',{}).get(str(logical),str(logical))).resolve()
    system=data['config']['system']
    # Locate the enclosing system directory; paths may reach tables/figures, never another system.
    roots=[p for p in [path.resolve(),*path.resolve().parents] if p.name==system]
    if not roots or not target.is_relative_to(roots[0]):
        raise ValueError(f'Artifact leaves system output: {target}')
    return target


def ready(path):
    path=Path(path);manifest=path/'manifest.json'
    if not manifest.exists():return False
    data=json.loads(manifest.read_text())
    return all(artifact_file(path,p).is_file() and artifact_file(path,p).stat().st_size==size for p,size in data['artifacts'].items())
