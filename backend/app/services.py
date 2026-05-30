from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from .models import (
    Certificate,
    CertificateReviewRecord,
    CertificateType,
    Crew,
    Dispatch,
    DispatchStatusLog,
    JobDemand,
    JobRequiredCertificate,
    OperationLog,
    Port,
    Position,
    Route,
    Ship,
    ShipCompany,
    User,
    VoyageRecord,
    utc_now,
)
from .passwords import hash_password, verify_password
from .schemas import (
    CertificateCreate,
    CertificateReview,
    CertificateTypeCreate,
    CertificateUpdate,
    CrewCreate,
    CrewUpdate,
    DispatchCreate,
    JobCreate,
    LoginRequest,
    PortCreate,
    PositionCreate,
    RouteCreate,
    ShipCreate,
)


class ApiError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message


def get_user(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)

#查人和密码
def authenticate_user(db: Session, payload: LoginRequest) -> User:
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise ApiError(401, "账号或密码错误")
    return user


def _commit_or_duplicate(db: Session, message: str):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ApiError(400, message)


def _flush_or_duplicate(db: Session, message: str):
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ApiError(400, message)


def _add_operation_log(
    db: Session,
    user: User | None,
    action: str,
    target_type: str,
    target_id: int | None,
    detail: str | None = None,
) -> None:
    db.add(
        OperationLog(
            user_id=user.id if user is not None else None,
            username=user.username if user is not None else None,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=detail,
        )
    )


def _append_dispatch_status_log(
    db: Session,
    dispatch: Dispatch,
    old_status: str | None,
    new_status: str,
    operator: User | None,
    remark: str | None = None,
) -> None:
    db.add(
        DispatchStatusLog(
            dispatch=dispatch,
            old_status=old_status,
            new_status=new_status,
            operator_user_id=operator.id if operator is not None else None,
            remark=remark,
        )
    )


def _get_crew_or_404(db: Session, crew_id: int) -> Crew:
    crew = db.get(Crew, crew_id)
    if crew is None:
        raise ApiError(404, "船员不存在")
    return crew


def _get_job_or_404(db: Session, job_id: int) -> JobDemand:
    job = db.get(JobDemand, job_id)
    if job is None:
        raise ApiError(404, "岗位需求不存在")
    return job


def _get_dispatch_or_404(db: Session, dispatch_id: int) -> Dispatch:
    dispatch = db.get(Dispatch, dispatch_id)
    if dispatch is None:
        raise ApiError(404, "派遣记录不存在")
    return dispatch


def _get_position_name(db: Session, position_id: int | None, fallback: str | None) -> tuple[int | None, str]:
    if position_id is not None:
        position = db.get(Position, position_id)
        if position is None:
            raise ApiError(404, "岗位不存在")
        return position.id, position.name
    if fallback:
        position = db.scalar(select(Position).where(Position.name == fallback))
        if position is None:
            position = Position(name=fallback)
            db.add(position)
            db.flush()
        return position.id, position.name
    raise ApiError(400, "岗位不能为空")


def _get_certificate_type_name(
    db: Session,
    certificate_type_id: int | None,
    fallback: str | None,
) -> tuple[int | None, str]:
    if certificate_type_id is not None:
        certificate_type = db.get(CertificateType, certificate_type_id)
        if certificate_type is None:
            raise ApiError(404, "证书类型不存在")
        return certificate_type.id, certificate_type.name
    if fallback:
        certificate_type = db.scalar(
            select(CertificateType).where(CertificateType.name == fallback)
        )
        if certificate_type is None:
            certificate_type = CertificateType(name=fallback, is_required=True)
            db.add(certificate_type)
            db.flush()
        return certificate_type.id, certificate_type.name
    raise ApiError(400, "证书类型不能为空")


def _route_label(route: Route) -> str:
    return f"{route.departure_port.name}-{route.destination_port.name}"


