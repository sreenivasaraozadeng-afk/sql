from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from .models import (
    Certificate,
    Crew,
    Dispatch,
    JobDemand,
    JobRequiredCertificate,
    User,
    VoyageRecord,
    utc_now,
)
from .passwords import hash_password, verify_password
from .schemas import (
    CertificateCreate,
    CertificateUpdate,
    CrewCreate,
    CrewUpdate,
    DispatchCreate,
    JobCreate,
    LoginRequest,
)


class ApiError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message


def get_user(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def authenticate_user(db: Session, payload: LoginRequest) -> User:
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise ApiError(401, "账号或密码错误")
    return user


def seed_demo_data(db: Session) -> None:
    if db.scalar(select(User).where(User.username == "admin")):
        return
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


def _commit_or_duplicate(db: Session, message: str):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ApiError(400, message)


def _get_crew_or_404(db: Session, crew_id: int) -> Crew:
    crew = db.get(Crew, crew_id)
    if crew is None:
        raise ApiError(404, "船员不存在")
    return crew


def _get_job_or_404(db: Session, job_id: int) -> JobDemand:
    job = db.get(JobDemand, job_id)
    if job is None:
        raise ApiError(404, "岗位不存在")
    return job


def _get_dispatch_or_404(db: Session, dispatch_id: int) -> Dispatch:
    dispatch = db.get(Dispatch, dispatch_id)
    if dispatch is None:
        raise ApiError(404, "派遣记录不存在")
    return dispatch


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
        "certificate_type": certificate.certificate_type,
        "certificate_no": certificate.certificate_no,
        "issued_at": certificate.issued_at,
        "expires_at": certificate.expires_at,
        **flags,
    }


def job_to_dict(job: JobDemand) -> dict:
    return {
        "id": job.id,
        "owner_user_id": job.owner_user_id,
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


def dispatch_to_dict(dispatch: Dispatch) -> dict:
    return {
        "id": dispatch.id,
        "job_id": dispatch.job_id,
        "crew_id": dispatch.crew_id,
        "status": dispatch.status,
    }


def list_crews(db: Session) -> list[dict]:
    crews = db.scalars(
        select(Crew)
        .options(joinedload(Crew.user))
        .where(Crew.status != "inactive")
        .order_by(Crew.id)
    ).all()
    return [crew_to_dict(crew) for crew in crews]


def create_crew(db: Session, payload: CrewCreate) -> dict:
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role="seafarer",
        display_name=payload.name,
    )
    crew = Crew(
        user=user,
        name=payload.name,
        gender=payload.gender,
        id_card=payload.id_card,
        phone=payload.phone,
        position=payload.position,
        status="available",
    )
    db.add(crew)
    _commit_or_duplicate(db, "账号、身份证号或证书编号已存在")
    db.refresh(crew)
    return crew_to_dict(crew)


def get_crew(db: Session, crew_id: int) -> dict:
    crew = _get_crew_or_404(db, crew_id)
    return crew_to_dict(crew)


def update_crew(db: Session, crew_id: int, payload: CrewUpdate) -> dict:
    crew = _get_crew_or_404(db, crew_id)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(crew, field, value)
        if field == "name":
            crew.user.display_name = value
    _commit_or_duplicate(db, "船员信息更新失败")
    db.refresh(crew)
    return crew_to_dict(crew)


def soft_delete_crew(db: Session, crew_id: int) -> dict:
    crew = _get_crew_or_404(db, crew_id)
    crew.status = "inactive"
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
        raise ApiError(400, "Crew is inactive")

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
        select(Certificate).options(joinedload(Certificate.crew)).order_by(Certificate.id)
    ).all()
    return [certificate_to_dict(certificate) for certificate in certificates]


def create_certificate(db: Session, payload: CertificateCreate) -> dict:
    crew = _get_crew_or_404(db, payload.crew_id)
    certificate = Certificate(
        crew=crew,
        certificate_type=payload.certificate_type,
        certificate_no=payload.certificate_no,
        issued_at=payload.issued_at,
        expires_at=payload.expires_at,
    )
    db.add(certificate)
    _commit_or_duplicate(db, "证书编号已存在")
    db.refresh(certificate)
    return certificate_to_dict(certificate)


def update_certificate(
    db: Session,
    certificate_id: int,
    payload: CertificateUpdate,
) -> dict:
    certificate = db.get(Certificate, certificate_id)
    if certificate is None:
        raise ApiError(404, "证书不存在")
    changes = payload.model_dump(exclude_unset=True)
    issued_at = changes.get("issued_at", certificate.issued_at)
    expires_at = changes.get("expires_at", certificate.expires_at)
    if expires_at < issued_at:
        raise ApiError(400, "证书到期日期不能早于签发日期")
    for field, value in changes.items():
        setattr(certificate, field, value)
    _commit_or_duplicate(db, "证书编号已存在")
    db.refresh(certificate)
    return certificate_to_dict(certificate)


