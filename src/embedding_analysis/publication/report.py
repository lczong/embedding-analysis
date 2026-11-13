"""Collect Figure 2/3-style views into a model-specific, multipage PDF."""
import argparse
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile

from ..artifacts import artifact_file, code_hash, file_digest, ready, write_json
from ..config import merge
from .figures import build_figure, selected_samples
from .render import ROOT, resolve_source, safe_name

MODELS = {'esm1b': 'ESM-1b 650M', 'esm2': 'ESM2 650M',
          'esm2-150m': 'ESM2 150M', 'esm2-35m': 'ESM2 35M'}


def preset(system, model, root=ROOT, kind="workflow"):
    """Reuse publication selections, including Peptidase's own combinations."""
    safe_name(model)
    if system not in ('cazy', 'peptidase'):
        raise ValueError('System must be cazy or peptidase')
    if kind == 'nca':
        template = json.loads((root / 'paper/figures/figure5.json').read_text())
        keys = ('b', 'c') if system == 'cazy' else ('h', 'i')
        panels = {}
        for name, key, suffix in zip(('nca_direct', 'nca_conditioned'), keys,
                                    ('__l2-frozen-nca', '__l1-ft-ce__l2-frozen-nca')):
            spec = copy.deepcopy(template['panels'][key])
            spec['source']['route'] = model + suffix
            spec['title'] = spec['corner_label'] + ' | t-SNE'
            panels[name] = spec
        return {'report_kind': 'nca', 'style': copy.deepcopy(template['style']), 'panels': panels}
    if kind != 'workflow':
        raise ValueError(f'Unknown report preset: {kind}')
    templates = {n: json.loads((root / f'paper/figures/figure{n}.json').read_text())
                 for n in (2, 3, 4)}
    training = templates[2 if system == 'cazy' else 4]
    keys = ('c', 'd', 'e') if system == 'cazy' else ('b', 'c', 'd')
    panels = {}
    for level, (name, key) in enumerate(zip(('binary_l0', 'classes_l1', 'families_l2'), keys)):
        panels[name] = copy.deepcopy(training['panels'][key])
        panels[name]['source']['route'] = f'{model}__l{level}-ft-ce'
        panels[name]['title'] = ['Level 0 | Binary t-SNE', 'Level 1 | Class t-SNE',
                                  'Level 2 | Class and family t-SNE'][level]
    for workflow in ('boundary', 'multilabel'):
        for level in range(3):
            template = (templates[3]['panels'][('b' if workflow == 'boundary' else 'e')]
                        if system == 'cazy' else templates[4]['panels'][('i' if workflow == 'boundary' else 'j')])
            spec = copy.deepcopy(template)
            spec['source']['route'] = f'{model}__l{level}-ft-ce'
            spec['corner_label'] = f'Level {level}'
            spec['title'] = f'Level {level} | {workflow.title()} UMAP'
            panels[f'{workflow}_l{level}'] = spec
    for name, cazy_key, pep_key in [('silhouette', 'h', 'k'), ('ba', 'i', 'l')]:
        template = templates[3]['panels'][cazy_key] if system == 'cazy' else templates[4]['panels'][pep_key]
        spec = copy.deepcopy(template)
        routes = [f'{model}__l{i}-ft-ce' for i in range(3)]
        spec['selection']['routes'] = routes
        spec['style']['route_labels'] = {r: f'Level {i}' for i, r in enumerate(routes)}
        spec['title'] = 'Levels 0–2 | ' + ('Boundary silhouette' if name == 'silhouette' else 'Barycentric alignment (BA)')
        panels[name] = spec
    return {'style': copy.deepcopy(training['style']), 'panels': panels}


def source_paths(root, system, version, panels):
    base = root / 'outputs' / system
    if version:
        base = base / '_versions' / version
    paths = []
    for spec in panels.values():
        source = spec['source']
        if source['route'] == 'summary':
            paths.extend(base / source['workflow'] / 'artifacts' / route / 'metrics'
                         for route in spec['selection']['routes'])
        else:
            paths.append(base / source['workflow'] / 'artifacts' / source['route'] / source['stage'])
    return paths