def seed_demo_data(db: Session) -> None:
    if not db.scalar(select(User).where(User.username == "admin")):
        for username, password, role, display_name in [
            ("admin", "admin123", "admin", "系统管理员"),
            ("manager", "manager123", "manager", "业务经理"),
            ("cert_admin", "cert123", "cert_admin", "证书管理员"),
            ("owner", "owner123", "shipowner", "船东甲"),
            ("other_owner", "owner123", "shipowner", "船东乙"),
        ]:
            db.add(
                User(
                    username=username,
                    password_hash=hash_password(password, salt=f"{username}-seed"),
                    role=role,
                    display_name=display_name,
                )
            )
        db.commit()

    for name, level, salary in [
        ("船长", "高级船员", 36000),
        ("轮机长", "高级船员", 34000),
        ("大副", "高级船员", 26000),
        ("二副", "驾驶部", 20000),
        ("水手", "普通船员", 12000),
        ("机工", "普通船员", 12000),
    ]:
        if not db.scalar(select(Position).where(Position.name == name)):
            db.add(Position(name=name, level=level, base_salary=salary))

    for name, months in [
        ("STCW", 60),
        ("GMDSS", 60),
        ("高级消防", 60),
        ("油化证", 60),
        ("健康证", 24),
    ]:
        if not db.scalar(select(CertificateType).where(CertificateType.name == name)):
            db.add(CertificateType(name=name, validity_months=months, is_required=True))

    for name, city in [
        ("上海港", "上海"),
        ("青岛港", "青岛"),
        ("新加坡港", "新加坡"),
        ("鹿特丹港", "鹿特丹"),
    ]:
        if not db.scalar(select(Port).where(Port.name == name)):
            db.add(Port(name=name, city=city, country="中国" if city in {"上海", "青岛"} else "海外"))
    db.commit()

    ports = {port.name: port for port in db.scalars(select(Port)).all()}
    for route_name, start, end, distance, days in [
        ("中近洋补给线", "上海港", "新加坡港", 2100, 8),
        ("远洋集装箱线", "青岛港", "鹿特丹港", 10500, 32),
    ]:
        exists = db.scalar(select(Route).where(Route.route_name == route_name))
        if exists is None:
            db.add(
                Route(
                    route_name=route_name,
                    departure_port_id=ports[start].id,
                    destination_port_id=ports[end].id,
                    distance_nm=distance,
                    estimated_days=days,
                )
            )

    owner = db.scalar(select(User).where(User.username == "owner"))
    if owner and not db.scalar(select(ShipCompany).where(ShipCompany.name == "东方航运")):
        company = ShipCompany(
            name="东方航运",
            owner_user_id=owner.id,
            contact_name="船东甲",
            phone="13900000001",
        )
        db.add(company)
        db.flush()
        db.add_all(
            [
                Ship(company=company, name="东方一号", ship_type="散货船", tonnage=56000, capacity=24),
                Ship(company=company, name="东方二号", ship_type="集装箱船", tonnage=72000, capacity=28),
            ]
        )
    db.commit()


def position_to_dict(position: Position) -> dict:
    return {
        "id": position.id,
        "name": position.name,
        "level": position.level,
        "base_salary": position.base_salary,
        "description": position.description,
    }


def certificate_type_to_dict(certificate_type: CertificateType) -> dict:
    return {
        "id": certificate_type.id,
        "name": certificate_type.name,
        "validity_months": certificate_type.validity_months,
        "is_required": certificate_type.is_required,
        "description": certificate_type.description,
    }


def port_to_dict(port: Port) -> dict:
    return {
        "id": port.id,
        "name": port.name,
        "country": port.country,
        "city": port.city,
    }


def route_to_dict(route: Route) -> dict:
    return {
        "id": route.id,
        "route_name": route.route_name,
        "departure_port_id": route.departure_port_id,
        "departure_port": route.departure_port.name,
        "destination_port_id": route.destination_port_id,
        "destination_port": route.destination_port.name,
        "route": _route_label(route),
        "distance_nm": route.distance_nm,
        "estimated_days": route.estimated_days,
        "status": route.status,
    }


def ship_to_dict(ship: Ship) -> dict:
    return {
        "id": ship.id,
        "company_id": ship.company_id,
        "company_name": ship.company.name,
        "name": ship.name,
        "ship_type": ship.ship_type,
        "tonnage": ship.tonnage,
        "capacity": ship.capacity,
        "status": ship.status,
    }


def list_positions(db: Session) -> list[dict]:
    positions = db.scalars(select(Position).order_by(Position.id)).all()
    return [position_to_dict(position) for position in positions]


def create_position(db: Session, payload: PositionCreate, actor: User | None) -> dict:
    position = Position(**payload.model_dump())
    db.add(position)
    _flush_or_duplicate(db, "岗位名称已存在")
    _add_operation_log(db, actor, "create", "position", position.id, position.name)
    _commit_or_duplicate(db, "岗位名称已存在")
    db.refresh(position)
    return position_to_dict(position)


def list_certificate_types(db: Session) -> list[dict]:
    certificate_types = db.scalars(select(CertificateType).order_by(CertificateType.id)).all()
    return [certificate_type_to_dict(item) for item in certificate_types]


def create_certificate_type(
    db: Session,
    payload: CertificateTypeCreate,
    actor: User | None,
) -> dict:
    certificate_type = CertificateType(**payload.model_dump())
    db.add(certificate_type)
    _flush_or_duplicate(db, "证书类型已存在")
    _add_operation_log(
        db,
        actor,
        "create",
        "certificate_type",
        certificate_type.id,
        certificate_type.name,
    )
    _commit_or_duplicate(db, "证书类型已存在")
    db.refresh(certificate_type)
    return certificate_type_to_dict(certificate_type)


def list_ports(db: Session) -> list[dict]:
    ports = db.scalars(select(Port).order_by(Port.id)).all()
    return [port_to_dict(port) for port in ports]


