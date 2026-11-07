"""System-scoped output paths, publication and browsable result indexes."""
import html
import os
from pathlib import Path
from .config import local_path


def system_root(cfg, version=None):
    root=local_path(cfg,cfg['output_root'])/cfg['system']
    return root/'_versions'/version if version else root


def stage_path(root, owner, route, stage, method='tsne'):
    if owner=='preprocess':
        if not route:raise ValueError('PCA requires --route')
        return root/'_shared/pca'/route
    scope=route or ('summary' if stage in ['tables','plots'] else '_shared')
    step=f'visualization-{method}' if stage=='visualization' else stage
    return root/owner/'artifacts'/scope/step


def publish_target(root,owner,route,stage,logical,method,table_patterns,table_names,figure_names):
    scope=route or 'summary'
    if logical.suffix.lower() in ['.png','.pdf','.svg']:
        parts=[p for p in logical.parts[:-1] if p!='figures']
        stem=figure_names.get(logical.stem,logical.stem)
        if stage=='visualization' and method in ['tsne','umap']:stem=method+'_'+stem
        return root/owner/'figures'/scope/Path(*parts)/(stem+logical.suffix)
    if any(logical.match(pattern) for pattern in table_patterns):
        return root/owner/'tables'/scope/logical.parent/table_names.get(logical.name,logical.name)
    return None


def indexes(root):
    """Generated only from published figures/tables, never creates empty workflows."""
    workflows=[]
    for workflow in sorted(root.iterdir()):
        if not workflow.is_dir() or workflow.name.startswith('_'):continue
        figures=sorted(p for p in (workflow/'figures').rglob('*') if p.suffix.lower() in ['.png','.pdf','.svg']) if (workflow/'figures').exists() else []
        tables=sorted((workflow/'tables').rglob('*.csv')) if (workflow/'tables').exists() else []
        if not figures and not tables:continue
        workflows.append(workflow)
        lines=[f'# {root.name} / {workflow.name}', '']
        if figures:
            lines+=['[图片预览](figures/index.html)', '', '## 图片', '']
            cards=[]
            for p in figures:
                rel=p.relative_to(workflow).as_posix();lines.append(f'- [{p.relative_to(workflow/"figures")}]({rel})')
                if p.suffix.lower()=='.png':
                    image_rel=p.relative_to(workflow/'figures').as_posix()
                    pdf=p.with_suffix('.pdf');extra=f' · <a href="{html.escape(pdf.relative_to(workflow/"figures").as_posix())}">PDF</a>' if pdf.exists() else ''
                    cards.append(f'<article><a href="{html.escape(image_rel)}"><img loading="lazy" src="{html.escape(image_rel)}"></a><p>{html.escape(image_rel)}{extra}</p></article>')
            (workflow/'figures/index.html').write_text('<!doctype html><meta charset="utf-8"><title>'+html.escape(workflow.name)+'</title><style>body{font:16px system-ui;margin:24px;background:#f5f5f5}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:20px}article{background:white;padding:14px;overflow-wrap:anywhere}img{width:100%;height:320px;object-fit:contain}</style><h1>'+html.escape(workflow.name)+'</h1><main>'+''.join(cards)+'</main>')
        if tables:
            lines+=['', '## 统计表', '']+[f'- [{p.relative_to(workflow/"tables")}]({p.relative_to(workflow).as_posix()})' for p in tables]
        (workflow/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    (root/'RESULTS.md').write_text('# '+root.name+' results\n\n'+'\n'.join(f'- [{w.name}]({w.name}/RESULTS.md)'+(f' · [图片预览]({w.name}/figures/index.html)' if (w/'figures/index.html').exists() else '') for w in workflows)+'\n')
