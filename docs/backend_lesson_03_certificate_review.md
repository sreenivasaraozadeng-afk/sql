# 后端逐行精讲 03：证书录入与审核

这一课讲证书模块两条核心接口：

```text
POST /api/certificates
PUT /api/certificates/{certificate_id}/review
```

目标是让你讲清楚：证书为什么要先录入、再审核，以及审核结果为什么会影响智能匹配。

## 1. 先看完整流程

```text
证书管理员/经理录入证书
-> CertificateCreate 校验证书信息
-> services.create_certificate 创建 certificates 记录
-> review_status 默认 pending
-> 证书管理员审核证书
-> CertificateReview 校验审核状态
-> services.review_certificate 修改 certificates 当前状态
-> 新增 certificate_review_records 审核历史
-> 写 operation_logs
-> 智能匹配只认可 approved 且未过期证书
```

涉及文件：

| 文件 | 在证书模块里做什么 |
| --- | --- |
| `routers/certificates.py` | 定义证书录入、查询、审核接口 |
| `schemas.py` | 校验证书请求和审核请求 |
| `services.py` | 创建证书、更新证书、审核证书、证书预警 |
| `models.py` | 定义 `certificates`、`certificate_review_records`、`certificate_types` |
| `dependencies.py` | 通过 `require_roles` 做角色权限 |

## 2. 路由层：`routers/certificates.py`

导入：

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import services
from ..dependencies import get_db, require_roles
from ..models import User
from ..schemas import CertificateCreate, CertificateReview, CertificateUpdate
```

解释：

- `APIRouter`：定义证书接口组。
- `Depends`：注入数据库连接和当前用户。
- `Session`：数据库会话。
- `services`：证书业务逻辑。
- `get_db`：提供数据库 session。
- `require_roles`：限制哪些角色能操作。
- `CertificateCreate`：录入证书请求。
- `CertificateReview`：审核证书请求。
- `CertificateUpdate`：更新证书请求。

路由前缀：

```python
router = APIRouter(prefix="/api/certificates", tags=["certificates"])
```

所以本文件接口都以：

```text
/api/certificates
```

开头。

## 3. 查询证书接口

代码：

```python
@router.get("")
def list_certificates(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("manager", "cert_admin", "admin")),
):
    return {"success": True, "data": services.list_certificates(db)}
```

完整地址：

```text
GET /api/certificates
```

权限：

```text
manager / cert_admin / admin
```

这说明普通船员和船东不能随便查看全部证书列表。

## 4. 录入证书接口

代码：

```python
@router.post("")
def create_certificate(
    payload: CertificateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("cert_admin", "manager", "admin")),
):
    return {
        "success": True,
        "message": "证书录入成功，等待审核",
        "data": services.create_certificate(db, payload, current_user),
    }
```

完整地址：

```text
POST /api/certificates
```

权限：

```text
cert_admin / manager / admin
```

逐行解释：

```python
payload: CertificateCreate
```

前端传来的证书信息会被 `CertificateCreate` 校验。

```python
current_user: User = Depends(require_roles("cert_admin", "manager", "admin"))
```

只有证书管理员、业务经理、管理员能录入证书。

```python
"message": "证书录入成功，等待审核"
```

注意这里写的是“等待审核”，不是“证书已生效”。

```python
services.create_certificate(db, payload, current_user)
```

真正的创建逻辑在 service 层。

答辩可以说：

> 证书录入接口只创建待审核证书，录入成功后默认等待证书管理员审核。

## 5. 审核证书接口

代码：

```python
@router.put("/{certificate_id}/review")
def review_certificate(
    certificate_id: int,
    payload: CertificateReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("cert_admin", "admin")),
):
    return {
        "success": True,
        "message": "证书审核完成",
        "data": services.review_certificate(db, certificate_id, payload, current_user),
    }