def create_port(db: Session, payload: PortCreate, actor: User | None) -> dict:
    port = Port(**payload.model_dump())
    db.add(port)
    _flush_or_duplicate(db, "港口名称已存在")
    _add_operation_log(db, actor, "create", "port", port.id, port.name)
    _commit_or_duplicate(db, "港口名称已存在")
    db.refresh(port)
    return port_to_dict(port)


def list_routes(db: Session) -> list[dict]:
    routes = db.scalars(
        select(Route)
        .options(joinedload(Route.departure_port), joinedload(Route.destination_port))
        .order_by(Route.id)
    ).all()
    return [route_to_dict(route) for route in routes]


def create_route(db: Session, payload: RouteCreate, actor: User | None) -> dict:
    departure = db.get(Port, payload.departure_port_id)
    destination = db.get(Port, payload.destination_port_id)
    if departure is None or destination is None:
        raise ApiError(404, "港口不存在")
    route = Route(
        route_name=payload.route_name or f"{departure.name}-{destination.name}",
        departure_port_id=departure.id,
        destination_port_id=destination.id,
        distance_nm=payload.distance_nm,
        estimated_days=payload.estimated_days,
        status=payload.status,
    )
    db.add(route)
    _flush_or_duplicate(db, "航线已存在")
    _add_operation_log(db, actor, "create", "route", route.id, route.route_name)
    _commit_or_duplicate(db, "航线已存在")
    db.refresh(route)
    return route_to_dict(route)


def list_ships(db: Session, user: User | None = None) -> list[dict]:
    query = select(Ship).options(joinedload(Ship.company)).order_by(Ship.id)
    if user is not None and user.role == "shipowner":
        query = query.join(ShipCompany).where(ShipCompany.owner_user_id == user.id)
    ships = db.scalars(query).all()
    return [ship_to_dict(ship) for ship in ships]


def create_ship(db: Session, payload: ShipCreate, actor: User | None) -> dict:
    company = db.get(ShipCompany, payload.company_id) if payload.company_id else None
    if company is None:
        company_name = payload.company_name or (
            f"{actor.display_name}航运公司" if actor is not None else "默认航运公司"
        )
        company = db.scalar(select(ShipCompany).where(ShipCompany.name == company_name))
        if company is None:
            company = ShipCompany(
                name=company_name,
                owner_user_id=actor.id if actor and actor.role == "shipowner" else None,
                contact_name=actor.display_name if actor else None,
            )
            db.add(company)
            db.flush()
    ship = Ship(
        company=company,
        name=payload.name,
        ship_type=payload.ship_type,
        tonnage=payload.tonnage,
        capacity=payload.capacity,
        status=payload.status,
    )
    db.add(ship)
    _flush_or_duplicate(db, "船舶名称已存在")
    _add_operation_log(db, actor, "create", "ship", ship.id, ship.name)
    _commit_or_duplicate(db, "船舶名称已存在")
    db.refresh(ship)
    return ship_to_dict(ship)


def certificate_flags(expires_at: date) -> dict[str, bool]:
    today = datetime.now(UTC).date()
    return {
        "is_expired": expires_at < today,
        "is_expiring_soon": today <= expires_at <= today + timedelta(days=30),
    }


def crew_to_dict(crew: Crew) -> dict:
    return {
        "id": crew.id,
        "username": crew.user.username,
        "password": "******",
        "name": crew.name,
        "gender": crew.gender,
        "id_card": crew.id_card,
        "phone": crew.phone,
        "position_id": crew.position_id,
        "position": crew.position,
        "status": crew.status,
        "is_at_sea": 1 if crew.status == "at_sea" else 0,
        "role": "admin" if crew.user.role == "admin" else "user",
    }


def certificate_to_dict(certificate: Certificate) -> dict:
    flags = certificate_flags(certificate.expires_at)
    return {
        "id": certificate.id,
        "crew_id": certificate.crew_id,
        "crew_name": certificate.crew.name,
        "certificate_type_id": certificate.certificate_type_id,
        "certificate_type": certificate.certificate_type,
        "certificate_no": certificate.certificate_no,
        "issued_at": certificate.issued_at,
        "expires_at": certificate.expires_at,
        "review_status": certificate.review_status,
        "review_remark": certificate.review_remark,
        "attachment_url": certificate.attachment_url,
        **flags,
    }


def job_to_dict(job: JobDemand) -> dict:
    return {
        "id": job.id,
        "owner_user_id": job.owner_user_id,
        "ship_id": job.ship_id,
        "route_id": job.route_id,
        "position_id": job.position_id,
        "title": job.title,
        "ship_name": job.ship_name,
        "route": job.route,
        "required_position": job.required_position,
        "required_certificates": [
            item.certificate_type for item in job.required_certificates
        ],
        "headcount": job.headcount,
        "onboard_at": job.onboard_at,
        "status": job.status,
    }


