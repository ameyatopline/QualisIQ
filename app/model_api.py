"""Read-only model governance and scoped advisory inference."""
import hashlib,json,os
from pathlib import Path
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models as m
from app.security import get_current_user
from app.services import scoped_event
from ml.runtime import load,scores,vector
router=APIRouter(prefix='/api/v1/ml',tags=['Experimental model'])
def bundle(user):
    if os.getenv('APP_ENV','demo')!='demo':raise HTTPException(503,'Synthetic research model disabled outside demo mode')
    root=Path(os.getenv('MODEL_DIR',str(Path(__file__).resolve().parents[1]/'artifacts/qualisiq')))
    try:
        report=json.loads((root/'report.json').read_text());artifact=load(root/'model.json')
        if hashlib.sha256((root/'model.json').read_bytes()).hexdigest()!=report['artifact_sha256']:raise ValueError('Checksum mismatch')
    except (OSError,ValueError,KeyError):raise HTTPException(503,'Verified model artifact unavailable; run offline trainer')
    if artifact['tenant_id']!=user.tenant_id:raise HTTPException(404,'No model for this tenant')
    return report,artifact
@router.get('/report')
def report(user=Depends(get_current_user)):
    if user.site_id:raise HTTPException(403,'Global model metrics require global site access')
    return bundle(user)[0]
@router.get('/events/{event_id}/score')
def event_score(event_id:int,user=Depends(get_current_user),db:Session=Depends(get_db)):
    ev=scoped_event(db,event_id,user);r=db.get(m.TestResult,ev.result_id);report,artifact=bundle(user)
    stats=artifact['stats'].get(str(r.specification_id))
    if not stats:return {'status':'NOT_ASSESSED','reason':'Specification absent from training data'}
    features=vector(r.value,stats);score=float(scores([features],artifact)[0])
    return {'status':'ADVISORY_ONLY','version':report['version'],'anomaly_score':score,'threshold':artifact['threshold'],'flagged_for_review':score>=artifact['threshold'],'robust_z':features[0],'source_references':[f'test_result:{r.id}',f'specification:{r.specification_id}'],'synthetic':True,'warning':'Anomaly score is not a probability. Approved specification rules and human QA remain authoritative.'}
