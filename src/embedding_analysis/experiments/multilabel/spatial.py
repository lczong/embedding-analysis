"""White-background multi-label views with aligned x/y KDE marginals.

Style adapted locally from normpca100/exp2/debug/plot_umap_multi_white.py.
Coordinates are read unchanged; no fitting of PCA or two-dimensional embeddings.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from scipy.stats import gaussian_kde
from ...legend import top_legend
from ...artifacts import write_json

PALETTE=['#e6194b','#3cb44b','#4363d8','#f58231','#911eb4','#42d4f4',
         '#f032e6','#bfef45','#fabed4','#469990','#dcbeff','#9A6324','#800000']


def axis_indicator(ax,method):
    kw=dict(arrowstyle='->',color='black',lw=1,mutation_scale=14,shrinkA=0,shrinkB=0)
    for end in [(.18,.04),(.04,.18)]:
        ax.annotate('',xy=end,xytext=(.04,.04),xycoords='axes fraction',arrowprops=kw,zorder=2000)
    ax.text(.19,.04,method+'-x',transform=ax.transAxes,ha='left',va='center',fontsize=11)
    ax.text(.04,.19,method+'-y',transform=ax.transAxes,ha='center',va='bottom',rotation=90,fontsize=11)


def density(values,grid,minimum):
    if len(values)<minimum:return None,'too_few_samples'
    if np.ptp(values)==0:return None,'constant_coordinate'
    try:d=gaussian_kde(values,bw_method='scott')(grid)
    except np.linalg.LinAlgError:return None,'singular_covariance'
    support=np.flatnonzero(d>=d.max()*.001)
    if not len(support):return None,'empty_density'
    cut=slice(support[0],support[-1]+1)
    return (grid[cut],d[cut]),None


def peak_labels(ax,peaks,palette,vertical):
    """Keep neighboring peak labels apart; displaced labels point to their peak."""
    if not peaks:return
    ax.figure.canvas.draw();renderer=ax.figure.canvas.get_renderer();box=ax.get_window_extent(renderer)
    texts=[]
    for category,x,y in peaks:
        label=ax.annotate(category,xy=(x,y),xytext=(4,0) if vertical else (0,4),textcoords='offset points',
                          color=palette[category],fontsize=12,fontweight='bold',
                          ha='left' if vertical else 'center',va='center' if vertical else 'bottom',clip_on=False,zorder=100)
        extent=label.get_window_extent(renderer)
        pixel=ax.transData.transform((x,y))[1 if vertical else 0]
        half=(extent.height if vertical else extent.width)/2
        texts.append((pixel,half,label,x,y))
    texts.sort(key=lambda item:item[0]);low=(box.y0 if vertical else box.x0)+2;high=(box.y1 if vertical else box.x1)-2
    centers=[]
    for pixel,half,*_ in texts:
        centers.append(max(pixel,low+half,centers[-1]+texts[len(centers)-1][1]+half+4 if centers else low+half))
    if centers[-1]+texts[-1][1]>high:
        centers[-1]=high-texts[-1][1]
        for i in range(len(centers)-2,-1,-1):centers[i]=min(centers[i],centers[i+1]-texts[i+1][1]-texts[i][1]-4)
    for center,(pixel,half,label,x,y) in zip(centers,texts):
        shift=(center-pixel)*72/ax.figure.dpi
        label.set_position((4,shift) if vertical else (shift,4))
        if abs(shift)>3:
            # A faint leader identifies the true peak when labels need spacing.
            original=ax.transData.transform((x,y));target=original.copy();target[1 if vertical else 0]=center
            point=ax.transData.inverted().transform(target)
            ax.plot([x,point[0]],[y,point[1]],color=label.get_color(),lw=.5,alpha=.5)


def draw_view(df,categories,combos,palette,curves,bounds,cfg,stem,method):
    options=cfg['plot'].get('multilabel',{})
    fig=plt.figure(figsize=options.get('figsize',[11,11]))
    grid=fig.add_gridspec(2,2,width_ratios=[4,1],height_ratios=[1,4],hspace=.05,wspace=.05)
    ax=fig.add_subplot(grid[1,0]);top=fig.add_subplot(grid[0,0],sharex=ax);right=fig.add_subplot(grid[1,1],sharey=ax)
    xlim,ylim=bounds;ax.set_xlim(*xlim);ax.set_ylim(*ylim);ax.set_aspect('equal',adjustable='box')
    foreground=df.class_label.isin(categories);bg=df[~foreground]
    ax.scatter(bg.x,bg.y,c='lightgray',s=3,alpha=.15,edgecolors='white',linewidths=.3,rasterized=True,zorder=1)
    handles=[];top_peaks=[];right_peaks=[];maxima=[0.,0.]
    for i,category in enumerate(categories):
        group=df[df.class_label==category]
        if group.empty:continue
        multi=category in combos;color=palette[category]
        ax.scatter(group.x,group.y,c=[color],s=14 if multi else 3,alpha=.95 if multi else .15,
                   marker='o',edgecolors='white',linewidths=.4 if multi else .3,rasterized=True,zorder=1000+i if multi else 2+i)
        handles.append(Line2D([],[],linestyle='none',marker='o',markersize=9,markerfacecolor=color,
                              markeredgecolor='white',markeredgewidth=.4,label=f'{category} ({len(group):,})'))
        for dimension,panel in enumerate([top,right]):
            curve=curves[(category,dimension)]
            if curve is None:continue
            coord,d=curve;z=2+i*3
            if dimension==0:
                panel.fill_between(coord,0,d,color='white',alpha=.5,linewidth=0,zorder=z)
                panel.fill_between(coord,0,d,color=color,alpha=.35,linewidth=0,zorder=z+1)
                panel.plot(coord,d,color=color,lw=.9,zorder=z+2)
                peak=int(np.argmax(d));top_peaks.append((category,float(coord[peak]),float(d[peak])))
            else:
                panel.fill_betweenx(coord,0,d,color='white',alpha=.5,linewidth=0,zorder=z)
                panel.fill_betweenx(coord,0,d,color=color,alpha=.35,linewidth=0,zorder=z+1)
                panel.plot(d,coord,color=color,lw=.9,zorder=z+2)
                peak=int(np.argmax(d));right_peaks.append((category,float(d[peak]),float(coord[peak])))
            maxima[dimension]=max(maxima[dimension],float(d.max()))
    for panel in [ax,top,right]:
        panel.set_xticks([]);panel.set_yticks([])
        for spine in panel.spines.values():spine.set_visible(False)
    top.spines['bottom'].set_visible(True);right.spines['left'].set_visible(True)
    for spine in [top.spines['bottom'],right.spines['left']]:spine.set_color('#999999');spine.set_linewidth(.8)
    top.set_ylim(0,maxima[0]*1.35 if maxima[0] else 1)
    right.set_xlim(0,maxima[1]*2 if maxima[1] else 1)
    axis_indicator(ax,method)
    # Align marginal extents with the square scatter after aspect adjustment.
    fig.canvas.draw();position=ax.get_position();tp=top.get_position();rp=right.get_position()
    top.set_position([position.x0,tp.y0,position.width,tp.height])
    right.set_position([rp.x0,position.y0,rp.width,position.height])
    peak_labels(top,top_peaks,palette,False);peak_labels(right,right_peaks,palette,True)
    # Anchor above the top marginal, not between the KDE and the scatter.
    top_legend(top,cfg,handles=handles)
    stem.parent.mkdir(parents=True,exist_ok=True)
    for extension in cfg['plot']['formats']:fig.savefig(stem.with_suffix('.'+extension),dpi=options.get('dpi',300),bbox_inches='tight')
    plt.close(fig)


def plot_visualization(path,cfg,destination):
    path=Path(path);destination=Path(destination)
    df=pd.read_csv(path/'coordinates.csv',dtype={'sequence_id':str})
    method={'tsne':'t-SNE','umap':'UMAP'}[json.loads((path/'manifest.json').read_text())['stage']]
    options=cfg['plot'].get('multilabel',{})
    order=options.get('class_order',cfg['classes'])
    bases=[c for c in order if c in set(df.class_label)]
    combos=list(dict.fromkeys('|'.join(sorted(c.split('|'))) for c in cfg['plot']['highlight_combinations']))
    combos=[c for c in combos if c in set(df.class_label)]
    palette=dict(cfg['class_colors']);fixed=options.get('combo_colors',{})
    used={palette[c] for c in set(part for combo in combos for part in combo.split('|'))};used.update(fixed.values())
    available=[color for color in PALETTE if color not in used]
    for i,combo in enumerate(combos):palette[combo]=fixed.get(combo,available[i%len(available)])
    xy=df[['x','y']].to_numpy();span=np.ptp(xy,axis=0).max()*1.1
    center=(xy.min(axis=0)+xy.max(axis=0))/2
    bounds=[(c-span/2,c+span/2) for c in center]
    grids=[np.linspace(*limit,400) for limit in bounds];curves={};skipped=[]
    for category in bases+combos:
        group=df[df.class_label==category]
        for dimension,column in enumerate(['x','y']):
            curve,reason=density(group[column].to_numpy(),grids[dimension],options.get('kde_min_samples',10))
            curves[(category,dimension)]=curve
            if reason:skipped.append({'category':category,'dimension':column,'reason':reason})
    views=[('classes',bases,[])]
    for combo in combos:views.append(('combo_'+'_'.join(combo.split('|')),[c for c in bases if c in combo.split('|')]+[combo],[combo]))
    if len(combos)>1:
        parents={part for combo in combos for part in combo.split('|')}
        views.append(('combos_'+'__'.join(c.replace('|','_') for c in combos),[c for c in bases if c in parents]+combos,combos))
    with plt.rc_context({'font.family':options.get('font','Arial')}):
        for name,categories,selected in views:draw_view(df,categories,selected,palette,curves,bounds,cfg,destination/'figures'/name,method)
    write_json(destination/'kde_skipped.json',skipped)
