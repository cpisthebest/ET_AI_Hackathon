import uuid
from datetime import datetime, date
from sqlalchemy import String, Text, DateTime, Date, ForeignKey, Integer, Float, Boolean, JSON, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.db.base import Base


class SourceDocument(Base):
    __tablename__ = "source_documents"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_type: Mapped[str] = mapped_column(String(50), index=True)
    title: Mapped[str] = mapped_column(String(500))
    sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    source_uri: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class RegulatoryDocument(Base):
    __tablename__ = "regulatory_documents"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("source_documents.id", ondelete="CASCADE"), unique=True)
    title: Mapped[str] = mapped_column(String(500))
    regulator: Mapped[str] = mapped_column(String(200))
    publication_date: Mapped[date | None] = mapped_column(Date)
    sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    source_uri: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    source_document = relationship("SourceDocument")
    versions = relationship("RegulationVersion", back_populates="document", cascade="all, delete-orphan")


class RegulationVersion(Base):
    __tablename__ = "regulation_versions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("regulatory_documents.id", ondelete="CASCADE"))
    version_label: Mapped[str] = mapped_column(String(100))
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("regulation_versions.id"))
    status: Mapped[str] = mapped_column(String(30), default="active")
    document = relationship("RegulatoryDocument", back_populates="versions")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("source_documents.id", ondelete="CASCADE"))
    chunk_index: Mapped[int] = mapped_column(Integer)
    page_number: Mapped[int | None] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    content_tsv: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384))
    document = relationship("SourceDocument", back_populates="chunks")
    __table_args__ = (Index("ix_chunks_document_index", "document_id", "chunk_index"),)


class Obligation(Base):
    __tablename__ = "obligations"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    regulation_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("regulation_versions.id", ondelete="CASCADE"))
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("source_documents.id", ondelete="SET NULL"), nullable=True)
    obligation_key: Mapped[str] = mapped_column(String(200), unique=True)
    text: Mapped[str] = mapped_column(Text)
    subject: Mapped[str] = mapped_column(String(300))
    action: Mapped[str] = mapped_column(String(300))
    frequency: Mapped[str | None] = mapped_column(String(100))
    retention_years: Mapped[int | None] = mapped_column(Integer)
    applicability_rule: Mapped[str] = mapped_column(Text, default="")
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)


class Control(Base):
    __tablename__ = "controls"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    control_key: Mapped[str] = mapped_column(String(200), unique=True)
    name: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)
    owner: Mapped[str] = mapped_column(String(200))
    frequency: Mapped[str | None] = mapped_column(String(100))
    retention_years: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(50), default="active")


class ControlDocument(Base):
    __tablename__ = "control_documents"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    control_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("controls.id", ondelete="CASCADE"))
    source_document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("source_documents.id", ondelete="CASCADE"))
    control = relationship("Control")
    source_document = relationship("SourceDocument")


class ObligationControlMapping(Base):
    __tablename__ = "obligation_control_mappings"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    obligation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("obligations.id", ondelete="CASCADE"))
    control_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("controls.id", ondelete="CASCADE"))
    mapping_confidence: Mapped[float] = mapped_column(Float)
    rationale: Mapped[str] = mapped_column(Text)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("source_documents.id", ondelete="SET NULL"), nullable=True)


class Evidence(Base):
    __tablename__ = "evidence"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    control_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("controls.id", ondelete="SET NULL"), nullable=True)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("source_documents.id", ondelete="SET NULL"))
    evidence_key: Mapped[str] = mapped_column(String(200), unique=True)
    description: Mapped[str] = mapped_column(Text)
    evidence_date: Mapped[date | None] = mapped_column(Date)
    source_uri: Mapped[str | None] = mapped_column(String(1000))
    sha256: Mapped[str | None] = mapped_column(String(64))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    source_document = relationship("SourceDocument")


class TestResult(Base):
    __tablename__ = "test_results"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    control_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("controls.id", ondelete="CASCADE"))
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("evidence.id"))
    test_name: Mapped[str] = mapped_column(String(500))
    result: Mapped[str] = mapped_column(String(50))
    score: Mapped[float] = mapped_column(Float)
    findings: Mapped[str] = mapped_column(Text)
    tested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("source_documents.id", ondelete="SET NULL"), nullable=True)


class Gap(Base):
    __tablename__ = "gaps"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    obligation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("obligations.id", ondelete="CASCADE"))
    control_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("controls.id"))
    severity: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)
    evidence_basis: Mapped[str] = mapped_column(Text)
    remediation: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="open")
    human_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("source_documents.id", ondelete="SET NULL"), nullable=True)


class Remediation(Base):
    __tablename__ = "remediations"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    gap_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("gaps.id", ondelete="CASCADE"))
    action: Mapped[str] = mapped_column(Text)
    owner: Mapped[str | None] = mapped_column(String(200))
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(50), default="proposed")
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("source_documents.id", ondelete="SET NULL"), nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[str] = mapped_column(String(100))
    actor: Mapped[str] = mapped_column(String(200))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
