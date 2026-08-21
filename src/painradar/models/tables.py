"""Esquema de la base de datos.

Una sola tabla `opportunity` sirve a los dos carriles: un proyecto de
Freelancer y un issue de GitHub son, estructuralmente, lo mismo — algo que
alguien publicó, que puedo resolver, y donde llegar temprano importa. Los
campos que solo aplican a un carril son nullable y están agrupados y
comentados como tales.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from painradar.models.base import Base, TimestampMixin
from painradar.models.enums import DraftKind, OutcomeStatus, Track


class Source(Base, TimestampMixin):
    """Una fuente de oportunidades: freelancer, github, stackexchange, reddit..."""

    __tablename__ = "source"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    track: Mapped[Track] = mapped_column(String(20), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    poll_interval_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    last_fetch_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    config_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    opportunities: Mapped[list[Opportunity]] = relationship(back_populates="source")


class Opportunity(Base, TimestampMixin):
    """Algo publicado por alguien que yo podría resolver."""

    __tablename__ = "opportunity"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_opportunity_source_external"),
        Index("ix_opportunity_published_at", "published_at"),
        Index("ix_opportunity_track_fetched", "track", "fetched_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("source.id"), nullable=False)
    track: Mapped[Track] = mapped_column(String(20), nullable=False)

    external_id: Mapped[str] = mapped_column(String(120), nullable=False)
    url: Mapped[str] = mapped_column(String(600), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)

    author: Mapped[str | None] = mapped_column(String(200))
    tags_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # --- solo track SALES ---
    budget_min: Mapped[float | None] = mapped_column(Float)
    budget_max: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str | None] = mapped_column(String(10))
    is_hourly: Mapped[bool | None] = mapped_column(Boolean)
    bids_count: Mapped[int | None] = mapped_column(Integer)
    client_country: Mapped[str | None] = mapped_column(String(80))
    client_rating: Mapped[float | None] = mapped_column(Float)
    client_spend: Mapped[float | None] = mapped_column(Float)
    client_payment_verified: Mapped[bool | None] = mapped_column(Boolean)

    # --- solo track CONTRIB ---
    container: Mapped[str | None] = mapped_column(String(200))  # repo, subreddit o sitio SE
    engagement_count: Mapped[int | None] = mapped_column(Integer)  # comentarios / respuestas
    is_answered: Mapped[bool | None] = mapped_column(Boolean)
    score: Mapped[int | None] = mapped_column(Integer)  # upvotes / reacciones

    # Respuesta cruda tal cual llegó. Permite re-normalizar sin volver a la red
    # y es la materia prima del análisis de la fase 0.
    raw_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    source: Mapped[Source] = relationship(back_populates="opportunities")
    assessment: Mapped[Assessment | None] = relationship(
        back_populates="opportunity", uselist=False, cascade="all, delete-orphan"
    )
    drafts: Mapped[list[Draft]] = relationship(
        back_populates="opportunity", cascade="all, delete-orphan"
    )
    outcome: Mapped[Outcome | None] = relationship(
        back_populates="opportunity", uselist=False, cascade="all, delete-orphan"
    )


class Assessment(Base, TimestampMixin):
    """Veredicto del filtro de reglas + el clasificador de IA (fase 2)."""

    __tablename__ = "assessment"

    id: Mapped[int] = mapped_column(primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(
        ForeignKey("opportunity.id"), unique=True, nullable=False
    )
    passed_rules: Mapped[bool] = mapped_column(Boolean, nullable=False)
    rule_reason: Mapped[str | None] = mapped_column(String(300))
    vertical: Mapped[str | None] = mapped_column(String(60))
    fit_score: Mapped[int | None] = mapped_column(Integer)  # 1-5: ¿lo sé hacer?
    quality_score: Mapped[int | None] = mapped_column(Integer)  # 1-5: ¿vale la pena?
    effort_hours: Mapped[float | None] = mapped_column(Float)  # estimación, clave en CONTRIB
    red_flags_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    reasoning: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(String(60))
    cost_usd: Mapped[float | None] = mapped_column(Float)

    opportunity: Mapped[Opportunity] = relationship(back_populates="assessment")


class Draft(Base, TimestampMixin):
    """Borrador generado por la IA. Nunca se publica solo."""

    __tablename__ = "draft"

    id: Mapped[int] = mapped_column(primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunity.id"), nullable=False)
    kind: Mapped[DraftKind] = mapped_column(String(20), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    angle: Mapped[str | None] = mapped_column(String(200))
    suggested_rate: Mapped[float | None] = mapped_column(Float)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    model: Mapped[str | None] = mapped_column(String(60))
    cost_usd: Mapped[float | None] = mapped_column(Float)

    opportunity: Mapped[Opportunity] = relationship(back_populates="drafts")


class Outcome(Base):
    """Qué pasó de verdad. Sin esto no hay reporte semanal ni ajuste del filtro."""

    __tablename__ = "outcome"

    id: Mapped[int] = mapped_column(primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(
        ForeignKey("opportunity.id"), unique=True, nullable=False
    )
    status: Mapped[OutcomeStatus] = mapped_column(
        String(20), default=OutcomeStatus.NEW, nullable=False
    )
    discard_reason: Mapped[str | None] = mapped_column(String(300))
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)

    opportunity: Mapped[Opportunity] = relationship(back_populates="outcome")