```

完整地址：

```text
PUT /api/certificates/{certificate_id}/review
```

例如：

```text
PUT /api/certificates/3/review
```

权限：

```text
cert_admin / admin
```

注意：

经理可以录入证书，但不能最终审核证书。这个权限分工很好讲。

答辩可以说：

> 系统把证书录入和证书审核分开，录入可以由经理或证书管理员完成，但审核只允许证书管理员或管理员执行，体现了角色权限控制。

## 6. 录入参数：`CertificateCreate`

代码：

```python
class CertificateCreate(BaseModel):
    crew_id: int
    certificate_type: str
    certificate_type_id: int | None = None
    certificate_no: str
    issued_at: date
    expires_at: date
    attachment_url: str | None = None
```

示例请求：

```json
{
  "crew_id": 1,
  "certificate_type": "STCW",
  "certificate_no": "CERT2026001",
  "issued_at": "2026-01-01",
  "expires_at": "2031-01-01",
  "attachment_url": ""
}
```

字段解释：

| 字段 | 作用 |
| --- | --- |
| `crew_id` | 证书属于哪个船员 |
| `certificate_type` | 证书类型名称 |
| `certificate_type_id` | 证书类型字典 id |
| `certificate_no` | 证书编号 |
| `issued_at` | 签发日期 |
| `expires_at` | 到期日期 |
| `attachment_url` | 附件地址，可为空 |

证书类型校验：

```python
def validate_certificate_type(cls, value: str):
    return _require_text(value, "证书类型", 50)
```

证书类型不能为空，最长 50。

证书编号校验：

```python
def validate_certificate_no(cls, value: str):
    return _require_text(value, "证书编号", 80)
```

证书编号不能为空，最长 80。

附件地址处理：

```python
value = _strip_text(value)
return value or None
```

如果前端传空字符串，就转成 `None`。

日期顺序校验：

```python
@model_validator(mode="after")
def validate_date_order(self):
    if self.expires_at < self.issued_at:
        raise ValueError("证书到期日期不能早于签发日期")
    return self
```

这表示：

```text
到期日期不能早于签发日期
```

答辩可以说：

> 证书录入时，Schema 会校验证书类型、证书编号和日期顺序，避免明显不合法的数据进入业务逻辑。

## 7. 审核参数：`CertificateReview`

代码：

```python
class CertificateReview(BaseModel):
    review_status: str
    remark: str | None = None
```

示例请求：

```json
{
  "review_status": "approved",
  "remark": "证书真实有效"
}
```

审核状态校验：

```python
if value not in CERTIFICATE_REVIEW_STATUSES:
    raise ValueError("证书审核状态不正确")
```

允许的状态来自 `models.py`：

```python
CERTIFICATE_REVIEW_STATUSES = ("pending", "approved", "rejected")
```

也就是说，审核状态只能是：

```text
pending / approved / rejected
```

备注处理：

```python
value = _strip_text(value)
return value or None
```

空备注会保存为 `None`。

答辩可以说：

> 审核请求通过 `CertificateReview` 限制状态值，只允许 pending、approved、rejected 三种状态，避免数据库中出现非法审核状态。

## 8. 证书类型字典：`_get_certificate_type_name`

代码：

```python
def _get_certificate_type_name(
    db: Session,
    certificate_type_id: int | None,
    fallback: str | None,
) -> tuple[int | None, str]:
    if certificate_type_id is not None:
        certificate_type = db.get(CertificateType, certificate_type_id)
        if certificate_type is None:
            raise ApiError(404, "证书类型不存在")
        return certificate_type.id, certificate_type.name
    if fallback:
        certificate_type = db.scalar(
            select(CertificateType).where(CertificateType.name == fallback)
        )
        if certificate_type is None:
            certificate_type = CertificateType(name=fallback, is_required=True)
            db.add(certificate_type)
            db.flush()
        return certificate_type.id, certificate_type.name
    raise ApiError(400, "证书类型不能为空")
