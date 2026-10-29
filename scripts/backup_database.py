"""Consistent local SQLite backup and integrity-checked restore rehearsal.

Use PostgreSQL-native encrypted backup tooling for a real deployment.
"""
import argparse,hashlib,json,sqlite3
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',default='don_qualityos_demo.db');p.add_argument('--output',required=True);a=p.parse_args()
source=Path(a.source).resolve();target=Path(a.output).resolve()
if target.exists():raise SystemExit('Refusing to overwrite an existing backup')
target.parent.mkdir(parents=True,exist_ok=True)
with sqlite3.connect(f'file:{source}?mode=ro',uri=True) as src,sqlite3.connect(target) as dst:
    src.backup(dst)
    assert dst.execute('pragma integrity_check').fetchone()[0]=='ok'
    assert dst.execute('pragma foreign_key_check').fetchall()==[]
    counts={name:dst.execute('select count(*) from '+name).fetchone()[0] for name in ('test_results','quality_events','audit_logs')}
report={'source_name':source.name,'backup_name':target.name,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'integrity':'ok','foreign_key_check':'ok','counts':counts,'classification':'SYNTHETIC DEMO','limits':'Local SQLite backup only; not a production RPO/RTO or encrypted disaster recovery drill'}
target.with_suffix('.manifest.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
