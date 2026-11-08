"""BA plots owned by multilabel, adapted from the original exp2 figures."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from scipy.stats import gaussian_kde
from ...legend import top_legend
from ...artifacts import artifact_file
from .spatial import plot_visualization, PALETTE


def save(fig, stem, cfg):
    stem=Path(stem);stem.parent.mkdir(parents=True,exist_ok=True)
    for ext in cfg['plot']['formats']:
        fig.savefig(stem.with_suffix('.'+ext),dpi=cfg['plot']['multilabel'].get('dpi',300),bbox_inches='tight')
    plt.close(fig)


def kde(ax,values,color,label):
    if len(values)<2 or np.ptp(values)==0:return False
    x=np.linspace(values.min()-.3,values.max()+.3,500)
    ax.plot(x,gaussian_kde(values,bw_method='scott')(x),color=color,lw=1.8,label=label)
    return True


def finish_density(ax,cfg,stem,title):
    ax.set(xlabel='Barycentric Alignment Score',ylabel='Density',title=title)
    ax.spines['top'].set_visible(False);ax.spines['right'].set_visible(False)
    top_legend(ax,cfg);save(ax.figure,stem,cfg)


def plot_metrics(path,cfg,destination):
    scores=pd.read_csv(artifact_file(Path(path),'scores.csv'))
    valid=scores[np.isfinite(scores.ba_score)]
    counts=valid.groupby('class_label').size().sort_values(ascending=False)
    combos=counts[counts>=cfg['experiments']['multilabel']['min_combination_size']].index
    selected=cfg['plot']['multilabel'].get('ba_plot_combinations')
    if selected is not None:combos=[c for c in selected if c in combos]
    dest=Path(destination)/'figures'
    with plt.rc_context({'font.family':'Arial','font.size':14,'pdf.fonttype':42}):
        overlay,oa=plt.subplots(figsize=(10,5))
        for i,combo in enumerate(combos):
            values=valid.loc[valid.class_label==combo,'ba_score'].to_numpy()
            color=cfg['plot']['multilabel'].get('combo_colors',{}).get(combo,PALETTE[i%len(PALETTE)])
            if not kde(oa,values,color,f'{combo} (n={len(values):,})'):
                oa.axvline(values[0],color=color,label=f'{combo} (n={len(values):,}, constant)')
            fig,ax=plt.subplots(figsize=(7,4))
            ax.hist(values,bins=30,density=True,alpha=.35,color='#4878d0',edgecolor='white',lw=.5,label='Histogram')
            kde(ax,values,'#4878d0','KDE')
            ax.axvline(0,color='gray',ls='--',lw=1,alpha=.7,label='BA = 0')
            ax.axvline(1,color='green',ls=':',lw=1,alpha=.7,label='BA = 1')
            ax.axvline(values.mean(),color='red',ls='-.',lw=1.2,alpha=.8,label=f'Mean = {values.mean():.3f}')
            finish_density(ax,cfg,dest/'ba_combos'/('ba_combo_'+combo.replace('|','_')),f'{combo} (n = {len(values):,})')
        oa.axvline(0,color='gray',ls='--',lw=1,alpha=.6)
        oa.axvline(1,color='green',ls=':',lw=1,alpha=.6)
        if not len(combos):oa.text(.5,.5,'No eligible combinations',ha='center',transform=oa.transAxes)
        finish_density(oa,cfg,dest/'ba','BA Score Distribution — All Multi-label Combinations')


def plot_summary(path,cfg,destination):
    df=pd.read_csv(artifact_file(Path(path),'samples.csv'))
    routes=list(dict.fromkeys(df.route));valid=df[np.isfinite(df.ba_score)]
    options=cfg['plot']['multilabel'];threshold=options.get('ba_summary_min_n',30)
    ref=valid[(valid.route==routes[0]) & (valid.class_label.str.count(r'\|')==1)]
    counts=ref.groupby('class_label').size().sort_values(ascending=False)
    combos=list(counts[counts>threshold].index)
    combos=options.get('combinations',combos)
    groups=options.get('ba_summary_groups',{'all':routes})
    for name,selected in groups.items():
        selected=[r for r in selected if r in routes]
        if selected:draw_summary(valid,selected,combos,cfg,Path(destination)/('ba_'+name))


def draw_summary(valid,routes,combos,cfg,stem):
    options=cfg['plot']['multilabel']
    colors=['#777777','#59A14F','#4E79A7','#B07AA1','#E15759','#F28E2B']
    fixed={'esm2':'#777777','esm2__l0-ft-ce':'#59A14F','esm2__l1-ft-ce':'#4E79A7',
           'esm2__l2-ft-ce':'#F28E2B','esm2__l1-ft-ce__l2-frozen-nca':'#B07AA1','esm2__l2-frozen-nca':'#E15759'}
    with plt.rc_context({'font.family':'Arial','font.size':14,'pdf.fonttype':42}):
        fig,ax=plt.subplots(figsize=(max(5,14*len(combos)/9),5))
        width=min(.25,.8/max(1,len(routes)));handles=[]
        for i,route in enumerate(routes):
            color=fixed.get(route,colors[i%len(colors)])
            label=route.replace('esm2__','').replace('__',' → ')
            handles.append(Patch(facecolor=color,edgecolor=color,alpha=.5,label=label))
            for j,combo in enumerate(combos):
                values=valid.loc[(valid.route==route)&(valid.class_label==combo),'ba_score'].to_numpy()
                position=j+(i-(len(routes)-1)/2)*width
                if not len(values):continue
                if len(values)>1 and np.ptp(values)>0:
                    parts=ax.violinplot([values],positions=[position],widths=width*.9,showmedians=True,showextrema=False)
                    for body in parts['bodies']:
                        body.set_facecolor(matplotlib.colors.to_rgba(color,.5));body.set_edgecolor(color);body.set_alpha(None);body.set_linewidth(1)
                    parts['cmedians'].set_color('#404040');parts['cmedians'].set_linewidth(2.2);parts['cmedians'].set_alpha(.7)
                else:ax.plot([position-width*.35,position+width*.35],[values[0]]*2,color=color,lw=2)
        for j,combo in enumerate(combos):
            ns=[len(valid[(valid.route==r)&(valid.class_label==combo)]) for r in routes]
            text=f'N={ns[0]}' if len(set(ns))==1 else 'N='+ '/'.join(map(str,ns))
            ax.text(j,.98,text,ha='center',va='top',fontsize=10,color='.4',transform=ax.get_xaxis_transform())
            if j<len(combos)-1:ax.axvline(j+.5,color='.6',ls='--',lw=.8,alpha=.6,zorder=0)
        ax.set_xticks(range(len(combos)),combos)
        ax.set_ylabel('Barycentric Alignment Score (BAS)')
        limits=options.get('ba_summary_ylim',[-7,1]);ax.set_ylim(*limits);ax.margins(x=.03)
        if not combos:ax.text(.5,.5,'No eligible two-class combinations',ha='center',transform=ax.transAxes)
        top_legend(ax,cfg,handles=handles)
        save(fig,stem,cfg)