```

这段和岗位字典类似，支持两种输入：

第一种：前端传 `certificate_type_id`。

后端直接查 `certificate_types` 表。

第二种：前端只传证书类型名称。

后端按名称查；如果不存在，就自动创建一条证书类型字典记录。

答辩可以说：

> 证书类型使用字典表统一管理。接口既支持传证书类型 id，也兼容直接传中文名称，后端会统一解析为证书类型 id 和名称。

## 9. 业务逻辑：`create_certificate`

完整代码：

```python
def create_certificate(
    db: Session,
    payload: CertificateCreate,
    actor: User | None = None,
) -> dict:
    crew = _get_crew_or_404(db, payload.crew_id)
    certificate_type_id, certificate_type_name = _get_certificate_type_name(
        db,
        payload.certificate_type_id,
        payload.certificate_type,
    )
    certificate = Certificate(
        crew=crew,
        certificate_type_id=certificate_type_id,
        certificate_type=certificate_type_name,
        certificate_no=payload.certificate_no,
        issued_at=payload.issued_at,
        expires_at=payload.expires_at,
        review_status="pending",
        attachment_url=payload.attachment_url,
    )
    db.add(certificate)
    _flush_or_duplicate(db, "证书编号已存在")
    _add_operation_log(
        db,
        actor,
        "create",
        "certificate",
        certificate.id,
        f"{crew.name}-{certificate.certificate_type}",
    )
    _commit_or_duplicate(db, "证书编号已存在")
    db.refresh(certificate)
    return certificate_to_dict(certificate)
```

逐行解释：

```python
crew = _get_crew_or_404(db, payload.crew_id)
```

先确认这个船员存在。

如果 `crew_id` 不存在，不能给不存在的船员录证书。

```python
certificate_type_id, certificate_type_name = _get_certificate_type_name(...)
```

处理证书类型字典。

```python
certificate = Certificate(...)
```

创建证书对象，对应 `certificates` 表。

```python
crew=crew
```

这表示证书属于这个船员。

```python
review_status="pending"
```

这是最重要的一行。

证书刚录入时，默认待审核，不是直接有效。

```python
db.add(certificate)
```

加入数据库会话。

```python
_flush_or_duplicate(db, "证书编号已存在")
```

先让数据库检查唯一约束。`certificate_no` 不能重复。

```python
_add_operation_log(...)
```

写操作日志，记录谁录入了哪本证书。

```python
_commit_or_duplicate(...)
```

提交事务。

```python
return certificate_to_dict(certificate)
```

转换成前端需要的数据格式。

答辩可以说：

> 录入证书时，系统会先确认船员存在，再处理证书类型字典，然后写入 `certificates` 表。新证书默认 `pending`，并不会直接参与匹配，等审核通过后才生效。

## 10. 业务逻辑：`review_certificate`

完整代码：

```python
def review_certificate(
    db: Session,
    certificate_id: int,
    payload: CertificateReview,
    reviewer: User,
) -> dict:
    certificate = db.get(Certificate, certificate_id)
    if certificate is None:
        raise ApiError(404, "证书不存在")
    old_status = certificate.review_status
    certificate.review_status = payload.review_status
    certificate.reviewed_by_user_id = reviewer.id
    certificate.reviewed_at = utc_now()
    certificate.review_remark = payload.remark
    db.add(
        CertificateReviewRecord(
            certificate=certificate,
            reviewer_user_id=reviewer.id,
            old_status=old_status,
            new_status=payload.review_status,
            remark=payload.remark,
        )
    )
    _add_operation_log(
        db,
        reviewer,
        "review",
        "certificate",
        certificate.id,
        f"{old_status}->{payload.review_status}",
    )
    db.commit()
    db.refresh(certificate)
    return certificate_to_dict(certificate)
```

逐行解释：

```python
certificate = db.get(Certificate, certificate_id)
```

按主键查证书。

```python
if certificate is None:
    raise ApiError(404, "证书不存在")
