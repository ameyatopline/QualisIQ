"""Portable Isolation Forest inference from JSON arrays, without pickle execution."""
import json, math
from pathlib import Path
import numpy as np

FEATURES=['robust_z', 'absolute_robust_z']

def adjustment(n):
    if n<=1:return 0.
    if n==2:return 1.
    return 2*(math.log(n-1)+0.5772156649015329)-2*(n-1)/n

def vector(value,stats):
    z=(float(value)-stats['median'])/stats['scale']
    return [z,abs(z)]

def scores(rows,artifact):
    """Same path-length scoring as sklearn IsolationForest.score_samples (negated)."""
    x=np.asarray(rows,dtype=np.float32)
    paths=np.zeros(len(x))
    for tree in artifact['trees']:
        for i,row in enumerate(x):
            node=0;depth=0
            while tree['left'][node]!=-1:
                node=tree['left'][node] if row[tree['feature'][node]]<=tree['threshold'][node] else tree['right'][node]
                depth+=1
            paths[i]+=depth+adjustment(tree['n'][node])
    return np.power(2.,-paths/(len(artifact['trees'])*adjustment(artifact['max_samples'])))

def load(path):
    obj=json.loads(Path(path).read_text())
    if obj['schema_version']!=1 or obj['features']!=FEATURES:raise ValueError('Unsupported model artifact')
    return obj
