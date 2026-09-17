from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.models.enums import ClubCategory, ReportStatus, UserRole


def _uuid() -> str:
    return str(uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    sso_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=True, create_constraint=True),
        nullable=False,
        default=UserRole.GUEST,
    )
    can_sudo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    club_leaderships: Mapped[list["ClubLeader"]] = relationship(back_populates="user")
    moderated_reports: Mapped[list["Report"]] = relationship(
        back_populates="moderated_by",
        foreign_keys="Report.moderated_by_id",
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="performed_by")


class Club(Base):
    __tablename__ = "clubs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[ClubCategory] = mapped_column(
        Enum(ClubCategory, name="club_category", native_enum=True, create_constraint=True),
        nullable=False,
    )

    leaders: Mapped[list["ClubLeader"]] = relationship(back_populates="club")
    reports: Mapped[list["Report"]] = relationship(back_populates="club")


class ClubLeader(Base):
    __tablename__ = "club_leaders"
    __table_args__ = (UniqueConstraint("club_id", "user_id", name="uq_club_leaders_club_user"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    club_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    club: Mapped[Club] = relationship(back_populates="leaders")
    user: Mapped[User] = relationship(back_populates="club_leaderships")


class Criteria(Base):
    __tablename__ = "criteria"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    name_ru: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[ClubCategory | None] = mapped_column(
        Enum(ClubCategory, name="club_category", native_enum=True, create_constraint=True),
        nullable=True,
    )

    rules: Mapped[list["CriteriaRule"]] = relationship(back_populates="criteria")
    reports: Mapped[list["Report"]] = relationship(back_populates="criteria")


class RulesVersion(Base):
    __tablename__ = "rules_versions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    semester: Mapped[str] = mapped_column(String(32), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    rules: Mapped[list["CriteriaRule"]] = relationship(back_populates="version")
    reports: Mapped[list["Report"]] = relationship(back_populates="rules_version")


class CriteriaRule(Base):
    __tablename__ = "criteria_rules"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    criteria_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("criteria.id", ondelete="CASCADE"), nullable=False
    )
    rule_type: Mapped[str] = mapped_column(String(64), nullable=False)
    config: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    version_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("rules_versions.id", ondelete="CASCADE"), nullable=False
    )

    criteria: Mapped[Criteria] = relationship(back_populates="rules")
    version: Mapped[RulesVersion] = relationship(back_populates="rules")


class ArchiveBatch(Base):
    __tablename__ = "archive_batches"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    period: Mapped[str] = mapped_column(String(32), nullable=False)
    archived_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    archived_by_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    report_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    reports: Mapped[list["Report"]] = relationship(back_populates="archive_batch")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    club_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("clubs.id", ondelete="RESTRICT"), nullable=False
    )
    criteria_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("criteria.id", ondelete="RESTRICT"), nullable=False
    )
    rules_version_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("rules_versions.id", ondelete="RESTRICT"), nullable=False
    )

    activity_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    report_data: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)

    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, name="report_status", native_enum=True, create_constraint=True),
        nullable=False,
        default=ReportStatus.DRAFT,
    )
    calculated_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    final_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    calculation_method: Mapped[str] = mapped_column(
        String(10), nullable=False, default="auto", server_default="auto"
    )
    manual_points: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    archive_batch_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("archive_batches.id", ondelete="SET NULL"), nullable=True
    )
    moderated_by_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    moderated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    moderation_comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    club: Mapped[Club] = relationship(back_populates="reports")
    criteria: Mapped[Criteria] = relationship(back_populates="reports")
    rules_version: Mapped[RulesVersion] = relationship(back_populates="reports")
    archive_batch: Mapped[ArchiveBatch | None] = relationship(back_populates="reports")
    moderated_by: Mapped[User | None] = relationship(
        back_populates="moderated_reports",
        foreign_keys=[moderated_by_id],
    )
    links: Mapped[list["ReportLink"]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
    )


class ReportLink(Base):
    __tablename__ = "report_links"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    report_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    report: Mapped[Report] = relationship(back_populates="links")


class AuditLog(Base):
    """Append-only audit trail with SHA-256 hash chain.

    DB role must REVOKE UPDATE/DELETE on this table (see migration).
    """

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    # Monotonic chain order (DB-generated).
    seq: Mapped[int] = mapped_column(BigInteger, Identity(always=True), unique=True, nullable=False)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    old_value: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    performed_by_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    performed_by_role: Mapped[str] = mapped_column(String(32), nullable=False)
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    performed_by: Mapped[User] = relationship(back_populates="audit_logs")


class SudoAction(Base):
    """Separate log for sudo-forced actions (in addition to audit_logs)."""

    __tablename__ = "sudo_actions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    performed_by_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    old_value: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AccessViolation(Base):
    __tablename__ = "access_violations"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
