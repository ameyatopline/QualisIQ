"""DON QualityOS API. All content and records seeded by this starter are synthetic/non-GMP."""
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app import models as m
from app.database import get_db, create_schema
from app.schemas import LoginIn, LabResultIn, TransitionIn, InvestigationUpdate, EvidenceIn, CAPAIn, CAPAUpdate
from app.security import create_token, verify_password, get_current_user, need_role, APP_ENV
from app.services import (ingest_result, scoped_event, event_view, transition,
                          tenant_audit, audit_integrity, utc_naive)

@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    from collections import OrderedDict
    app.state.login_attempts=OrderedDict()
    app.state.login_lock=asyncio.Lock()
    if APP_ENV == 'demo': create_schema()
    yield

app = FastAPI(title='QualisIQ / DON QualityOS',version='0.3.0',lifespan=lifespan,docs_url=None if APP_ENV=='production' else '/docs',redoc_url=None if APP_ENV=='production' else '/redoc',openapi_url=None if APP_ENV=='production' else '/openapi.json',
    description='SAP-inspired pharmaceutical QMS/LIMS prototype. SYNTHETIC DATA ONLY. NOT VALIDATED FOR GMP.')

def scoped_stmt(model, user):
    stmt=select(model).where(model.tenant_id==user.tenant_id)
    if user.site_id and hasattr(model,'site_id'):
        stmt=stmt.where(model.site_id==user.site_id)
    return stmt

def check_site_scope(site_id, user):
    if user.site_id and user.site_id!=site_id: raise HTTPException(403,'Site access denied')

@app.get('/health')
def health():
    return {'service':'DON QualityOS','status':'ok','environment':APP_ENV,'gmp_validated':False,'synthetic_demo':APP_ENV=='demo'}

@app.get('/ready')
def readiness(db:Session=Depends(get_db)):
    from sqlalchemy import text
    try:
        db.execute(text('SELECT 1'))
        db.execute(select(m.Tenant.id).limit(1))
    except Exception:
        raise HTTPException(503,'Database or schema unavailable')
    return {'status':'ready','environment':APP_ENV,'gmp_validated':False}

@app.post('/api/v1/auth/login')
def login(credentials: LoginIn, db: Session=Depends(get_db)):
    tenant=db.execute(select(m.Tenant).where(m.Tenant.code==credentials.tenant_code)).scalar_one_or_none()
    user=db.execute(select(m.User).where(m.User.tenant_id==tenant.id,
          m.User.email==credentials.email.lower())).scalar_one_or_none() if tenant else None
    if not user or not user.active or not verify_password(credentials.password,user.password_hash):
        raise HTTPException(401,'Invalid email, password or tenant')
    return {'access_token':create_token(user),'token_type':'bearer',
            'user':{'id':user.id,'role':user.role,'site_id':user.site_id,'tenant_id':user.tenant_id},
            'warning':'Demo authentication, not production SSO or Part 11 e-signature'}

@app.get('/api/v1/auth/me')
def me(user: m.User=Depends(get_current_user)):
    return {'id':user.id,'email':user.email,'role':user.role,'tenant_id':user.tenant_id,'site_id':user.site_id}

@app.get('/api/v1/master/sites')
def sites(user: m.User=Depends(get_current_user), db: Session=Depends(get_db)):
    stmt=scoped_stmt(m.Site,user)
    if user.site_id: stmt=stmt.where(m.Site.id==user.site_id)
    return [{'id':s.id,'code':s.code,'name':s.name,'region':s.region} for s in db.execute(stmt.order_by(m.Site.code)).scalars()]

@app.get('/api/v1/master/materials')
def materials(limit:int=Query(50,ge=1,le=100),offset:int=Query(0,ge=0),
              user: m.User=Depends(get_current_user),db:Session=Depends(get_db)):
    rows=db.execute(scoped_stmt(m.Material,user).order_by(m.Material.id).offset(offset).limit(limit)).scalars()
    return [{'id':r.id,'code':r.code,'description':r.description,'dosage_form':r.dosage_form} for r in rows]

