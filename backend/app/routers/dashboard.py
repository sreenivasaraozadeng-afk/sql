from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import services
from ..dependencies import get_db, require_roles
from ..models import User


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
def summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("manager", "cert_admin", "shipowner", "admin")),
):
    return {"success": True, "data": services.dashboard_summary(db)}


@router.get("/crew-status")
def crew_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("manager", "cert_admin", "shipowner", "admin")),
):
    return {"success": True, "data": services.dashboard_crew_status(db)}


@router.get("/certificate-alerts")
def certificate_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("manager", "cert_admin", "shipowner", "admin")),
):
    return {"success": True, "data": services.dashboard_certificate_alerts(db)}


@router.get("/dispatch-trend")
def dispatch_trend(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("manager", "shipowner", "admin")),
):
    return {"success": True, "data": services.dashboard_dispatch_trend(db)}


@router.get("/route-workload")
def route_workload(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("manager", "shipowner", "admin")),
):
    return {"success": True, "data": services.dashboard_route_workload(db)}
