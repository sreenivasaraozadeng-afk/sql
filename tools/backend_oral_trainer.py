"""Backend oral-defense trainer for the Seafarer Management project.

Run from the project root:

    python tools/backend_oral_trainer.py

This is different from backend_quiz.py. The quiz checks recognition with
multiple-choice questions; this script trains you to speak a backend answer out
loud before seeing the reference answer.
"""

from __future__ import annotations

import argparse
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class OralCard:
    topic: str
    prompt: str
    must_mention: tuple[str, ...]
    sample_answer: str
    files: tuple[str, ...]


CARDS: tuple[OralCard, ...] = (
    OralCard(
        "整体结构",
        "请你用 1 分钟介绍后端整体分层，以及一个请求进入后端会经过哪些步骤。",
        (
            "routers 负责接口和权限",
            "schemas 负责参数校验",
            "services 负责业务逻辑",
            "models 对应数据库表",
            "请求链路是 router -> schema/dependency -> service -> model -> database",
        ),
        "后端采用 FastAPI 和 SQLAlchemy，代码分为 routers、schemas、services、models。"
        "router 层接收请求并做权限入口，schema 校验前端参数，dependency 注入数据库 session 和当前用户，"
        "service 层执行业务规则，model 层映射数据库表，最后返回统一 JSON 给前端。",
        (
            "backend/app/main.py",
            "backend/app/routers/*.py",
            "backend/app/schemas.py",
            "backend/app/services.py",
            "backend/app/models.py",
        ),
    ),
    OralCard(
        "登录权限",
        "请你讲清楚登录接口从前端提交账号密码到返回 token，中间发生了什么。",
        (
            "POST /api/auth/login",
            "LoginRequest 校验 username/password",
            "authenticate_user 查询 users 表",
            "verify_password 校验 password_hash",
            "create_access_token 生成 token",
            "require_roles 控制后续接口权限",
        ),
        "登录接口是 POST /api/auth/login。前端传 username 和 password 后，LoginRequest 先校验字段，"
        "services.authenticate_user 根据 username 查询 users 表，再用 verify_password 对比密码哈希。"
        "成功后 create_access_token 生成 token，后续接口通过 token 识别当前用户，并用 require_roles 判断角色权限。",
        (
            "backend/app/routers/auth.py",
            "backend/app/schemas.py",
            "backend/app/services.py",
            "backend/app/passwords.py",
            "backend/app/security.py",
            "backend/app/dependencies.py",
        ),
    ),
    OralCard(
        "船员管理",
        "为什么创建船员时要同时写 users 和 crews 两张表？请结合代码层次说。",
        (
            "users 保存登录账号、密码哈希、角色",
            "crews 保存船员业务档案",
            "crews.user_id 外键指向 users.id",
            "一对一关系",
            "新船员默认 seafarer 和 available",
            "写 operation_logs",
        ),
        "创建船员接口是 POST /api/crews，入口在 routers/crews.py。CrewCreate 校验参数后，"
        "services.create_crew 会同时创建 User 和 Crew。User 用于登录权限，Crew 保存姓名、身份证、电话、岗位和状态。"
        "crews.user_id 指向 users.id 并且唯一，形成一对一关系。新船员默认角色 seafarer，状态 available，并记录操作日志。",
        (
            "backend/app/routers/crews.py",
            "backend/app/schemas.py",
            "backend/app/services.py",
            "backend/app/models.py",
        ),
    ),
    OralCard(
        "证书审核",
        "证书从录入到审核通过，会改哪些表？为什么审核会影响智能匹配？",
        (
            "POST /api/certificates",
            "PUT /api/certificates/{id}/review",
            "certificates 保存当前证书状态",
            "certificate_review_records 保存审核历史",
            "pending/approved/rejected",
            "只有 approved 且未过期证书参与匹配",
        ),
        "证书录入后写 certificates 表，默认 review_status 是 pending。证书管理员调用审核接口后，"
        "review_certificate 会更新 certificates 的 review_status 和 review_remark，并新增 certificate_review_records 审核记录。"
        "智能匹配只统计 approved 且 expires_at 没过期的证书，所以审核结果会直接影响岗位匹配和派遣校验。",
        (
            "backend/app/routers/certificates.py",
            "backend/app/schemas.py",
            "backend/app/services.py",
            "backend/app/models.py",
        ),
    ),
    OralCard(
        "岗位需求",
        "为什么岗位需求要拆成 job_demands 和 job_required_certificates 两张表？",
        (
            "job_demands 是岗位需求主表",
            "job_required_certificates 是所需证书明细表",
            "一个岗位可以要求多个证书",
            "一对多关系",
            "避免逗号拼接多值字段",
            "方便查询、统计和外键约束",
        ),
        "job_demands 保存岗位主信息，比如船舶、航线、岗位、人数和上船时间。"
        "岗位所需证书单独放在 job_required_certificates，因为一个岗位可能要求多种证书。"
        "这样是主表加明细表的一对多设计，比把多个证书拼成一个字符串更规范，也方便查询和统计。",
        (
            "backend/app/routers/jobs.py",
            "backend/app/schemas.py",
            "backend/app/services.py",
            "backend/app/models.py",
        ),
    ),
    OralCard(
        "智能匹配",
        "请你讲清楚智能匹配 100 分模型，以及为什么它不是前端写死的。",
        (
            "GET /api/jobs/{job_id}/matches",
            "list_matching_crews 查询 available 船员",
            "_score_match 计算分数",
            "岗位 40 分",
            "证书满足度 40 分",
            "证书有效期风险 10 分",
            "历史海历 10 分",
            "只返回 60 分以上",
        ),
        "智能匹配接口在 routers/matching.py，真正逻辑在 services.list_matching_crews 和 _score_match。"
        "后端会查询 available 船员，并加载证书和海历。评分总分 100，岗位匹配 40，证书满足度 40，"
        "证书有效期风险 10，历史海历经验 10。最后只返回 60 分以上，并给出 match_reasons、missing_certificates 等解释。",
        (
            "backend/app/routers/matching.py",
            "backend/app/services.py",
            "backend/app/models.py",
        ),
    ),
    OralCard(
        "派遣流程",
        "请你讲清楚从发起派遣到下船，dispatches、crews、voyage_records 怎么变化。",
        (
            "POST /api/dispatches",
            "pending_owner -> confirmed -> onboard -> offboard",
            "船东确认后 crew.status 变 pending",
            "上船后 crew.status 变 at_sea",
            "上船时新增 voyage_records",
            "下船后 crew.status 恢复 available",
            "下船后写 offboard_at",
        ),
        "经理发起派遣后，dispatches 新增记录，状态是 pending_owner。船东确认后状态变 confirmed，船员状态变 pending。"
        "经理确认上船后状态变 onboard，船员状态变 at_sea，同时新增 voyage_records 海历。"
        "确认下船后状态变 offboard，船员恢复 available，岗位关闭，海历写入 offboard_at。",
        (
            "backend/app/routers/dispatches.py",
            "backend/app/services.py",
            "backend/app/models.py",
        ),
    ),
    OralCard(
        "派遣校验",
        "创建派遣前，后端为什么还要校验船员岗位和证书？不是已经智能匹配了吗？",
        (
            "智能匹配是推荐",
            "create_dispatch 是强校验",
            "_ensure_crew_matches_job",
            "船员必须 available",
            "岗位必须匹配",
            "不能有进行中派遣",
            "证书必须 approved 且未过期",
        ),
        "智能匹配只是推荐列表，不能代替后端规则。create_dispatch 会调用 _ensure_crew_matches_job，"
        "再次检查船员是否 available、岗位是否一致、是否已有 pending_owner/confirmed/onboard 的派遣，"
        "以及证书是否审核通过且未过期。这样即使绕过前端，后端也能保证数据合法。",
        (
            "backend/app/services.py",
            "backend/app/models.py",
        ),
    ),
    OralCard(
        "日志设计",
        "operation_logs 和 dispatch_status_logs 有什么区别？为什么两张都需要？",
        (
            "operation_logs 是系统级操作审计",
            "dispatch_status_logs 是派遣状态流转日志",
            "operation_logs 覆盖船员、证书、岗位、派遣",
            "dispatch_status_logs 记录 old_status/new_status",
            "两者粒度不同",
        ),
        "operation_logs 是系统级操作审计，记录谁对什么对象做了什么，比如创建船员、审核证书、创建派遣。"
        "dispatch_status_logs 是派遣业务专用日志，只记录某条派遣从 old_status 变成 new_status。"
        "一个偏系统审计，一个偏业务流程轨迹，所以两张表都需要。",
        (
            "backend/app/services.py",
            "backend/app/models.py",
            "backend/app/routers/logs.py",
        ),
    ),
    OralCard(
        "统计首页",
        "请你说明首页统计接口的数据分别从哪些表来。",
        (
            "summary 查 crews/certificates/job_demands/dispatches/ships",
            "crew-status 按 crews.status 统计",
            "certificate-alerts 查 certificates 并关联 crews",
            "dispatch-trend 按 dispatches.created_at 统计",
            "route-workload 按 voyage_records.route 统计",
            "前端只负责展示",
        ),
        "统计接口在 routers/dashboard.py。summary 从 crews、certificates、job_demands、dispatches、ships 统计卡片数据。"
        "crew-status 按 crews.status 分布统计，certificate-alerts 查询 30 天内到期证书并关联船员，"
        "dispatch-trend 按 dispatches.created_at 的年月统计，route-workload 按 voyage_records.route 统计航线工作量。"
        "这些都由后端查询，前端只展示。",
        (
            "backend/app/routers/dashboard.py",
            "backend/app/services.py",
            "backend/app/models.py",
        ),
    ),
    OralCard(
        "数据库设计",
        "请你用数据库课程设计角度总结这个后端的亮点。",
        (
            "不是简单 CRUD",
            "表拆分清晰",
            "外键关联",
            "状态流转",
            "审核记录和操作日志",
            "统计查询",
            "证书影响匹配，派遣生成海历，海历支持统计",
        ),
        "这个后端的重点不是简单 CRUD，而是用数据库表关系支撑完整业务流程。"
        "users 和 crews 拆分账号与档案，证书有审核历史，岗位需求和所需证书是一对多，"
        "派遣有状态流转和日志，上船自动生成海历，海历又能支持航线工作量统计。"
        "这些设计体现了外键关系、约束、日志追溯和统计查询。",
        (
            "backend/app/models.py",
            "backend/app/services.py",
            "docs/backend_defense_speech.md",
        ),
    ),
)


