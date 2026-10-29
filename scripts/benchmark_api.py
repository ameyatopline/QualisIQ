"""Bounded local read benchmark, not a production SLA or ingest throughput test."""
import argparse,concurrent.futures,json,os,statistics,time
from pathlib import Path
import httpx
p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:8010');p.add_argument('--requests',type=int,default=200);p.add_argument('--workers',type=int,default=8);p.add_argument('--output',default='docs/LOCAL_BENCHMARK.json');args=p.parse_args()
password=os.getenv('DEMO_PASSWORD')
if not password:
    defaults=dict(line.split('=',1) for line in (Path(__file__).resolve().parents[1]/'.env.example').read_text().splitlines() if line and not line.startswith('#'))
    password=defaults['DEMO_PASSWORD']
with httpx.Client(base_url=args.url,trust_env=False,timeout=30) as client:
    auth=client.post('/api/v1/auth/login',json={'email':'qc_analyst@don-demo.test','password':password,'tenant_code':'DON-DEMO'});auth.raise_for_status();headers={'Authorization':'Bearer '+auth.json()['access_token']}
    paths=['/api/v1/workbench/summary','/api/v1/workbench/events?limit=10','/api/v1/workbench/sites','/api/v1/workbench/trends']
    def sample(i):
        start=time.perf_counter();r=client.get(paths[i%len(paths)],headers=headers);r.raise_for_status();r.json();return (time.perf_counter()-start)*1000
    for i in range(4):sample(i)
    start=time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:latencies=list(pool.map(sample,range(args.requests)))
    elapsed=time.perf_counter()-start
    ordered=sorted(latencies)
    def quantile(q):return ordered[min(len(ordered)-1,int((len(ordered)-1)*q))]
    report={'scope':'Local single-process SQLite read-only mixed-endpoint benchmark; not a production SLA','requests':args.requests,'concurrency':args.workers,'endpoints':paths,'completed':len(latencies),'failures':0,'duration_seconds':elapsed,'requests_per_second':len(latencies)/elapsed,'latency_ms':{'p50':quantile(.5),'p95':quantile(.95),'p99':quantile(.99)},'dataset':'50000 synthetic laboratory results / 24 sites / 1192 events','limitations':['Loopback network, one API process, one synthetic tenant, SQLite','No write, ingest, failover, distributed load or real-world throughput conclusion']}
    Path(args.output).write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
