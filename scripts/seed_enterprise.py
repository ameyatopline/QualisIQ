#!/usr/bin/env python3
"""Deterministic, explicitly SYNTHETIC enterprise demo/scale dataset. Never imports company records."""
import argparse, hashlib, os, random, sys, uuid
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from sqlalchemy import select, insert, func

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.database import SessionLocal, create_schema
from app.security import hash_password, APP_ENV
from app import models as m
from app.services import tenant_audit

PRODUCTS = [
 ('DON-MAT-001','Paracetamol 500 mg tablets','Tablet'),
 ('DON-MAT-002','Metformin 500 mg tablets','Tablet'),
 ('DON-MAT-003','Amlodipine 5 mg tablets','Tablet'),
 ('DON-MAT-004','Omeprazole 20 mg capsules','Capsule'),
 ('DON-MAT-005','Cetirizine 10 mg tablets','Tablet'),
 ('DON-MAT-006','Vitamin C 500 mg tablets','Tablet'),
 ('DON-MAT-007','Ibuprofen 200 mg tablets','Tablet'),
 ('DON-MAT-008','Losartan 50 mg tablets','Tablet')
]
TESTS = [
 ('Assay','%',Decimal('95'),Decimal('105'),Decimal('99.5'),Decimal('0.9')),
 ('Related Impurity A','%',Decimal('0'),Decimal('0.5'),Decimal('0.15'),Decimal('0.05')),
 ('Dissolution','%',Decimal('75'),Decimal('110'),Decimal('93'),Decimal('4')),
]
REGIONS=['India West','India South','India North','Europe Central','Europe West','North America','Latin America','Asia Pacific']
ROLES=['qc_analyst','qc_manager','qa_reviewer','qa_head','auditor','admin']

def get_or_add(db, model, filters, fields):
    record = db.execute(select(model).filter_by(**filters)).scalar_one_or_none()
    if record: return record
    record=model(**fields)
    db.add(record);db.flush();return record

