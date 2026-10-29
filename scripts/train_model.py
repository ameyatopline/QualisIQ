"""Reproducible per-tenant, batch-disjoint anomaly evaluation. No clinical accuracy claim."""
import argparse, hashlib, json, sys
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import average_precision_score, roc_auc_score, confusion_matrix
from sqlalchemy import select
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.database import SessionLocal
from app import models as m
from ml.runtime import FEATURES, vector, scores

def evaluate(labels,score,threshold):
    pred=np.asarray(score)>=threshold
    tn,fp,fn,tp=confusion_matrix(labels,pred,labels=[0,1]).ravel()
    return {'rows':len(labels),'positives':int(sum(labels)),'threshold':float(threshold),
            'roc_auc':float(roc_auc_score(labels,score)) if len(set(labels))==2 else None,
            'average_precision':float(average_precision_score(labels,score)) if sum(labels) else None,
            'precision':float(tp/(tp+fp)) if tp+fp else 0.,'recall':float(tp/(tp+fn)) if tp+fn else 0.,
            'false_positive_rate':float(fp/(fp+tn)) if fp+tn else 0.,
            'confusion_matrix':{'tn':int(tn),'fp':int(fp),'fn':int(fn),'tp':int(tp)}}

def train(tenant_code,output):
    with SessionLocal() as db:
        tenant=db.scalar(select(m.Tenant).where(m.Tenant.code==tenant_code))
        if not tenant:raise ValueError('Unknown tenant')
        if not tenant.synthetic:raise ValueError('This research trainer accepts synthetic tenants only')
        rows=db.execute(select(m.TestResult.id,m.TestResult.batch_id,m.TestResult.specification_id,m.TestResult.value,m.TestResult.outcome,m.TestResult.measured_at,m.TestResult.source_hash,m.Batch.manufactured_at).join(m.Batch,m.TestResult.batch_id==m.Batch.id).where(m.TestResult.tenant_id==tenant.id).order_by(m.TestResult.id)).all()
        if len(rows)<500:raise ValueError('At least 500 synthetic results required')
        batches=sorted({(r.manufactured_at,r.batch_id) for r in rows})
        a=int(len(batches)*.6);b=int(len(batches)*.8)
        train_ids={i for _,i in batches[:a]};cal_ids={i for _,i in batches[a:b]};test_ids={i for _,i in batches[b:]}
        partitions=[[r for r in rows if r.batch_id in ids] for ids in (train_ids,cal_ids,test_ids)]
        stats={}
        for sid in {r.specification_id for r in partitions[0]}:
            values=np.asarray([float(r.value) for r in partitions[0] if r.specification_id==sid])
            median=float(np.median(values));mad=float(np.median(abs(values-median)))
            if len(values)>=30 and mad>1e-12:stats[str(sid)]={'median':median,'scale':1.4826*mad,'n':len(values)}
        usable=[[r for r in part if str(r.specification_id) in stats] for part in partitions]
        if any(not part for part in usable):raise ValueError('Every split needs rows with sufficiently supported training specifications')
        matrices=[np.asarray([vector(r.value,stats[str(r.specification_id)]) for r in part],dtype=np.float32) for part in usable]
        forest=IsolationForest(n_estimators=120,max_samples=256,random_state=20261030,n_jobs=2).fit(matrices[0])
        artifact={'schema_version':1,'features':FEATURES,'tenant_id':tenant.id,'tenant_code':tenant.code,'synthetic':True,'max_samples':int(forest.max_samples_),'stats':stats,'trees':[]}
        for estimator in forest.estimators_:
            t=estimator.tree_;artifact['trees'].append({'feature':t.feature.tolist(),'threshold':t.threshold.tolist(),'left':t.children_left.tolist(),'right':t.children_right.tolist(),'n':t.n_node_samples.tolist()})
        # Calibration uses no outcome labels. 1% alert budget, not a validated clinical threshold.
        cal=-forest.score_samples(matrices[1]);test=-forest.score_samples(matrices[2]);threshold=float(np.quantile(cal,.99))
        artifact['threshold']=threshold
        labels=np.asarray([int(r.outcome in ('OOS','OOT')) for r in usable[2]])
        parity=float(np.max(abs(scores(matrices[2][:200],artifact)-test[:200])))
        if parity>1e-10:raise ValueError(f'Portable scorer mismatch {parity}')
        fingerprint=hashlib.sha256(json.dumps([[r.id,r.batch_id,r.specification_id,str(r.value),r.outcome,r.measured_at.isoformat(),r.source_hash,r.manufactured_at.isoformat()] for r in rows],separators=(',',':')).encode()).hexdigest()
        version='iforest-'+fingerprint[:12]
        artifact['version']=version
        report={'version':version,'created_at':datetime.now(timezone.utc).isoformat(),'synthetic':True,'intended_use':'Research triage only; never a specification, OOT, root-cause or release decision','algorithm':'IsolationForest / 120 trees / deterministic seed 20261030','features':FEATURES,'forbidden_features':['outcome','alert','quality_event','source identifiers'],'normalization':'Training-only median and MAD per specification; unseen specifications abstain','split':'60/20/20 batches ordered by manufacture timestamp then batch ID; disjoint batch IDs, not a strict temporal result holdout','split_batches':{'train':len(train_ids),'calibration':len(cal_ids),'test':len(test_ids)},'split_rows':dict(zip(['train','calibration','test'],map(len,usable))),'excluded_unknown_spec_rows':len(rows)-sum(map(len,usable)),'dataset_sha256':fingerprint,'evaluation_label':'Seeded rule-based OOS/OOT outcome, a proxy label; not independent expert ground truth','metrics':evaluate(labels,test,threshold),'baseline':evaluate(labels,abs(matrices[2][:,0]),float(np.quantile(abs(matrices[1][:,0]),.99))),'portable_scorer_max_error':parity,'limitations':['Synthetic data only; no real-world effectiveness established','Outcomes are seeded rules; this benchmark cannot validate clinical suitability','Two correlated univariate features; not a multivariate instrument model','Manufacture-date split can overlap result measurement dates','No external validation, drift SLA, product approval, or independent qualification','Model is tenant-global: site-restricted users cannot inspect global metrics']}
        report['operating_points']=[{'calibration_alert_budget':budget,**evaluate(labels,test,float(np.quantile(cal,1-budget)))} for budget in (.01,.03,.05)]
        from importlib.metadata import version as package_version
        report['library_versions']={name:package_version(name) for name in ('scikit-learn','numpy','scipy')}
        report['training_code_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        report['split_batch_sha256']={name:hashlib.sha256(json.dumps(sorted(ids)).encode()).hexdigest() for name,ids in zip(('train','calibration','test'),(train_ids,cal_ids,test_ids))}
        report['deployment_eligible']=False
        report['baseline_advantage_demonstrated']=False
        output=Path(output);output.mkdir(parents=True,exist_ok=True)
        (output/'model.json').write_text(json.dumps(artifact,separators=(',',':')))
        report['artifact_sha256']=hashlib.sha256((output/'model.json').read_bytes()).hexdigest()
        (output/'report.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--tenant',default='DON-DEMO');p.add_argument('--output',default='artifacts/qualisiq');a=p.parse_args();train(a.tenant,a.output)
