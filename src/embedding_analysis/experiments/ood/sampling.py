"""OOD cross-route sample selection."""
import json
from ...sampling import choose_ids
from ...data import read_ids
from ...config import local_path
from ...artifacts import write_json

def ood_manifest(cfg, run_id):
    path = local_path(cfg, cfg['output_root']) / cfg['system'] / '_sampling' / run_id / 'ood.json'
    if path.exists():
        return json.loads(path.read_text())
    result = {}
    for role in ['ood', 'shuffled', 'idr']:
        sets = {route: set(read_ids(cfg, info['datasets'][role])) for (route, info) in cfg['routes'].items() if role in info['datasets']}
        if not sets:
            raise ValueError(f'No inputs for {role}')
        common = set.intersection(*sets.values())
        if len(common) < 2:
            raise ValueError(f'{role} has fewer than 2 common IDs across routes')
        ids = choose_ids(common, cfg['experiments']['ood']['target_size'], cfg['seed'], role)
        result[role] = {'ids': ids, 'requested': cfg['experiments']['ood']['target_size'], 'actual': len(ids), 'common_count': len(common), 'source_counts': {r: len(v) for (r, v) in sets.items()}}
    write_json(path, result)
    return result

