"""Browser tests receive a disposable copy; never edit the supplied demo database."""
import os,sqlite3,subprocess,sys,tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='qualisiq-e2e-') as tmp:
    path=Path(tmp)/'demo.db'
    with sqlite3.connect(f'file:{root / "don_qualityos_demo.db"}?mode=ro',uri=True) as src,sqlite3.connect(path) as dst:src.backup(dst)
    env={**os.environ,'DATABASE_URL':f'sqlite:///{path}','APP_ENV':'demo'}
    raise SystemExit(subprocess.call([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8011'],cwd=root,env=env))
