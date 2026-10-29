"""Authenticated, tenant/site-scoped read models for the quality workbench."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, case, or_
from sqlalchemy.orm import Session
from app import models as m
from app.database import get_db
from app.security import get_current_user
from app.services import scoped_event, event_view

router = APIRouter(prefix='/api/v1/workbench', tags=['Quality workbench'])

def scope(stmt, model, user, site_id=None):
    stmt = stmt.where(model.tenant_id == user.tenant_id)
    if user.site_id:
        if site_id and site_id != user.site_id:
            raise HTTPException(403, 'Site is outside your access scope')
        site_id = user.site_id
    if site_id:
        stmt = stmt.where(model.site_id == site_id)
    return stmt

@router.get('/summary')
def summary(site_id: int | None = Query(None, gt=0), user=Depends(get_current_user), db: Session=Depends(get_db)):
    result = scope(select(m.TestResult.outcome, func.count()).group_by(m.TestResult.outcome), m.TestResult, user, site_id)
    outcomes = dict(db.execute(result).all())
    states = dict(db.execute(scope(select(m.QualityEvent.status, func.count()).group_by(m.QualityEvent.status), m.QualityEvent, user, site_id)).all())
    capastmt = select(m.CAPA.status, func.count()).join(m.QualityEvent, m.CAPA.event_id == m.QualityEvent.id).where(m.CAPA.tenant_id == user.tenant_id).group_by(m.CAPA.status)
    capas = dict(db.execute(scope(capastmt, m.QualityEvent, user, site_id)).all())
    return {'synthetic': True, 'total_results': sum(outcomes.values()), 'outcomes': outcomes,
            'event_states': states, 'total_events': sum(states.values()),
            'open_events': sum(n for s,n in states.items() if s != 'CLOSED'), 'capas': capas,
            'generated_at': datetime.now(timezone.utc).isoformat()}

@router.get('/sites')
def site_metrics(user=Depends(get_current_user), db: Session=Depends(get_db)):
    results = scope(select(m.TestResult.site_id.label('sid'), func.count().label('results'),
        func.sum(case((m.TestResult.outcome=='OOS',1), else_=0)).label('oos'),
        func.sum(case((m.TestResult.outcome=='OOT',1), else_=0)).label('oot')).group_by(m.TestResult.site_id),m.TestResult,user).subquery()
    events = scope(select(m.QualityEvent.site_id.label('sid'),func.count().label('events'),
        func.sum(case((m.QualityEvent.status!='CLOSED',1),else_=0)).label('open')).group_by(m.QualityEvent.site_id),m.QualityEvent,user).subquery()
    stmt = select(m.Site,results.c.results,results.c.oos,results.c.oot,events.c.events,events.c.open).outerjoin(results,results.c.sid==m.Site.id).outerjoin(events,events.c.sid==m.Site.id).where(m.Site.tenant_id==user.tenant_id)
    if user.site_id: stmt=stmt.where(m.Site.id==user.site_id)
    return [dict(id=s.id,code=s.code,name=s.name,region=s.region,results=n or 0,oos=oos or 0,oot=oot or 0,events=ev or 0,open_events=op or 0,synthetic=True) for s,n,oos,oot,ev,op in db.execute(stmt.order_by(m.Site.code))]

@router.get('/trends')
def trends(site_id: int | None=Query(None,gt=0), user=Depends(get_current_user),db:Session=Depends(get_db)):
    day=func.date(m.TestResult.measured_at)
    stmt=scope(select(day.label('day'),m.TestResult.outcome,func.count()).group_by(day,m.TestResult.outcome).order_by(day),m.TestResult,user,site_id)
    days={}
    for d,outcome,n in db.execute(stmt):
        row=days.setdefault(str(d),{'date':str(d),'total':0,'OOS':0,'OOT':0})
        row['total']+=n
        if outcome in ('OOS','OOT'):row[outcome]+=n
    return list(days.values())[-90:]

@router.get('/events')
def events(q:str=Query('',max_length=100),kind:str|None=None,state:str|None=None,
           site_id:int|None=Query(None,gt=0),limit:int=Query(20,ge=1,le=100),offset:int=Query(0,ge=0),
           user=Depends(get_current_user),db:Session=Depends(get_db)):
    stmt=scope(select(m.QualityEvent).join(m.TestResult,m.QualityEvent.result_id==m.TestResult.id),m.QualityEvent,user,site_id)
    if kind:stmt=stmt.where(m.QualityEvent.kind==kind)
    if state:stmt=stmt.where(m.QualityEvent.status==state)
    if q:
        pattern='%'+q.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%'
        stmt=stmt.where(or_(m.QualityEvent.event_number.ilike(pattern,escape='\\'),m.TestResult.test_name.ilike(pattern,escape='\\'),m.TestResult.source_record_id.ilike(pattern,escape='\\')))
    total=db.scalar(select(func.count()).select_from(stmt.subquery()))
    # Bounded page: existing object serializer preserves investigation/specification detail.
    return {'items':[event_view(db,r) for r in db.scalars(stmt.order_by(m.QualityEvent.id.desc()).offset(offset).limit(limit))], 'total':total,'offset':offset,'limit':limit}

@router.get('/events/{event_id}/lineage')
def lineage(event_id:int,user=Depends(get_current_user),db:Session=Depends(get_db)):
    ev=scoped_event(db,event_id,user);r=db.get(m.TestResult,ev.result_id)
    batch=db.get(m.Batch,r.batch_id);lot=db.get(m.InspectionLot,r.inspection_lot_id);sample=db.get(m.Sample,r.sample_id);mat=db.get(m.Material,r.material_id);spec=db.get(m.Specification,r.specification_id)
    evidence=db.scalars(select(m.Evidence).where(m.Evidence.event_id==ev.id,m.Evidence.tenant_id==user.tenant_id)).all()
    return {'synthetic':True,'source':{'system':r.source_system,'record_id':r.source_record_id,'sha256':r.source_hash,'measured_at':r.measured_at},'material':{'code':mat.code,'description':mat.description},'batch':batch.batch_number,'inspection_lot':lot.lot_number,'sample':sample.sample_number,'specification':{'id':spec.id,'version':spec.version,'test':spec.test_name},'evidence':[{'id':e.id,'kind':e.kind,'label':e.label,'reference_uri':e.reference_uri,'sha256':e.sha256} for e in evidence]}

@router.get('/capas')
def capas(site_id:int|None=Query(None,gt=0),limit:int=Query(50,ge=1,le=100),offset:int=Query(0,ge=0),user=Depends(get_current_user),db:Session=Depends(get_db)):
    stmt=scope(select(m.CAPA,m.QualityEvent.event_number,m.QualityEvent.site_id).join(m.QualityEvent,m.CAPA.event_id==m.QualityEvent.id).where(m.CAPA.tenant_id==user.tenant_id),m.QualityEvent,user,site_id)
    total=db.scalar(select(func.count()).select_from(stmt.subquery()))
    return {'total':total,'items':[{'id':c.id,'event_id':c.event_id,'event_number':num,'site_id':sid,'title':c.title,'due_at':c.due_at,'status':c.status,'effectiveness_note':c.effectiveness_note} for c,num,sid in db.execute(stmt.order_by(m.CAPA.due_at).offset(offset).limit(limit))]}

@router.get('/documents')
def documents(user=Depends(get_current_user),db:Session=Depends(get_db)):
    return [{'code':d.document_code,'version':d.version,'title':d.title,'status':d.status,'reference':d.content_reference,'sha256':d.checksum,'synthetic':True} for d in db.scalars(select(m.ControlledDocument).where(m.ControlledDocument.tenant_id==user.tenant_id).order_by(m.ControlledDocument.document_code))]

@router.get('/events/{event_id}/transitions')
def transitions(event_id:int,user=Depends(get_current_user),db:Session=Depends(get_db)):
    from app.services import TRANSITIONS,CROSS,ROLE_GROUPS
    ev=scoped_event(db,event_id,user)
    options={**TRANSITIONS[ev.kind].get(ev.status,{}),**CROSS.get(ev.status,{})}
    return {'allowed':[target for target,group in options.items() if user.role in ROLE_GROUPS[group] and not (target=='APPROVED' and ev.investigator_id==user.id)],'expected_version':ev.version,'note':'Document completeness, independent approval and evidence gates are enforced on transition.'}

@router.get('/inspection-lots')
def inspection_lots(q:str=Query('',max_length=80),site_id:int|None=Query(None,gt=0),limit:int=Query(30,ge=1,le=100),user=Depends(get_current_user),db:Session=Depends(get_db)):
    stmt=select(m.InspectionLot,m.Batch,m.Material,m.Sample,m.Site).join(m.Batch,m.Batch.id==m.InspectionLot.batch_id).join(m.Material,m.Material.id==m.Batch.material_id).join(m.Sample,m.Sample.inspection_lot_id==m.InspectionLot.id).join(m.Site,m.Site.id==m.Batch.site_id)
    stmt=scope(stmt,m.Batch,user,site_id).where(m.InspectionLot.tenant_id==user.tenant_id,m.Material.tenant_id==user.tenant_id,m.Sample.tenant_id==user.tenant_id,m.Site.tenant_id==user.tenant_id)
    if q:
        pattern='%'+q.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%'
        stmt=stmt.where(or_(m.InspectionLot.lot_number.ilike(pattern,escape='\\'),m.Batch.batch_number.ilike(pattern,escape='\\')))
    return [{'id':l.id,'inspection_lot':l.lot_number,'batch_number':b.batch_number,'material_code':mat.code,'material':mat.description,'sample_number':sample.sample_number,'site_code':site.code,'site_id':site.id} for l,b,mat,sample,site in db.execute(stmt.order_by(m.InspectionLot.id.desc()).limit(limit))]

@router.get('/storage')
def storage(user=Depends(get_current_user),db:Session=Depends(get_db)):
    """Show the active local demo file, never connection strings or credentials."""
    from sqlalchemy import text
    from app.security import APP_ENV
    backend=db.get_bind().dialect.name
    if APP_ENV!='demo':
        return {'backend':backend,'location':'Database service (connection details hidden)'}
    if backend=='sqlite':
        main=next(row for row in db.execute(text('PRAGMA database_list')).mappings() if row['name']=='main')
        return {'backend':'sqlite','location':main['file'] or 'In-memory database (no file)'}
    return {'backend':backend,'location':'Database service (connection details hidden)'}

@router.get('/events/{event_id}/analysis')
def investigation_analysis(
    event_id: int,
    limit: int = Query(40, ge=2, le=100),
    user=Depends(get_current_user),
    db: Session=Depends(get_db),
):
    """Retrospective, comparable result history; never estimates a new OOT baseline."""
    from sqlalchemy import and_

    event = scoped_event(db, event_id, user)
    current = db.scalar(select(m.TestResult).where(
        m.TestResult.id == event.result_id,
        m.TestResult.tenant_id == user.tenant_id,
        m.TestResult.site_id == event.site_id,
    ))
    if current is None:
        raise HTTPException(404, 'Investigation result not found')
    specification = db.scalar(select(m.Specification).where(
        m.Specification.id == current.specification_id,
        m.Specification.tenant_id == user.tenant_id,
    ))
    if specification is None:
        raise HTTPException(404, 'Investigation specification not found')
    if current.unit != specification.unit:
        raise HTTPException(422, 'Stored result and specification units do not match')

    # Use the result's linked baseline, rather than selecting a newer/current profile.
    baseline = db.get(m.OOTProfile, current.oot_profile_id) if current.oot_profile_id else None
    reason = None
    if baseline is None:
        reason = 'No stored OOT baseline is linked to this result.'
    elif baseline.specification_id != specification.id:
        reason = 'The linked OOT baseline does not match this specification.'
    elif not baseline.approved_for_demo:
        reason = 'The linked OOT baseline is not approved for demo use.'
    elif baseline.sigma <= 0 or baseline.z_threshold <= 0:
        reason = 'The linked OOT baseline requires positive sigma and threshold.'
    elif baseline.baseline_n < 8:
        reason = 'The linked OOT baseline has fewer than eight observations.'
    usable_baseline = baseline if reason is None else None

    stmt = select(m.TestResult).where(
        m.TestResult.tenant_id == user.tenant_id,
        m.TestResult.site_id == current.site_id,
        m.TestResult.material_id == current.material_id,
        m.TestResult.specification_id == specification.id,
        m.TestResult.test_name == current.test_name,
        m.TestResult.unit == current.unit,
        or_(
            m.TestResult.measured_at < current.measured_at,
            and_(m.TestResult.measured_at == current.measured_at, m.TestResult.id <= current.id),
        ),
    )
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = list(db.scalars(stmt.order_by(
        m.TestResult.measured_at.desc(), m.TestResult.id.desc(),
    ).limit(limit)))[::-1]

    def utc_timestamp(value):
        value = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')

    points = []
    for row in rows:
        # No retrospective normalization against a different profile version.
        z = ((row.value - usable_baseline.mean) / usable_baseline.sigma
             if usable_baseline and row.oot_profile_id == usable_baseline.id else None)
        points.append({
            'result_id': row.id, 'value': str(row.value), 'signed_z': str(z) if z is not None else None,
            'measured_at': utc_timestamp(row.measured_at), 'outcome': row.outcome,
            'source_system': row.source_system, 'source_record_id': row.source_record_id,
            'is_current': row.id == current.id,
        })
    lower, upper = specification.lower_limit, specification.upper_limit
    within = (None if lower is None and upper is None else
              (lower is None or current.value >= lower) and (upper is None or current.value <= upper))
    site = db.scalar(select(m.Site).where(m.Site.id == current.site_id, m.Site.tenant_id == user.tenant_id))
    material = db.scalar(select(m.Material).where(m.Material.id == current.material_id, m.Material.tenant_id == user.tenant_id))
    return {
        'event_id': event.id, 'event_number': event.event_number, 'kind': event.kind,
        'current_result_id': current.id, 'current_value': str(current.value), 'unit': current.unit,
        'cohort': {'site': site.code if site else None, 'material': material.code if material else None,
                   'test': current.test_name, 'specification_id': specification.id},
        'specification': {'version': specification.version, 'lower': str(lower) if lower is not None else None,
                          'upper': str(upper) if upper is not None else None, 'within_limits': within},
        'baseline': ({'id': usable_baseline.id, 'version': usable_baseline.version,
                      'mean': str(usable_baseline.mean), 'sigma': str(usable_baseline.sigma),
                      'threshold': str(usable_baseline.z_threshold), 'n': usable_baseline.baseline_n,
                      'method': usable_baseline.method} if usable_baseline else None),
        'oot_status': ('NOT_ASSESSED' if not usable_baseline else
                       'CONTEXT_ONLY_OOS' if current.outcome == 'OOS' else 'ASSESSED_DEMO'),
        'oot_reason': reason,
        'history': points,
        'window': {'limit': limit, 'shown': len(points), 'available': total, 'truncated': total > len(points),
                   'order': 'measurement time, then result ID; ending at the case result'},
        'synthetic': db.get(m.Tenant, user.tenant_id).synthetic,
        'notice': 'Stored demo limits and baseline only. Z-scores are context, not a validated OOT procedure. OOS takes precedence; human investigation remains required.',
    }