```

证书不存在就返回 404。

```python
old_status = certificate.review_status
```

先记录审核前状态。

为什么要记录？

因为后面要写审核历史，比如 `pending -> approved`。

```python
certificate.review_status = payload.review_status
```

修改当前审核状态。

```python
certificate.reviewed_by_user_id = reviewer.id
```

记录是谁审核的。

```python
certificate.reviewed_at = utc_now()
```

记录审核时间。

```python
certificate.review_remark = payload.remark
```

保存审核备注。

接着写审核历史：

```python
CertificateReviewRecord(
    certificate=certificate,
    reviewer_user_id=reviewer.id,
    old_status=old_status,
    new_status=payload.review_status,
    remark=payload.remark,
)
```

这会插入 `certificate_review_records` 表。

它保存：

- 哪本证书。
- 谁审核。
- 审核前状态。
- 审核后状态。
- 审核备注。
- 创建时间。

然后写操作日志：

```python
_add_operation_log(..., "review", "certificate", ...)
```

最后提交：

```python
db.commit()
```

答辩可以说：

> 审核证书时，系统不仅修改 `certificates` 表中的当前审核状态，还会插入 `certificate_review_records` 保存审核历史，并写入操作日志。这样既能看到证书当前状态，也能追溯每次审核过程。

## 11. 表结构：`CertificateType`、`Certificate`、`CertificateReviewRecord`

`CertificateType`：

```python
class CertificateType(Base):
    __tablename__ = "certificate_types"
    name = 证书类型名称，唯一
    validity_months = 有效期月份
    is_required = 是否常用必需证书
```

作用：

统一管理证书类型，如 `STCW`、`GMDSS`、`健康证`。

`Certificate`：

```python
class Certificate(Base):
    __tablename__ = "certificates"
    crew_id = ForeignKey("crews.id")
    certificate_type_id = ForeignKey("certificate_types.id")
    certificate_type = 证书类型名称
    certificate_no = 证书编号，唯一
    issued_at = 签发日期
    expires_at = 到期日期
    review_status = 审核状态
    reviewed_by_user_id = 审核人
    reviewed_at = 审核时间
    review_remark = 审核备注
```

作用：

保存证书当前信息和当前审核状态。

`CertificateReviewRecord`：

```python
class CertificateReviewRecord(Base):
    __tablename__ = "certificate_review_records"
    certificate_id = ForeignKey("certificates.id")
    reviewer_user_id = ForeignKey("users.id")
    old_status = 审核前状态
    new_status = 审核后状态
    remark = 审核备注
```

作用：

保存每次审核历史。

答辩可以说：

> `certificates` 表保存证书当前状态，`certificate_review_records` 表保存审核历史，`certificate_types` 表统一管理证书类型。这种拆分能同时满足当前查询和历史追溯。

## 12. 返回数据：`certificate_to_dict`

代码：

```python
def certificate_to_dict(certificate: Certificate) -> dict:
    flags = certificate_flags(certificate.expires_at)
    return {
        "id": certificate.id,
        "crew_id": certificate.crew_id,
        "crew_name": certificate.crew.name,
        "certificate_type_id": certificate.certificate_type_id,
        "certificate_type": certificate.certificate_type,
        "certificate_no": certificate.certificate_no,
        "issued_at": certificate.issued_at,
        "expires_at": certificate.expires_at,
        "review_status": certificate.review_status,
        "review_remark": certificate.review_remark,
        "attachment_url": certificate.attachment_url,
        **flags,
    }
```

它会返回证书基础信息，也会通过：

```python
certificate_flags(certificate.expires_at)
```

计算两个前端展示字段：

```python
"is_expired": expires_at < today
"is_expiring_soon": today <= expires_at <= today + timedelta(days=30)
```

也就是：

- 是否已过期。
- 是否 30 天内即将过期。

答辩可以说：

> 返回证书数据时，后端会额外计算过期和即将过期标记，方便前端做证书预警展示。

## 13. 审核如何影响智能匹配

智能匹配里有这段：

```python
def _valid_certificate_types(crew: Crew, today: date) -> set[str]:
    return {
        certificate.certificate_type
        for certificate in crew.certificates
        if certificate.review_status == "approved" and certificate.expires_at >= today
    }