def choose_version(root, system, panels, requested):
    """Never mix default/versioned artifacts or silently choose between two runs."""
    if requested != 'auto':
        version = None if requested == 'default' else safe_name(requested)
        candidates = [version]
    else:
        directory = root / 'outputs' / system / '_versions'
        candidates = [None] + sorted(p.name for p in directory.iterdir() if p.is_dir()) if directory.exists() else [None]
    complete = []
    missing = {}
    for version in candidates:
        absent = [str(p.relative_to(root)) for p in source_paths(root, system, version, panels)
                  if not (p / 'manifest.json').is_file()]
        if not absent:
            complete.append(version)
        missing[version or 'default'] = absent
    if len(complete) > 1:
        raise ValueError('Multiple complete versions: ' + ', '.join(v or 'default' for v in complete)
                         + '. Specify --version explicitly.')
    if not complete:
        closest = min(missing, key=lambda v: len(missing[v]))
        raise ValueError(f'Missing workflow sources (version {closest}):\n  ' + '\n  '.join(missing[closest]))
    return complete[0]


def metric_source(spec, root, version):
    """Combine existing per-sample scores in memory; never rewrite summary outputs."""
    import numpy as np
    import pandas as pd
    source = spec['source']
    frames, records, configs = [], [], []
    value = 'silhouette' if spec['kind'] == 'boundary_silhouette' else 'ba_score'
    logical = 'samples.csv' if value == 'silhouette' else 'scores.csv'
    for route in spec['selection']['routes']:
        base = root / 'outputs' / source['system']
        if version:
            base = base / '_versions' / version
        path = base / source['workflow'] / 'artifacts' / route / 'metrics'
        if not ready(path):
            raise ValueError(f'Incomplete or changed metric source: {path}')
        meta = json.loads((path / 'manifest.json').read_text())
        actual = (meta['config']['system'], meta['experiment'], meta['route'], meta['stage'])
        if actual != (source['system'], source['workflow'], route, 'metrics'):
            raise ValueError(f'Metric source identity mismatch: {path}')
        if logical not in meta['artifacts']:
            raise ValueError(f'Missing per-sample scores: {path}')
        csv = artifact_file(path, logical)
        data = pd.read_csv(csv, dtype={'sequence_id': str})
        label = 'dataset_role' if value == 'silhouette' else 'class_label'
        if not {'sequence_id', label, value} <= set(data) or data.empty:
            raise ValueError(f'Missing columns or empty scores: {csv}')
        if data[['sequence_id', label]].isna().any().any() or data.sequence_id.duplicated().any():
            raise ValueError(f'Missing labels or duplicate IDs: {csv}')
        if value == 'silhouette' and not np.isfinite(data[value]).all():
            raise ValueError(f'Nonfinite silhouette: {csv}')
        data.insert(0, 'route', route)
        frames.append(data)
        configs.append(meta['config'])
        records.append({'checkpoint': str(path.relative_to(root)), 'manifest_sha256': file_digest(path/'manifest.json'),
                        'samples_sha256': file_digest(csv), 'rows': len(data)})
    data = pd.concat(frames, ignore_index=True)
    selected_samples(data, spec['selection'], value)
    return data, configs[0], {'metric_sources': records}


def load_jobs(config, root, version):
    jobs = []
    for name, original in config['panels'].items():
        spec = copy.deepcopy(original)
        if version:
            spec['source']['version'] = version
        if spec['source']['route'] == 'summary':
            data, cfg, provenance = metric_source(spec, root, version)
        else:
            data, cfg, provenance = resolve_source(spec, root)
        style = merge(config['style'], spec.get('style', {}))
        jobs.append((name, spec, style, data, cfg, provenance))
    return jobs


def draw_page(job, heading, page, count):
    import matplotlib.pyplot as plt
    from ..legend import top_legend
    name, spec, style, data, cfg, provenance = job
    style = {**style, 'size_inches': [10, 10]}
    fig, ax, handles, details = build_figure(data, cfg, spec, style)
    # Reserve independent header and legend bands, preserving marginal KDE geometry.
    for axes in list(fig.axes):
        box = axes.get_position()
        axes.set_position([.04 + .92*box.x0, .08 + .76*box.y0, .92*box.width, .76*box.height])
    legend_ax = fig.add_axes([.07, .845, .86, .001])
    legend_ax.set_axis_off()
    top_legend(legend_ax, {'plot': {'legend': {'fontsize': 10}}}, handles=handles)
    fig.text(.07, .965, spec['title'], ha='left', va='top', fontsize=15)
    return fig, details