def dispatch_to_dict(dispatch: Dispatch, include_logs: bool = False) -> dict:
    data = {
        "id": dispatch.id,
        "job_id": dispatch.job_id,
        "job_title": dispatch.job.title,
        "crew_id": dispatch.crew_id,
        "crew_name": dispatch.crew.name,
        "ship_name": dispatch.job.ship_name,
        "route": dispatch.job.route,
        "position": dispatch.job.required_position,
        "status": dispatch.status,
        "created_at": dispatch.created_at,
        "updated_at": dispatch.updated_at,
    }
    if include_logs:
        data["status_logs"] = [
            {
                "id": item.id,
                "old_status": item.old_status,
                "new_status": item.new_status,
                "operator_user_id": item.operator_user_id,
                "remark": item.remark,
                "created_at": item.created_at,
            }
            for item in sorted(dispatch.status_logs, key=lambda log: log.id)
        ]
    return data


def list_crews(db: Session) -> list[dict]:
    crews = db.scalars(
        select(Crew)
        .options(joinedload(Crew.user))
        .where(Crew.status != "inactive")
        .order_by(Crew.id)
    ).all()
    return [crew_to_dict(crew) for crew in crews]

#写入数据库
def create_crew(db: Session, payload: CrewCreate, actor: User | None = None) -> dict:
    position_id, position_name = _get_position_name(db, payload.position_id, payload.position)
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role="seafarer",
        display_name=payload.name,
    )
    crew = Crew(
        user=user,
        position_id=position_id,
        name=payload.name,
        gender=payload.gender,
        id_card=payload.id_card,
        phone=payload.phone,
        position=position_name,
        status="available",
    )
    db.add(crew)
    #1.创建 User：这是登录账号，写入 users 表。
    #2.创建 Crew：这是船员档案，写入 crews 表。
    _flush_or_duplicate(db, "账号、身份证号或证书编号已存在")
    _add_operation_log(db, actor, "create", "crew", crew.id, crew.name)
    _commit_or_duplicate(db, "账号、身份证号或证书编号已存在")
    db.refresh(crew)
    return crew_to_dict(crew)


def get_crew(db: Session, crew_id: int) -> dict:
    crew = _get_crew_or_404(db, crew_id)
    return crew_to_dict(crew)


def update_crew(
    db: Session,
    crew_id: int,
    payload: CrewUpdate,
    actor: User | None = None,
) -> dict:
    crew = _get_crew_or_404(db, crew_id)
    changes = payload.model_dump(exclude_unset=True)
    if "position_id" in changes or "position" in changes:
        position_id, position_name = _get_position_name(
            db,
            changes.get("position_id", crew.position_id),
            changes.get("position", crew.position),
        )
        crew.position_id = position_id
        crew.position = position_name
        changes.pop("position_id", None)
        changes.pop("position", None)
    for field, value in changes.items():
        setattr(crew, field, value)
        if field == "name":
            crew.user.display_name = value
    _add_operation_log(db, actor, "update", "crew", crew.id, crew.name)
    _commit_or_duplicate(db, "船员信息更新失败")
    db.refresh(crew)
    return crew_to_dict(crew)


def soft_delete_crew(db: Session, crew_id: int, actor: User | None = None) -> dict:
    crew = _get_crew_or_404(db, crew_id)
    crew.status = "inactive"
    _add_operation_log(db, actor, "delete", "crew", crew.id, crew.name)
    db.commit()
    db.refresh(crew)
    return crew_to_dict(crew)


def crew_stats(db: Session) -> dict:
    crews = db.scalars(select(Crew).where(Crew.status != "inactive")).all()
    return {
        "total": len(crews),
        "at_sea": sum(1 for crew in crews if crew.status == "at_sea"),
    }


def set_crew_sea_status(db: Session, crew_id: int, is_at_sea: bool) -> dict:
    crew = _get_crew_or_404(db, crew_id)
    if crew.status == "inactive":
        raise ApiError(400, "船员已停用")

    if is_at_sea:
        crew.status = "at_sea"
        db.commit()
        db.refresh(crew)
        return crew_to_dict(crew)

    active_onboard_dispatch = db.scalar(
        select(Dispatch)
        .where(Dispatch.crew_id == crew.id, Dispatch.status == "onboard")
        .order_by(Dispatch.id.desc())
    )
    if active_onboard_dispatch is not None:
        offboard_dispatch(db, active_onboard_dispatch.id)
        return get_crew(db, crew_id)

    crew.status = "available"
    db.commit()
    db.refresh(crew)
    return crew_to_dict(crew)


def list_certificates(db: Session) -> list[dict]:
    certificates = db.scalars(
        select(Certificate)
        .options(joinedload(Certificate.crew))
        .order_by(Certificate.id)
    ).all()
    return [certificate_to_dict(certificate) for certificate in certificates]