@app.get('/api/v1/lab/inspection-lots')
def inspection_lots(limit:int=Query(30,ge=1,le=100),offset:int=Query(0,ge=0),
                    user:m.User=Depends(get_current_user),db:Session=Depends(get_db)):
    stmt=scoped_stmt(m.InspectionLot,user).join(m.Batch,m.Batch.id==m.InspectionLot.batch_id)
    if user.site_id: stmt=stmt.where(m.Batch.site_id==user.site_id)
    rows=db.execute(stmt.order_by(m.InspectionLot.id.desc()).offset(offset).limit(limit)).scalars()
    return [{'id':l.id,'lot_number':l.lot_number,'batch_id':l.batch_id,'status':l.status} for l in rows]

@app.post('/api/v1/lab/results',status_code=201)
def create_result(body:LabResultIn,user:m.User=Depends(need_role('qc_analyst','qc_manager','admin')),
                  db:Session=Depends(get_db)):
    data=ingest_result(db,user,body)
    db.commit()
    return data

@app.get('/api/v1/lab/results')
def results(limit:int=Query(30,ge=1,le=100),offset:int=Query(0,ge=0),
            outcome:str|None=None,user:m.User=Depends(get_current_user),db:Session=Depends(get_db)):
    stmt=scoped_stmt(m.TestResult,user)
    if outcome: stmt=stmt.where(m.TestResult.outcome==outcome)
    rows=db.execute(stmt.order_by(m.TestResult.id.desc()).offset(offset).limit(limit)).scalars()
    return [{'id':r.id,'site_id':r.site_id,'batch_id':r.batch_id,
             'test_name':r.test_name,'value':str(r.value),'unit':r.unit,
             'outcome':r.outcome,'source_system':r.source_system,
             'source_record_id':r.source_record_id,'specification_id':r.specification_id,
             'measured_at':r.measured_at.isoformat()+'Z'} for r in rows]

@app.get('/api/v1/quality/events')
def events(limit:int=Query(30,ge=1,le=100),offset:int=Query(0,ge=0),
           kind:str|None=None,state:str|None=None,
           user:m.User=Depends(get_current_user),db:Session=Depends(get_db)):
    stmt=scoped_stmt(m.QualityEvent,user)
    if kind: stmt=stmt.where(m.QualityEvent.kind==kind)
    if state: stmt=stmt.where(m.QualityEvent.status==state)
    return [event_view(db,r) for r in db.execute(stmt.order_by(m.QualityEvent.id.desc()).offset(offset).limit(limit)).scalars()]

@app.get('/api/v1/quality/events/{event_id}')
def event_detail(event_id:int,user:m.User=Depends(get_current_user),db:Session=Depends(get_db)):
    return event_view(db,scoped_event(db,event_id,user))

@app.patch('/api/v1/quality/events/{event_id}/investigation')
def update_investigation(event_id:int,body:InvestigationUpdate,
         user:m.User=Depends(need_role('qc_analyst','qc_manager','admin')),db:Session=Depends(get_db)):
    ev=scoped_event(db,event_id,user)
    if ev.status in ('APPROVED','CLOSED'):raise HTTPException(409,'Approved or closed investigation is immutable')
    if ev.version != body.expected_version:raise HTTPException(409,'Stale version')
    inv=db.execute(select(m.Investigation).where(m.Investigation.event_id==ev.id)).scalar_one()
    # Store prior values only in the audit stream, with no destructive overwriting of audit history.
    before={'summary':inv.summary,'root_cause_hypothesis':inv.root_cause_hypothesis,
            'impact_assessment':inv.impact_assessment,'capa_rationale':inv.capa_rationale}
    inv.summary=body.summary; inv.root_cause_hypothesis=body.root_cause_hypothesis
    inv.impact_assessment=body.impact_assessment; inv.capa_rationale=body.capa_rationale
    ev.version+=1
    tenant_audit(db,user.tenant_id,user.id,'INVESTIGATION_EDITED','quality_event',str(ev.id),
                 {'previous':before,'new':{'summary':inv.summary,'root_cause_hypothesis':inv.root_cause_hypothesis,
                    'impact_assessment':inv.impact_assessment,'capa_rationale':inv.capa_rationale}})
    db.commit()
    return event_view(db,ev)

