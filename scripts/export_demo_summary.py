"""Export a public-facing manifest showing exactly which metrics are synthetic."""
import json,sys
from pathlib import Path
from sqlalchemy import select,func
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.database import SessionLocal
from app import models as m

with SessionLocal() as db:
    tenant=db.execute(select(m.Tenant).where(m.Tenant.code=='DON-DEMO')).scalar_one()
    counts={}
    for key,model in [('sites',m.Site),('materials',m.Material),('batches',m.Batch),('inspection_lots',m.InspectionLot),
                      ('samples',m.Sample),('test_results',m.TestResult),('oos_oot_alerts',m.Alert),
                      ('quality_events',m.QualityEvent),('capas',m.CAPA),('controlled_documents',m.ControlledDocument),
                      ('audit_events',m.AuditLog)]:
        counts[key]=db.execute(select(func.count()).select_from(model).where(model.tenant_id==tenant.id)).scalar_one()
    counts['event_states']={key:value for key,value in db.execute(select(m.QualityEvent.status,func.count())
        .where(m.QualityEvent.tenant_id==tenant.id).group_by(m.QualityEvent.status)).all()}
    data={'product':'DON QualityOS','data_classification':'SYNTHETIC / NON-GMP / DEMO ONLY',
          'generated_organization':'DON QualityOS Fictional Demo Organization',
          'source_system':'SYNTHETIC_LIMS','real_manufacturer_data':False,
          'production_throughput_verified':False,'real_QA_approvals':False,'metrics':counts}
    target=Path(__file__).resolve().parents[1]/'demo_data'/'DATASET_MANIFEST.json'
    target.write_text(json.dumps(data,indent=2)+'\n')
    print(target)
