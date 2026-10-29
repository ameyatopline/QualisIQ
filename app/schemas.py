from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, field_validator

class LoginIn(BaseModel):
    email: str
    password: str
    tenant_code: str='DON-DEMO'

class LabResultIn(BaseModel):
    site_code: str
    material_code: str
    batch_number: str
    inspection_lot: str
    sample_number: str
    test_name: str
    value: Decimal
    unit: str
    measured_at: datetime
    source_system: str = Field(min_length=2, max_length=60)
    source_record_id: str = Field(min_length=2, max_length=140)
    idempotency_key: str = Field(min_length=4, max_length=160)

    @field_validator('value')
    @classmethod
    def finite_value(cls, v):
        if not v.is_finite(): raise ValueError('Result must be finite')
        return v

class InvestigationUpdate(BaseModel):
    summary: str = Field(min_length=12, max_length=10000)
    root_cause_hypothesis: str = Field(default='', max_length=10000)
    impact_assessment: str = Field(min_length=12, max_length=10000)
    capa_rationale: str = Field(min_length=12, max_length=5000)
    expected_version: int

class TransitionIn(BaseModel):
    target_status: str
    reason: str = Field(min_length=12, max_length=2000)
    expected_version: int

class EvidenceIn(BaseModel):
    kind: str = Field(min_length=3, max_length=50)
    label: str = Field(min_length=5, max_length=240)
    reference_uri: str = Field(min_length=6, max_length=500)
    sha256: str = Field(pattern=r'^[0-9a-f]{64}$')

class CAPAIn(BaseModel):
    title: str = Field(min_length=12, max_length=240)
    assigned_to_id: int
    due_at: datetime

class CAPAUpdate(BaseModel):
    status: str
    effectiveness_note: str = Field(min_length=12, max_length=5000)

class Page(BaseModel):
    items: list[dict]
    total: int
    limit: int
    offset: int
