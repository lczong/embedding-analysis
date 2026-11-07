from ...artifacts import artifact_file
"""Balanced, per-target panels and silhouette plots restored from normpca100/exp1."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import patheffects
from scipy.stats import gaussian_kde

COLORS={'train':'#76B7B2','ood':'#E15759','shuffled':'#4E79A7','idr':'#B07AA1'}
TARGETS=['ood','shuffled','idr']
BOX_ORDER=['shuffled','idr','ood']


def save(fig,stem,cfg):
    stem=Path(stem);stem.parent.mkdir(parents=True,exist_ok=True)
    for ext in cfg['plot']['formats']:
        fig.savefig(stem.with_suffix('.'+ext),dpi=cfg['plot'].get('boundary',{}).get('dpi',300),bbox_inches='tight')
    plt.close(fig)


def darken(color,factor):
    return '#'+''.join(f'{max(0,min(255,round(int(color[i:i+2],16)*factor))):02x}' for i in [1,3,5])


def labels(cfg):
    names=dict(cfg['role_labels'])
    names.update(cfg['plot'].get('boundary',{}).get('role_labels',{}))
    return names


def contour(ax,xy,color,percentile,linewidth=1.2,dashes=(4,2),halo=2):
    if len(xy)<10 or np.linalg.matrix_rank(np.cov(xy.T))<2:return
    kde=gaussian_kde(xy.T)
    # Original convention: 90% of sample locations have densities at/above the 10th percentile.
    level=float(np.quantile(kde(xy.T),1-percentile/100))
    low=xy.min(axis=0);high=xy.max(axis=0);margin=(high-low)*.1+1e-9
    x,y=np.meshgrid(np.linspace(low[0]-margin[0],high[0]+margin[0],200),
                    np.linspace(low[1]-margin[1],high[1]+margin[1],200))
    z=kde(np.vstack([x.ravel(),y.ravel()])).reshape(x.shape)
    if not z.min()<level<z.max():return
    cs=ax.contour(x,y,z,levels=[level],colors=[color],linewidths=linewidth,
                  linestyles=[(0,tuple(dashes))],zorder=110)
    if halo:
        effects=[patheffects.Stroke(linewidth=linewidth+halo,foreground='white'),patheffects.Normal()]
        # ContourSet itself is a Collection on current Matplotlib.
        cs.set_path_effects(effects)


def axis_indicator(ax,method):
    kw=dict(arrowstyle='->',color='black',lw=1,mutation_scale=14,shrinkA=0,shrinkB=0)
    ax.annotate('',xy=(.18,.04),xytext=(.04,.04),xycoords='axes fraction',arrowprops=kw,zorder=1000)
    ax.annotate('',xy=(.04,.18),xytext=(.04,.04),xycoords='axes fraction',arrowprops=kw,zorder=1000)
    ax.text(.19,.04,method+'-x',transform=ax.transAxes,ha='left',va='center',fontsize=11)
    ax.text(.04,.19,method+'-y',transform=ax.transAxes,ha='center',va='bottom',rotation=90,fontsize=11)


def background(ax,train,options,lighten):
    hb=ax.hexbin(train.x,train.y,gridsize=options.get('hexbin_gridsize',120),
                 cmap=options.get('hexbin_cmap','BuGn'),mincnt=1,linewidths=0,zorder=1)
    multiplier=options.get('hexbin_vmax_mult',1.5) if lighten else 1
    if multiplier!=1 and len(hb.get_array()):hb.set_clim(vmin=1,vmax=float(hb.get_array().max())*multiplier)


def foreground(ax,group,role,options):
    ax.scatter(group.x,group.y,c=COLORS[role],s=options.get('point_size',10),
               alpha=options.get('alpha',.55),edgecolors='white',linewidths=.25,rasterized=True,zorder=10+TARGETS.index(role))


def plot_visualization(path,cfg,destination):
    path=Path(path);dest=Path(destination)/'figures'
    df=pd.read_csv(path/'coordinates.csv');train=df[df.dataset_role=='train']
    method={'tsne':'t-SNE','umap':'UMAP'}[json.loads((path/'manifest.json').read_text())['stage']]
    options=cfg['plot'].get('boundary',{});names=labels(cfg)
    with plt.rc_context({'font.family':options.get('font','Arial')}):
        fig,ax=plt.subplots(figsize=(9,9));background(ax,train,options,lighten=True)
        handles=[mpatches.Patch(facecolor=COLORS['train'],label=names['train']+' density')]
        for role in TARGETS:
            group=df[df.dataset_role==role];foreground(ax,group,role,options)
            contour(ax,group[['x','y']].to_numpy(),darken(COLORS[role],.7),options.get('contour_percentile',90))
            handles.append(ax.scatter([],[],c=COLORS[role],s=50,edgecolors='white',linewidths=.25,label=names[role]))
        ax.legend(handles=handles,loc='upper right',frameon=True,facecolor='white',edgecolor='#CCCCCC',
                  prop={'size':13},handlelength=1.2,handletextpad=.6)
        ax.set_aspect('equal',adjustable='datalim');ax.axis('off');axis_indicator(ax,method)
        save(fig,dest/'balanced',cfg)
        # Original per-target layout has 80% contours and its own shared bounds.
        fig,axes=plt.subplots(1,3,figsize=(24,8),sharey=True)
        xy=df[['x','y']].to_numpy();low=xy.min(axis=0);high=xy.max(axis=0);margin=(high-low)*.04
        for ax,role in zip(axes,TARGETS):
            background(ax,train,options,lighten=False)
            group=df[df.dataset_role==role];foreground(ax,group,role,options)
            contour(ax,group[['x','y']].to_numpy(),COLORS[role],options.get('panel_contour_percentile',80),linewidth=2,dashes=(3.7,1.6),halo=0)
            ax.set_title(names[role],fontsize=16,fontweight='bold')
            ax.set_xlim(low[0]-margin[0],high[0]+margin[0]);ax.set_ylim(low[1]-margin[1],high[1]+margin[1])
            ax.set_aspect('equal');ax.axis('off')
        fig.tight_layout();save(fig,dest/'per_ood_panels',cfg)


def route_label(route):
    return route.removeprefix('esm2__').replace('__',' → ')


def boxplot(samples,cfg,stem):
    options=cfg['plot'].get('boundary',{});names=labels(cfg)
    routes=samples.route.drop_duplicates().tolist()
    with plt.rc_context({'font.family':options.get('font','Arial')}):
        single=len(routes)==1
        figsize=options.get('silhouette_single_figsize',[3.6,6]) if single else (10,4)
        fig,ax=plt.subplots(figsize=figsize);positions=[];values=[];faces=[];edges=[]
        for i,route in enumerate(routes):
            for j,role in enumerate(BOX_ORDER):
                group=samples[(samples.route==route)&(samples.dataset_role==role)].silhouette
                if not len(group):raise ValueError(f'Missing silhouette samples: {route}/{role}')
                values.append(group.to_numpy());positions.append(i*4+j)
                faces.append(COLORS[role]);edges.append(darken(COLORS[role],.6))
        bp=ax.boxplot(values,positions=positions,widths=.8,patch_artist=True,
                      flierprops=dict(marker='o',markersize=2,markerfacecolor='#888888',markeredgecolor='none',alpha=.4),
                      whiskerprops=dict(linewidth=1),capprops=dict(linewidth=1))
        for patch,face,edge in zip(bp['boxes'],faces,edges):
            patch.set_facecolor(face);patch.set_edgecolor(edge);patch.set_alpha(.6);patch.set_linewidth(1.2)
        for median,edge in zip(bp['medians'],edges):median.set_color(edge);median.set_linewidth(1.6)
        for key in ['whiskers','caps']:
            for artist,edge in zip(bp[key],[c for c in edges for _ in range(2)]):artist.set_color(edge)
        ax.axhline(0,color='#888888',lw=.8,linestyle='--',zorder=0)
        ax.set_xticks([i*4+1 for i in range(len(routes))]);ax.set_xticklabels([route_label(r) for r in routes],fontsize=12)
        ax.set_ylim(*options.get('silhouette_ylim',[-.2,1]));ax.set_ylabel('Per-sample silhouette score',fontsize=12)
        ax.tick_params(axis='y',labelsize=11);ax.spines['top'].set_visible(False);ax.spines['right'].set_visible(False)
        handles=[mpatches.Patch(facecolor=COLORS[r],edgecolor=darken(COLORS[r],.6),alpha=.6,label=names[r]) for r in BOX_ORDER]
        if single:
            ax.legend(handles=handles,loc='lower left',bbox_to_anchor=(0,1.02),borderaxespad=0,
                      facecolor='white',edgecolor='#CCCCCC',prop={'size':9})
        else:
            ax.legend(handles=handles,loc='upper right',facecolor='white',edgecolor='#CCCCCC',prop={'size':12})
        save(fig,stem,cfg)


def plot_metrics(path,cfg,destination):
    path=Path(path);samples=pd.read_csv(artifact_file(path, 'samples.csv'))
    samples.insert(0,'route',json.loads((path/'manifest.json').read_text())['route'])
    boxplot(samples,cfg,Path(destination)/'figures/silhouette')


def plot_summary(path,cfg,destination):
    # Quantile boxes require sample-level data, not route means.
    boxplot(pd.read_csv(artifact_file(Path(path), 'samples.csv')),cfg,Path(destination)/'comparison')
