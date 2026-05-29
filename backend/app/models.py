from datetime import UTC, date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


USER_ROLES = ("seafarer", "manager", "cert_admin", "shipowner", "admin")
CREW_STATUSES = ("available", "pending", "at_sea", "inactive")
JOB_STATUSES = ("open", "matched", "closed")
DISPATCH_STATUSES = ("pending_owner", "confirmed", "onboard", "offboard", "cancelled")
VOYAGE_STATUSES = ("onboard", "offboard", "cancelled")
CERTIFICATE_REVIEW_STATUSES = ("pending", "approved", "rejected")
SHIP_STATUSES = ("active", "maintenance", "inactive")
ROUTE_STATUSES = ("active", "inactive")


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


class ShipCompany(Base):
    __tablename__ = "ship_companies"
    __table_args__ = (
        UniqueConstraint("name", name="uq_ship_companies_name"),
        Index("idx_ship_companies_owner_user_id", "owner_user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    contact_name: Mapped[str | None] = mapped_column(String(50))
    phone: Mapped[str | None] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(String(200))
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

    ships: Mapped[list["Ship"]] = relationship(back_populates="company")


class Ship(Base):
    __tablename__ = "ships"
    __table_args__ = (
        CheckConstraint(
            f"status in ({_sql_values(SHIP_STATUSES)})",
            name="ck_ships_status",
        ),
        UniqueConstraint("name", name="uq_ships_name"),
        Index("idx_ships_company_id", "company_id"),
        Index("idx_ships_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("ship_companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    ship_type: Mapped[str] = mapped_column(String(50), nullable=False, default="bulk")
    tonnage: Mapped[int | None] = mapped_column(Integer)
    capacity: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
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

    company: Mapped[ShipCompany] = relationship(back_populates="ships")
    jobs: Mapped[list["JobDemand"]] = relationship(back_populates="ship")


class Port(Base):
    __tablename__ = "ports"
    __table_args__ = (
        UniqueConstraint("name", name="uq_ports_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(50), nullable=False, default="中国")
    city: Mapped[str | None] = mapped_column(String(50))
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

    departure_routes: Mapped[list["Route"]] = relationship(
        foreign_keys="Route.departure_port_id",
        back_populates="departure_port",
    )
    destination_routes: Mapped[list["Route"]] = relationship(
        foreign_keys="Route.destination_port_id",
        back_populates="destination_port",
    )


class Route(Base):
    __tablename__ = "routes"
    __table_args__ = (
        CheckConstraint(
            f"status in ({_sql_values(ROUTE_STATUSES)})",
            name="ck_routes_status",
        ),
        UniqueConstraint(
            "departure_port_id",
            "destination_port_id",
            "route_name",
            name="uq_routes_path_name",
        ),
        Index("idx_routes_departure_port_id", "departure_port_id"),
        Index("idx_routes_destination_port_id", "destination_port_id"),
        Index("idx_routes_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    route_name: Mapped[str] = mapped_column(String(120), nullable=False)
    departure_port_id: Mapped[int] = mapped_column(ForeignKey("ports.id"), nullable=False)
    destination_port_id: Mapped[int] = mapped_column(ForeignKey("ports.id"), nullable=False)
    distance_nm: Mapped[int | None] = mapped_column(Integer)
    estimated_days: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
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

    departure_port: Mapped[Port] = relationship(
        foreign_keys=[departure_port_id],
        back_populates="departure_routes",
    )
    destination_port: Mapped[Port] = relationship(
        foreign_keys=[destination_port_id],
        back_populates="destination_routes",
    )
    jobs: Mapped[list["JobDemand"]] = relationship(back_populates="route_ref")


class Position(Base):
    __tablename__ = "positions"
    __table_args__ = (
        UniqueConstraint("name", name="uq_positions_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    level: Mapped[str | None] = mapped_column(String(30))
    base_salary: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(String(200))
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

    crews: Mapped[list["Crew"]] = relationship(back_populates="position_ref")
    jobs: Mapped[list["JobDemand"]] = relationship(back_populates="position_ref")


class CertificateType(Base):
    __tablename__ = "certificate_types"
    __table_args__ = (
        UniqueConstraint("name", name="uq_certificate_types_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    validity_months: Mapped[int | None] = mapped_column(Integer)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    description: Mapped[str | None] = mapped_column(String(200))
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

    certificates: Mapped[list["Certificate"]] = relationship(back_populates="certificate_type_ref")


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
        Index("idx_crews_position_id", "position_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    position_id: Mapped[int | None] = mapped_column(ForeignKey("positions.id"))
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
    position_ref: Mapped[Position | None] = relationship(back_populates="crews")
    certificates: Mapped[list["Certificate"]] = relationship(back_populates="crew")
    dispatches: Mapped[list["Dispatch"]] = relationship(back_populates="crew")
    voyages: Mapped[list["VoyageRecord"]] = relationship(back_populates="crew")


class Certificate(Base):
    __tablename__ = "certificates"
    __table_args__ = (
        CheckConstraint(
            f"review_status in ({_sql_values(CERTIFICATE_REVIEW_STATUSES)})",
            name="ck_certificates_review_status",
        ),
        UniqueConstraint("certificate_no", name="uq_certificates_certificate_no"),
        Index("idx_certificates_crew_id", "crew_id"),
        Index("idx_certificates_type", "certificate_type"),
        Index("idx_certificates_certificate_type_id", "certificate_type_id"),
        Index("idx_certificates_expires_at", "expires_at"),
        Index("idx_certificates_review_status", "review_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    crew_id: Mapped[int] = mapped_column(
        ForeignKey("crews.id", ondelete="CASCADE"),
        nullable=False,
    )
    certificate_type_id: Mapped[int | None] = mapped_column(ForeignKey("certificate_types.id"))
    certificate_type: Mapped[str] = mapped_column(String(50), nullable=False)
    certificate_no: Mapped[str] = mapped_column(String(80), nullable=False)
    issued_at: Mapped[date] = mapped_column(Date, nullable=False)
    expires_at: Mapped[date] = mapped_column(Date, nullable=False)
    review_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    reviewed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    review_remark: Mapped[str | None] = mapped_column(String(200))
    attachment_url: Mapped[str | None] = mapped_column(String(300))
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
    certificate_type_ref: Mapped[CertificateType | None] = relationship(back_populates="certificates")
    review_records: Mapped[list["CertificateReviewRecord"]] = relationship(
        back_populates="certificate",
        cascade="all, delete-orphan",
    )


class CertificateReviewRecord(Base):
    __tablename__ = "certificate_review_records"
    __table_args__ = (
        Index("idx_certificate_review_records_certificate_id", "certificate_id"),
        Index("idx_certificate_review_records_reviewer_user_id", "reviewer_user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    certificate_id: Mapped[int] = mapped_column(
        ForeignKey("certificates.id", ondelete="CASCADE"),
        nullable=False,
    )
    reviewer_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    old_status: Mapped[str] = mapped_column(String(20), nullable=False)
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    remark: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    certificate: Mapped[Certificate] = relationship(back_populates="review_records")


class JobDemand(Base):
    __tablename__ = "job_demands"
    __table_args__ = (
        CheckConstraint(
            f"status in ({_sql_values(JOB_STATUSES)})",
            name="ck_job_demands_status",
        ),
        Index("idx_job_demands_owner_user_id", "owner_user_id"),
        Index("idx_job_demands_ship_id", "ship_id"),
        Index("idx_job_demands_route_id", "route_id"),
        Index("idx_job_demands_position_id", "position_id"),
        Index("idx_job_demands_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    ship_id: Mapped[int | None] = mapped_column(ForeignKey("ships.id"))
    route_id: Mapped[int | None] = mapped_column(ForeignKey("routes.id"))
    position_id: Mapped[int | None] = mapped_column(ForeignKey("positions.id"))
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    ship_name: Mapped[str] = mapped_column(String(100), nullable=False)
    route: Mapped[str] = mapped_column(String(120), nullable=False)
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

    ship: Mapped[Ship | None] = relationship(back_populates="jobs")
    route_ref: Mapped[Route | None] = relationship(back_populates="jobs")
    position_ref: Mapped[Position | None] = relationship(back_populates="jobs")
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
        Index("idx_job_required_certificates_certificate_type_id", "certificate_type_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("job_demands.id", ondelete="CASCADE"),
        nullable=False,
    )
    certificate_type_id: Mapped[int | None] = mapped_column(ForeignKey("certificate_types.id"))
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
    status_logs: Mapped[list["DispatchStatusLog"]] = relationship(
        back_populates="dispatch",
        cascade="all, delete-orphan",
    )


class DispatchStatusLog(Base):
    __tablename__ = "dispatch_status_logs"
    __table_args__ = (
        Index("idx_dispatch_status_logs_dispatch_id", "dispatch_id"),
        Index("idx_dispatch_status_logs_operator_user_id", "operator_user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dispatch_id: Mapped[int] = mapped_column(
        ForeignKey("dispatches.id", ondelete="CASCADE"),
        nullable=False,
    )
    old_status: Mapped[str | None] = mapped_column(String(20))
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    operator_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    remark: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    dispatch: Mapped[Dispatch] = relationship(back_populates="status_logs")


class VoyageRecord(Base):
    __tablename__ = "voyage_records"
    __table_args__ = (
        CheckConstraint(
            f"status in ({_sql_values(VOYAGE_STATUSES)})",
            name="ck_voyage_records_status",
        ),
        Index("idx_voyage_records_crew_id", "crew_id"),
        Index("idx_voyage_records_job_id", "job_id"),
        Index("idx_voyage_records_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dispatch_id: Mapped[int] = mapped_column(ForeignKey("dispatches.id"), unique=True)
    crew_id: Mapped[int] = mapped_column(ForeignKey("crews.id"), nullable=False)
    job_id: Mapped[int] = mapped_column(ForeignKey("job_demands.id"), nullable=False)
    ship_name: Mapped[str] = mapped_column(String(100), nullable=False)
    route: Mapped[str] = mapped_column(String(120), nullable=False)
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


class OperationLog(Base):
    __tablename__ = "operation_logs"
    __table_args__ = (
        Index("idx_operation_logs_user_id", "user_id"),
        Index("idx_operation_logs_action", "action"),
        Index("idx_operation_logs_target", "target_type", "target_id"),
        Index("idx_operation_logs_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    username: Mapped[str | None] = mapped_column(String(50))
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[int | None] = mapped_column(Integer)
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