def setup_master(db, site_count):
    tenant=get_or_add(db,m.Tenant,{'code':'DON-DEMO'},
                      {'code':'DON-DEMO','name':'DON QualityOS Fictional Demo Organization','synthetic':True})
    password=os.getenv('DEMO_PASSWORD','DemoOnly!2026')
    for i,role in enumerate(ROLES):
        email=f'{role}@don-demo.test'
        existing=db.execute(select(m.User).where(m.User.tenant_id==tenant.id,m.User.email==email)).scalar_one_or_none()
        if not existing:
            db.add(m.User(tenant_id=tenant.id,email=email,role=role,password_hash=hash_password(password),site_id=None))
    db.flush()
    sites=[]
    for i in range(site_count):
        code=f'DQ-{i+1:03d}'
        sites.append(get_or_add(db,m.Site,{'tenant_id':tenant.id,'code':code},
            {'tenant_id':tenant.id,'code':code,'name':f'Synthetic Plant {i+1:03d}',
             'region':REGIONS[i % len(REGIONS)]}))
    materials=[]; specs={}; profiles={}
    for code,desc,form in PRODUCTS:
        mat=get_or_add(db,m.Material,{'tenant_id':tenant.id,'code':code},
             {'tenant_id':tenant.id,'code':code,'description':desc,'dosage_form':form})
        materials.append(mat)
        for test,unit,lo,hi,mean,sigma in TESTS:
            spec=get_or_add(db,m.Specification,
                {'material_id':mat.id,'test_name':test,'version':'DEMO-SPEC-v1'},
                {'tenant_id':tenant.id,'material_id':mat.id,'test_name':test,
                 'unit':unit,'lower_limit':lo,'upper_limit':hi,'version':'DEMO-SPEC-v1',
                 'effective_from':datetime(2020,1,1),'approved_for_demo':True})
            profile=get_or_add(db,m.OOTProfile,
                {'specification_id':spec.id,'version':'DEMO-BASE-v1'},
                {'specification_id':spec.id,'version':'DEMO-BASE-v1','mean':mean,
                 'sigma':sigma,'z_threshold':Decimal('3.0'),'baseline_n':90,
                 'method':'SIMULATED mean + 3 SD, not production control limits'})
            specs[(mat.id,test)]=spec
            profiles[(mat.id,test)]=profile
    for code,title in [('SOP-QC-014','OOS Investigation Workflow'),
                       ('SOP-QC-022','OOT Trend Review Workflow'),
                       ('SOP-QA-030','CAPA Management'),
                       ('SOP-DI-001','Data Integrity and Records')]:
        get_or_add(db,m.ControlledDocument,{'tenant_id':tenant.id,'document_code':code,'version':'DEMO-1.0'},
                {'tenant_id':tenant.id,'document_code':code,'version':'DEMO-1.0',
                 'title':title,'content_reference':'synthetic://document/'+code,
                 'checksum':hashlib.sha256((code+title).encode()).hexdigest(),
                 'status':'CONTROLLED_DEMO'})
    references=[
      ('FDA-OOS-2022','REGULATORY','US FDA','Investigating OOS Test Results, May 2022',
       'https://www.fda.gov/regulatory-information/search-fda-guidance-documents/investigating-out-specification-oos-test-results-pharmaceutical-production-level-2-revision','OOS scientific investigation'),
      ('FDA-21CFR-211192','REGULATORY','US FDA / eCFR','21 CFR 211.192 Production record review',
       'https://www.ecfr.gov/current/title-21/chapter-I/subchapter-C/part-211/subpart-J/section-211.192','Production investigation requirements'),
      ('FDA-ICH-Q9-R1','REGULATORY','US FDA / ICH','Quality Risk Management Q9(R1)',
       'https://www.fda.gov/regulatory-information/search-fda-guidance-documents/q9r1-quality-risk-management','Risk-based quality investigations'),
      ('MHRA-GXP-DI','REGULATORY','UK MHRA','GxP data integrity guidance',
       'https://www.gov.uk/government/publications/guidance-on-gxp-data-integrity','Source records and ALCOA+ principles'),
      ('FDA-PART11-SCOPE','REGULATORY','US FDA','Part 11 electronic records scope and application',
       'https://www.fda.gov/regulatory-information/search-fda-guidance-documents/part-11-electronic-records-electronic-signatures-scope-and-application','Electronic records governance'),
      ('SAP-QM-LOT','PUBLIC_BENCHMARK','SAP','Inspection Lots and Quality Notifications',
       'https://learning.sap.com/courses/applying-sap-s-4hana-quality-management/using-inspection-lots-and-quality-notifications-in-the-logistics-supply-chain_a0e23470-b5bb-4b30-b4b8-7e886a42df1c','ERP quality object model, not regulatory instruction'),
      ('SANOFI-QUALITY','PUBLIC_BENCHMARK','Sanofi / Veeva','How Sanofi is Driving Efficiency and Growth with Quality',
       'https://www.veeva.com/customer-stories/sanofi-driving-efficiency-and-growth-with-vault-quality/','Multi-site quality harmonization design only'),
      ('CIPLA-ANNUAL-2023','PUBLIC_BENCHMARK','Cipla','Cipla FY 2022-23 Annual Report',
       'https://www.cipla.com/sites/default/files/Annual-Report-FY-2022-23-Double-page.pdf','TrackWise, CAPA and laboratory modernization design only'),
    ]
    for code,kind,publisher,title,url,scope in references:
        get_or_add(db,m.KnowledgeReference,{'reference_code':code},
             {'reference_code':code,'kind':kind,'publisher':publisher,
              'title':title,'url':url,'scope':scope,'imported_content':False,
              'source_data_classification':'PUBLIC_URL_METADATA'})
    db.commit()
    return tenant,sites,materials,specs,profiles

