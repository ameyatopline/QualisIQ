from app import models as m
from app.security import hash_password

def post_oos(env,token,incoming):
    client,_=env
    resp=client.post('/api/v1/lab/results',json=incoming,headers=token('qc_analyst'))
    assert resp.status_code==201,resp.text
    assert resp.json()['outcome']=='OOS'
    return resp.json()['event_id']

def test_auth_and_no_auth(env,token):
    client,_=env
    assert client.get('/api/v1/quality/events').status_code==401
    assert client.get('/api/v1/analytics/overview',headers=token('auditor')).status_code==200
    assert client.post('/api/v1/auth/login',json={'email':'qc_analyst@don-demo.test','password':'wrong'}).status_code==401

def test_oos_and_idempotency(env,token,incoming):
    client,_=env
    ev_id=post_oos(env,token,incoming)
    resp=client.post('/api/v1/lab/results',json=incoming,headers=token('qc_analyst'))
    assert resp.status_code==201 and resp.json()['replayed']
    assert resp.json()['event_id']==ev_id
    revised={**incoming,'value':'94.8'}
    assert client.post('/api/v1/lab/results',json=revised,headers=token('qc_analyst')).status_code==409
    unique_key={**incoming,'idempotency_key':'DEMO-INGEST-OTHER','value':'94.8'}
    assert client.post('/api/v1/lab/results',json=unique_key,headers=token('qc_analyst')).status_code==409
    result=client.get('/api/v1/quality/events/'+str(ev_id),headers=token('qc_analyst')).json()
    assert result['status']=='DETECTED' and result['kind']=='OOS'
    assert result['approved_limits']['min']=='95.000000'

def test_oot_and_normal(env,token,incoming):
    client,_=env
    new={**incoming,'test_name':'Related Impurity A','value':'0.35',
         'source_record_id':'CDS-TEST-OOT','idempotency_key':'DEMO-INGEST-OOT'}
    resp=client.post('/api/v1/lab/results',json=new,headers=token('qc_analyst'))
    assert resp.status_code==201,resp.text
    assert resp.json()['outcome']=='OOT'
    new.update({'value':'0.17','source_record_id':'CDS-TEST-NORMAL','idempotency_key':'DEMO-INGEST-OK'})
    resp=client.post('/api/v1/lab/results',json=new,headers=token('qc_analyst'))
    assert resp.status_code==201 and resp.json()['outcome']=='IN_SPEC' and resp.json()['event_id'] is None

def test_master_lineage_and_role_permissions(env,token,incoming):
    client,_=env
    bad={**incoming,'batch_number':'INVALID-LOT'}
    assert client.post('/api/v1/lab/results',json=bad,headers=token('qc_analyst')).status_code==422
    forbidden=client.post('/api/v1/lab/results',json=incoming,headers=token('auditor'))
    assert forbidden.status_code==403
    ev_id=post_oos(env,token,incoming)
    assert client.post(f'/api/v1/quality/events/{ev_id}/transition',json={
        'target_status':'APPROVED','reason':'Attempt to skip review','expected_version':1},
        headers=token('qa_reviewer')).status_code==409
    assert client.get('/api/v1/audit/events',headers=token('qc_analyst')).status_code==403

def test_qc_qa_workflow_and_audit(env,token,incoming):
    client,_=env
    event_id=post_oos(env,token,incoming)
    qc=token('qc_analyst'); manager=token('qc_manager'); qa=token('qa_reviewer')
    def move(target,actor,reason='Reviewed associated laboratory evidence'):
        ev=client.get(f'/api/v1/quality/events/{event_id}',headers=actor).json()
        return client.post(f'/api/v1/quality/events/{event_id}/transition',headers=actor,
                json={'target_status':target,'reason':reason,'expected_version':ev['version']})
    assert move('TRIAGED',qc).status_code==200
    assert move('PHASE_I_OPEN',qc).status_code==200
    assert move('PHASE_I_REVIEW',qc).status_code==200
    # cannot skip investigation documentation
    assert move('QA_EVALUATION',manager).status_code==422
    ev=client.get(f'/api/v1/quality/events/{event_id}',headers=qc).json()
    note=client.patch(f'/api/v1/quality/events/{event_id}/investigation',headers=qc,json={
        'summary':'Synthetic OOS for assay; laboratory review is complete for demo.',
        'root_cause_hypothesis':'Possible analytical preparation error, not established.',
        'impact_assessment':'Related batches and laboratory runs require evaluation.',
        'capa_rationale':'Document whether CAPA is necessary following verified conclusion.',
        'expected_version':ev['version']})
    assert note.status_code==200,note.text
    assert move('QA_EVALUATION',manager).status_code==200
    assert move('REPORT_DRAFT',manager).status_code==200
    assert move('QA_REVIEW_PENDING',qc).status_code==200
    assert move('APPROVED',qc).status_code==403
    assert move('APPROVED',qa).status_code==422
    evidence=client.post(f'/api/v1/quality/events/{event_id}/evidence',headers=qc,json={
        'kind':'RAW_CDS','label':'Synthetic instrument log and chromatogram',
        'reference_uri':'synthetic://evidence/run-55','sha256':'a'*64})
    assert evidence.status_code==201,evidence.text
    assert move('APPROVED',qa).status_code==200
    assert move('CLOSED',qa).status_code==200
    assert move('PHASE_II_OPEN',manager).status_code==409
    assert client.get('/api/v1/audit/verify',headers=token('auditor')).json()['integrity']=='VALID_DEMO_CHAIN'