def list_certificate_alerts(db: Session) -> list[dict]:
    today = datetime.now(UTC).date()
    deadline = today + timedelta(days=30)
    certificates = db.scalars(
        select(Certificate)
        .options(joinedload(Certificate.crew))
        .where(Certificate.expires_at >= today, Certificate.expires_at <= deadline)
        .order_by(Certificate.expires_at)
    ).all()
    return [certificate_to_dict(certificate) for certificate in certificates]


def list_jobs(db: Session) -> list[dict]:
    jobs = db.scalars(
        select(JobDemand)
        .options(joinedload(JobDemand.required_certificates))
        .order_by(JobDemand.id.desc())
    ).unique().all()
    return [job_to_dict(job) for job in jobs]


def create_job(db: Session, payload: JobCreate, owner: User) -> dict:
    job = JobDemand(
        owner_user_id=owner.id,
        title=payload.title,
        ship_name=payload.ship_name,
        route=payload.route,
        required_position=payload.required_position,
        headcount=payload.headcount,
        onboard_at=payload.onboard_at,
        status="open",
    )
    for certificate_type in dict.fromkeys(payload.required_certificates):
        job.required_certificates.append(
            JobRequiredCertificate(certificate_type=certificate_type)
        )
    db.add(job)
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
    db.commit()
    db.refresh(job)
    return job_to_dict(job)


def _crew_has_valid_certificates(
    crew: Crew,
    required_certificates: list[str],
    today: date,
) -> bool:
    valid_types = {
        certificate.certificate_type
        for certificate in crew.certificates
        if certificate.expires_at >= today
    }
    return set(required_certificates).issubset(valid_types)


def list_matching_crews(db: Session, job_id: int) -> list[dict]:
    job = _get_job_or_404(db, job_id)
    required_certificates = [
        item.certificate_type for item in job.required_certificates
    ]
    today = datetime.now(UTC).date()
    crews = db.scalars(
        select(Crew)
        .options(joinedload(Crew.user), joinedload(Crew.certificates))
        .where(Crew.status == "available", Crew.position == job.required_position)
        .order_by(Crew.id)
    ).unique().all()
    return [
        crew_to_dict(crew)
        for crew in crews
        if _crew_has_valid_certificates(crew, required_certificates, today)
    ]


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
        raise ApiError(400, "船员证书不满足岗位需求")


def create_dispatch(db: Session, payload: DispatchCreate, creator: User) -> dict:
    job = _get_job_or_404(db, payload.job_id)
    crew = _get_crew_or_404(db, payload.crew_id)
    if job.status != "open":
        raise ApiError(400, "岗位当前不可派遣")
    _ensure_crew_matches_job(db, crew, job)
    dispatch = Dispatch(
        job=job,
        crew=crew,
        status="pending_owner",
        created_by_user_id=creator.id,
    )
    db.add(dispatch)
    db.commit()
    db.refresh(dispatch)
    return dispatch_to_dict(dispatch)


def confirm_dispatch(db: Session, dispatch_id: int, user: User) -> dict:
    dispatch = _get_dispatch_or_404(db, dispatch_id)
    if dispatch.status != "pending_owner":
        raise ApiError(400, "只有待船东确认的派遣可以确认")
    if user.role == "shipowner" and dispatch.job.owner_user_id != user.id:
        raise ApiError(403, "船东只能确认自己岗位的派遣")
    dispatch.status = "confirmed"
    dispatch.confirmed_by_user_id = user.id
    dispatch.crew.status = "pending"
    dispatch.job.status = "matched"
    db.commit()
    db.refresh(dispatch)
    return dispatch_to_dict(dispatch)


def onboard_dispatch(db: Session, dispatch_id: int) -> dict:
    dispatch = _get_dispatch_or_404(db, dispatch_id)
    if dispatch.status != "confirmed":
        raise ApiError(400, "只有已确认的派遣可以上船")
    now = utc_now()
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
    db.commit()
    db.refresh(dispatch)
    return dispatch_to_dict(dispatch)


def offboard_dispatch(db: Session, dispatch_id: int) -> dict:
    dispatch = _get_dispatch_or_404(db, dispatch_id)
    if dispatch.status != "onboard":
        raise ApiError(400, "只有已上船的派遣可以下船")
    now = utc_now()
    dispatch.status = "offboard"
    dispatch.crew.status = "available"
    dispatch.job.status = "closed"
    if dispatch.voyage is not None:
        dispatch.voyage.offboard_at = now
        dispatch.voyage.status = "offboard"
    db.commit()
    db.refresh(dispatch)
    return dispatch_to_dict(dispatch)


def cancel_dispatch(db: Session, dispatch_id: int) -> dict:
    dispatch = _get_dispatch_or_404(db, dispatch_id)
    if dispatch.status == "offboard":
        raise ApiError(400, "已下船的派遣不能取消")
    dispatch.status = "cancelled"
    if dispatch.crew.status in {"pending", "at_sea"}:
        dispatch.crew.status = "available"
    if dispatch.job.status == "matched":
        dispatch.job.status = "open"
    if dispatch.voyage is not None:
        dispatch.voyage.status = "cancelled"
        dispatch.voyage.offboard_at = dispatch.voyage.offboard_at or utc_now()
    db.commit()
    db.refresh(dispatch)
    return dispatch_to_dict(dispatch)