def create_certificate(
    db: Session,
    payload: CertificateCreate,
    actor: User | None = None,
) -> dict:
    crew = _get_crew_or_404(db, payload.crew_id)
    certificate_type_id, certificate_type_name = _get_certificate_type_name(
        db,
        payload.certificate_type_id,
        payload.certificate_type,
    )
    certificate = Certificate(
        crew=crew,
        certificate_type_id=certificate_type_id,
        certificate_type=certificate_type_name,
        certificate_no=payload.certificate_no,
        issued_at=payload.issued_at,
        expires_at=payload.expires_at,
        review_status="pending",
        attachment_url=payload.attachment_url,
    )
    db.add(certificate)
    _flush_or_duplicate(db, "证书编号已存在")
    _add_operation_log(
        db,
        actor,
        "create",
        "certificate",
        certificate.id,
        f"{crew.name}-{certificate.certificate_type}",
    )
    _commit_or_duplicate(db, "证书编号已存在")
    db.refresh(certificate)
    return certificate_to_dict(certificate)


def update_certificate(
    db: Session,
    certificate_id: int,
    payload: CertificateUpdate,
    actor: User | None = None,
) -> dict:
    certificate = db.get(Certificate, certificate_id)
    if certificate is None:
        raise ApiError(404, "证书不存在")
    changes = payload.model_dump(exclude_unset=True)
    if "certificate_type_id" in changes or "certificate_type" in changes:
        type_id, type_name = _get_certificate_type_name(
            db,
            changes.get("certificate_type_id", certificate.certificate_type_id),
            changes.get("certificate_type", certificate.certificate_type),
        )
        certificate.certificate_type_id = type_id
        certificate.certificate_type = type_name
        changes.pop("certificate_type_id", None)
        changes.pop("certificate_type", None)
    issued_at = changes.get("issued_at", certificate.issued_at)
    expires_at = changes.get("expires_at", certificate.expires_at)
    if expires_at < issued_at:
        raise ApiError(400, "证书到期日期不能早于签发日期")
    for field, value in changes.items():
        setattr(certificate, field, value)
    _add_operation_log(db, actor, "update", "certificate", certificate.id, certificate.certificate_no)
    _commit_or_duplicate(db, "证书编号已存在")
    db.refresh(certificate)
    return certificate_to_dict(certificate)


def review_certificate(
    db: Session,
    certificate_id: int,
    payload: CertificateReview,
    reviewer: User,
) -> dict:
    certificate = db.get(Certificate, certificate_id)
    if certificate is None:
        raise ApiError(404, "证书不存在")
    old_status = certificate.review_status
    certificate.review_status = payload.review_status
    certificate.reviewed_by_user_id = reviewer.id
    certificate.reviewed_at = utc_now()
    certificate.review_remark = payload.remark
    db.add(
        CertificateReviewRecord(
            certificate=certificate,
            reviewer_user_id=reviewer.id,
            old_status=old_status,
            new_status=payload.review_status,
            remark=payload.remark,
        )
    )
    _add_operation_log(
        db,
        reviewer,
        "review",
        "certificate",
        certificate.id,
        f"{old_status}->{payload.review_status}",
    )
    db.commit()
    db.refresh(certificate)
    return certificate_to_dict(certificate)


def list_certificate_alerts(db: Session) -> list[dict]:
    today = datetime.now(UTC).date()
    deadline = today + timedelta(days=30)
    certificates = db.scalars(
        select(Certificate)
        .options(joinedload(Certificate.crew))
        .where(
            Certificate.review_status.in_(["pending", "approved"]),
            Certificate.expires_at >= today,
            Certificate.expires_at <= deadline,
        )
        .order_by(Certificate.expires_at)
    ).all()
    return [certificate_to_dict(certificate) for certificate in certificates]


def list_jobs(db: Session, user: User | None = None) -> list[dict]:
    query = (
        select(JobDemand)
        .options(joinedload(JobDemand.required_certificates))
        .order_by(JobDemand.id.desc())
    )
    if user is not None and user.role == "shipowner":
        query = query.where(JobDemand.owner_user_id == user.id)
    jobs = db.scalars(query).unique().all()
    return [job_to_dict(job) for job in jobs]


def create_job(db: Session, payload: JobCreate, owner: User) -> dict:
    ship_id = payload.ship_id
    ship_name = payload.ship_name
    if ship_id is not None:
        ship = db.get(Ship, ship_id)
        if ship is None:
            raise ApiError(404, "船舶不存在")
        ship_name = ship.name
    if not ship_name:
        raise ApiError(400, "船舶不能为空")

    route_id = payload.route_id
    route_name = payload.route
    if route_id is not None:
        route = db.get(Route, route_id)
        if route is None:
            raise ApiError(404, "航线不存在")
        route_name = _route_label(route)
    if not route_name:
        raise ApiError(400, "航线不能为空")

    position_id, position_name = _get_position_name(
        db,
        payload.position_id,
        payload.required_position,
    )
    job = JobDemand(
        owner_user_id=owner.id,
        ship_id=ship_id,
        route_id=route_id,
        position_id=position_id,
        title=payload.title,
        ship_name=ship_name,
        route=route_name,
        required_position=position_name,
        headcount=payload.headcount,
        onboard_at=payload.onboard_at,
        status="open",
    )
    required_names = list(dict.fromkeys(payload.required_certificates))
    for cert_type_id in dict.fromkeys(payload.required_certificate_type_ids):
        type_id, type_name = _get_certificate_type_name(db, cert_type_id, None)
        required_names.append(type_name)
    for certificate_type in dict.fromkeys(required_names):
        type_id, type_name = _get_certificate_type_name(db, None, certificate_type)
        job.required_certificates.append(
            JobRequiredCertificate(
                certificate_type_id=type_id,
                certificate_type=type_name,
            )
        )
    db.add(job)
    db.flush()
    _add_operation_log(db, owner, "create", "job", job.id, job.title)
    db.commit()
    db.refresh(job)
    return job_to_dict(job)


