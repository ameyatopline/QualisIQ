"""Transaction and state-machine services; non-GMP demonstration implementation."""
import hashlib, json, secrets
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app import models as m
from app.schemas import LabResultIn

def utc_naive(dt: datetime) -> datetime:
    if dt.tzinfo is None: raise HTTPException(422, 'measured_at / due_at must include timezone')
    return dt.astimezone(timezone.utc).replace(tzinfo=None)

def canonical(obj) -> str:
    return json.dumps(obj, ensure_ascii=True, sort_keys=True, separators=(',',':'))

def sha(obj) -> str:
    return hashlib.sha256(canonical(obj).encode()).hexdigest()

def tenant_audit(db: Session, tenant_id: int, actor_id: int | None, action: str,
                 resource_type: str, resource_id: str, data: dict):
    """Tenant-scoped hash chain; head row locked on PostgreSQL. See docs/security_limits.md."""
    head = db.execute(select(m.AuditHead).where(m.AuditHead.tenant_id == tenant_id).with_for_update()).scalar_one_or_none()
    if not head:
        head = m.AuditHead(tenant_id=tenant_id, sequence=0, last_hash='0'*64)
        db.add(head)
        db.flush()
    n = head.sequence + 1
    ts = datetime.now(timezone.utc).replace(tzinfo=None)
    body = dict(sequence=n, actor_id=actor_id, action=action, resource_type=resource_type,
                resource_id=resource_id, data=data, ts=ts.isoformat()+'Z')
    prev = head.last_hash
    digest = hashlib.sha256((prev + canonical(body)).encode()).hexdigest()
    db.add(m.AuditLog(tenant_id=tenant_id, sequence=n, actor_id=actor_id, action=action,
                      resource_type=resource_type, resource_id=resource_id,
                      data_json={'data':data, 'ts':body['ts']}, happened_at=ts,
                      prev_hash=prev, event_hash=digest))
    head.last_hash = digest
    head.sequence = n

def audit_integrity(db: Session, tenant_id: int) -> dict:
    rows = db.execute(select(m.AuditLog).where(m.AuditLog.tenant_id == tenant_id).order_by(m.AuditLog.sequence)).scalars().all()
    prev='0'*64
    for i, r in enumerate(rows,1):
        body = dict(sequence=r.sequence, actor_id=r.actor_id, action=r.action,
                    resource_type=r.resource_type, resource_id=r.resource_id,
                    data=r.data_json['data'], ts=r.data_json['ts'])
        digest = hashlib.sha256((prev + canonical(body)).encode()).hexdigest()
        if r.sequence!=i or r.prev_hash!=prev or r.event_hash!=digest:
            return {'integrity':'FAILED', 'first_bad_sequence':r.sequence, 'checked':i}
        prev=digest
    head=db.get(m.AuditHead, tenant_id)
    if head and (head.last_hash!=prev or head.sequence!=len(rows)):
        return {'integrity':'FAILED', 'first_bad_sequence':'HEAD','checked':len(rows)}
    return {'integrity':'VALID_DEMO_CHAIN', 'checked':len(rows), 'last_hash':prev,
            'warning':'Hash chains do not replace independent WORM storage, audit controls or system validation.'}

def scoped_event(db: Session, event_id: int, user: m.User) -> m.QualityEvent:
    ev=db.get(m.QualityEvent,event_id)
    if not ev or ev.tenant_id != user.tenant_id or (user.site_id and ev.site_id!=user.site_id):
        raise HTTPException(404, 'Quality event not found')
    return ev

