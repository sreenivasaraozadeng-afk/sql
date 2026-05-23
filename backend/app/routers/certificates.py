from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import services
from ..dependencies import get_db, require_roles
from ..models import User
from ..schemas import CertificateCreate, CertificateUpdate


router = APIRouter(prefix="/api/certificates", tags=["certificates"])


@router.get("")
def list_certificates(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("manager", "cert_admin", "admin")),
):
    return {"success": True, "data": services.list_certificates(db)}


@router.post("")
def create_certificate(
    payload: CertificateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("cert_admin", "manager", "admin")),
):
    return {
        "success": True,
        "message": "证书录入成功",
        "data": services.create_certificate(db, payload),
    }


@router.get("/alerts")
def certificate_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("cert_admin", "manager", "admin")),
):
    return {"success": True, "data": services.list_certificate_alerts(db)}


@router.put("/{certificate_id}")
def update_certificate(
    certificate_id: int,
    payload: CertificateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("cert_admin", "manager", "admin")),
):
    return {
        "success": True,
        "message": "证书更新成功",
        "data": services.update_certificate(db, certificate_id, payload),
    }
