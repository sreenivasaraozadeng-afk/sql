from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import services
from ..dependencies import get_db, require_roles
from ..models import User


router = APIRouter(prefix="/api/jobs", tags=["matching"])


@router.get("/{job_id}/matches")
def match_crews(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("manager", "admin")),
):
    return {"success": True, "data": services.list_matching_crews(db, job_id)}
