"""Parse archived percentage tables without recomputing prediction metrics."""
import re
import numpy as np
import pandas as pd

METHODS_BY_TASK = {
    'L0': ['esm2_1nn', 'l0_ft_1nn'],
    'L1': ['esm2_1nn', 'l1_ft_1nn'],
    'L2': ['esm2_1nn', 'l2_ft_1nn', 'l2_nca_from_esm2_1nn', 'l2_nca_from_l1_ft_1nn'],
}
OVERALL = ['Accuracy', 'Macro-P', 'Macro-R', 'Macro-F1', 'Weighted-F1']
CLASS = ['Precision', 'Recall / class accuracy', 'F1']


def read_report(path, cfg):
    text = path.read_text()
    title = text.splitlines()[0].lower()
    if cfg['system'] not in title:
        raise ValueError('Performance report system does not match config')
    task, section, header = None, 'overall', None
    rows, counts = [], {}
    for line_number, line in enumerate(text.splitlines(), 1):
        if line.startswith('## '):
            match = re.match(r'## (L[012])\b', line)
            task, section, header = match[1] if match else None, 'overall', None
        elif task and line.startswith('### '):
            if 'body' in line.lower():
                section = 'bins'
            elif '各类' in line:
                section = 'classes'
            else:
                raise ValueError(f'Unknown performance subsection: {line}')
            header = None
        elif task and '总样本' in line:
            match = re.search(r'总样本 ([\d,]+)，纳入指标 ([\d,]+)', line)
            if not match:
                raise ValueError(f'Malformed test sample counts at line {line_number}')
            total, included = (int(x.replace(',', '')) for x in match.groups())
            if not 0 < included <= total:
                raise ValueError('Invalid test sample counts')
            counts[task] = {'total_samples': total, 'included_samples': included}
        elif task and line.startswith('|'):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if header is None:
                header = cells
                if len(set(header)) != len(header):
                    raise ValueError('Duplicate report columns')
            elif all(set(c) <= {'-', ':'} for c in cells):
                continue
            else:
                if len(cells) != len(header):
                    raise ValueError(f'Wrong column count at line {line_number}')
                row = dict(zip(header, cells))
                metrics = CLASS if section == 'classes' else OVERALL + (['AUROC', 'AUPRC (AP)'] if task == 'L0' else [])
                info = {'overall': [], 'classes': ['Class', 'Support'], 'bins': ['Bin', 'Test families', 'Test samples']}[section]
                if set(header) != set(['方法'] + metrics + info):
                    raise ValueError(f'Unexpected report columns: {task}/{section}')
                method = row['方法']
                if method not in METHODS_BY_TASK[task] or method not in cfg['performance']['methods']:
                    raise ValueError(f'Unexpected performance method: {task}/{method}')
                record = {'task': task, 'section': section, 'method': method,
                          'route': cfg['performance']['methods'][method],
                          'label': row.get('Class', row.get('Bin', 'overall'))}
                for original, column in [('Support', 'support'), ('Test families', 'test_families'), ('Test samples', 'test_samples')]:
                    record[column] = int(row[original]) if original in row else np.nan
                    if original in row and record[column] < 0:
                        raise ValueError('Negative sample/family count')
                for metric in metrics:
                    raw = row[metric]
                    if raw == 'N/A':
                        if section != 'bins' or record['test_samples'] != 0:
                            raise ValueError('N/A is allowed only for bins with no test samples')
                        score = np.nan
                    else:
                        if not raw.endswith('%'):
                            raise ValueError(f'Expected percentage: {raw}')
                        score = float(raw[:-1])
                        if not np.isfinite(score) or not 0 <= score <= 100:
                            raise ValueError(f'Invalid percentage: {raw}')
                        if section == 'bins' and record['test_samples'] == 0:
                            raise ValueError('Empty bins must have N/A scores')
                    rows.append({**record, 'metric': metric, 'value': score})
    data = pd.DataFrame(rows)
    if data.empty or set(counts) != {'L0', 'L1', 'L2'}:
        raise ValueError('Incomplete performance report')
    identity = ['task', 'section', 'method', 'label', 'metric']
    if data.duplicated(identity).any():
        raise ValueError('Duplicate report metric')
    expected_sections = {('L0', 'overall'), ('L0', 'classes'), ('L1', 'overall'), ('L1', 'classes'), ('L2', 'overall'), ('L2', 'bins')}
    if set(zip(data.task, data.section)) != expected_sections:
        raise ValueError('Missing or unexpected report sections')
    for (task, section), group in data.groupby(['task', 'section'], sort=False):
        labels = set(group.label)
        if section == 'bins' and labels != {'head', 'body', 'tail'}:
            raise ValueError('Expected head/body/tail bins')
        if section == 'classes' and task == 'L1' and labels != set(cfg['classes']):
            raise ValueError('Report classes do not match config')
        if section == 'classes' and task == 'L0' and len(labels) != 2:
            raise ValueError('Expected two L0 classes')
        for label, subset in group.groupby('label', sort=False):
            if set(subset.method) != set(METHODS_BY_TASK[task]):
                raise ValueError(f'Missing methods: {task}/{section}/{label}')
            for column in ['support', 'test_families', 'test_samples']:
                if subset[column].dropna().nunique() > 1:
                    raise ValueError('Counts differ between methods')
        if section in ['classes', 'bins']:
            column = 'support' if section == 'classes' else 'test_samples'
            total = group.drop_duplicates('label')[column].sum()
            if total != counts[task]['included_samples']:
                raise ValueError(f'Test counts do not sum to included samples: {task}/{section}')
    for task, record in counts.items():
        for column, number in record.items():
            data.loc[data.task == task, column] = number
    return data


def plotting_tables(data):
    """Reconstitute the legacy row layout from the canonical numeric CSV."""
    tables = {}
    for (task, section, method, label), group in data.groupby(['task', 'section', 'method', 'label'], sort=False):
        row = {'方法': method, **dict(zip(group.metric, group.value))}
        first = group.iloc[0]
        if section == 'classes':
            row.update({'Class': label, 'Support': int(first.support)})
        elif section == 'bins':
            row.update({'Bin': label, 'Test families': int(first.test_families), 'Test samples': int(first.test_samples)})
        tables.setdefault((task, section), []).append(row)
    return tables
