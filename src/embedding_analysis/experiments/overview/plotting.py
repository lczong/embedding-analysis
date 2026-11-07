"""Class-colored views restored from normpca100/train_plot plotting scripts."""
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


def save(fig, stem, cfg):
    stem=Path(stem);stem.parent.mkdir(parents=True,exist_ok=True)
    options=cfg['plot'].get('overview',{})
    for ext in cfg['plot']['formats']:
        fig.savefig(stem.with_suffix('.'+ext),dpi=options.get('dpi',300),bbox_inches='tight')
    plt.close(fig)


def axis_indicator(ax, method):
    ox=oy=.04;length=.14
    kw=dict(arrowstyle='->',color='black',lw=1,mutation_scale=14,shrinkA=0,shrinkB=0)
    ax.annotate('',xy=(ox+length,oy),xytext=(ox,oy),xycoords='axes fraction',arrowprops=kw,zorder=1000)
    ax.annotate('',xy=(ox,oy+length),xytext=(ox,oy),xycoords='axes fraction',arrowprops=kw,zorder=1000)
    ax.text(ox+length+.01,oy,method+'-x',transform=ax.transAxes,ha='left',va='center',fontsize=11)
    ax.text(ox,oy+length+.01,method+'-y',transform=ax.transAxes,ha='center',va='bottom',rotation=90,fontsize=11)


def selected_families(df, classes, fraction):
    """Top ceil(N_families * fraction) by count within each class, as in the original."""
    selected=[]
    for cls in classes:
        # Stable count sorting preserves first-seen tie order in the original scripts.
        counts=df.loc[df.class_label==cls,'family_label'].value_counts(sort=False)
        ranked=counts.sort_values(ascending=False,kind='stable')
        selected.extend(ranked.index[:max(1,math.ceil(len(ranked)*fraction))])
    return sorted(set(selected))


def legend(df, classes, dest, cfg):
    handles=[Line2D([0],[0],linestyle='none',marker='o',markerfacecolor=cfg['class_colors'][cls],
                    markeredgecolor='white',markeredgewidth=.3,markersize=14,alpha=1,
                    label=f'{cls} ({int((df.class_label==cls).sum()):,})') for cls in classes]
    ncol=math.ceil(len(classes)/2)
    fig,ax=plt.subplots(figsize=(ncol*1.9,1.4));ax.axis('off')
    ax.legend(handles=handles,loc='center',ncol=ncol,fontsize=14,frameon=False,
              handletextpad=.4,columnspacing=1,labelspacing=.6)
    save(fig,dest,cfg)


def plot_visualization(path,cfg,destination):
    path=Path(path);dest=Path(destination)/'figures'
    df=pd.read_csv(path/'coordinates.csv',dtype={'sequence_id':str})
    stage=json.loads((path/'manifest.json').read_text())['stage']
    method={'tsne':'t-SNE','umap':'UMAP'}[stage]
    options=cfg['plot'].get('overview',{})
    fraction=options.get('top_family_fraction',.15)
    if not 0<fraction<=1:raise ValueError('top_family_fraction must be in (0,1]')
    preferred=options.get('class_order',cfg['classes'])
    present=set(df.class_label);classes=[c for c in preferred if c in present]+sorted(present-set(preferred))
    family_labels=selected_families(df,classes,fraction)
    xy=df[['x','y']].to_numpy();lo=xy.min();hi=xy.max();pad=(hi-lo)*.05
    with plt.rc_context({'font.family':options.get('font','Arial')}):
        for stem,annotate_family in [('classes',False),('class_label_family',True)]:
            fig,ax=plt.subplots(figsize=options.get('figsize',[12,10]),constrained_layout=True)
            for cls in classes:
                g=df[df.class_label==cls]
                ax.scatter(g.x,g.y,c=cfg['class_colors'][cls],s=6,alpha=.4,edgecolors='white',linewidths=0,marker='o')
            names=family_labels if annotate_family else classes
            column='family_label' if annotate_family else 'class_label'
            for name in names:
                g=df[df[column]==name]
                ax.text(float(g.x.median()),float(g.y.median()),name,fontsize=8 if annotate_family else 25,
                        color='black',ha='center',va='center',zorder=10,
                        bbox=dict(boxstyle='round,pad=0.15' if annotate_family else 'round,pad=0.25',
                                  facecolor='white',edgecolor='none',alpha=.7 if annotate_family else .75))
            ax.set_xlim(lo-pad,hi+pad);ax.set_ylim(lo-pad,hi+pad);ax.set_aspect('equal',adjustable='box')
            ax.set_xticks([]);ax.set_yticks([])
            for spine in ax.spines.values():spine.set_visible(False)
            axis_indicator(ax,method)
            save(fig,dest/stem,cfg)
            legend(df,classes,dest/(stem+'_legend'),cfg)
    # Record exactly which families are annotated without touching source coordinates.
    dest.parent.mkdir(parents=True,exist_ok=True)
    (dest.parent/'annotated_families.json').write_text(json.dumps({'fraction':fraction,'families':family_labels},indent=2)+'\n')
