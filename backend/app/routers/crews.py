from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import services
from ..dependencies import get_db, get_optional_current_user
from ..models import User
from ..schemas import CrewCreate, CrewUpdate


router = APIRouter(prefix="/api/crews", tags=["crews"])


def _enforce_role_when_authenticated(
    current_user: User | None,
    allowed_roles: set[str],
) -> None:
    if current_user is not None and current_user.role not in allowed_roles:
        raise services.ApiError(403, "Forbidden")


@router.get("")
def list_crews(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    _enforce_role_when_authenticated(
        current_user,
        {"manager", "cert_admin", "shipowner", "admin"},
    )
    return {"success": True, "data": services.list_crews(db)}


@router.post("")
def create_crew(
    payload: CrewCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    _enforce_role_when_authenticated(current_user, {"manager", "admin"})
    return {
        "success": True,
        "message": "Crew created",
        "data": services.create_crew(db, payload),
    }


@router.get("/{crew_id}")
def get_crew(
    crew_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    _enforce_role_when_authenticated(
        current_user,
        {"manager", "cert_admin", "shipowner", "admin"},
    )
    return {"success": True, "data": services.get_crew(db, crew_id)}


@router.put("/{crew_id}")
def update_crew(
    crew_id: int,
    payload: CrewUpdate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    _enforce_role_when_authenticated(current_user, {"manager", "admin"})
    return {
        "success": True,
        "message": "Crew updated",
        "data": services.update_crew(db, crew_id, payload),
    }


@router.delete("/{crew_id}")
def delete_crew(
    crew_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    _enforce_role_when_authenticated(current_user, {"manager", "admin"})
    return {
        "success": True,
        "message": "Crew deactivated",
        "data": services.soft_delete_crew(db, crew_id),
    }
