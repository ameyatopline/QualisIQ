import pytest
from app import models as m
from app.services import TRANSITIONS

@pytest.mark.parametrize('path',['/workbench/summary','/workbench/sites','/workbench/trends','/workbench/events','/workbench/events/1/lineage','/workbench/events/1/transitions','/workbench/capas','/workbench/documents','/ml/report','/ml/events/1/score'])
def test_new_routes_require_auth(env,path):
    client,_=env
    assert client.get('/api/v1'+path).status_code==401

def test_workbench_filters_and_scopes(env,token,incoming):
    client,Factory=env;h=token('qc_analyst')
    response=client.post('/api/v1/lab/results',json=incoming,headers=h);event_id=response.json()['event_id']
    assert client.get('/api/v1/workbench/summary',headers=h).json()['total_results']==1
    page=client.get('/api/v1/workbench/events?kind=OOS&q=Assay',headers=h).json()
    assert page['total']==1 and page['items'][0]['id']==event_id
    assert client.get('/api/v1/workbench/events?q=NO_MATCH',headers=h).json()['total']==0
    assert client.get('/api/v1/workbench/events?q=%25',headers=h).json()['total']==0
    assert client.get('/api/v1/workbench/events?limit=1000',headers=h).status_code==422
    assert client.get('/api/v1/workbench/summary?site_id=-1',headers=h).status_code==422
    assert client.get('/api/v1/workbench/events?kind=OOT',headers=h).json()['total']==0
    data=client.get(f'/api/v1/workbench/events/{event_id}/lineage',headers=h).json()
    assert data['source']['record_id']==incoming['source_record_id']
    with Factory() as db:
        site=db.query(m.Site).filter_by(code='DQ-002').one();user=db.query(m.User).filter_by(email='qc_analyst@don-demo.test').one();user.site_id=site.id;db.commit()
    restricted=token('qc_analyst')
    assert client.get('/api/v1/workbench/summary',headers=restricted).json()['total_results']==0
    assert len(client.get('/api/v1/workbench/sites',headers=restricted).json())==1
    assert client.get('/api/v1/workbench/events',headers=restricted).json()['total']==0
    assert client.get('/api/v1/workbench/trends',headers=restricted).json()==[]
    assert client.get('/api/v1/workbench/capas',headers=restricted).json()['total']==0
    assert client.get(f'/api/v1/workbench/events/{event_id}/lineage',headers=restricted).status_code==404
    assert client.get(f'/api/v1/workbench/events/{event_id}/transitions',headers=restricted).status_code==404
    assert client.get(f'/api/v1/ml/events/{event_id}/score',headers=restricted).status_code==404
    assert client.get('/api/v1/ml/report',headers=restricted).status_code==403
    assert client.get('/api/v1/workbench/summary?site_id=1',headers=restricted).status_code==403

def test_cross_tenant_read_models(env,token,incoming):
    from app.security import hash_password
    client,Factory=env
    ev=client.post('/api/v1/lab/results',json=incoming,headers=token('qc_analyst')).json()['event_id']
    with Factory() as db:
        tenant=m.Tenant(code='OTHER',name='Other synthetic tenant',synthetic=True);db.add(tenant);db.flush();db.add(m.User(tenant_id=tenant.id,email='other@test.test',role='auditor',password_hash=hash_password('OtherOnly123!')));db.commit()
    response=client.post('/api/v1/auth/login',json={'tenant_code':'OTHER','email':'other@test.test','password':'OtherOnly123!'})
    h={'Authorization':'Bearer '+response.json()['access_token']}
    for path in ('sites','trends','documents'):assert client.get('/api/v1/workbench/'+path,headers=h).json()==[]
    assert client.get('/api/v1/workbench/summary',headers=h).json()['total_results']==0
    for path in ('events','capas'):assert client.get('/api/v1/workbench/'+path,headers=h).json()['total']==0
    assert client.get(f'/api/v1/workbench/events/{ev}/lineage',headers=h).status_code==404
    assert client.get(f'/api/v1/ml/events/{ev}/score',headers=h).status_code==404

