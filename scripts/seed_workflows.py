#!/usr/bin/env python3
"""SYNTHETIC investigation histories for demo navigation. No real QC/QA approvals."""
from pathlib import Path
import sys, hashlib, argparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select
from app.database import SessionLocal
from app.security import APP_ENV
from app import models as m
from app.services import transition,tenant_audit

HYPOTHESES=[
 'SIMULATED HYPOTHESIS: unusual sample dilution factor; raw data review required.',
 'SIMULATED HYPOTHESIS: method-version change could affect trend interpretation.',
 'SIMULATED HYPOTHESIS: instrument calibration status must be verified.',
 'SIMULATED HYPOTHESIS: atypical stability timepoint may merit review.',
 'SIMULATED HYPOTHESIS: standard preparation/recovery should be assessed.',
]


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--cases',type=int,default=240)
    args=p.parse_args()
    if APP_ENV!='demo':raise SystemExit('Demo-only generator')
    with SessionLocal() as db:
        tenant=db.execute(select(m.Tenant).where(m.Tenant.code=='DON-DEMO')).scalar_one()
        actors={u.role:u for u in db.execute(select(m.User).where(m.User.tenant_id==tenant.id)).scalars()}
        events=db.execute(select(m.QualityEvent).where(m.QualityEvent.tenant_id==tenant.id,
                          m.QualityEvent.status!='DOES_NOT_EXIST').order_by(m.QualityEvent.id).limit(args.cases)).scalars().all()
        for i,ev in enumerate(events):
            if ev.status != 'DETECTED': continue
            analyst=actors['qc_analyst'];manager=actors['qc_manager'];qa=actors['qa_reviewer']
            depth=i%10
            path=(['TRIAGED','PHASE_I_OPEN','PHASE_I_REVIEW']+
                  (['PHASE_II_OPEN','PHASE_II_REVIEW'] if i%3==0 else [])+
                  ['QA_EVALUATION','REPORT_DRAFT','QA_REVIEW_PENDING','APPROVED','CLOSED']
                  if ev.kind=='OOS' else
                  ['TRIAGED','OOT_REVIEW']+(['OOT_ESCALATED'] if i%3==0 else [])+
                  ['QA_EVALUATION','REPORT_DRAFT','QA_REVIEW_PENDING','APPROVED','CLOSED'])
            # Distribute stages across open, reviewed and closed cases.
            length=min(len(path),max(1,int((depth+1)*len(path)/10)))
            inv=db.execute(select(m.Investigation).where(m.Investigation.event_id==ev.id)).scalar_one()
            inv.summary=f'SYNTHETIC CASE ONLY: Demo laboratory event {ev.event_number}; human verification simulated.'
            inv.root_cause_hypothesis=HYPOTHESES[i%len(HYPOTHESES)]
            inv.impact_assessment='SIMULATED: assess associated lots, same instrument and method version.'
            inv.capa_rationale='SIMULATED: QA determines whether CAPA is justified by verified evidence.'
            doc_ref=f'synthetic://lab-evidence/{ev.event_number}'
            digest=hashlib.sha256(doc_ref.encode()).hexdigest()
            evid=db.execute(select(m.Evidence).where(m.Evidence.event_id==ev.id)).scalar_one_or_none()
            if not evid:
                db.add(m.Evidence(tenant_id=tenant.id,event_id=ev.id,kind='SIMULATED_CDS_RECORD',
                    label='SYNTHETIC analyst raw-data review placeholder',
                    reference_uri=doc_ref,sha256=digest,created_by=analyst.id))
                db.flush()
                tenant_audit(db,tenant.id,analyst.id,'DEMO_EVIDENCE_CREATED','quality_event',str(ev.id),
                             {'synthetic':True,'evidence_uri':doc_ref})
            for state in path[:length]:
                actor = qa if state in ('APPROVED','CLOSED') else manager if state in (
                  'PHASE_II_OPEN','QA_EVALUATION','REPORT_DRAFT','OOT_ESCALATED') else analyst
                transition(db,ev,actor,state,'Synthetic demo walkthrough; no real QC/QA review',ev.version)
            if i%4==0:
                capa=m.CAPA(tenant_id=tenant.id,event_id=ev.id,title='SYNTHETIC: evaluate lab process control',
                    assigned_to_id=analyst.id,due_at=__import__('datetime').datetime(2027,1,30),
                    status='OPEN',effectiveness_note='No verified effectiveness; demo only')
                db.add(capa);db.flush()
                tenant_audit(db,tenant.id,manager.id,'DEMO_CAPA_CREATED','capa',str(capa.id),
                             {'event_id':ev.id,'synthetic':True})
            if i%25==0:
                db.commit()
        db.commit()
        print(f'Prepared {len(events)} synthetic investigation histories; do not interpret as real GxP approvals.')

if __name__=='__main__':main()