def event_view(db: Session, ev: m.QualityEvent) -> dict:
    result=db.get(m.TestResult,ev.result_id)
    alert=db.get(m.Alert,ev.alert_id)
    inv=db.execute(select(m.Investigation).where(m.Investigation.event_id==ev.id)).scalar_one_or_none()
    spec=db.get(m.Specification,result.specification_id)
    return {'id':ev.id,'event_number':ev.event_number,'kind':ev.kind,'status':ev.status,
            'site_id':ev.site_id,'version':ev.version,'investigator_id':ev.investigator_id,
            'result_id':result.id,'result_value':str(result.value),'unit':result.unit,
            'test_name':result.test_name,'result_outcome':result.outcome,
            'specification_version':spec.version,'approved_limits':
              {'min':str(spec.lower_limit) if spec.lower_limit is not None else None,
               'max':str(spec.upper_limit) if spec.upper_limit is not None else None},
            'alert_reason':alert.explanation,
            'investigation': {'summary':inv.summary,'root_cause_hypothesis':inv.root_cause_hypothesis,
                              'impact_assessment':inv.impact_assessment,'capa_rationale':inv.capa_rationale,
                              'approved_by':inv.approved_by} if inv else None,
            'evidence_count':db.query(m.Evidence).filter_by(event_id=ev.id).count(),
            'capa_count':db.query(m.CAPA).filter_by(event_id=ev.id).count(),
            'synthetic':True}

