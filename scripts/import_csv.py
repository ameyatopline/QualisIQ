#!/usr/bin/env python3
"""Small CSV demo connector; expects an existing API and valid demo-user credentials."""
import argparse, csv, json, os
from pathlib import Path
import httpx

p=argparse.ArgumentParser()
p.add_argument('csv_path')
p.add_argument('--api',default='http://127.0.0.1:8000')
p.add_argument('--email',default='qc_analyst@don-demo.test')
a=p.parse_args()
password=os.environ.get('DEMO_PASSWORD')
if not password: raise SystemExit('Set DEMO_PASSWORD in this shell; do not put passwords in CSV files')
with httpx.Client(timeout=60) as client:
    login=client.post(a.api+'/api/v1/auth/login',json={'email':a.email,'password':password,'tenant_code':'DON-DEMO'})
    login.raise_for_status()
    headers={'Authorization':'Bearer '+login.json()['access_token']}
    with Path(a.csv_path).open(newline='') as f:
        records=list(csv.DictReader(f))
    for i in range(0,len(records),250):
        resp=client.post(a.api+'/api/v1/lab/results/bulk',json=records[i:i+250],headers=headers)
        if resp.is_error:
            raise SystemExit(f'Import batch {i//250+1} failed {resp.status_code}: {resp.text[:1000]}')
        result=resp.json()
        print(f'Atomic batch {i//250+1}: accepted/replayed {result["count"]} records')
