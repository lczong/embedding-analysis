"""Shared workflows, parameterized exclusively by config and dataset roles."""
from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd
from .artifacts import output_dir, ready, complete, write_json
from .data import Embedding, load_embedding, read_metadata
from .reduction import fit_pca, reduce_2d
from .sampling import ood_manifest, select_families
from .metrics import target_silhouette, class_ba, family_centroids, centroid_structure, family_quality
from .plotting import plot_experiment

REQUIRED = {'overview':{'train'},'ood':{'train','ood','shuffled','idr'},'multilabel':{'train','multi'},'unseen':{'train','unseen'},'structure':{'train'}}


def prepare(cfg, route, run_id, payload, force=False):
    path=output_dir(cfg,route,'preprocess',run_id)
    if not force and ready(path): return path
    (path/'manifest.json').unlink(missing_ok=True)
    datasets=cfg['routes'][route]['datasets']
    train=load_embedding(cfg,datasets['train'])
    train_ids=set(train.ids)
    pipe,X=fit_pca(train.values,cfg['preprocessing']['n_components'],cfg['seed'])
    joblib.dump(pipe,path/'pca_model.joblib')
    np.savez(path/'train.npz',ids=train.ids,values=X)
    read_metadata(cfg,'train',train.ids).to_csv(path/'train.metadata.csv',index=False)
    expected=train.values.shape[1]
    del train,X
    for role,spec in datasets.items():
        if role=='train': continue
        data=load_embedding(cfg,spec)
        if data.values.shape[1] != expected: raise ValueError(f'{route}/{role}: incompatible feature dimension')
        if role in ['unseen','multi'] and train_ids.intersection(data.ids):
            raise ValueError(f'{role} overlaps train sequence IDs')
        projected=pipe.transform(data.values).astype(np.float32)
        np.savez(path/f'{role}.npz',ids=data.ids,values=projected)
        if role in cfg['metadata']['files']:
            read_metadata(cfg,role,data.ids).to_csv(path/f'{role}.metadata.csv',index=False)
    evr=pipe.named_steps['pca'].explained_variance_ratio_
    pd.DataFrame({'component':np.arange(1,len(evr)+1),'explained_variance':evr,'cumulative':evr.cumsum()}).to_csv(path/'explained_variance.csv',index=False)
    complete(path,{**payload,'route':route,'experiment':'preprocess','fit_on':'train'})
    return path


def load_prepared(path,role):
    with np.load(path/f'{role}.npz',allow_pickle=False) as z:
        data=Embedding(z['ids'],z['values'])
    p=path/f'{role}.metadata.csv'
    meta=pd.read_csv(p,dtype=str) if p.exists() else pd.DataFrame({'sequence_id':data.ids,'dataset_role':role})
    if meta.sequence_id.tolist()!=data.ids.tolist(): raise ValueError('Prepared metadata order mismatch')
    return data,meta


def coordinates(cfg,X,meta,method,path):
    xy=reduce_2d(X,method,cfg['reduction'][method],cfg['seed'])
    out=meta.reset_index(drop=True).copy();out['x']=xy[:,0];out['y']=xy[:,1]
    out.to_csv(path/'coordinates.csv',index=False)


