from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import services
from ..dependencies import get_db, require_roles
from ..models import User
from ..schemas import CertificateTypeCreate, PortCreate, PositionCreate, RouteCreate


positions_router = APIRouter(prefix="/api/positions", tags=["positions"])
certificate_types_router = APIRouter(
    prefix="/api/certificate-types",
    tags=["certificate-types"],
)
ports_router = APIRouter(prefix="/api/ports", tags=["ports"])
routes_router = APIRouter(prefix="/api/routes", tags=["routes"])


@positions_router.get("")
def list_positions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("manager", "cert_admin", "shipowner", "admin")),
):
    return {"success": True, "data": services.list_positions(db)}


@positions_router.post("")
def create_position(
    payload: PositionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("manager", "admin")),
):
    return {
        "success": True,
        "message": "岗位已创建",
        "data": services.create_position(db, payload, current_user),
    }


@certificate_types_router.get("")
def list_certificate_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("manager", "cert_admin", "shipowner", "admin")),
):
    return {"success": True, "data": services.list_certificate_types(db)}


@certificate_types_router.post("")
def create_certificate_type(
    payload: CertificateTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("cert_admin", "admin")),
):
    return {
        "success": True,
        "message": "证书类型已创建",
        "data": services.create_certificate_type(db, payload, current_user),
    }


@ports_router.get("")
def list_ports(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("manager", "shipowner", "admin")),
):
    return {"success": True, "data": services.list_ports(db)}


@ports_router.post("")
def create_port(
    payload: PortCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("manager", "admin")),
):
    return {
        "success": True,
        "message": "港口已创建",
        "data": services.create_port(db, payload, current_user),
    }


@routes_router.get("")
def list_routes(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("manager", "shipowner", "admin")),
):
    return {"success": True, "data": services.list_routes(db)}


@routes_router.post("")
def create_route(
    payload: RouteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("manager", "admin")),
):
    return {
        "success": True,
        "message": "航线已创建",
        "data": services.create_route(db, payload, current_user),
    }
