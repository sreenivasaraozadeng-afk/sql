from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from .. import services
from ..dependencies import get_db
from ..models import Crew, Dispatch, User, VoyageRecord
from ..schemas import DispatchCreate, JobCreate, LoginRequest
from ..security import create_access_token


router = APIRouter(prefix="/api", tags=["legacy-compat"])

RUNNING = "\u8fdb\u884c\u4e2d"
ARRIVED = "\u5df2\u62b5\u8fbe"
CANCELLED = "\u5df2\u53d6\u6d88"


class LegacyCrewStatusUpdate(BaseModel):
    is_at_sea: int


class LegacyVoyageCreate(BaseModel):
    crew_id: int
    departure_point: str
    destination_point: str
    departure_time: datetime
    expected_arrival_time: datetime | None = None


def _legacy_role(user: User) -> str:
    return "user" if user.role == "seafarer" else "admin"


def _legacy_user_id(user: User) -> int:
    if user.crew is not None:
        return user.crew.id
    return user.id


def _legacy_actor(db: Session) -> User:
    user = db.scalar(select(User).where(User.role == "admin").order_by(User.id))
    if user is None:
        user = db.scalar(select(User).where(User.role != "seafarer").order_by(User.id))
    if user is None:
        user = db.scalar(select(User).order_by(User.id))
    if user is None:
        raise services.ApiError(400, "No system user exists")
    return user


def _naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.replace(tzinfo=None)


def _route_parts(route: str) -> tuple[str, str]:
    for separator in ("->", "-", "\u2014", "\u81f3"):
        if separator in route:
            departure, destination = route.split(separator, 1)
            return departure.strip(), destination.strip()
    return route, ""


def _legacy_status(status: str) -> str:
    if status == "onboard":
        return RUNNING
    if status == "cancelled":
        return CANCELLED
    return ARRIVED


def _legacy_voyage_to_dict(voyage: VoyageRecord) -> dict:
    departure, destination = _route_parts(voyage.route)
    expected_arrival = None
    if voyage.dispatch is not None and voyage.dispatch.job is not None:
        expected_arrival = voyage.dispatch.job.onboard_at
    return {
        "record_id": voyage.id,
        "crew_id": voyage.crew_id,
        "crew_name": voyage.crew.name,
        "departure_point": departure,
        "destination_point": destination,
        "departure_time": voyage.onboard_at,
        "expected_arrival_time": expected_arrival,
        "actual_arrival_time": voyage.offboard_at,
        "status": _legacy_status(voyage.status),
    }


def _list_legacy_voyages(db: Session, crew_id: int | None = None) -> list[dict]:
    query = (
        select(VoyageRecord)
        .options(
            joinedload(VoyageRecord.crew),
            joinedload(VoyageRecord.dispatch).joinedload(Dispatch.job),
        )
        .order_by(VoyageRecord.id.desc())
    )
    if crew_id is not None:
        query = query.where(VoyageRecord.crew_id == crew_id)
    voyages = db.scalars(query).unique().all()
    return [_legacy_voyage_to_dict(voyage) for voyage in voyages]


@router.post("/login")
def legacy_login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = services.authenticate_user(db, payload)
    token = create_access_token(user.id, user.role)
    return {
        "success": True,
        "message": "Login successful",
        "token": token,
        "id": _legacy_user_id(user),
        "username": user.username,
        "name": user.display_name,
        "role": _legacy_role(user),
    }


@router.get("/stats")
def legacy_stats(db: Session = Depends(get_db)):
    return {"success": True, "data": services.crew_stats(db)}


@router.put("/crews/{crew_id}/status")
def legacy_update_crew_status(
    crew_id: int,
    payload: LegacyCrewStatusUpdate,
    db: Session = Depends(get_db),
):
    data = services.set_crew_sea_status(db, crew_id, bool(payload.is_at_sea))
    return {"success": True, "message": "Crew status updated", "data": data}


@router.get("/voyages")
def legacy_list_voyages(db: Session = Depends(get_db)):
    return {"success": True, "data": _list_legacy_voyages(db)}


@router.post("/voyages")
def legacy_create_voyage(payload: LegacyVoyageCreate, db: Session = Depends(get_db)):
    crew = db.get(Crew, payload.crew_id)
    if crew is None:
        raise services.ApiError(404, "Crew not found")

    actor = _legacy_actor(db)
    expected_arrival = payload.expected_arrival_time or payload.departure_time
    job_data = services.create_job(
        db,
        JobCreate(
            title="Legacy voyage",
            ship_name="Legacy ship",
            route=f"{payload.departure_point}-{payload.destination_point}",
            required_position=crew.position,
            required_certificates=[],
            headcount=1,
            onboard_at=_naive(expected_arrival),
        ),
        actor,
    )
    dispatch_data = services.create_dispatch(
        db,
        DispatchCreate(job_id=job_data["id"], crew_id=crew.id),
        actor,
    )
    services.confirm_dispatch(db, dispatch_data["id"], actor)
    services.onboard_dispatch(db, dispatch_data["id"])

    voyage = db.scalar(
        select(VoyageRecord)
        .options(
            joinedload(VoyageRecord.crew),
            joinedload(VoyageRecord.dispatch).joinedload(Dispatch.job),
        )
        .where(VoyageRecord.dispatch_id == dispatch_data["id"])
    )
    if voyage is None:
        raise services.ApiError(500, "Voyage was not created")
    voyage.onboard_at = _naive(payload.departure_time)
    db.commit()
    db.refresh(voyage)
    return {
        "success": True,
        "message": "Voyage assigned",
        "data": _legacy_voyage_to_dict(voyage),
    }


@router.get("/my-profile/{crew_id}")
def legacy_my_profile(crew_id: int, db: Session = Depends(get_db)):
    return {"success": True, "data": services.get_crew(db, crew_id)}


@router.get("/my-voyages/{crew_id}")
def legacy_my_voyages(crew_id: int, db: Session = Depends(get_db)):
    return {"success": True, "data": _list_legacy_voyages(db, crew_id)}