def compute(cfg,route,experiment,prepared,path,run_id):
    settings=cfg['experiments'][experiment]
    train,mt=load_prepared(prepared,'train')
    if experiment=='overview':
        coordinates(cfg,train.values,mt,settings['method'],path)
    elif experiment=='ood':
        manifest=ood_manifest(cfg,run_id)
        write_json(path/'sampling.json',manifest)
        matrices=[train.values];metas=[mt[['sequence_id','dataset_role']]];samples=[]
        for role in ['ood','shuffled','idr']:
            target,_=load_prepared(prepared,role);target=target.take(manifest[role]['ids'])
            scores=target_silhouette(target.values,train.values,settings['distance'],settings['chunk_size'])
            samples.append(pd.DataFrame({'sequence_id':target.ids,'dataset_role':role,'silhouette':scores}))
            matrices.append(target.values);metas.append(pd.DataFrame({'sequence_id':target.ids,'dataset_role':role}))
        frame=pd.concat(samples,ignore_index=True);frame.to_csv(path/'samples.csv',index=False)
        frame.groupby('dataset_role').silhouette.agg(['count','mean','median','std','min','max']).reset_index().to_csv(path/'summary.csv',index=False)
        coordinates(cfg,np.vstack(matrices),pd.concat(metas),settings['method'],path)
    elif experiment=='multilabel':
        multi,mm=load_prepared(prepared,'multi')
        scores=class_ba(train.values,mt.class_label.to_numpy(),multi.values,mm.class_label.to_numpy())
        scores.insert(0,'sequence_id',multi.ids);scores.to_csv(path/'scores.csv',index=False)
        scores.groupby('class_label').ba_score.describe().reset_index().to_csv(path/'summary.csv',index=False)
        coordinates(cfg,np.vstack([train.values,multi.values]),pd.concat([mt,mm]),settings['method'],path)
    elif experiment=='structure':
        C,meta=family_centroids(train.values,mt,settings['min_family_size'])
        centroid_structure(C,meta.class_label.to_numpy(),settings['ks']).to_csv(path/'metrics.csv',index=False)
        pd.concat([meta,pd.DataFrame(C,columns=[f'PC{i+1}' for i in range(C.shape[1])])],axis=1).to_csv(path/'centroids.csv',index=False)
    elif experiment=='unseen':
        query,mq=load_prepared(prepared,'unseen')
        pcs=settings['n_pcs']
        if pcs>train.values.shape[1]: raise ValueError('Unseen n_pcs exceeds fitted PCA dimensions')
        family_tables=[];global_rows=[];selection={};skipped=[]
        for cls in cfg['classes']:
            t=mt[mt.class_label==cls];q=mq[mq.class_label==cls]
            tc=t.family_label.value_counts();qc=q.family_label.value_counts()
            candidates=tc[tc>=settings['min_family_size']].index.tolist()
            targets=qc[qc>=settings['min_family_size']].index.tolist()
            if not candidates or not targets:
                skipped.append({'class':cls,'reason':'no eligible train or unseen families'});continue
            chosen=select_families(candidates,settings['train_family_count'],cfg['seed'],cls)
            ti=t[t.family_label.isin(chosen)].index.to_numpy();qi=q[q.family_label.isin(targets)].index.to_numpy()
            meta=pd.concat([mt.loc[ti],mq.loc[qi]],ignore_index=True)
            if set(chosen).intersection(targets): raise ValueError('Unseen family appears in train')
            X=np.vstack([train.values[ti,:pcs],query.values[qi,:pcs]])
            fam,glob=family_quality(X,meta.family_label.to_numpy(),settings['chunk_size'])
            out=path/cls;out.mkdir(exist_ok=True)
            fam.to_csv(out/'joint_families.csv',index=False)
            unseen=fam[fam.family_label.isin(targets)].copy();unseen.insert(0,'class_label',cls)
            family_tables.append(unseen);global_rows.append({'class_label':cls,'context':'joint_unseen_and_sampled_train',**glob})
            if len(chosen)>=2:
                tf,tg=family_quality(train.values[ti,:pcs],mt.loc[ti,'family_label'].to_numpy(),settings['chunk_size'])
                tf.to_csv(out/'train_sample_families.csv',index=False)
                global_rows.append({'class_label':cls,'context':'sampled_train_only',**tg})
            selection[cls]={'train_families':chosen,'unseen_families':targets,'train_count':len(ti),'unseen_count':len(qi)}
            # Visualization uses all class train proteins, matching the legacy background.
            all_t=t.index.to_numpy()
            coordinates(cfg,np.vstack([train.values[all_t,:pcs],query.values[qi,:pcs]]),pd.concat([mt.loc[all_t],mq.loc[qi]]),settings['method'],out)
        pd.concat(family_tables,ignore_index=True).to_csv(path/'families.csv',index=False) if family_tables else pd.DataFrame(columns=['class_label','family_label']).to_csv(path/'families.csv',index=False)
        pd.DataFrame(global_rows,columns=None if global_rows else ['class_label','context']).to_csv(path/'global.csv',index=False)
        write_json(path/'reference_families.json',selection);write_json(path/'skipped_classes.json',skipped)


def run_experiment(cfg,route,experiment,run_id,payload,force=False,plot=True):
    missing=REQUIRED[experiment]-cfg['routes'][route]['datasets'].keys()
    if missing: raise ValueError(f'{route}/{experiment} missing inputs: {sorted(missing)}')
    prepared=prepare(cfg,route,run_id,payload,force=False)
    path=output_dir(cfg,route,experiment,run_id)
    if force or not ready(path):
        (path/'manifest.json').unlink(missing_ok=True)
        compute(cfg,route,experiment,prepared,path,run_id)
        complete(path,{**payload,'route':route,'experiment':experiment})
    if plot: plot_experiment(path,experiment,cfg)
    return path