def ingest_result(db: Session, user: m.User, incoming: LabResultIn) -> dict:
    payload=incoming.model_dump(mode='json')
    content={k:v for k,v in payload.items() if k != 'idempotency_key'}
    fingerprint=sha(content)
    existing_receipt=db.execute(select(m.IntegrationReceipt).where(
        m.IntegrationReceipt.tenant_id==user.tenant_id,
        m.IntegrationReceipt.source_system==incoming.source_system,
        m.IntegrationReceipt.idempotency_key==incoming.idempotency_key)).scalar_one_or_none()
    if existing_receipt:
        if existing_receipt.request_hash != fingerprint:
            raise HTTPException(409,'Idempotency key reused with different payload')
        result=db.get(m.TestResult,existing_receipt.result_id)
        return {'result_id':result.id,'outcome':result.outcome,'replayed':True,
                'event_id':db.execute(select(m.QualityEvent.id).where(m.QualityEvent.result_id==result.id)).scalar_one_or_none()}
    conflict=db.execute(select(m.TestResult).where(m.TestResult.tenant_id==user.tenant_id,
        m.TestResult.source_system==incoming.source_system,
        m.TestResult.source_record_id==incoming.source_record_id)).scalar_one_or_none()
    if conflict:
        if conflict.source_hash != fingerprint:
            raise HTTPException(409,'Immutable source record ID already used with different data')
        db.add(m.IntegrationReceipt(tenant_id=user.tenant_id,source_system=incoming.source_system,
            idempotency_key=incoming.idempotency_key,request_hash=fingerprint,result_id=conflict.id))
        db.flush()
        return {'result_id':conflict.id,'outcome':conflict.outcome,'replayed':True,
                'event_id':db.execute(select(m.QualityEvent.id).where(m.QualityEvent.result_id==conflict.id)).scalar_one_or_none()}
    site=db.execute(select(m.Site).where(m.Site.tenant_id==user.tenant_id,m.Site.code==incoming.site_code)).scalar_one_or_none()
    mat=db.execute(select(m.Material).where(m.Material.tenant_id==user.tenant_id,m.Material.code==incoming.material_code)).scalar_one_or_none()
    if not site or not mat: raise HTTPException(422,'Site or material not in tenant master data')
    if user.site_id and site.id != user.site_id: raise HTTPException(403,'Cross-site ingestion forbidden')
    batch=db.execute(select(m.Batch).where(m.Batch.tenant_id==user.tenant_id,
                                m.Batch.batch_number==incoming.batch_number)).scalar_one_or_none()
    if not batch or batch.site_id!=site.id or batch.material_id!=mat.id:
        raise HTTPException(422,'Batch does not match site and material')
    lot=db.execute(select(m.InspectionLot).where(m.InspectionLot.tenant_id==user.tenant_id,
                                        m.InspectionLot.lot_number==incoming.inspection_lot)).scalar_one_or_none()
    if not lot or lot.batch_id!=batch.id: raise HTTPException(422,'Inspection lot is not linked to batch')
    sample=db.execute(select(m.Sample).where(m.Sample.tenant_id==user.tenant_id,
                                         m.Sample.sample_number==incoming.sample_number)).scalar_one_or_none()
    if not sample or sample.inspection_lot_id!=lot.id:
        raise HTTPException(422,'Sample is not linked to inspection lot')
    measured_at=utc_naive(incoming.measured_at)
    versions=db.execute(select(m.Specification).where(m.Specification.tenant_id==user.tenant_id,
        m.Specification.material_id==mat.id,m.Specification.test_name==incoming.test_name,
        m.Specification.effective_from<=measured_at,
        ((m.Specification.effective_to.is_(None)) | (m.Specification.effective_to>measured_at)))).scalars().all()
    if len(versions)!=1 or not versions[0].approved_for_demo:
        raise HTTPException(422,'Expected exactly one approved, effective specification version')
    spec=versions[0]
    if incoming.unit != spec.unit: raise HTTPException(422,'Measurement unit mismatch; explicit conversion required')
    oor=(spec.lower_limit is not None and incoming.value < spec.lower_limit) or (spec.upper_limit is not None and incoming.value > spec.upper_limit)
    profile=db.execute(select(m.OOTProfile).where(m.OOTProfile.specification_id==spec.id,
                                                  m.OOTProfile.approved_for_demo.is_(True))).scalars().all()
    if len(profile)>1: raise HTTPException(422,'More than one active trend baseline')
    baseline=profile[0] if profile else None
    trend_flag=False
    zscore=None
    if not oor and baseline and baseline.sigma>0 and baseline.baseline_n>=8:
        zscore=float(abs((incoming.value-baseline.mean)/baseline.sigma))
        trend_flag=zscore>float(baseline.z_threshold)
    outcome='OOS' if oor else ('OOT' if trend_flag else ('IN_SPEC' if baseline else 'OOT_NOT_ASSESSED'))
    r=m.TestResult(tenant_id=user.tenant_id,site_id=site.id,material_id=mat.id,batch_id=batch.id,
        inspection_lot_id=lot.id,sample_id=sample.id,specification_id=spec.id,
        oot_profile_id=baseline.id if baseline else None,test_name=incoming.test_name,
        value=incoming.value,unit=incoming.unit,outcome=outcome,measured_at=measured_at,
        source_system=incoming.source_system,source_record_id=incoming.source_record_id,source_hash=fingerprint)
    db.add(r); db.flush()
    ev=None
    if outcome in ('OOS','OOT'):
        reason=(f'Result {incoming.value} {incoming.unit} outside specification '
                f'[{spec.lower_limit},{spec.upper_limit}] {spec.version}' if outcome=='OOS' else
                f'In-spec result with z={zscore:.2f} above approved demo threshold {baseline.z_threshold}; baseline N={baseline.baseline_n}')
        alert=m.Alert(tenant_id=user.tenant_id,site_id=site.id,result_id=r.id,
                      kind=outcome,explanation=reason,severity='CRITICAL' if outcome=='OOS' else 'MEDIUM')
        db.add(alert); db.flush()
        ev=m.QualityEvent(tenant_id=user.tenant_id,site_id=site.id,alert_id=alert.id,
                          result_id=r.id,event_number='DON-QE-'+secrets.token_hex(5).upper(),kind=outcome,status='DETECTED')
        db.add(ev); db.flush()
        db.add(m.Investigation(event_id=ev.id,summary='',impact_assessment='',capa_rationale=''))
        db.add(m.OutboxEvent(tenant_id=user.tenant_id,event_type='quality_event.created',
            payload_json={'quality_event_id':ev.id,'source_result_id':r.id,'kind':outcome}))
    db.add(m.IntegrationReceipt(tenant_id=user.tenant_id,source_system=incoming.source_system,
        idempotency_key=incoming.idempotency_key,request_hash=fingerprint,result_id=r.id))
    tenant_audit(db,user.tenant_id,user.id,'LAB_RESULT_IMPORTED','test_result',str(r.id),
                 {'source_system':incoming.source_system,'source_record_id':incoming.source_record_id,'outcome':outcome})
    if ev:
        tenant_audit(db,user.tenant_id,user.id,'QUALITY_EVENT_CREATED','quality_event',str(ev.id),
                     {'kind':ev.kind,'result_id':r.id,'status':'DETECTED'})
    db.flush()
    return {'result_id':r.id,'outcome':outcome,'replayed':False,'event_id':ev.id if ev else None,
            'specification_version':spec.version,'synthetic':True}