def get_job(db: Session, job_id: int) -> dict:
    job = _get_job_or_404(db, job_id)
    return job_to_dict(job)


def close_job(db: Session, job_id: int, user: User) -> dict:
    job = _get_job_or_404(db, job_id)
    if user.role == "shipowner" and job.owner_user_id != user.id:
        raise ApiError(403, "只能关闭自己发布的岗位")
    job.status = "closed"
    _add_operation_log(db, user, "close", "job", job.id, job.title)
    db.commit()
    db.refresh(job)
    return job_to_dict(job)


def _valid_certificate_types(crew: Crew, today: date) -> set[str]:
    return {
        certificate.certificate_type
        for certificate in crew.certificates
        if certificate.review_status == "approved" and certificate.expires_at >= today
    }


def _crew_has_valid_certificates(
    crew: Crew,
    required_certificates: list[str],
    today: date,
) -> bool:
    return set(required_certificates).issubset(_valid_certificate_types(crew, today))


def _score_match(crew: Crew, job: JobDemand, today: date) -> dict:
    required_certificates = [item.certificate_type for item in job.required_certificates]
    score = 0
    reasons: list[str] = []

    if crew.position == job.required_position:
        score += 40
        reasons.append("岗位完全匹配")
    else:
        reasons.append("岗位不匹配")

    valid_types = _valid_certificate_types(crew, today)
    missing = [item for item in required_certificates if item not in valid_types]
    if required_certificates:
        cert_score = int(40 * (len(required_certificates) - len(missing)) / len(required_certificates))
    else:
        cert_score = 40
    score += cert_score
    if not missing:
        reasons.append("所需证书齐全且已审核")
    else:
        reasons.append("缺少证书：" + "、".join(missing))

    valid_required = [
        certificate
        for certificate in crew.certificates
        if certificate.certificate_type in required_certificates
        and certificate.review_status == "approved"
        and certificate.expires_at >= today
    ]
    days_to_expire = [
        (certificate.expires_at - today).days for certificate in valid_required
    ]
    if not required_certificates:
        score += 10
        certificate_risk = "无强制证书要求"
    elif days_to_expire and min(days_to_expire) >= 180:
        score += 10
        certificate_risk = "证书有效期充足"
    elif days_to_expire and min(days_to_expire) >= 30:
        score += 6
        certificate_risk = "证书半年内需关注"
    elif days_to_expire:
        score += 2
        certificate_risk = "证书临近到期"
    else:
        certificate_risk = "证书不可用"
    reasons.append(certificate_risk)

    has_similar_voyage = any(
        voyage.position == job.required_position or voyage.route == job.route
        for voyage in crew.voyages
    )
    if has_similar_voyage:
        score += 10
        reasons.append("有相近岗位或航线海历")
    else:
        reasons.append("暂无相近海历")

    data = crew_to_dict(crew)
    data.update(
        {
            "match_score": min(score, 100),
            "match_reasons": reasons,
            "missing_certificates": missing,
            "certificate_risk": certificate_risk,
        }
    )
    return data


def list_matching_crews(db: Session, job_id: int) -> list[dict]:
    job = _get_job_or_404(db, job_id)
    today = datetime.now(UTC).date()
    crews = db.scalars(
        select(Crew)
        .options(
            joinedload(Crew.user),
            joinedload(Crew.certificates),
            selectinload(Crew.voyages),
        )
        .where(Crew.status == "available")
        .order_by(Crew.id)
    ).unique().all()
    scored = [_score_match(crew, job, today) for crew in crews]
    return sorted(
        [item for item in scored if item["match_score"] >= 60],
        key=lambda item: item["match_score"],
        reverse=True,
    )


def _active_dispatch_count(db: Session, job_id: int) -> int:
    return db.scalar(
        select(func.count())
        .select_from(Dispatch)
        .where(
            Dispatch.job_id == job_id,
            Dispatch.status.in_(["pending_owner", "confirmed", "onboard"]),
        )
    ) or 0