def available_topics() -> list[str]:
    return sorted({card.topic for card in CARDS})


def choose_cards(topic: str | None, count: int, all_cards: bool, seed: int | None) -> list[OralCard]:
    cards = [card for card in CARDS if topic is None or card.topic == topic]
    if not cards:
        valid = "、".join(available_topics())
        raise SystemExit(f"没有找到主题：{topic}。可选主题：{valid}")
    if all_cards:
        return cards
    rng = random.Random(seed)
    selected = cards[:]
    rng.shuffle(selected)
    return selected[: min(count, len(selected))]


def read_score() -> int:
    while True:
        value = input("给自己打分 0/1/2（0 不会，1 说到一半，2 基本讲清楚）：").strip()
        if value in {"0", "1", "2"}:
            return int(value)
        print("请输入 0、1 或 2。")


def run_session(cards: list[OralCard], show_files: bool) -> None:
    print("后端口述训练开始")
    print("规则：先自己大声回答，再按回车看关键词和参考答案。")
    print()

    topic_scores: dict[str, list[int]] = {}
    total = 0

    for index, card in enumerate(cards, start=1):
        print("=" * 72)
        print(f"第 {index}/{len(cards)} 题｜{card.topic}")
        print(card.prompt)
        input("先自己讲一遍。讲完按回车查看参考要点...")
        print()
        print("你回答时至少要提到：")
        for item in card.must_mention:
            print(f"- {item}")
        print()
        print("参考答法：")
        print(card.sample_answer)
        if show_files:
            print()
            print("对应代码文件：")
            for file in card.files:
                print(f"- {file}")
        print()
        score = read_score()
        topic_scores.setdefault(card.topic, []).append(score)
        total += score
        print()

    max_score = len(cards) * 2
    percent = int(total * 100 / max_score) if max_score else 0
    print("=" * 72)
    print(f"本轮得分：{total}/{max_score}，约 {percent}%")
    print()
    print("分主题情况：")
    for topic, scores in sorted(topic_scores.items()):
        topic_total = sum(scores)
        topic_max = len(scores) * 2
        print(f"- {topic}: {topic_total}/{topic_max}")

    weak_topics = [topic for topic, scores in topic_scores.items() if sum(scores) < len(scores) * 2]
    if weak_topics:
        print()
        print("建议回看这些主题的逐行精讲：")
        for topic in sorted(weak_topics):
            print(f"- {topic}")
    else:
        print()
        print("这轮很稳。下一步可以打开代码文件，边指代码边讲。")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Practice backend oral defense answers.")
    parser.add_argument("--topic", choices=available_topics(), help="只练某一个主题")
    parser.add_argument("--count", type=int, default=6, help="本轮抽几题，默认 6")
    parser.add_argument("--all", action="store_true", help="练当前范围内全部题目")
    parser.add_argument("--seed", type=int, default=None, help="固定抽题顺序")
    parser.add_argument("--show-files", action="store_true", help="显示每题对应代码文件")
    parser.add_argument("--list-topics", action="store_true", help="列出可练主题后退出")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.list_topics:
        print("可选主题：")
        for topic in available_topics():
            print(f"- {topic}")
        return 0
    if args.count < 1:
        raise SystemExit("--count 必须大于等于 1")
    cards = choose_cards(args.topic, args.count, args.all, args.seed)
    run_session(cards, args.show_files)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
