"""OOD cross-route sample selection."""
from ...sampling import choose_ids
from ...data import read_ids

def boundary_manifest(cfg):
    result = {}
    for role in ['ood', 'shuffled', 'idr']:
        sets = {route: set(read_ids(cfg, info['datasets'][role])) for (route, info) in cfg['routes'].items() if role in info['datasets']}
        if not sets:
            raise ValueError(f'No inputs for {role}')
        common = set.intersection(*sets.values())
        if len(common) < 2:
            raise ValueError(f'{role} has fewer than 2 common IDs across routes')
        ids = choose_ids(common, cfg['experiments']['boundary']['target_size'], cfg['seed'], role)
        result[role] = {'ids': ids, 'requested': cfg['experiments']['boundary']['target_size'], 'actual': len(ids), 'common_count': len(common), 'source_counts': {r: len(v) for (r, v) in sets.items()}}
    return result