def _ensure_crew_matches_job(db: Session, crew: Crew, job: JobDemand) -> None:
    if crew.status != "available":
        raise ApiError(400, "该船员当前不可派遣")
    if crew.position != job.required_position:
        raise ApiError(400, "船员岗位不满足岗位需求")
    active_dispatch = db.scalar(
        select(Dispatch).where(
            Dispatch.crew_id == crew.id,
            Dispatch.status.in_(["pending_owner", "confirmed", "onboard"]),
        )
    )
    if active_dispatch is not None:
        raise ApiError(400, "该船员已有进行中的派遣")
    required_certificates = [
        item.certificate_type for item in job.required_certificates
    ]
    if not _crew_has_valid_certificates(crew, required_certificates, datetime.now(UTC).date()):
        raise ApiError(400, "船员证书未审核、已过期或不满足岗位需求")


def list_dispatches(db: Session, user: User | None = None) -> list[dict]:
    query = (
        select(Dispatch)
        .options(joinedload(Dispatch.crew), joinedload(Dispatch.job))
        .order_by(Dispatch.id.desc())
    )
    if user is not None and user.role == "shipowner":
        query = query.join(JobDemand).where(JobDemand.owner_user_id == user.id)
    dispatches = db.scalars(query).unique().all()
    return [dispatch_to_dict(dispatch) for dispatch in dispatches]


def get_dispatch(db: Session, dispatch_id: int, user: User | None = None) -> dict:
    dispatch = db.scalar(
        select(Dispatch)
        .options(
            joinedload(Dispatch.crew),
            joinedload(Dispatch.job),
            selectinload(Dispatch.status_logs),
        )
        .where(Dispatch.id == dispatch_id)
    )
    if dispatch is None:
        raise ApiError(404, "派遣记录不存在")
    if user is not None and user.role == "shipowner" and dispatch.job.owner_user_id != user.id:
        raise ApiError(403, "只能查看自己岗位对应的派遣")
    return dispatch_to_dict(dispatch, include_logs=True)


def create_dispatch(db: Session, payload: DispatchCreate, creator: User) -> dict:
    job = _get_job_or_404(db, payload.job_id)
    crew = _get_crew_or_404(db, payload.crew_id)
    if job.status not in {"open", "matched"}:
        raise ApiError(400, "岗位当前不可派遣")
    if _active_dispatch_count(db, job.id) >= job.headcount:
        raise ApiError(400, "该岗位招聘人数已满")
    _ensure_crew_matches_job(db, crew, job)
    dispatch = Dispatch(
        job=job,
        crew=crew,
        status="pending_owner",
        created_by_user_id=creator.id,
    )
    db.add(dispatch)
    db.flush()
    _append_dispatch_status_log(db, dispatch, None, "pending_owner", creator, "业务经理发起派遣")
    _add_operation_log(db, creator, "create", "dispatch", dispatch.id, f"{crew.name}->{job.title}")
    db.commit()
    db.refresh(dispatch)
    return dispatch_to_dict(dispatch)


def confirm_dispatch(db: Session, dispatch_id: int, user: User) -> dict:
    dispatch = _get_dispatch_or_404(db, dispatch_id)
    if dispatch.status != "pending_owner":
        raise ApiError(400, "只有待船东确认的派遣可以确认")
    if user.role == "shipowner" and dispatch.job.owner_user_id != user.id:
        raise ApiError(403, "船东只能确认自己岗位的派遣")
    old_status = dispatch.status
    dispatch.status = "confirmed"
    dispatch.confirmed_by_user_id = user.id
    dispatch.crew.status = "pending"
    if _active_dispatch_count(db, dispatch.job_id) >= dispatch.job.headcount:
        dispatch.job.status = "matched"
    _append_dispatch_status_log(db, dispatch, old_status, "confirmed", user, "船东确认派遣")
    _add_operation_log(db, user, "confirm", "dispatch", dispatch.id, dispatch.crew.name)
    db.commit()
    db.refresh(dispatch)
    return dispatch_to_dict(dispatch)


def onboard_dispatch(db: Session, dispatch_id: int, user: User | None = None) -> dict:
    dispatch = _get_dispatch_or_404(db, dispatch_id)
    if dispatch.status != "confirmed":
        raise ApiError(400, "只有已确认的派遣可以上船")
    now = utc_now()
    old_status = dispatch.status
    dispatch.status = "onboard"
    dispatch.crew.status = "at_sea"
    voyage = VoyageRecord(
        dispatch=dispatch,
        crew=dispatch.crew,
        job_id=dispatch.job_id,
        ship_name=dispatch.job.ship_name,
        route=dispatch.job.route,
        position=dispatch.job.required_position,
        onboard_at=now,
        status="onboard",
    )
    db.add(voyage)
    _append_dispatch_status_log(db, dispatch, old_status, "onboard", user, "确认上船")
    _add_operation_log(db, user, "onboard", "dispatch", dispatch.id, dispatch.crew.name)
    db.commit()
    db.refresh(dispatch)
    return dispatch_to_dict(dispatch)


