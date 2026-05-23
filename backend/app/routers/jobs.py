from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import services
from ..dependencies import get_db, require_roles
from ..models import User
from ..schemas import JobCreate


router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("")
def list_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("manager", "shipowner", "admin")
    ),
):
    return {"success": True, "data": services.list_jobs(db)}


@router.post("")
def create_job(
    payload: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("shipowner", "admin")),
):
    return {
        "success": True,
        "message": "岗位发布成功",
        "data": services.create_job(db, payload, current_user),
    }


@router.put("/{job_id}/close")
def close_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("shipowner", "manager", "admin")),
):
    return {
        "success": True,
        "message": "岗位已关闭",
        "data": services.close_job(db, job_id, current_user),
    }


@router.get("/{job_id}")
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("manager", "shipowner", "admin")
    ),
):
    return {"success": True, "data": services.get_job(db, job_id)}
