from datetime import date, datetime
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .models import (
    CERTIFICATE_REVIEW_STATUSES,
    CREW_STATUSES,
    DISPATCH_STATUSES,
    JOB_STATUSES,
    ROUTE_STATUSES,
    SHIP_STATUSES,
    USER_ROLES,
)


PHONE_PATTERN = re.compile(r"^\+?\d{6,20}$")
ID_CARD_PATTERN = re.compile(r"^\d{15}$|^\d{17}[\dXx]$")


def _strip_text(value: str) -> str:
    return value.strip() if isinstance(value, str) else value


def _require_text(value: str, field_name: str, max_length: int | None = None) -> str:
    value = _strip_text(value)
    if not value:
        raise ValueError(f"{field_name}不能为空")
    if max_length is not None and len(value) > max_length:
        raise ValueError(f"{field_name}长度不能超过 {max_length} 个字符")
    return value


def _validate_optional_phone(value: str | None) -> str | None:
    value = _strip_text(value)
    if value in (None, ""):
        return None
    if not PHONE_PATTERN.fullmatch(value):
        raise ValueError("联系电话格式不正确")
    return value


class LoginRequest(BaseModel):
    username: str
    password: str

    @field_validator("username", mode="before")
    @classmethod
    def validate_username(cls, value: str):
        return _require_text(value, "账号", 50)

    @field_validator("password", mode="before")
    @classmethod
    def validate_password(cls, value: str):
        return _require_text(value, "密码")


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str
    display_name: str


class LoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class PositionCreate(BaseModel):
    name: str
    level: str | None = None
    base_salary: int | None = None
    description: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: str):
        return _require_text(value, "岗位名称", 50)

    @field_validator("level", "description", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: str | None):
        value = _strip_text(value)
        return value or None


class CertificateTypeCreate(BaseModel):
    name: str
    validity_months: int | None = None
    is_required: bool = True
    description: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: str):
        return _require_text(value, "证书类型", 50)

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: str | None):
        value = _strip_text(value)
        return value or None


class PortCreate(BaseModel):
    name: str
    country: str = "中国"
    city: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: str):
        return _require_text(value, "港口名称", 100)

    @field_validator("country", mode="before")
    @classmethod
    def validate_country(cls, value: str):
        return _require_text(value, "国家", 50)

    @field_validator("city", mode="before")
    @classmethod
    def normalize_city(cls, value: str | None):
        value = _strip_text(value)
        return value or None


class RouteCreate(BaseModel):
    route_name: str | None = None
    departure_port_id: int
    destination_port_id: int
    distance_nm: int | None = None
    estimated_days: int | None = None
    status: str = "active"

    @field_validator("route_name", mode="before")
    @classmethod
    def normalize_route_name(cls, value: str | None):
        value = _strip_text(value)
        return value or None

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, value: str):
        value = _strip_text(value)
        if value not in ROUTE_STATUSES:
            raise ValueError("航线状态不正确")
        return value

    @model_validator(mode="after")
    def validate_ports(self):
        if self.departure_port_id == self.destination_port_id:
            raise ValueError("出发港和目的港不能相同")
        return self


class ShipCreate(BaseModel):
    name: str
    company_id: int | None = None
    company_name: str | None = None
    ship_type: str = "散货船"
    tonnage: int | None = None
    capacity: int | None = None
    status: str = "active"

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: str):
        return _require_text(value, "船舶名称", 100)

    @field_validator("company_name", mode="before")
    @classmethod
    def normalize_company_name(cls, value: str | None):
        value = _strip_text(value)
        return value or None

    @field_validator("ship_type", mode="before")
    @classmethod
    def validate_ship_type(cls, value: str):
        return _require_text(value, "船舶类型", 50)

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, value: str):
        value = _strip_text(value)
        if value not in SHIP_STATUSES:
            raise ValueError("船舶状态不正确")
        return value


class CrewCreate(BaseModel):
    username: str
    password: str
    name: str
    gender: str = "男"
    id_card: str
    phone: str | None = None
    position: str = "水手"
    position_id: int | None = None

    @field_validator("username", mode="before")
    @classmethod
    def validate_username(cls, value: str):
        return _require_text(value, "账号", 50)

    @field_validator("password", mode="before")
    @classmethod
    def validate_password(cls, value: str):
        value = _require_text(value, "密码")
        if len(value) < 3:
            raise ValueError("密码长度不能少于 3 位")
        return value

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: str):
        return _require_text(value, "姓名", 50)

    @field_validator("gender", mode="before")
    @classmethod
    def validate_gender(cls, value: str):
        value = _strip_text(value)
        if value not in {"男", "女"}:
            raise ValueError("性别只能是男或女")
        return value

    @field_validator("id_card", mode="before")
    @classmethod
    def validate_id_card(cls, value: str):
        value = _require_text(value, "身份证号", 18)
        if not ID_CARD_PATTERN.fullmatch(value):
            raise ValueError("身份证号格式不正确")
        return value

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, value: str | None):
        return _validate_optional_phone(value)

    @field_validator("position", mode="before")
    @classmethod
    def validate_position(cls, value: str):
        return _require_text(value, "岗位", 50)


class CrewUpdate(BaseModel):
    name: str | None = None
    gender: str | None = None
    phone: str | None = None
    position: str | None = None
    position_id: int | None = None
    status: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: str | None):
        if value is None:
            return None
        return _require_text(value, "姓名", 50)

    @field_validator("gender", mode="before")
    @classmethod
    def validate_gender(cls, value: str | None):
        if value is None:
            return None
        value = _strip_text(value)
        if value not in {"男", "女"}:
            raise ValueError("性别只能是男或女")
        return value

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, value: str | None):
        return _validate_optional_phone(value)

    @field_validator("position", mode="before")
    @classmethod
    def validate_position(cls, value: str | None):
        if value is None:
            return None
        return _require_text(value, "岗位", 50)

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, value: str | None):
        if value is None:
            return None
        value = _strip_text(value)
        if value not in CREW_STATUSES:
            raise ValueError("船员状态不正确")
        return value


class CrewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    name: str
    gender: str
    id_card: str
    phone: str | None
    position: str
    status: str


class CertificateCreate(BaseModel):
    crew_id: int
    certificate_type: str
    certificate_type_id: int | None = None
    certificate_no: str
    issued_at: date
    expires_at: date
    attachment_url: str | None = None

    @field_validator("certificate_type", mode="before")
    @classmethod
    def validate_certificate_type(cls, value: str):
        return _require_text(value, "证书类型", 50)

    @field_validator("certificate_no", mode="before")
    @classmethod
    def validate_certificate_no(cls, value: str):
        return _require_text(value, "证书编号", 80)

    @field_validator("attachment_url", mode="before")
    @classmethod
    def normalize_attachment_url(cls, value: str | None):
        value = _strip_text(value)
        return value or None

    @model_validator(mode="after")
    def validate_date_order(self):
        if self.expires_at < self.issued_at:
            raise ValueError("证书到期日期不能早于签发日期")
        return self


class CertificateUpdate(BaseModel):
    certificate_type: str | None = None
    certificate_type_id: int | None = None
    certificate_no: str | None = None
    issued_at: date | None = None
    expires_at: date | None = None
    attachment_url: str | None = None

    @field_validator("certificate_type", mode="before")
    @classmethod
    def validate_certificate_type(cls, value: str | None):
        if value is None:
            return None
        return _require_text(value, "证书类型", 50)

    @field_validator("certificate_no", mode="before")
    @classmethod
    def validate_certificate_no(cls, value: str | None):
        if value is None:
            return None
        return _require_text(value, "证书编号", 80)

    @field_validator("attachment_url", mode="before")
    @classmethod
    def normalize_attachment_url(cls, value: str | None):
        value = _strip_text(value)
        return value or None

    @model_validator(mode="after")
    def validate_date_order(self):
        if self.issued_at and self.expires_at and self.expires_at < self.issued_at:
            raise ValueError("证书到期日期不能早于签发日期")
        return self


class CertificateReview(BaseModel):
    review_status: str
    remark: str | None = None

    @field_validator("review_status", mode="before")
    @classmethod
    def validate_review_status(cls, value: str):
        value = _strip_text(value)
        if value not in CERTIFICATE_REVIEW_STATUSES:
            raise ValueError("证书审核状态不正确")
        return value

    @field_validator("remark", mode="before")
    @classmethod
    def normalize_remark(cls, value: str | None):
        value = _strip_text(value)
        return value or None


class CertificateOut(BaseModel):
    id: int
    crew_id: int
    crew_name: str
    certificate_type: str
    certificate_no: str
    issued_at: date
    expires_at: date
    review_status: str
    review_remark: str | None
    is_expired: bool
    is_expiring_soon: bool


class JobCreate(BaseModel):
    title: str
    ship_name: str | None = None
    ship_id: int | None = None
    route: str | None = None
    route_id: int | None = None
    required_position: str | None = None
    position_id: int | None = None
    required_certificates: list[str] = Field(default_factory=list)
    required_certificate_type_ids: list[int] = Field(default_factory=list)
    headcount: int = 1
    onboard_at: datetime

    @field_validator("title", mode="before")
    @classmethod
    def validate_title(cls, value: str):
        return _require_text(value, "岗位标题", 100)

    @field_validator("ship_name", mode="before")
    @classmethod
    def normalize_ship_name(cls, value: str | None):
        value = _strip_text(value)
        return value or None

    @field_validator("route", mode="before")
    @classmethod
    def normalize_route(cls, value: str | None):
        value = _strip_text(value)
        return value or None

    @field_validator("required_position", mode="before")
    @classmethod
    def normalize_required_position(cls, value: str | None):
        value = _strip_text(value)
        return value or None

    @field_validator("required_certificates", mode="before")
    @classmethod
    def validate_required_certificates(cls, value: list[str]):
        return value or []

    @field_validator("required_certificate_type_ids", mode="before")
    @classmethod
    def validate_required_certificate_type_ids(cls, value: list[int]):
        return value or []

    @field_validator("headcount")
    @classmethod
    def validate_headcount(cls, value: int):
        if value < 1:
            raise ValueError("招聘人数不能少于 1")
        return value


class JobOut(BaseModel):
    id: int
    owner_user_id: int
    title: str
    ship_name: str
    route: str
    required_position: str
    required_certificates: list[str]
    headcount: int
    onboard_at: datetime
    status: str


class DispatchCreate(BaseModel):
    job_id: int
    crew_id: int


class DispatchOut(BaseModel):
    id: int
    job_id: int
    crew_id: int
    status: str


class VoyageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dispatch_id: int
    crew_id: int
    job_id: int
    ship_name: str
    route: str
    position: str
    onboard_at: datetime
    offboard_at: datetime | None
    status: str


def ensure_valid_role(role: str) -> str:
    if role not in USER_ROLES:
        raise ValueError("系统角色不正确")
    return role


def ensure_valid_job_status(status: str) -> str:
    if status not in JOB_STATUSES:
        raise ValueError("岗位状态不正确")
    return status


def ensure_valid_dispatch_status(status: str) -> str:
    if status not in DISPATCH_STATUSES:
        raise ValueError("派遣状态不正确")
    return status