def offboard_dispatch(db: Session, dispatch_id: int, user: User | None = None) -> dict:
    dispatch = _get_dispatch_or_404(db, dispatch_id)
    if dispatch.status != "onboard":
        raise ApiError(400, "只有已上船的派遣可以下船")
    now = utc_now()
    old_status = dispatch.status
    dispatch.status = "offboard"
    dispatch.crew.status = "available"
    dispatch.job.status = "closed"
    if dispatch.voyage is not None:
        dispatch.voyage.offboard_at = now
        dispatch.voyage.status = "offboard"
    _append_dispatch_status_log(db, dispatch, old_status, "offboard", user, "确认下船")
    _add_operation_log(db, user, "offboard", "dispatch", dispatch.id, dispatch.crew.name)
    db.commit()
    db.refresh(dispatch)
    return dispatch_to_dict(dispatch)


def cancel_dispatch(db: Session, dispatch_id: int, user: User | None = None) -> dict:
    dispatch = _get_dispatch_or_404(db, dispatch_id)
    if dispatch.status == "offboard":
        raise ApiError(400, "已下船的派遣不能取消")
    old_status = dispatch.status
    dispatch.status = "cancelled"
    if dispatch.crew.status in {"pending", "at_sea"}:
        dispatch.crew.status = "available"
    if dispatch.job.status == "matched":
        dispatch.job.status = "open"
    if dispatch.voyage is not None:
        dispatch.voyage.status = "cancelled"
        dispatch.voyage.offboard_at = dispatch.voyage.offboard_at or utc_now()
    _append_dispatch_status_log(db, dispatch, old_status, "cancelled", user, "取消派遣")
    _add_operation_log(db, user, "cancel", "dispatch", dispatch.id, dispatch.crew.name)
    db.commit()
    db.refresh(dispatch)
    return dispatch_to_dict(dispatch)


def dashboard_summary(db: Session) -> dict:
    total_crews = db.scalar(select(func.count()).select_from(Crew).where(Crew.status != "inactive")) or 0
    at_sea = db.scalar(select(func.count()).select_from(Crew).where(Crew.status == "at_sea")) or 0
    available = db.scalar(select(func.count()).select_from(Crew).where(Crew.status == "available")) or 0
    pending_reviews = (
        db.scalar(select(func.count()).select_from(Certificate).where(Certificate.review_status == "pending")) or 0
    )
    certificate_alert_count = len(list_certificate_alerts(db))
    open_jobs = db.scalar(select(func.count()).select_from(JobDemand).where(JobDemand.status == "open")) or 0
    active_dispatches = (
        db.scalar(
            select(func.count())
            .select_from(Dispatch)
            .where(Dispatch.status.in_(["pending_owner", "confirmed", "onboard"]))
        )
        or 0
    )
    total_ships = db.scalar(select(func.count()).select_from(Ship).where(Ship.status != "inactive")) or 0
    return {
        "total_crews": total_crews,
        "available_crews": available,
        "at_sea_crews": at_sea,
        "pending_certificate_reviews": pending_reviews,
        "certificate_alerts": certificate_alert_count,
        "open_jobs": open_jobs,
        "active_dispatches": active_dispatches,
        "total_ships": total_ships,
    }


def dashboard_crew_status(db: Session) -> list[dict]:
    label_map = {
        "available": "在岸可派遣",
        "pending": "待上船",
        "at_sea": "出海中",
        "inactive": "已停用",
    }
    crews = db.scalars(select(Crew)).all()
    counter = Counter(crew.status for crew in crews)
    return [
        {"status": status, "label": label_map[status], "count": counter.get(status, 0)}
        for status in ["available", "pending", "at_sea", "inactive"]
    ]


def dashboard_certificate_alerts(db: Session) -> list[dict]:
    return list_certificate_alerts(db)


def dashboard_dispatch_trend(db: Session) -> list[dict]:
    dispatches = db.scalars(select(Dispatch).order_by(Dispatch.created_at)).all()
    counter: dict[str, int] = defaultdict(int)
    for dispatch in dispatches:
        counter[dispatch.created_at.strftime("%Y-%m")] += 1
    return [{"month": month, "count": counter[month]} for month in sorted(counter)]


def dashboard_route_workload(db: Session) -> list[dict]:
    voyages = db.scalars(select(VoyageRecord)).all()
    counter: dict[str, int] = defaultdict(int)
    onboard_counter: dict[str, int] = defaultdict(int)
    for voyage in voyages:
        counter[voyage.route] += 1
        if voyage.status == "onboard":
            onboard_counter[voyage.route] += 1
    if not counter:
        jobs = db.scalars(select(JobDemand)).all()
        for job in jobs:
            counter[job.route] += 0
    return [
        {
            "route": route,
            "voyage_count": counter[route],
            "onboard_count": onboard_counter.get(route, 0),
        }
        for route in sorted(counter, key=lambda item: counter[item], reverse=True)
    ]


def list_operation_logs(db: Session, limit: int = 100) -> list[dict]:
    logs = db.scalars(
        select(OperationLog).order_by(OperationLog.id.desc()).limit(limit)
    ).all()
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "username": log.username,
            "action": log.action,
            "target_type": log.target_type,
            "target_id": log.target_id,
            "detail": log.detail,
            "created_at": log.created_at,
        }
        for log in logs
    ]