def test_transitions_and_security_headers(env,token,incoming):
    client,_=env;h=token('qc_analyst');ev=client.post('/api/v1/lab/results',json=incoming,headers=h).json()['event_id']
    assert client.get(f'/api/v1/workbench/events/{ev}/transitions',headers=h).json()['allowed']==['TRIAGED']
    assert client.get(f'/api/v1/workbench/events/{ev}/transitions',headers=token('auditor')).json()['allowed']==[]
    response=client.get('/api/v1/workbench/events',headers=h)
    assert response.headers['cache-control']=='no-store'
    assert response.headers['x-content-type-options']=='nosniff'
    assert len(response.headers['x-request-id'])==36
    assert client.get('/health',headers={'host':'attacker.example'}).status_code==400

def test_model_missing_fails_closed(env,token,monkeypatch,tmp_path):
    monkeypatch.setenv('MODEL_DIR',str(tmp_path))
    client,_=env
    assert client.get('/api/v1/ml/report',headers=token('auditor')).status_code==503

def test_login_rate_limit(env):
    client,_=env
    for _ in range(20):
        assert client.post('/api/v1/auth/login',json={'email':'unknown@test.test','password':'wrong','tenant_code':'UNKNOWN'}).status_code==401
    response=client.post('/api/v1/auth/login',json={'email':'unknown@test.test','password':'wrong','tenant_code':'UNKNOWN'})
    assert response.status_code==429 and response.headers['retry-after']=='60'

def test_inspection_intake_lineage_is_scoped(env,token):
    client,Factory=env;h=token('qc_analyst')
    rows=client.get('/api/v1/workbench/inspection-lots',headers=h).json()
    assert rows and rows[0]['sample_number'] and rows[0]['batch_number']
    assert client.get('/api/v1/workbench/inspection-lots?q=%25',headers=h).json()==[]
    with Factory() as db:
        user=db.query(m.User).filter_by(email='qc_analyst@don-demo.test').one();user.site_id=2;db.commit()
    rows=client.get('/api/v1/workbench/inspection-lots',headers=token('qc_analyst')).json()
    assert all(r['site_id']==2 for r in rows)
    assert client.get('/api/v1/workbench/inspection-lots?site_id=1',headers=token('qc_analyst')).status_code==403

def test_tenant_wide_admin_data_rejects_site_only_accounts(env,token):
    client,Factory=env
    with Factory() as db:
        for role in ('auditor','admin'):
            user=db.query(m.User).filter_by(email=role+'@don-demo.test').one();user.site_id=1
        db.commit()
    for path in ('/audit/verify','/audit/events'):
        assert client.get('/api/v1'+path,headers=token('auditor')).status_code==403
    assert client.get('/api/v1/integrations/outbox',headers=token('admin')).status_code==403

def test_model_integrity_tenant_binding_and_abstention(env,token,incoming,monkeypatch,tmp_path):
    import hashlib,json
    from ml.runtime import FEATURES
    monkeypatch.setenv('MODEL_DIR',str(tmp_path))
    client,_=env
    h=token('qc_analyst');ev=client.post('/api/v1/lab/results',json=incoming,headers=h).json()['event_id']
    artifact={'schema_version':1,'features':FEATURES,'tenant_id':1,'stats':{}}
    def write_bundle():
        encoded=json.dumps(artifact).encode();(tmp_path/'model.json').write_bytes(encoded)
        (tmp_path/'report.json').write_text(json.dumps({'version':'test','artifact_sha256':hashlib.sha256(encoded).hexdigest()}))
    write_bundle()
    assert client.get(f'/api/v1/ml/events/{ev}/score',headers=h).json()['status']=='NOT_ASSESSED'
    (tmp_path/'model.json').write_text(json.dumps({**artifact,'tenant_id':2}))
    assert client.get('/api/v1/ml/report',headers=h).status_code==503
    artifact['tenant_id']=2;write_bundle()
    assert client.get('/api/v1/ml/report',headers=h).status_code==404
    monkeypatch.setenv('APP_ENV','production')
    assert client.get('/api/v1/ml/report',headers=h).status_code==503

def test_readiness_and_token_audience(env,token):
    import jwt
    from app.security import JWT_SECRET
    client,_=env
    assert client.get('/ready').json()['status']=='ready'
    valid=token('auditor')['Authorization'].split()[1]
    claims=jwt.decode(valid,JWT_SECRET,algorithms=['HS256'],audience='quality-workbench')
    claims['aud']='another-service'
    forged=jwt.encode(claims,JWT_SECRET,algorithm='HS256')
    assert client.get('/api/v1/workbench/summary',headers={'Authorization':'Bearer '+forged}).status_code==401
