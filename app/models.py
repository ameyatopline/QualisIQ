"""Core transactional domain models; compact demo schema, migration needed before prod."""
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import (String, ForeignKey, UniqueConstraint, Index, Boolean, Integer,
                        Numeric, DateTime, Text, JSON)
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

def utcnow():
    return datetime.now(timezone.utc)

class Tenant(Base):
    __tablename__ = 'tenants'
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    synthetic: Mapped[bool] = mapped_column(Boolean, default=True)

class Site(Base):
    __tablename__ = 'sites'
    __table_args__ = (UniqueConstraint('tenant_id', 'code'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id'), index=True)
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(150))
    region: Mapped[str] = mapped_column(String(80), default='Demo Region')

class User(Base):
    __tablename__ = 'users'
    __table_args__ = (UniqueConstraint('tenant_id', 'email'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id'), index=True)
    site_id: Mapped[int | None] = mapped_column(ForeignKey('sites.id'), nullable=True)
    email: Mapped[str] = mapped_column(String(180))
    password_hash: Mapped[str] = mapped_column(String(240))
    role: Mapped[str] = mapped_column(String(32))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Material(Base):
    __tablename__ = 'materials'
    __table_args__ = (UniqueConstraint('tenant_id', 'code'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id'), index=True)
    code: Mapped[str] = mapped_column(String(48))
    description: Mapped[str] = mapped_column(String(180))
    dosage_form: Mapped[str] = mapped_column(String(50))

class Specification(Base):
    __tablename__ = 'specifications'
    __table_args__ = (UniqueConstraint('material_id', 'test_name', 'version'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id'), index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey('materials.id'), index=True)
    test_name: Mapped[str] = mapped_column(String(100))
    unit: Mapped[str] = mapped_column(String(24))
    lower_limit: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    upper_limit: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    version: Mapped[str] = mapped_column(String(40))
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_for_demo: Mapped[bool] = mapped_column(Boolean, default=True)

class OOTProfile(Base):
    __tablename__ = 'oot_profiles'
    __table_args__ = (UniqueConstraint('specification_id', 'version'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    specification_id: Mapped[int] = mapped_column(ForeignKey('specifications.id'), index=True)
    version: Mapped[str] = mapped_column(String(40))
    mean: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    sigma: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    z_threshold: Mapped[Decimal] = mapped_column(Numeric(8, 3), default=Decimal('3.0'))
    baseline_n: Mapped[int] = mapped_column(Integer)
    method: Mapped[str] = mapped_column(String(80), default='Approved demo Shewhart Z')
    approved_for_demo: Mapped[bool] = mapped_column(Boolean, default=True)

class Batch(Base):
    __tablename__ = 'batches'
    __table_args__ = (UniqueConstraint('tenant_id', 'batch_number'), Index('ix_batches_site_material', 'site_id', 'material_id'))
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id'), index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey('sites.id'), index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey('materials.id'))
    batch_number: Mapped[str] = mapped_column(String(70))
    manufactured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # No automated batch release or disposition.

class InspectionLot(Base):
    __tablename__ = 'inspection_lots'
    __table_args__ = (UniqueConstraint('tenant_id', 'lot_number'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id'), index=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey('batches.id'), index=True)
    lot_number: Mapped[str] = mapped_column(String(70))
    inspection_type: Mapped[str] = mapped_column(String(40), default='FINISHED_PRODUCT')
    status: Mapped[str] = mapped_column(String(30), default='OPEN')

class Sample(Base):
    __tablename__ = 'samples'
    __table_args__ = (UniqueConstraint('tenant_id', 'sample_number'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id'), index=True)
    inspection_lot_id: Mapped[int] = mapped_column(ForeignKey('inspection_lots.id'), index=True)
    sample_number: Mapped[str] = mapped_column(String(80))

class TestResult(Base):
    __tablename__ = 'test_results'
    __table_args__ = (UniqueConstraint('tenant_id', 'source_system', 'source_record_id'), Index('ix_results_tenant_test_time', 'tenant_id', 'test_name', 'measured_at'))
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id'), index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey('sites.id'), index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey('materials.id'))
    batch_id: Mapped[int] = mapped_column(ForeignKey('batches.id'), index=True)
    inspection_lot_id: Mapped[int] = mapped_column(ForeignKey('inspection_lots.id'), index=True)
    sample_id: Mapped[int] = mapped_column(ForeignKey('samples.id'), index=True)
    specification_id: Mapped[int] = mapped_column(ForeignKey('specifications.id'))
    oot_profile_id: Mapped[int | None] = mapped_column(ForeignKey('oot_profiles.id'), nullable=True)
    test_name: Mapped[str] = mapped_column(String(100))
    value: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    unit: Mapped[str] = mapped_column(String(24))
    outcome: Mapped[str] = mapped_column(String(32))
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_system: Mapped[str] = mapped_column(String(60))
    source_record_id: Mapped[str] = mapped_column(String(140))
    source_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Alert(Base):
    __tablename__ = 'alerts'
    __table_args__ = (UniqueConstraint('result_id', 'kind'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id'), index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey('sites.id'), index=True)
    result_id: Mapped[int] = mapped_column(ForeignKey('test_results.id'), index=True)
    kind: Mapped[str] = mapped_column(String(12))
    explanation: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(12), default='HIGH')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class QualityEvent(Base):
    __tablename__ = 'quality_events'
    __table_args__ = (UniqueConstraint('tenant_id', 'event_number'), UniqueConstraint('alert_id'))
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id'), index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey('sites.id'), index=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey('alerts.id'))
    result_id: Mapped[int] = mapped_column(ForeignKey('test_results.id'), index=True)
    event_number: Mapped[str] = mapped_column(String(60))
    kind: Mapped[str] = mapped_column(String(12))
    status: Mapped[str] = mapped_column(String(40), default='DETECTED')
    investigator_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Investigation(Base):
    __tablename__ = 'investigations'
    __table_args__ = (UniqueConstraint('event_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey('quality_events.id'), index=True)
    summary: Mapped[str] = mapped_column(Text, default='')
    root_cause_hypothesis: Mapped[str] = mapped_column(Text, default='')
    impact_assessment: Mapped[str] = mapped_column(Text, default='')
    capa_rationale: Mapped[str] = mapped_column(Text, default='')
    approved_by: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class Evidence(Base):
    __tablename__ = 'evidence'
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id'))
    event_id: Mapped[int] = mapped_column(ForeignKey('quality_events.id'), index=True)
    kind: Mapped[str] = mapped_column(String(50))
    label: Mapped[str] = mapped_column(String(240))
    reference_uri: Mapped[str] = mapped_column(String(500))
    sha256: Mapped[str] = mapped_column(String(64))
    created_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class CAPA(Base):
    __tablename__ = 'capas'
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id'), index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey('quality_events.id'), index=True)
    title: Mapped[str] = mapped_column(String(240))
    assigned_to_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(40), default='OPEN')
    effectiveness_note: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class ControlledDocument(Base):
    __tablename__ = 'controlled_documents'
    __table_args__ = (UniqueConstraint('tenant_id', 'document_code', 'version'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id'), index=True)
    document_code: Mapped[str] = mapped_column(String(80))
    version: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(250))
    content_reference: Mapped[str] = mapped_column(String(500))
    checksum: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(40), default='CONTROLLED_DEMO')

class AuditHead(Base):
    __tablename__ = 'audit_heads'
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id'), primary_key=True)
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    last_hash: Mapped[str] = mapped_column(String(64), default='0'*64)

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    __table_args__ = (UniqueConstraint('tenant_id', 'sequence'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id'), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    resource_type: Mapped[str] = mapped_column(String(60))
    resource_id: Mapped[str] = mapped_column(String(80))
    data_json: Mapped[dict] = mapped_column(JSON)
    happened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    prev_hash: Mapped[str] = mapped_column(String(64))
    event_hash: Mapped[str] = mapped_column(String(64))

class IntegrationReceipt(Base):
    __tablename__ = 'integration_receipts'
    __table_args__ = (UniqueConstraint('tenant_id', 'source_system', 'idempotency_key'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id'), index=True)
    source_system: Mapped[str] = mapped_column(String(60))
    idempotency_key: Mapped[str] = mapped_column(String(160))
    request_hash: Mapped[str] = mapped_column(String(64))
    result_id: Mapped[int] = mapped_column(ForeignKey('test_results.id'))

class OutboxEvent(Base):
    __tablename__ = 'outbox_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id'), index=True)
    event_type: Mapped[str] = mapped_column(String(100))
    payload_json: Mapped[dict] = mapped_column(JSON)
    delivery_status: Mapped[str] = mapped_column(String(25), default='PENDING')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class KnowledgeReference(Base):
    """Public metadata only: no proprietary/full-text documents stored."""
    __tablename__ = 'knowledge_references'
    id: Mapped[int] = mapped_column(primary_key=True)
    reference_code: Mapped[str] = mapped_column(String(64), unique=True)
    kind: Mapped[str] = mapped_column(String(30))
    publisher: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(250))
    url: Mapped[str] = mapped_column(String(650))
    scope: Mapped[str] = mapped_column(String(300))
    imported_content: Mapped[bool] = mapped_column(Boolean, default=False)
    source_data_classification: Mapped[str] = mapped_column(String(50), default='PUBLIC_URL_METADATA')
