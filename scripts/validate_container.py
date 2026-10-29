"""Validate a built image on loopback; stop only the container created here."""
import json,os,subprocess,time,uuid
from pathlib import Path
import httpx
root=Path(__file__).resolve().parents[1]
env=os.environ.copy()
for key in ('DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH'):env.pop(key,None)
cmd=['docker','--host=unix:///var/run/docker.sock'];container=None
try:
    container=subprocess.check_output(cmd+['run','--rm','-d','--name','qualisiq-image-check-'+uuid.uuid4().hex[:8],'-p','127.0.0.1::8000','qualisiq:local-review'],env=env,text=True).strip()
    mapping=subprocess.check_output(cmd+['port',container,'8000/tcp'],env=env,text=True).strip();port=mapping.rsplit(':',1)[1]
    with httpx.Client(base_url='http://127.0.0.1:'+port,trust_env=False,timeout=3) as client:
        for _ in range(40):
            try:
                if client.get('/ready').json()['status']=='ready':break
            except (httpx.HTTPError,ValueError,KeyError):pass
            time.sleep(.25)
        else:raise RuntimeError('Container readiness failed')
        response=client.get('/');response.raise_for_status();assert 'QualisIQ' in response.text
    user=subprocess.check_output(cmd+['inspect','--format','{{.Config.User}}',container],env=env,text=True).strip();assert user=='qualisiq'
    image=subprocess.check_output(cmd+['inspect','--format','{{.Image}}',container],env=env,text=True).strip()
    report={'image':'qualisiq:local-review','image_id':image,'build':'passed','runtime_user':user,'readiness':'passed','built_website':'passed','scope':'Local container with empty SQLite demo database; no public deployment or production approval'}
    (root/'docs/CONTAINER_VALIDATION.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
finally:
    if container:subprocess.run(cmd+['stop',container],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
