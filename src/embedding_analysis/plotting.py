"""System-neutral publication exports from saved coordinates and metric tables."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde

ROLE_COLORS = {'train':'#76B7B2', 'ood':'#E15759', 'shuffled':'#4E79A7', 'idr':'#B07AA1'}


def save(fig, stem, cfg):
    stem = Path(stem); stem.parent.mkdir(parents=True, exist_ok=True)
    for ext in cfg['plot']['formats']:
        fig.savefig(stem.with_suffix('.'+ext), dpi=cfg['plot']['dpi'], bbox_inches='tight')
    plt.close(fig)


def colors(labels, cfg):
    unique = sorted(set(labels))
    cmap = plt.get_cmap('tab20' if len(unique) <= 20 else 'hsv')
    return {v:cfg['class_colors'].get(v, cmap(i if len(unique) <= 20 else i / len(unique))) for i,v in enumerate(unique)}


def scatter(df, column, stem, cfg, title='', background_train=False):
    fig, ax = plt.subplots(figsize=(7,6))
    foreground = df
    if background_train:
        bg = df[df.dataset_role == 'train']
        ax.scatter(bg.x, bg.y, c='#cccccc', s=cfg['plot']['point_size'], alpha=.15, rasterized=True)
        foreground = df[df.dataset_role != 'train']
    palette = colors(foreground[column], cfg)
    for label, group in foreground.groupby(column, sort=True):
        ax.scatter(group.x, group.y, s=cfg['plot']['point_size'], color=palette[label], label=label, alpha=.6, rasterized=True)
    if len(palette) <= 25: ax.legend(markerscale=3, fontsize=8, frameon=False, loc='best')
    ax.set(title=title, xlabel='Dimension 1', ylabel='Dimension 2', aspect='equal')
    ax.set_xticks([]); ax.set_yticks([])
    save(fig, stem, cfg)


def density(df, stem, cfg):
    fig, ax = plt.subplots(figsize=(7,6))
    train = df[df.dataset_role == 'train']
    ax.hexbin(train.x, train.y, gridsize=65, mincnt=1, cmap='Greys', vmin=0, linewidths=0, rasterized=True)
    ax.scatter([], [], marker='h', color='#777777', label=cfg['role_labels']['train'])
    for role in ['ood','shuffled','idr']:
        group = df[df.dataset_role == role]
        ax.scatter(group.x, group.y, s=3, alpha=.4, color=ROLE_COLORS[role], label=cfg['role_labels'][role], rasterized=True)
        pts = group[['x','y']].to_numpy().T
        if len(group) >= 3 and np.linalg.matrix_rank(np.cov(pts)) == 2:
            kde = gaussian_kde(pts)
            threshold = np.percentile(kde(pts), 90)
            gx,gy = np.meshgrid(np.linspace(group.x.min(),group.x.max(),90),np.linspace(group.y.min(),group.y.max(),90))
            z = kde(np.vstack([gx.ravel(),gy.ravel()])).reshape(gx.shape)
            if z.min() < threshold < z.max(): ax.contour(gx,gy,z,levels=[threshold],colors=[ROLE_COLORS[role]],linewidths=1)
    ax.legend(markerscale=3, frameon=False)
    ax.set(title='OOD populations', aspect='equal'); ax.set_xticks([]); ax.set_yticks([])
    save(fig,stem,cfg)


def distributions(df, value, group, stem, cfg, title):
    valid = df[np.isfinite(df[value])]
    fig,ax = plt.subplots(figsize=(max(6,valid[group].nunique()*.6),4))
    groups=list(valid.groupby(group, sort=True))
    if groups:
        ax.boxplot([g[value].to_numpy() for _,g in groups], tick_labels=[str(k) for k,_ in groups], showfliers=False)
    else: ax.text(.5,.5,'No finite scores',ha='center',transform=ax.transAxes)
    ax.set(ylabel=value,title=title); ax.tick_params(axis='x',labelrotation=45)
    save(fig,stem,cfg)


def plot_experiment(path, experiment, cfg):
    path = Path(path)
    if experiment=='overview':
        df=pd.read_csv(path/'coordinates.csv',dtype={'sequence_id':str})
        scatter(df,'class_label',path/'figures/classes',cfg,'Training classes')
        scatter(df,'family_label',path/'figures/families',cfg,'Training families')
    elif experiment=='ood':
        density(pd.read_csv(path/'coordinates.csv'),path/'figures/density',cfg)
        distributions(pd.read_csv(path/'samples.csv'),'silhouette','dataset_role',path/'figures/silhouette',cfg,'OOD silhouette')
    elif experiment=='multilabel':
        df=pd.read_csv(path/'coordinates.csv')
        scatter(df,'class_label',path/'figures/classes',cfg,'Train + multi-class')
        for combo in cfg['plot']['highlight_combinations']:
            # Slugs avoid pipes and path separators in artifact names.
            parents=combo.split('|'); subset=df.copy()
            subset['selection']=np.where(subset.class_label.isin(parents+[combo]),subset.class_label,'background')
            scatter(subset,'selection',path/'figures'/('combo_'+'_'.join(parents)),cfg,combo)
        scores=pd.read_csv(path/'scores.csv')
        count=scores.groupby('class_label').size()
        scores=scores[scores.class_label.isin(count[count>=cfg['experiments']['multilabel']['min_combination_size']].index)]
        distributions(scores,'ba_score','class_label',path/'figures/ba',cfg,'Class barycentric alignment')
    elif experiment=='unseen':
        for p in sorted(path.glob('*/coordinates.csv')):
            scatter(pd.read_csv(p),'family_label',p.parent/'figures/families',cfg,p.parent.name,background_train=True)
        df=pd.read_csv(path/'families.csv')
        if len(df):
            for metric in ['silhouette_mean','dunn_cosine','legacy_pairwise_dbi']:
                distributions(df,metric,'class_label',path/'figures'/metric,cfg,'Unseen families')
    elif experiment=='structure':
        df=pd.read_csv(path/'metrics.csv')
        knn=df[df.metric=='knn_class_purity']
        fig,ax=plt.subplots(figsize=(6,4));ax.plot(knn.k,knn.value,marker='o')
        ax.set(xlabel='k',ylabel='Family centroid class purity',ylim=(0,1))
        save(fig,path/'figures/knn_class_purity',cfg)
        c=pd.read_csv(path/'centroids.csv');pc=[x for x in c if x.startswith('PC')]
        from scipy.spatial.distance import squareform,pdist
        order=c.sort_values(['class_label','family_label']).index
        D=squareform(pdist(c.loc[order,pc].to_numpy()))
        fig,ax=plt.subplots(figsize=(6,5));im=ax.imshow(D,cmap='viridis',rasterized=True);fig.colorbar(im,ax=ax,label='Euclidean distance')
        ax.set(title='Family centroid distances',xlabel='Families ordered by class',ylabel='Families ordered by class')
        save(fig,path/'figures/centroid_distances',cfg)
    else: raise ValueError(experiment)
