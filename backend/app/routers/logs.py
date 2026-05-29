from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import services
from ..dependencies import get_db, require_roles
from ..models import User


router = APIRouter(prefix="/api/operation-logs", tags=["operation-logs"])


@router.get("")
def list_operation_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("manager", "admin")),
):
    return {"success": True, "data": services.list_operation_logs(db)}
