from datetime import UTC, date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


USER_ROLES = ("seafarer", "manager", "cert_admin", "shipowner", "admin")
CREW_STATUSES = ("available", "pending", "at_sea", "inactive")
JOB_STATUSES = ("open", "matched", "closed")
DISPATCH_STATUSES = ("pending_owner", "confirmed", "onboard", "offboard", "cancelled")
VOYAGE_STATUSES = ("onboard", "offboard", "cancelled")


class Base(DeclarativeBase):
    pass


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _sql_values(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(f"role in ({_sql_values(USER_ROLES)})", name="ck_users_role"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    display_name: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=utc_now,
    )

    crew: Mapped["Crew | None"] = relationship(back_populates="user")


class Crew(Base):
    __tablename__ = "crews"
    __table_args__ = (
        CheckConstraint("gender in ('男', '女')", name="ck_crews_gender"),
        CheckConstraint(
            f"status in ({_sql_values(CREW_STATUSES)})",
            name="ck_crews_status",
        ),
        Index("idx_crews_status", "status"),
        Index("idx_crews_position", "position"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    gender: Mapped[str] = mapped_column(String(10), nullable=False, default="男")
    id_card: Mapped[str] = mapped_column(String(18), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    position: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="available")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=utc_now,
    )

    user: Mapped[User] = relationship(back_populates="crew")
    certificates: Mapped[list["Certificate"]] = relationship(back_populates="crew")
    dispatches: Mapped[list["Dispatch"]] = relationship(back_populates="crew")
    voyages: Mapped[list["VoyageRecord"]] = relationship(back_populates="crew")


class Certificate(Base):
    __tablename__ = "certificates"
    __table_args__ = (
        UniqueConstraint("certificate_no", name="uq_certificates_certificate_no"),
        Index("idx_certificates_crew_id", "crew_id"),
        Index("idx_certificates_type", "certificate_type"),
        Index("idx_certificates_expires_at", "expires_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    crew_id: Mapped[int] = mapped_column(
        ForeignKey("crews.id", ondelete="CASCADE"),
        nullable=False,
    )
    certificate_type: Mapped[str] = mapped_column(String(50), nullable=False)
    certificate_no: Mapped[str] = mapped_column(String(80), nullable=False)
    issued_at: Mapped[date] = mapped_column(Date, nullable=False)
    expires_at: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=utc_now,
    )

    crew: Mapped[Crew] = relationship(back_populates="certificates")


class JobDemand(Base):
    __tablename__ = "job_demands"
    __table_args__ = (
        CheckConstraint(
            f"status in ({_sql_values(JOB_STATUSES)})",
            name="ck_job_demands_status",
        ),
        Index("idx_job_demands_owner_user_id", "owner_user_id"),
        Index("idx_job_demands_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    ship_name: Mapped[str] = mapped_column(String(100), nullable=False)
    route: Mapped[str] = mapped_column(String(100), nullable=False)
    required_position: Mapped[str] = mapped_column(String(50), nullable=False)
    headcount: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    onboard_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=utc_now,
    )

    required_certificates: Mapped[list["JobRequiredCertificate"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )
    dispatches: Mapped[list["Dispatch"]] = relationship(back_populates="job")


class JobRequiredCertificate(Base):
    __tablename__ = "job_required_certificates"
    __table_args__ = (
        UniqueConstraint("job_id", "certificate_type", name="uq_job_required_certificate"),
        Index("idx_job_required_certificates_job_id", "job_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("job_demands.id", ondelete="CASCADE"),
        nullable=False,
    )
    certificate_type: Mapped[str] = mapped_column(String(50), nullable=False)

    job: Mapped[JobDemand] = relationship(back_populates="required_certificates")


class Dispatch(Base):
    __tablename__ = "dispatches"
    __table_args__ = (
        CheckConstraint(
            f"status in ({_sql_values(DISPATCH_STATUSES)})",
            name="ck_dispatches_status",
        ),
        Index("idx_dispatches_job_id", "job_id"),
        Index("idx_dispatches_crew_id", "crew_id"),
        Index("idx_dispatches_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job_demands.id"), nullable=False)
    crew_id: Mapped[int] = mapped_column(ForeignKey("crews.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending_owner")
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    confirmed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=utc_now,
    )

    job: Mapped[JobDemand] = relationship(back_populates="dispatches")
    crew: Mapped[Crew] = relationship(back_populates="dispatches")
    voyage: Mapped["VoyageRecord | None"] = relationship(back_populates="dispatch")


class VoyageRecord(Base):
    __tablename__ = "voyage_records"
    __table_args__ = (
        CheckConstraint(
            f"status in ({_sql_values(VOYAGE_STATUSES)})",
            name="ck_voyage_records_status",
        ),
        Index("idx_voyage_records_crew_id", "crew_id"),
        Index("idx_voyage_records_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dispatch_id: Mapped[int] = mapped_column(ForeignKey("dispatches.id"), unique=True)
    crew_id: Mapped[int] = mapped_column(ForeignKey("crews.id"), nullable=False)
    job_id: Mapped[int] = mapped_column(ForeignKey("job_demands.id"), nullable=False)
    ship_name: Mapped[str] = mapped_column(String(100), nullable=False)
    route: Mapped[str] = mapped_column(String(100), nullable=False)
    position: Mapped[str] = mapped_column(String(50), nullable=False)
    onboard_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    offboard_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="onboard")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=utc_now,
    )

    dispatch: Mapped[Dispatch] = relationship(back_populates="voyage")
    crew: Mapped[Crew] = relationship(back_populates="voyages")
