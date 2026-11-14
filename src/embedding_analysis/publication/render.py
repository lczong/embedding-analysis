"""Publication CLI with validated sources and per-panel provenance."""
import argparse
import html
import json
import os
from pathlib import Path
import re
import tempfile

from ..artifacts import artifact_file, file_digest, ready, write_json
from ..config import merge

ROOT = Path(__file__).resolve().parents[3]
KINDS = {'binary': 'binary', 'overview_classes': 'overview', 'overview_families': 'overview',
         'boundary_balanced': 'boundary', 'multilabel_combos': 'multilabel',
         'boundary_silhouette': 'boundary', 'multilabel_ba': 'multilabel',
         'centroid_purity': 'centroid', 'performance': 'performance',
         'nae_survival': 'nae', 'nae_matrix': 'nae'}
TABLE_KINDS = {'boundary_silhouette', 'multilabel_ba', 'centroid_purity', 'performance', 'nae_survival', 'nae_matrix'}


def safe_name(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', value):
        raise ValueError(f'Invalid name: {value!r}')
    return value


def resolve_source(spec, root=ROOT):
    kind = spec['kind']
    if kind not in KINDS:
        raise ValueError(f'Unsupported panel kind: {kind}')
    source = spec['source']
    table = kind in TABLE_KINDS
    if source['workflow'] != KINDS[kind] or source['stage'] not in (('tables',) if table else ('tsne', 'umap')):
        raise ValueError('Panel kind and source workflow/stage do not match')
    if table and source['route'] != 'summary':
        raise ValueError('Table panels must use route=summary')
    path = root / 'outputs' / safe_name(source['system'])
    if source.get('version'):
        path = path / '_versions' / safe_name(source['version'])
    path = path / safe_name(source['workflow']) / 'artifacts' / safe_name(source['route']) / source['stage']
    if not (path / 'manifest.json').is_file():
        raise ValueError(f'Missing source: {path}. Run the corresponding workflow {source["stage"]} step first.')
    meta = json.loads((path / 'manifest.json').read_text())
    actual = (meta['config']['system'], meta['experiment'], meta['route'], meta['stage'])
    expected = (source['system'], source['workflow'], None if table else source['route'], source['stage'])
    if actual != expected:
        raise ValueError(f'Source identity mismatch: {path}')
    if kind.startswith('nae_'):
        from ..experiments.nae.data import FILES, load_tables, select
        if not set(FILES) <= set(meta['artifacts']) or not ready(path):
            raise ValueError(f'Incomplete or changed NAE source: {path}')
        for name in FILES:
            file = path/name
            if file.is_symlink() or any(p.is_symlink() for p in file.parents):
                raise ValueError(f'NAE inputs must be physical files: {file}')
        data = load_tables(path)
        select(data, source['system'], spec['selection'])
        return data, meta['config'], {
            'checkpoint': str(path.relative_to(root)),
            'manifest_sha256': file_digest(path/'manifest.json'),
            'inputs_sha256': {name: file_digest(path/name) for name in FILES},
            'rows': {name: len(frame) for name, frame in data.items()}}
    logical = ('metrics.csv' if kind == 'performance' else 'summary.csv'
               if kind == 'centroid_purity' else 'samples.csv' if table else 'coordinates.csv')
    if logical not in meta['artifacts'] or not ready(path):
        raise ValueError(f'Incomplete or changed source artifacts: {path}')
    coordinates = artifact_file(path, logical)
    digest = file_digest(coordinates)
    if source.get('coordinates_sha256') and source['coordinates_sha256'] != digest:
        raise ValueError(f'Locked coordinates changed: {path}')
    if source.get('samples_sha256') and source['samples_sha256'] != digest:
        raise ValueError(f'Locked samples changed: {path}')
    import numpy as np
    import pandas as pd
    data = pd.read_csv(coordinates, dtype={'sequence_id': str})
    if kind == 'performance':
        from .figures import selected_performance
        selected_performance(data, spec['selection'])
        if source.get('metrics_sha256') and source['metrics_sha256'] != digest:
            raise ValueError(f'Locked performance metrics changed: {path}')
        return data, meta['config'], {
            'checkpoint': str(path.relative_to(root)),
            'manifest_sha256': file_digest(path / 'manifest.json'),
            'signature': meta.get('signature'), 'metrics_sha256': digest, 'rows': len(data)}
    if kind == 'centroid_purity':
        from .figures import selected_purity
        selected_purity(data, spec['selection'])
        if source.get('summary_sha256') and source['summary_sha256'] != digest:
            raise ValueError(f'Locked summary changed: {path}')
        return data, meta['config'], {
            'checkpoint': str(path.relative_to(root)),
            'manifest_sha256': file_digest(path / 'manifest.json'),
            'signature': meta.get('signature'), 'summary_sha256': digest, 'rows': len(data)}
    required = {'sequence_id', 'dataset_role', 'x', 'y'}
    if kind.startswith('overview') or kind == 'multilabel_combos':
        required |= {'class_label', 'family_label'}
    if table:
        required = {'route', 'sequence_id'} | ({'dataset_role', 'silhouette'}
                    if kind == 'boundary_silhouette' else {'class_label', 'ba_score'})
    if not required <= set(data.columns) or data.empty:
        raise ValueError(f'Missing columns or empty coordinates: {coordinates}')
    nonnull = required - ({'ba_score'} if kind == 'multilabel_ba' else set())
    identity = ['route', 'sequence_id'] if table else ['sequence_id']
    if data[list(nonnull)].isna().any().any() or data.duplicated(identity).any():
        raise ValueError(f'Missing values or duplicate IDs: {coordinates}')
    numeric = ['silhouette'] if kind == 'boundary_silhouette' else ['x', 'y']
    if kind != 'multilabel_ba' and not np.isfinite(data[numeric].to_numpy()).all():
        raise ValueError(f'Nonfinite coordinates: {coordinates}')
    if not table:
        roles = set(data.dataset_role)
        expected_roles = {'binary': {'train', 'non_target_train'},
                          'boundary_balanced': {'train', 'ood', 'shuffled', 'idr'},
                          'multilabel_combos': {'train', 'multi'}}.get(kind, {'train'})
        if roles != expected_roles:
            raise ValueError(f'Unexpected source roles: {roles}')
    else:
        from .figures import selected_samples
        selected_samples(data, spec['selection'], 'silhouette' if kind == 'boundary_silhouette' else 'ba_score')
    record = {'checkpoint': str(path.relative_to(root)),
              'manifest_sha256': file_digest(path / 'manifest.json'),
              'signature': meta.get('signature'), ('samples_sha256' if table else 'coordinates_sha256'): digest,
              'rows': len(data)}
    return data, meta['config'], record


def render_panel(destination, panel_id, spec, style, data, cfg, provenance, config_digest):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from ..legend import top_legend
    from .figures import build_figure

    destination.mkdir(parents=True, exist_ok=True)
    # Only publish this panel after all its formats have rendered successfully.
    with tempfile.TemporaryDirectory(prefix=f'.{panel_id}-', dir=destination) as temporary:
        temp = Path(temporary)
        with plt.rc_context({'font.family': style['font'], 'pdf.fonttype': 42,
                             'svg.fonttype': 'none'}):
            fig, ax, handles, details = build_figure(data, cfg, spec, style)
            try:
                fig.text(.5, .975, spec.get('title', ''), fontsize=style.get('title_fontsize', 18),
                         ha='center', va='top')
                ax.text(.98, .02, spec.get('corner_label', ''), transform=ax.transAxes,
                        fontsize=style.get('corner_fontsize', 12), ha='right', va='bottom',
                        color='black', zorder=1000)
                for extension in style['formats']:
                    fig.savefig(temp / f'{panel_id}.{extension}', dpi=style['dpi'], facecolor='white',
                                **({'bbox_inches': 'tight'} if style.get('bbox_inches') == 'tight' else {}))
            finally:
                plt.close(fig)
            if handles:
                legend_fig = plt.figure(figsize=(style['size_inches'][0], 1.2))
                try:
                    legend_ax = legend_fig.add_axes([0, 0, 1, .2])
                    legend_ax.set_axis_off()
                    if style.get('legend_ncol'):
                        legend = legend_ax.legend(handles=handles, ncol=style['legend_ncol'],
                            loc='center', frameon=False, fontsize=style['legend_fontsize'],
                            handlelength=2.3, columnspacing=1.8)
                    else:
                        legend = top_legend(legend_ax, {'plot': {'legend': {
                            'fontsize': style['legend_fontsize']}}}, handles=handles)
                    legend_fig.canvas.draw()
                    bounds = legend.get_window_extent(legend_fig.canvas.get_renderer())
                    bounds = bounds.transformed(legend_fig.dpi_scale_trans.inverted()).padded(.1)
                    for extension in style['formats']:
                        legend_fig.savefig(temp / f'{panel_id}_legend.{extension}',
                                           dpi=style['dpi'], facecolor='white', bbox_inches=bounds)
                finally:
                    plt.close(legend_fig)
        files = {p.name: file_digest(p) for p in temp.iterdir()}
        code_files = [Path(__file__), Path(__file__).with_name('panels.py'), Path(__file__).with_name('figures.py'),
                      ROOT/'src/embedding_analysis/legend.py',
                      ROOT/'src/embedding_analysis/experiments/overview/plotting.py',
                      ROOT/'src/embedding_analysis/experiments/boundary/plotting.py',
                      ROOT/'src/embedding_analysis/experiments/multilabel/plotting.py',
                      ROOT/'src/embedding_analysis/experiments/centroid/plotting.py',
                      ROOT/'src/embedding_analysis/experiments/performance/plotting.py',
                      ROOT/'src/embedding_analysis/experiments/performance/tables.py',
                      ROOT/'src/embedding_analysis/experiments/multilabel/spatial.py',
                      ROOT/'src/embedding_analysis/experiments/nae/plotting.py',
                      ROOT/'src/embedding_analysis/experiments/nae/data.py']
        write_json(temp / f'{panel_id}.manifest.json', {
            'panel': panel_id, 'spec': spec, 'style': style, 'source': provenance,
            'figure_config_sha256': config_digest, 'source_config': cfg,
            'drawing': details, 'files_sha256': files,
            'code_sha256': {str(p.relative_to(ROOT)): file_digest(p) for p in code_files},
            'matplotlib_version': matplotlib.__version__,
        })
        previous = destination / f'{panel_id}.manifest.json'
        old_files = json.loads(previous.read_text()).get('files_sha256', {}) if previous.exists() else {}
        for p in temp.iterdir():
            os.replace(p, destination / p.name)
        for name in set(old_files)-set(files):
            if name in {f'{stem}.{ext}' for stem in (panel_id, panel_id+'_legend')
                        for ext in ('pdf', 'png', 'svg')}:
                (destination / name).unlink(missing_ok=True)


def refresh_previews(root=ROOT):
    paper_dir = root/'outputs'/'paper'
    preview_dir = paper_dir/'preview'
    preview_dir.mkdir(parents=True, exist_ok=True)
    figures = []
    for dest in sorted(paper_dir.glob('figure*')):
        if not dest.is_dir() or not any(dest.glob('*.manifest.json')):
            continue
        figure = safe_name(dest.name)
        figures.append(figure)
        cards = []
        for p in sorted(dest.glob('*.manifest.json')):
            panel_id = p.name.removesuffix('.manifest.json')
            record = json.loads(p.read_text())
            links = ' · '.join(f'<a href="{html.escape("../"+figure+"/"+name)}">{html.escape(name)}</a>' for name in record['files_sha256'])
            preview = ''
            if f'{panel_id}.png' in record['files_sha256']:
                # Hide only the exported canvas's top white margin in the gallery.
                # Keep publication files and their fixed physical dimensions intact.
                from PIL import Image, ImageChops
                with Image.open(dest/f'{panel_id}.png') as picture:
                    rgb = picture.convert('RGB')
                    bounds = ImageChops.difference(rgb, Image.new('RGB', rgb.size, 'white')).getbbox()
                    top = max(0, bounds[1]-12) if bounds else 0
                    offset = top / picture.width * 100
                preview = (f'<div class="plot-preview"><img src="../{figure}/{panel_id}.png" '
                           f'style="margin-top:-{offset:.4f}%" alt="Panel {panel_id}"></div>')
            if f'{panel_id}_legend.png' in record['files_sha256']:
                preview += f'<img src="../{figure}/{panel_id}_legend.png" alt="Separate legend">'
            cards.append(f'<article><h2>{panel_id}</h2>{preview}<p>{links}</p></article>')
        (preview_dir/f'{figure}.html').write_text('<!doctype html><meta charset="utf-8"><title>'+figure+
            '</title><style>body{font:16px sans-serif;margin:24px}main{display:flex;flex-wrap:wrap;gap:20px}'
            'article{width:440px;max-width:100%;align-self:flex-start}h2{margin:0 0 4px}'
            '.plot-preview{overflow:hidden}img{display:block;width:100%}p{overflow-wrap:anywhere}'
            '</style><nav><a href="index.html">All figures</a></nav><h1>'+figure+'</h1><main>'+''.join(cards)+'</main>')
        (dest/'index.html').unlink(missing_ok=True)
    links = ''.join(f'<li><a href="{figure}.html">{figure}</a></li>' for figure in figures)
    (preview_dir/'index.html').write_text(
        '<!doctype html><meta charset="utf-8"><title>Paper previews</title>'
        '<style>body{font:18px sans-serif;margin:32px}li{margin:16px 0}</style>'
        '<h1>Paper figures</h1><ul>'+links+'</ul>')
    return preview_dir/'index.html'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['check', 'render', 'preview'])
    parser.add_argument('config', type=Path, nargs='?')
    parser.add_argument('--panel', nargs='+', help='Only these panel IDs, e.g. c e')
    args = parser.parse_args(argv)
    for name, folder in [('MPLCONFIGDIR', 'matplotlib'), ('XDG_CACHE_HOME', 'xdg')]:
        os.environ.setdefault(name, str(ROOT/'.cache'/folder))
    try:
        if args.command == 'preview':
            print(f'Preview: {refresh_previews()}')
            return
        if args.config is None:
            parser.error('config is required for check/render')
        config = json.loads(args.config.read_text())
        figure = safe_name(config['figure'])
        selected = args.panel or list(config['panels'])
        jobs = []
        for panel_id in selected:
            safe_name(panel_id)
            if panel_id not in config['panels']:
                raise ValueError(f'Unknown panel: {panel_id}')
            spec = config['panels'][panel_id]
            style = merge(config['style'], spec.get('style', {}))
            if not style['formats'] or set(style['formats']) - {'png', 'pdf', 'svg'}:
                raise ValueError('Formats must be png, pdf and/or svg')
            data, cfg, provenance = resolve_source(spec)
            jobs.append((panel_id, spec, style, data, cfg, provenance))
            counts = provenance['rows']
            count_text = ', '.join(f'{name}={n:,}' for name, n in counts.items()) if isinstance(counts, dict) else f'{counts:,} rows'
            print(f'Checked {figure}/{panel_id}: {count_text}, {provenance["checkpoint"]}')
        if args.command == 'check':
            return
        dest = ROOT/'outputs'/'paper'/figure
        for job in jobs:
            render_panel(dest, *job, file_digest(args.config))
            print(f'Rendered {figure}/{job[0]}: {dest}')
        print(f'Preview: {refresh_previews()}')
    except (ValueError, KeyError, OSError) as exc:
        parser.error(str(exc))