@app.post('/api/v1/quality/events/{event_id}/transition')
def event_transition(event_id:int,body:TransitionIn,
       user:m.User=Depends(get_current_user),db:Session=Depends(get_db)):
    ev=scoped_event(db,event_id,user)
    view=transition(db,ev,user,body.target_status,body.reason,body.expected_version)
    db.commit()
    return view

@app.post('/api/v1/quality/events/{event_id}/evidence',status_code=201)
def attach_evidence(event_id:int,body:EvidenceIn,
       user:m.User=Depends(need_role('qc_analyst','qc_manager','qa_reviewer','qa_head','admin')),
       db:Session=Depends(get_db)):
    ev=scoped_event(db,event_id,user)
    if ev.status=='CLOSED': raise HTTPException(409,'Closed event cannot be modified')
    # Metadata only: external referenced objects must be verified and protected by document storage.
    e=m.Evidence(tenant_id=user.tenant_id,event_id=ev.id,kind=body.kind,label=body.label,
                 reference_uri=body.reference_uri,sha256=body.sha256,created_by=user.id)
    db.add(e);db.flush()
    tenant_audit(db,user.tenant_id,user.id,'EVIDENCE_LINKED','evidence',str(e.id),
                 {'event_id':ev.id,'sha256':body.sha256,'reference_uri':body.reference_uri})
    db.commit()
    return {'id':e.id,'event_id':ev.id,'sha256':e.sha256,
            'warning':'External content authenticity not verified by this prototype'}

@app.post('/api/v1/quality/events/{event_id}/capa',status_code=201)
def create_capa(event_id:int,body:CAPAIn,
       user:m.User=Depends(need_role('qc_manager','qa_reviewer','qa_head','admin')),
       db:Session=Depends(get_db)):
    ev=scoped_event(db,event_id,user)
    assigned=db.get(m.User,body.assigned_to_id)
    if not assigned or assigned.tenant_id!=user.tenant_id or (assigned.site_id and assigned.site_id!=ev.site_id):
        raise HTTPException(422,'Assignee must be authorized for site and tenant')
    capa=m.CAPA(tenant_id=user.tenant_id,event_id=ev.id,title=body.title,
                assigned_to_id=assigned.id,due_at=utc_naive(body.due_at))
    db.add(capa);db.flush()
    tenant_audit(db,user.tenant_id,user.id,'CAPA_CREATED','capa',str(capa.id),
                 {'event_id':ev.id,'title':body.title,'assigned_to':assigned.id})
    db.commit()
    return {'id':capa.id,'status':capa.status}

@app.post('/api/v1/quality/capa/{capa_id}/update')
def update_capa(capa_id:int,body:CAPAUpdate,
       user:m.User=Depends(get_current_user),db:Session=Depends(get_db)):
    capa=db.get(m.CAPA,capa_id)
    if not capa or capa.tenant_id!=user.tenant_id:raise HTTPException(404,'CAPA not found')
    ev=scoped_event(db,capa.event_id,user)
    if user.role not in {'qc_manager','qa_reviewer','qa_head','admin'} and user.id!=capa.assigned_to_id:
        raise HTTPException(403,'CAPA update requires assigned owner or reviewer')
    if body.status not in {'IN_PROGRESS','EFFECTIVENESS_PENDING','VERIFIED','CANCELLED'}:
        raise HTTPException(422,'Invalid CAPA status')
    if body.status=='VERIFIED':
        if user.role not in {'qa_reviewer','qa_head','admin'}:
            raise HTTPException(403,'Independent QA reviewer required for CAPA effectiveness verification')
        if user.id==capa.assigned_to_id:
            raise HTTPException(403,'CAPA owner cannot verify own effectiveness')
        if capa.status!='EFFECTIVENESS_PENDING':
            raise HTTPException(409,'CAPA must reach EFFECTIVENESS_PENDING before VERIFIED')
    if body.status=='EFFECTIVENESS_PENDING' and capa.status!='IN_PROGRESS':
        raise HTTPException(409,'CAPA must be IN_PROGRESS before effectiveness review')
    if body.status=='IN_PROGRESS' and capa.status!='OPEN':
        raise HTTPException(409,'CAPA can enter IN_PROGRESS only from OPEN')
    if body.status=='CANCELLED' and user.role not in {'qa_reviewer','qa_head','admin'}:
        raise HTTPException(403,'QA must authorize cancelling CAPA')
    if capa.status in {'VERIFIED','CANCELLED'}:
        raise HTTPException(409,'Terminal CAPA is immutable')
    prev=capa.status;capa.status=body.status;capa.effectiveness_note=body.effectiveness_note
    tenant_audit(db,user.tenant_id,user.id,'CAPA_UPDATED','capa',str(capa.id),
                 {'from':prev,'to':body.status,'note':body.effectiveness_note})
    db.commit()
    return {'id':capa.id,'status':capa.status}

