"""Binary train overview: joint PCA, separate two-dimensional reduction."""
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from ...data import load_embedding
from ...reduction import fit_pca
from ...prepared import coordinates

def prepare(cfg, route, destination):
    datasets=cfg['routes'][route]['datasets']
    groups=[load_embedding(cfg,datasets[role]) for role in ['train','non_target_train']]
    if set(groups[0].ids)&set(groups[1].ids):
        raise ValueError('Target and non-target train IDs overlap')
    X=np.concatenate([g.values for g in groups])
    if X.shape[1]!=cfg['routes'][route]['dimensions']:raise ValueError('Feature dimension mismatch')
    pipe,values=fit_pca(X,cfg['preprocessing']['n_components'],cfg['seed'])
    joblib.dump(pipe,destination/'pca_model.joblib')
    np.savez(destination/'joint.npz',values=values)
    pd.concat([pd.DataFrame({'sequence_id':g.ids,'dataset_role':role}) for g,role in zip(groups,['train','non_target_train'])],ignore_index=True).to_csv(destination/'metadata.csv',index=False)
    evr=pipe.named_steps['pca'].explained_variance_ratio_
    pd.DataFrame({'component':np.arange(1,len(evr)+1),'explained_variance':evr,'cumulative':evr.cumsum()}).to_csv(destination/'explained_variance.csv',index=False)

def compute_coordinates(cfg, source, destination, method):
    with np.load(source/'joint.npz',allow_pickle=False) as z:values=z['values']
    meta=pd.read_csv(source/'metadata.csv',dtype=str)
    if len(meta)!=len(values):raise ValueError('PCA metadata row mismatch')
    coordinates(cfg,values,meta,method,destination)