TRANSITIONS = {
 'OOS':{
  'DETECTED': {'TRIAGED':'qc'},
  'TRIAGED': {'PHASE_I_OPEN':'qc'},
  'PHASE_I_OPEN': {'PHASE_I_REVIEW':'qc'},
  'PHASE_I_REVIEW': {'PHASE_II_OPEN':'qc_manager','QA_EVALUATION':'qc_manager'},
  'PHASE_II_OPEN': {'PHASE_II_REVIEW':'qc'},
  'PHASE_II_REVIEW': {'QA_EVALUATION':'qc_manager'},
 },
 'OOT':{
  'DETECTED': {'TRIAGED':'qc'},
  'TRIAGED': {'OOT_REVIEW':'qc'},
  'OOT_REVIEW': {'OOT_ESCALATED':'qc_manager','QA_EVALUATION':'qc_manager'},
  'OOT_ESCALATED': {'QA_EVALUATION':'qc_manager'},
 }
}
CROSS = {
 'QA_EVALUATION':{'REPORT_DRAFT':'qc_manager'},
 'REPORT_DRAFT':{'QA_REVIEW_PENDING':'qc'},
 'QA_REVIEW_PENDING':{'APPROVED':'qa','REPORT_DRAFT':'qa'},
 'APPROVED':{'CLOSED':'qa'},
}
ROLE_GROUPS={'qc':{'qc_analyst','qc_manager','admin'},
             'qc_manager':{'qc_manager','admin'},
             'qa':{'qa_reviewer','qa_head','admin'}}

def transition(db: Session, ev: m.QualityEvent, user: m.User, target: str, reason: str, expected_version:int):
    if ev.version!=expected_version: raise HTTPException(409,'Stale version; reload event')
    allowed=dict(TRANSITIONS[ev.kind].get(ev.status,{}))
    allowed.update(CROSS.get(ev.status,{}))
    group=allowed.get(target)
    if group is None: raise HTTPException(409,f'Illegal transition {ev.status} -> {target}')
    if user.role not in ROLE_GROUPS[group]: raise HTTPException(403,'Role cannot perform transition')
    inv=db.execute(select(m.Investigation).where(m.Investigation.event_id==ev.id)).scalar_one()
    if ev.investigator_id is None and target=='TRIAGED': ev.investigator_id=user.id
    if target in {'QA_EVALUATION','QA_REVIEW_PENDING'}:
        if not inv.summary.strip() or not inv.impact_assessment.strip() or not inv.capa_rationale.strip():
            raise HTTPException(422,'Complete investigation summary, impact assessment and CAPA rationale')
    if target=='APPROVED':
        if ev.investigator_id==user.id: raise HTTPException(403,'Investigator cannot approve their own case')
        if not db.query(m.Evidence).filter(m.Evidence.event_id==ev.id).count():
            raise HTTPException(422,'At least one evidence record required before QA approval')
        if not inv.summary.strip(): raise HTTPException(422,'Investigation not completed')
        inv.approved_by=user.id
        inv.approved_at=datetime.utcnow()
    prev=ev.status
    ev.status=target; ev.version+=1; ev.updated_at=datetime.utcnow()
    tenant_audit(db,ev.tenant_id,user.id,'QUALITY_EVENT_STATUS_CHANGED','quality_event',str(ev.id),
                 {'from':prev,'to':target,'reason':reason,'version':ev.version})
    db.add(m.OutboxEvent(tenant_id=ev.tenant_id,event_type='quality_event.status_changed',
        payload_json={'event_id':ev.id,'from':prev,'to':target}))
    return event_view(db,ev)