@app.get('/api/v1/quality/events/{event_id}/ai-brief')
def ai_brief(event_id:int,user:m.User=Depends(get_current_user),db:Session=Depends(get_db)):
    ev=scoped_event(db,event_id,user)
    result=db.get(m.TestResult,ev.result_id)
    spec=db.get(m.Specification,result.specification_id)
    reference=[f'test_result:{result.id}',f'specification:{spec.id}',f'quality_event:{ev.id}']
    evidence=db.execute(select(m.Evidence).where(m.Evidence.event_id==ev.id).limit(20)).scalars().all()
    reference += [f'evidence:{e.id}' for e in evidence]
    controls=(['Confirm raw chromatogram/instrument audit trail', 'Review calculations and system suitability',
               'Verify sample preparation, standards and instrument calibration'] if ev.kind=='OOS'
               else ['Review approved OOT baseline and statistical method','Compare historical product/site trends',
                     'Check stability timepoint and analytical method changes'])
    return {'model':'DETERMINISTIC_EVIDENCE_ASSISTANT_V0','generated_by_llm':False,
            'summary':f'{ev.kind} result {result.value} {result.unit}, specification version {spec.version}.',
            'hypotheses_not_conclusions':controls,
            'source_references':reference,
            'public_methodology_references':(['FDA-OOS-2022','FDA-21CFR-211192','MHRA-GXP-DI']
                 if ev.kind=='OOS' else ['FDA-ICH-Q9-R1','MHRA-GXP-DI']),
            'next_step':'Human QC investigation; independent QA decision required.',
            'disclaimer':'NOT AI-determined root cause. Does not invalidate results, direct retesting, or release a batch.'}

@app.get('/api/v1/knowledge/sources')
def knowledge_sources(kind:str|None=None,user:m.User=Depends(get_current_user),
                      db:Session=Depends(get_db)):
    """Curated public metadata: not original commercial or regulatory document content."""
    stmt=select(m.KnowledgeReference)
    if kind: stmt=stmt.where(m.KnowledgeReference.kind==kind)
    return [{'reference_code':r.reference_code,'kind':r.kind,'publisher':r.publisher,
             'title':r.title,'url':r.url,'scope':r.scope,
             'imported_content':r.imported_content} for r in db.execute(
                stmt.order_by(m.KnowledgeReference.reference_code)).scalars()]