def test_tenant_isolation(env,token,incoming):
    client,Factory=env
    ev_id=post_oos(env,token,incoming)
    with Factory() as db:
        t=m.Tenant(code='DIFFERENT-TENANT',name='Isolated demo org',synthetic=True)
        db.add(t);db.flush()
        db.add(m.User(tenant_id=t.id,email='auditor@other.test',password_hash=hash_password('IsolatedTest123!'),
                      role='auditor'))
        db.commit()
    resp=client.post('/api/v1/auth/login',json={'tenant_code':'DIFFERENT-TENANT',
        'email':'auditor@other.test','password':'IsolatedTest123!'})
    assert resp.status_code==200
    other={'Authorization':'Bearer '+resp.json()['access_token']}
    assert client.get(f'/api/v1/quality/events/{ev_id}',headers=other).status_code==404
    assert client.get('/api/v1/quality/events',headers=other).json()==[]

def test_ai_is_grounded_not_regulatory_decision(env,token,incoming):
    client,_=env
    ev_id=post_oos(env,token,incoming)
    result=client.get(f'/api/v1/quality/events/{ev_id}/ai-brief',headers=token('qc_analyst'))
    assert result.status_code==200
    body=result.json()
    assert body['generated_by_llm'] is False
    assert any(ref.startswith('specification:') for ref in body['source_references'])
    assert 'Does not invalidate results' in body['disclaimer']

def test_bulk_is_atomic(env,token,incoming):
    client,_=env
    second={**incoming,'source_record_id':'CDS-TEST-002','idempotency_key':'DEMO-INGEST-002',
            'sample_number':'UNKNOWN-SAMPLE'}
    resp=client.post('/api/v1/lab/results/bulk',json=[incoming,second],headers=token('qc_analyst'))
    assert resp.status_code==422
    assert client.get('/api/v1/lab/results',headers=token('qc_analyst')).json()==[]
    assert client.get('/api/v1/audit/verify',headers=token('auditor')).json()['integrity']=='VALID_DEMO_CHAIN'

def test_bulk_has_limit(env,token,incoming):
    client,_=env
    assert client.post('/api/v1/lab/results/bulk',json=[incoming]*251,
            headers=token('qc_analyst')).status_code==422


def test_missing_oot_baseline_is_unknown_not_pass(env,token,incoming):
    client,Factory=env
    with Factory() as db:
        db.query(m.OOTProfile).delete()
        db.commit()
    normal={**incoming,'value':'99.7'}
    resp=client.post('/api/v1/lab/results',json=normal,headers=token('qc_analyst'))
    assert resp.status_code==201,resp.text
    assert resp.json()['outcome']=='OOT_NOT_ASSESSED'


def test_site_scope_on_results_and_events(env,token,incoming):
    client,Factory=env
    ev=post_oos(env,token,incoming)
    with Factory() as db:
        u=db.query(m.User).filter_by(email='qc_analyst@don-demo.test').one()
        site2=db.query(m.Site).filter_by(code='DQ-002').one()
        u.site_id=site2.id
        db.commit()
    restricted=token('qc_analyst')
    assert client.get(f'/api/v1/quality/events/{ev}',headers=restricted).status_code==404
    assert client.get('/api/v1/quality/events',headers=restricted).json()==[]
    revised={**incoming,'source_record_id':'CDS-TEST-CROSS-SITE','idempotency_key':'IDEM-CROSS-SITE'}
    assert client.post('/api/v1/lab/results',json=revised,headers=restricted).status_code==403


def test_audit_change_detected(env,token,incoming):
    client,Factory=env
    post_oos(env,token,incoming)
    with Factory() as db:
        row=db.query(m.AuditLog).first()
        row.action='TAMPERED_ACTION'
        db.commit()
    result=client.get('/api/v1/audit/verify',headers=token('auditor')).json()
    assert result['integrity']=='FAILED'


def test_capa_independent_effectiveness(env,token,incoming):
    client,Factory=env
    ev=post_oos(env,token,incoming)
    with Factory() as db:
        analyst=db.query(m.User).filter_by(email='qc_analyst@don-demo.test').one()
        analyst_id=analyst.id
    resp=client.post(f'/api/v1/quality/events/{ev}/capa',json={
        'title':'Synthetic CAPA: review laboratory method controls',
        'assigned_to_id':analyst_id,'due_at':'2026-12-01T00:00:00Z'},headers=token('qc_manager'))
    assert resp.status_code==201,resp.text
    capa_id=resp.json()['id']
    def change(actor,state):
        return client.post(f'/api/v1/quality/capa/{capa_id}/update',headers=token(actor),
          json={'status':state,'effectiveness_note':'Synthetic documented review and evidence.'})
    assert change('qc_analyst','VERIFIED').status_code==403
    assert change('qc_analyst','IN_PROGRESS').status_code==200
    assert change('qc_analyst','EFFECTIVENESS_PENDING').status_code==200
    assert change('qc_analyst','VERIFIED').status_code==403
    assert change('qa_reviewer','VERIFIED').status_code==200
    assert change('qa_reviewer','IN_PROGRESS').status_code==409