def create_batches(db,tenant,sites,materials,target):
    existing = db.execute(select(func.count()).select_from(m.Batch).where(m.Batch.tenant_id==tenant.id)).scalar_one()
    if existing>=target:
        return db.execute(select(m.Batch.id,m.Batch.site_id,m.Batch.material_id,m.Batch.batch_number,
                        m.InspectionLot.id,m.InspectionLot.lot_number,m.Sample.id,m.Sample.sample_number)
                        .join(m.InspectionLot,m.InspectionLot.batch_id==m.Batch.id)
                        .join(m.Sample,m.Sample.inspection_lot_id==m.InspectionLot.id)
                        .where(m.Batch.tenant_id==tenant.id).order_by(m.Batch.id).limit(target)).all()
    for i in range(existing,target):
        site=sites[i%len(sites)]; mat=materials[(i//len(sites))%len(materials)]
        batch=m.Batch(tenant_id=tenant.id,site_id=site.id,material_id=mat.id,
            batch_number=f'DON-SYN-B-{i+1:07d}',
            manufactured_at=datetime(2023,1,1)+timedelta(days=i%1300))
        db.add(batch);db.flush()
        lot=m.InspectionLot(tenant_id=tenant.id,batch_id=batch.id,
            lot_number=f'DON-SYN-L-{i+1:07d}',status='OPEN')
        db.add(lot);db.flush()
        db.add(m.Sample(tenant_id=tenant.id,inspection_lot_id=lot.id,sample_number=f'DON-SYN-S-{i+1:07d}'))
        if i%500==0: db.flush()
    db.commit()
    return db.execute(select(m.Batch.id,m.Batch.site_id,m.Batch.material_id,m.Batch.batch_number,
                    m.InspectionLot.id,m.InspectionLot.lot_number,m.Sample.id,m.Sample.sample_number)
                    .join(m.InspectionLot,m.InspectionLot.batch_id==m.Batch.id)
                    .join(m.Sample,m.Sample.inspection_lot_id==m.InspectionLot.id)
                    .where(m.Batch.tenant_id==tenant.id).order_by(m.Batch.id).limit(target)).all()

def generate(db,tenant,sites,materials,specs,profiles,batches,total,seed,chunk_size=1000):
    rng=random.Random(seed)
    existing=db.execute(select(func.count()).select_from(m.TestResult).where(m.TestResult.tenant_id==tenant.id,
                       m.TestResult.source_system=='SYNTHETIC_LIMS')).scalar_one()
    if existing>=total:
        print(f'Results already seeded: {existing} >= requested {total}');return
    buffer=[]; flagged=[]
    site_codes={s.id:s.code for s in sites}
    for i in range(existing,total):
        b=batches[i%len(batches)]
        batch_id,site_id,mat_id,batch_number,lot_id,lot_number,sample_id,sample_number=b
        test,unit,lo,hi,mean,sigma=TESTS[(i//len(batches))%3] if len(batches)>=total else TESTS[i%3]
        # In-spec normal results, scheduled OOT and OOS anomaly scenarios.
        outcome='IN_SPEC'
        injected = 'OOS' if i%101==17 else 'OOT' if i%71==29 else None
        if injected=='OOS':
            value=hi+Decimal('0.45') if i%2 else lo-Decimal('0.25')
            outcome='OOS'
        elif injected=='OOT':
            value=mean+sigma*Decimal('3.5')
            if value<hi and value>lo: outcome='OOT'
            else: value=mean+sigma*Decimal('0.5');injected=None
        else:
            value=mean+sigma*Decimal(str(round(rng.gauss(0,0.78),3)))
            value=max(lo+Decimal('0.05'),min(hi-Decimal('0.05'),value))
        value=value.quantize(Decimal('0.000001'))
        spec=specs[(mat_id,test)]
        profile=profiles[(mat_id,test)]
        measured=datetime(2023,1,1)+timedelta(days=i%1300,hours=i%24)
        source_id=f'SYN-RES-{i+1:09d}'
        data={'source_record_id':source_id,'site_code':site_codes[site_id],
              'batch_number':batch_number,'lot_number':lot_number,
              'sample_number':sample_number,'test_name':test,'value':str(value),
              'specification_id':spec.id,'unit':unit,'measured_at':measured.isoformat()+'Z'}
        buffer.append({'tenant_id':tenant.id,'site_id':site_id,'material_id':mat_id,'batch_id':batch_id,
                       'inspection_lot_id':lot_id,'sample_id':sample_id,'specification_id':spec.id,
                       'oot_profile_id':profile.id,'test_name':test,'value':value,'unit':unit,
                       'outcome':outcome,'measured_at':measured,'source_system':'SYNTHETIC_LIMS',
                       'source_record_id':source_id,'source_hash':hashlib.sha256(str(data).encode()).hexdigest(),
                       'created_at':datetime.utcnow()})
        if outcome in ('OOS','OOT'): flagged.append((source_id,site_id,outcome,str(value)))
        if len(buffer)>=chunk_size or i==total-1:
            db.execute(insert(m.TestResult),buffer)
            if flagged:
                source_ids=[x[0] for x in flagged]
                result_map={r.source_record_id:r.id for r in db.execute(select(m.TestResult).where(
                    m.TestResult.tenant_id==tenant.id,m.TestResult.source_system=='SYNTHETIC_LIMS',
                    m.TestResult.source_record_id.in_(source_ids))).scalars()}
                for source_id,sid,kind,value_str in flagged:
                    result_id=result_map[source_id]
                    alert=m.Alert(tenant_id=tenant.id,site_id=sid,result_id=result_id,
                          kind=kind,severity='CRITICAL' if kind=='OOS' else 'MEDIUM',
                          explanation=f'SYNTHETIC {kind} seed scenario: {value_str}')
                    db.add(alert);db.flush()
                    ev=m.QualityEvent(tenant_id=tenant.id,site_id=sid,alert_id=alert.id,
                        result_id=result_id,event_number=f'DON-SYN-QE-{source_id[8:]}',kind=kind)
                    db.add(ev);db.flush()
                    db.add(m.Investigation(event_id=ev.id,summary='',impact_assessment='',capa_rationale=''))
            db.commit()
            buffer.clear();flagged.clear()
            if (i+1)%50000==0: print(f'Seeded {i+1:,}/{total:,} results')
    tenant_audit(db,tenant.id,None,'SYNTHETIC_DATASET_GENERATED','dataset','SYNTHETIC_LIMS',
                 {'results_requested':total,'seed':seed,'note':'Bulk seed bypasses live ingestion audit per record; non-GMP'})
    db.commit()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--sites',type=int,default=4)
    parser.add_argument('--batches',type=int,default=200)
    parser.add_argument('--results',type=int,default=2000)
    parser.add_argument('--seed',type=int,default=20261029)
    args=parser.parse_args()
    if APP_ENV!='demo': raise SystemExit('Seeder blocked outside APP_ENV=demo')
    if args.sites<1 or args.batches<1 or args.results<1: raise SystemExit('All counts must be positive')
    create_schema()
    with SessionLocal() as db:
        tenant,sites,materials,specs,profiles=setup_master(db,args.sites)
        batches=create_batches(db,tenant,sites,materials,args.batches)
        generate(db,tenant,sites,materials,specs,profiles,batches,args.results,args.seed)
        n=db.execute(select(func.count()).select_from(m.TestResult).where(m.TestResult.tenant_id==tenant.id)).scalar_one()
        alerts=db.execute(select(func.count()).select_from(m.Alert).where(m.Alert.tenant_id==tenant.id)).scalar_one()
        print(f'*** SYNTHETIC NON-GMP DATASET *** sites={len(sites)} batches={len(batches)} results={n} alerts={alerts}')
        print('Example demo accounts: qc_analyst@don-demo.test / qa_reviewer@don-demo.test; password from DEMO_PASSWORD')

if __name__=='__main__': main()