@app.get('/api/v1/analytics/overview')
def overview(user:m.User=Depends(get_current_user),db:Session=Depends(get_db)):
    """Database-side aggregates: no full-table materialization at enterprise scale."""
    result_stmt=select(m.TestResult.outcome,func.count(m.TestResult.id)).where(
        m.TestResult.tenant_id==user.tenant_id)
    event_stmt=select(m.QualityEvent.kind,m.QualityEvent.status,func.count(m.QualityEvent.id)).where(
        m.QualityEvent.tenant_id==user.tenant_id)
    if user.site_id:
        result_stmt=result_stmt.where(m.TestResult.site_id==user.site_id)
        event_stmt=event_stmt.where(m.QualityEvent.site_id==user.site_id)
    by_result=dict(db.execute(result_stmt.group_by(m.TestResult.outcome)).all())
    by_event=db.execute(event_stmt.group_by(m.QualityEvent.kind,m.QualityEvent.status)).all()
    return {'tenant_id':user.tenant_id,'site_id':user.site_id,'demo_only':True,
            'total_results':sum(by_result.values()),'oos_results':by_result.get('OOS',0),
            'oot_results':by_result.get('OOT',0),
            'quality_events':sum(c for _,_,c in by_event),
            'open_events':sum(c for _,state,c in by_event if state!='CLOSED'),
            'by_result':by_result,'by_event':[{'kind':kind,'status':state,'count':count}
                                            for kind,state,count in by_event]}

@app.post('/api/v1/lab/results/bulk',status_code=201)
def bulk_result_ingest(rows:list[LabResultIn],
                       user:m.User=Depends(need_role('qc_analyst','qc_manager','admin')),
                       db:Session=Depends(get_db)):
    """Small atomic ingestion batches; integration workers should chunk larger jobs."""
    if not rows or len(rows)>250:
        raise HTTPException(422,'Bulk import requires 1 to 250 records')
    try:
        outputs=[ingest_result(db,user,body) for body in rows]
        db.commit()
        return {'count':len(outputs),'outcomes':outputs,'atomic':True}
    except Exception:
        db.rollback()
        raise

@app.get('/api/v1/audit/verify')
def audit_verify(user:m.User=Depends(need_role('auditor','qa_head','admin')),
                 db:Session=Depends(get_db)):
    if user.site_id: raise HTTPException(403,'Tenant-global audit access requires global site authorization')
    return audit_integrity(db,user.tenant_id)

@app.get('/api/v1/audit/events')
def audit_events(limit:int=Query(50,ge=1,le=100), offset:int=Query(0,ge=0),
      user:m.User=Depends(need_role('auditor','qa_head','admin')),
      db:Session=Depends(get_db)):
    if user.site_id: raise HTTPException(403,'Tenant-global audit access requires global site authorization')
    stmt=select(m.AuditLog).where(m.AuditLog.tenant_id==user.tenant_id)
    rows=db.execute(stmt.order_by(m.AuditLog.sequence.desc()).offset(offset).limit(limit)).scalars()
    return [{'sequence':r.sequence,'action':r.action,'resource_type':r.resource_type,
             'resource_id':r.resource_id,'actor_id':r.actor_id,'happened_at':r.happened_at.isoformat()+'Z',
             'hash':r.event_hash} for r in rows]

@app.get('/api/v1/integrations/outbox')
def integration_outbox(limit:int=Query(30,ge=1,le=100),
         user:m.User=Depends(need_role('admin')),
         db:Session=Depends(get_db)):
    if user.site_id: raise HTTPException(403,'Tenant-global outbox access requires global site authorization')
    stmt=select(m.OutboxEvent).where(m.OutboxEvent.tenant_id==user.tenant_id).order_by(m.OutboxEvent.id.desc()).limit(limit)
    return [{'id':e.id,'event_type':e.event_type,'payload':e.payload_json,
             'status':e.delivery_status} for e in db.execute(stmt).scalars()]

# Same-origin website is mounted after all specific API routes.
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from app.workbench import router as workbench_router
from app.model_api import router as model_router
from app.http_controls import HTTPControls
import os
app.include_router(workbench_router)
app.include_router(model_router)
app.add_middleware(HTTPControls)
app.add_middleware(TrustedHostMiddleware,allowed_hosts=os.getenv('ALLOWED_HOSTS','localhost,127.0.0.1,testserver').split(','))
web_dist=Path(__file__).resolve().parents[1]/'frontend'/'dist'
if web_dist.is_dir():app.mount('/',StaticFiles(directory=web_dist,html=True),name='workbench')
