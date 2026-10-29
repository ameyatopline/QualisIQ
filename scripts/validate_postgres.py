"""Ephemeral PostgreSQL migration/ingest smoke validation. Removes only its own container."""
import json,os,secrets,subprocess,sys,time,uuid
from pathlib import Path
import httpx
root=Path(__file__).resolve().parents[1]
env=os.environ.copy()
for key in ('DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH'):env.pop(key,None)
cmd=['docker','--host=unix:///var/run/docker.sock']
password=secrets.token_hex(20)
name='qualisiq-validation-'+uuid.uuid4().hex[:10]
env.update(POSTGRES_PASSWORD=password)
container=None;api=None
try:
    r=subprocess.run(cmd+['run','--rm','-d','--name',name,'-e','POSTGRES_PASSWORD','-e','POSTGRES_USER=quality','-e','POSTGRES_DB=quality','-p','127.0.0.1::5432','postgres:16-bookworm'],env=env,text=True,capture_output=True)
    if r.returncode:
        print('PostgreSQL container failed:',r.stderr[-1800:]);raise SystemExit(1)
    container=r.stdout.strip()
    mapping=subprocess.check_output(cmd+['port',container,'5432/tcp'],env=env,text=True).strip()
    port=mapping.rsplit(':',1)[1]
    for _ in range(60):
        result=subprocess.run(cmd+['exec',container,'pg_isready','-U','quality','-d','quality'],env=env,capture_output=True)
        if result.returncode==0:break
        time.sleep(.5)
    else:raise RuntimeError('PostgreSQL readiness timed out')
    runtime={**os.environ,'DATABASE_URL':f'postgresql+psycopg://quality:{password}@127.0.0.1:{port}/quality','APP_ENV':'demo'}
    for args in (['-m','alembic','upgrade','head'],['-m','alembic','check'],['scripts/seed_enterprise.py','--sites','2','--batches','8','--results','500']):
        subprocess.run([sys.executable,*args],cwd=root,env=runtime,check=True)
    api=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8013'],cwd=root,env=runtime,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    with httpx.Client(base_url='http://127.0.0.1:8013',trust_env=False,timeout=20) as client:
        for _ in range(40):
            try:
                if client.get('/ready').status_code==200:break
            except httpx.HTTPError:pass
            time.sleep(.25)
        else:raise RuntimeError('API readiness timed out')
        r=client.post('/api/v1/auth/login',json={'email':'qc_analyst@don-demo.test','password':'DemoOnly!2026','tenant_code':'DON-DEMO'});r.raise_for_status();h={'Authorization':'Bearer '+r.json()['access_token']}
        incoming=json.loads((root/'demo_data/sample_ingest.json').read_text());incoming['source_record_id']='PG-VALIDATION-001';incoming['idempotency_key']='PG-VALIDATION-IDEM-001'
        r=client.post('/api/v1/lab/results',json=incoming,headers=h);r.raise_for_status();assert r.json()['outcome']=='OOS'
        ev=r.json()['event_id']
        r=client.post('/api/v1/lab/results',json=incoming,headers=h);r.raise_for_status();assert r.json()['replayed'] is True
        r=client.get(f'/api/v1/workbench/events/{ev}/lineage',headers=h);r.raise_for_status();assert r.json()['source']['record_id']=='PG-VALIDATION-001'
        r=client.get(f'/api/v1/workbench/events/{ev}/analysis',headers=h);r.raise_for_status();assert r.json()['history'][-1]['is_current'] and r.json()['specification']['within_limits'] is False
        r=client.get('/api/v1/workbench/summary',headers=h);r.raise_for_status();assert r.json()['total_results']==501
    report={'database':'Ephemeral PostgreSQL 16','migration_upgrade':'passed','schema_drift_check':'passed','seed_results':500,'authenticated_ingest':'passed','OOS_event':'passed','idempotent_replay':'passed','scoped_lineage':'passed','investigation_graph_data':'passed','SQL_aggregate_count':501,'limitations':'Local smoke only; no HA, concurrent writes, disaster recovery or production capacity claim'}
    (root/'docs/POSTGRES_VALIDATION.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
finally:
    if api:
        api.terminate()
        try:api.wait(timeout=10)
        except subprocess.TimeoutExpired:api.kill();api.wait()
    if container:subprocess.run(cmd+['stop',container],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