PAGE_GROUPS = [
    ('training', 'Training space | t-SNE', ('binary_l0', 'classes_l1', 'families_l2')),
    ('boundary', 'Boundary | UMAP', ('boundary_l0', 'boundary_l1', 'boundary_l2')),
    ('multilabel', 'Multilabel | UMAP', ('multilabel_l0', 'multilabel_l1', 'multilabel_l2')),
    ('metrics', 'Silhouette and barycentric alignment', ('silhouette', 'ba')),
    ('nca', 'Figure 5 | Direct and L1-conditioned L2 NCA', ('nca_direct', 'nca_conditioned')),
]


def grouped_jobs(jobs):
    """Keep requested order within each scientific group; omit empty groups."""
    return [(key, title, [job for job in jobs if job[0] in members])
            for key, title, members in PAGE_GROUPS if any(job[0] in members for job in jobs)]


def render_report(config, jobs, system, model, version, root=ROOT, dpi=200, force=False):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import pypdf
    from pypdf import PdfReader, PdfWriter, Transformation
    from PIL import Image
    version_name = version or 'default'
    kind = config.get('report_kind', 'workflow')
    full = list(preset(system, model, root, kind=kind)['panels'])
    selection = list(config['panels'])
    suffix = '' if selection == full else '_' + hashlib.sha256('|'.join(selection).encode()).hexdigest()[:10]
    preset_suffix = '_nca' if kind == 'nca' else ''
    name = f'{system}_{model}_{version_name}{preset_suffix}{suffix}'
    destination = root / 'outputs/paper/reports' / system / model / version_name
    pdf = destination / (name + '.pdf')
    manifest = destination / (name + '.manifest.json')
    signature_data = {'system': system, 'model': model, 'version': version_name, 'config': config,
                      'layout': 'grouped-vector-v1', 'dpi': dpi, 'code_sha256': code_hash(),
                      'matplotlib': matplotlib.__version__, 'pypdf': pypdf.__version__,
                      'sources': {job[0]: job[5] for job in jobs}}
    signature = hashlib.sha256(json.dumps(signature_data, sort_keys=True).encode()).hexdigest()
    if not force and manifest.exists():
        old = json.loads(manifest.read_text())
        if old.get('signature') == signature and pdf.exists() and old.get('pdf_sha256') == file_digest(pdf):
            print(f'Cached: {pdf}')
            return pdf
    destination.mkdir(parents=True, exist_ok=True)
    heading = f'{"CAZy" if system == "cazy" else "Peptidase"} | {MODELS.get(model, model)} | {version_name}'
    groups = grouped_jobs(jobs)
    with tempfile.TemporaryDirectory(prefix='.report-', dir=destination) as directory:
        temporary = Path(directory)
        writer = PdfWriter()
        writer.add_metadata({'/Title': heading, '/Subject': 'Training, boundary and multilabel workflow review',
                             '/Author': 'Embedding analysis'})
        pages, previews = [], []
        with plt.rc_context({'font.family': 'Arial', 'pdf.fonttype': 42}):
            for page_number, (key, title, members) in enumerate(groups, 1):
                # Each 10-inch panel is scaled to 7.5 inches, retaining vector text.
                tile, margin, header = 540, 20, 55
                width, height = len(members)*tile + 2*margin, tile + margin + header
                page = writer.add_blank_page(width=width, height=height)
                preview = Image.new('RGB', (round(width*100/72), round(height*100/72)), 'white')
                panels = []
                for column, job in enumerate(members):
                    fig, details = draw_page(job, heading, page_number, len(groups))
                    try:
                        buffer = io.BytesIO()
                        fig.savefig(buffer, format='pdf', dpi=dpi, facecolor='white')
                        buffer.seek(0)
                        source = PdfReader(buffer).pages[0]
                        page.merge_transformed_page(source, Transformation().scale(.75).translate(margin+column*tile, margin))
                        png = io.BytesIO()
                        fig.savefig(png, format='png', dpi=75, facecolor='white')
                        png.seek(0)
                        with Image.open(png) as image:
                            preview.paste(image.convert('RGB'), (round((margin+column*tile)*100/72), round(header*100/72)))
                    finally:
                        plt.close(fig)
                    panels.append({'panel': job[0], 'spec': job[1], 'drawing': details, 'source': job[5]})
                label = plt.figure(figsize=(width/72, height/72))
                try:
                    label.text(margin/width, 1-12/height, heading, fontsize=17, weight='bold', va='top')
                    label.text(margin/width, 1-34/height, title, fontsize=12, va='top')
                    label.text(1-margin/width, 1-15/height, f'{page_number} / {len(groups)}', fontsize=10, ha='right', va='top')
                    buffer = io.BytesIO()
                    label.savefig(buffer, format='pdf', transparent=True)
                    buffer.seek(0)
                    page.merge_page(PdfReader(buffer).pages[0])
                    png = io.BytesIO()
                    label.savefig(png, format='png', dpi=100, transparent=True)
                    png.seek(0)
                    with Image.open(png) as image:
                        overlay = image.convert('RGBA')
                        preview.paste(overlay, (0, 0), overlay)
                finally:
                    plt.close(label)
                preview_name = f'{name}_{page_number:02d}_{key}.png'
                preview.save(temporary/preview_name)
                previews.append(preview_name)
                writer.add_outline_item(title, page_number-1)
                pages.append({'page': page_number, 'group': key, 'panels': panels})
                print(f'Rendered page {page_number}/{len(groups)}: {key} ({len(members)} panels)', flush=True)
        with (temporary/pdf.name).open('wb') as stream:
            writer.write(stream)
        if len(PdfReader(temporary/pdf.name).pages) != len(groups):
            raise ValueError('PDF page count verification failed')
        write_json(temporary/manifest.name, {**signature_data, 'signature': signature, 'pages': pages,
                                           'previews': previews, 'pdf_sha256': file_digest(temporary/pdf.name)})
        for path in temporary.iterdir():
            os.replace(path, destination/path.name)
        for old in destination.glob(f'{name}_[0-9][0-9]_*.png'):
            if old.name not in previews:
                old.unlink()
    print(f'PDF: {pdf}')
    return pdf


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['check', 'render'])
    parser.add_argument('--system', required=True, choices=['cazy', 'peptidase'])
    parser.add_argument('--model', required=True, help='Route prefix, e.g. esm1b, esm2-150m, esm2-35m')
    parser.add_argument('--preset', choices=['workflow', 'nca'], default='workflow',
                        help='Four-page workflow report or one-page Figure 5 NCA pair')
    parser.add_argument('--version', default='auto', help='auto (unique complete run), default, or explicit version')
    parser.add_argument('--panels', nargs='+', help='Subset grouped by training/boundary/multilabel/metrics; see paper/README.md')
    parser.add_argument('--dpi', type=int, default=200)
    parser.add_argument('--force', action='store_true', help='Redraw even if cached')
    args = parser.parse_args(argv)
    os.environ.setdefault('MPLCONFIGDIR', str(ROOT/'.cache/matplotlib'))
    try:
        if args.dpi <= 0:
            raise ValueError('DPI must be positive')
        config = preset(args.system, args.model, kind=args.preset)
        if args.panels:
            if len(set(args.panels)) != len(args.panels) or set(args.panels)-set(config['panels']):
                raise ValueError('Select distinct valid panels: ' + ', '.join(config['panels']))
            config['panels'] = {name: config['panels'][name] for name in args.panels}
        version = choose_version(ROOT, args.system, config['panels'], args.version)
        jobs = load_jobs(config, ROOT, version)
        print(f'Checked {len(jobs)} panels: {args.system}/{args.model}, version={version or "default"}')
        if args.command == 'render':
            render_report(config, jobs, args.system, args.model, version, dpi=args.dpi, force=args.force)
    except (ValueError, KeyError, OSError) as exc:
        parser.error(str(exc))
