from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import services
from ..dependencies import get_db, require_roles
from ..models import User
from ..schemas import DispatchCreate


router = APIRouter(prefix="/api/dispatches", tags=["dispatches"])


@router.post("")
def create_dispatch(
    payload: DispatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("manager", "admin")),
):
    return {
        "success": True,
        "message": "派遣已提交船东确认",
        "data": services.create_dispatch(db, payload, current_user),
    }


@router.put("/{dispatch_id}/confirm")
def confirm_dispatch(
    dispatch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("shipowner", "admin")),
):
    return {
        "success": True,
        "message": "派遣已确认",
        "data": services.confirm_dispatch(db, dispatch_id, current_user),
    }


@router.put("/{dispatch_id}/onboard")
def onboard_dispatch(
    dispatch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("manager", "admin")),
):
    return {
        "success": True,
        "message": "已确认上船",
        "data": services.onboard_dispatch(db, dispatch_id),
    }


@router.put("/{dispatch_id}/offboard")
def offboard_dispatch(
    dispatch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("manager", "admin")),
):
    return {
        "success": True,
        "message": "已确认下船",
        "data": services.offboard_dispatch(db, dispatch_id),
    }


@router.put("/{dispatch_id}/cancel")
def cancel_dispatch(
    dispatch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("manager", "admin")),
):
    return {
        "success": True,
        "message": "派遣已取消",
        "data": services.cancel_dispatch(db, dispatch_id),
    }
