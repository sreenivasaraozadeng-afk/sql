from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import services
from ..dependencies import get_db, require_roles
from ..models import User
from ..schemas import ShipCreate


router = APIRouter(prefix="/api/ships", tags=["ships"])


@router.get("")
def list_ships(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("manager", "shipowner", "admin")),
):
    return {"success": True, "data": services.list_ships(db, current_user)}


@router.post("")
def create_ship(
    payload: ShipCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("shipowner", "admin")),
):
    return {
        "success": True,
        "message": "船舶已创建",
        "data": services.create_ship(db, payload, current_user),
    }
