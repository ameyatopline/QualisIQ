import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app import models  # noqa: F401
from app.main import app
from scripts.seed_enterprise import setup_master, create_batches

@pytest.fixture()
def env():
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Factory=sessionmaker(bind=engine,autoflush=False,expire_on_commit=False)
    with Factory() as db:
        tenant,sites,materials,specs,profiles=setup_master(db,2)
        create_batches(db,tenant,sites,materials,8)
    def override():
        with Factory() as db:
            yield db
    app.dependency_overrides[get_db]=override
    with TestClient(app) as client:
        yield client,Factory
    app.dependency_overrides.clear()
    engine.dispose()

@pytest.fixture()
def token(env):
    client,_=env
    def inner(role):
        result=client.post('/api/v1/auth/login',json={'email':f'{role}@don-demo.test',
            'password':'DemoOnly!2026','tenant_code':'DON-DEMO'})
        assert result.status_code==200,result.text
        return {'Authorization':'Bearer '+result.json()['access_token']}
    return inner

@pytest.fixture()
def incoming():
    return {'site_code':'DQ-001','material_code':'DON-MAT-001',
            'batch_number':'DON-SYN-B-0000001','inspection_lot':'DON-SYN-L-0000001',
            'sample_number':'DON-SYN-S-0000001','test_name':'Assay','value':'93.5',
            'unit':'%','measured_at':'2026-10-29T10:00:00Z',
            'source_system':'SYNTHETIC_CDS','source_record_id':'CDS-TEST-001',
            'idempotency_key':'DEMO-INGEST-001'}