```

解释：

对某个船员，系统会遍历他的证书。

只有同时满足两个条件的证书才算有效：

```text
review_status == approved
expires_at >= today
```

所以：

- `pending` 证书不能匹配。
- `rejected` 证书不能匹配。
- 已过期证书不能匹配。
- 只有审核通过且未过期证书能匹配。

答辩可以说：

> 证书审核不是孤立功能，它直接影响岗位匹配。系统只把审核通过且未过期的证书计入有效证书集合，因此证书管理员的审核结果会决定船员是否满足岗位要求。

## 14. 这条链路体现了哪些数据库设计

| 设计点 | 体现在哪里 | 作用 |
| --- | --- | --- |
| 外键 | `certificates.crew_id` | 证书属于某个船员 |
| 外键 | `certificates.certificate_type_id` | 证书关联证书类型字典 |
| 外键 | `certificate_review_records.certificate_id` | 审核历史属于某本证书 |
| 外键 | `certificate_review_records.reviewer_user_id` | 记录审核人 |
| 唯一约束 | `certificates.certificate_no` | 证书编号不能重复 |
| 检查约束 | `certificates.review_status` | 状态只能是 pending/approved/rejected |
| 索引 | `expires_at`、`review_status` | 方便证书预警和审核状态查询 |
| 历史表 | `certificate_review_records` | 可追溯审核过程 |

答辩可以说：

> 证书模块不仅有普通增删改查，还体现了状态约束、唯一约束、外键关联、历史记录和预警查询，是数据库设计重点之一。

## 15. 调试这条接口

启动后端：

```powershell
cd C:\Users\zxj\Desktop\SeafarerManagementSystem_DBwork\backend
python run_sqlite.py
```

打开接口文档：

```text
http://127.0.0.1:3000/docs
```

先登录：

```json
{
  "username": "cert_admin",
  "password": "cert123"
}
```

录入证书：

```text
POST /api/certificates
```

示例：

```json
{
  "crew_id": 1,
  "certificate_type": "STCW",
  "certificate_no": "CERT_TEST_001",
  "issued_at": "2026-01-01",
  "expires_at": "2031-01-01",
  "attachment_url": ""
}
```

审核证书：

```text
PUT /api/certificates/{certificate_id}/review
```

示例：

```json
{
  "review_status": "approved",
  "remark": "证书真实有效"
}
```

建议打断点：

1. `routers/certificates.py` 的 `create_certificate`。
2. `services.py` 的 `_get_certificate_type_name`。
3. `services.py` 的 `create_certificate`。
4. `routers/certificates.py` 的 `review_certificate`。
5. `services.py` 的 `review_certificate`。
6. `services.py` 的 `_valid_certificate_types`。

观察变量：

| 变量 | 看什么 |
| --- | --- |
| `payload` | 前端传来的证书或审核信息 |
| `crew` | 证书所属船员 |
| `certificate` | 当前证书对象 |
| `old_status` | 审核前状态 |
| `payload.review_status` | 审核后状态 |
| `reviewer` | 审核人 |

## 16. 答辩模板

短版：

> 证书录入接口是 `POST /api/certificates`，录入后默认状态为 `pending`。证书审核接口是 `PUT /api/certificates/{id}/review`，只有证书管理员或管理员可以审核。审核时系统会修改 `certificates` 当前状态，同时写入 `certificate_review_records` 保存历史记录。后续智能匹配只认可审核通过且未过期的证书。

详细版：

> 证书模块分为录入和审核两步。录入时，后端使用 `CertificateCreate` 校验证书类型、证书编号和日期顺序，然后在 `services.create_certificate` 中确认船员存在、处理证书类型字典，并创建 `certificates` 记录，默认 `review_status` 为 `pending`。审核时，`CertificateReview` 会限制状态只能是 `pending`、`approved`、`rejected`，`services.review_certificate` 会修改证书当前状态、记录审核人、审核时间和备注，同时插入 `certificate_review_records` 保存从旧状态到新状态的审核历史。智能匹配时只统计 `approved` 且未过期的证书，因此证书审核直接影响岗位匹配结果。

## 17. 自测题

1. 证书录入接口和审核接口分别是什么？
2. 哪些角色可以录入证书？哪些角色可以审核证书？
3. `CertificateCreate` 校验了哪些字段？
4. 为什么到期日期不能早于签发日期？
5. 新录入证书默认状态是什么？
6. `certificates` 和 `certificate_review_records` 有什么区别？
7. 审核时为什么要保存 `old_status`？
8. 哪些证书能参与智能匹配？
9. 证书预警字段 `is_expired` 和 `is_expiring_soon` 从哪里来？
10. 证书模块体现了哪些数据库设计点？

能讲清这 10 个问题，证书审核链路就过关了。

