"""Interactive backend code quiz for the Seafarer Management project.

Run from the project root:

    python tools/backend_quiz.py

The quiz is intentionally small and practical. It checks whether you can connect
API routes, schemas, services, models, and database tables.
"""

from __future__ import annotations

import argparse
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Question:
    topic: str
    prompt: str
    choices: tuple[str, str, str, str]
    answer: str
    explanation: str


QUESTIONS: tuple[Question, ...] = (
    Question(
        "整体结构",
        "后端一次请求的主要代码链路是什么？",
        (
            "router -> schema/dependency -> service -> model -> database",
            "model -> router -> frontend -> schema -> database",
            "schema -> css -> service -> database -> html",
            "database -> frontend -> router -> model -> schema",
        ),
        "A",
        "接口先进 routers，参数由 schemas 校验，数据库和权限来自 dependencies，业务在 services，表结构在 models。",
    ),
    Question(
        "登录",
        "登录接口 POST /api/auth/login 的路由文件是哪个？",
        (
            "backend/app/routers/auth.py",
            "backend/app/routers/legacy.py only",
            "backend/app/security.py",
            "backend/app/passwords.py",
        ),
        "A",
        "新登录接口在 routers/auth.py；legacy.py 保留旧 /api/login 兼容旧页面。",
    ),
    Question(
        "登录",
        "登录成功后，后端返回的 access_token 主要用途是什么？",
        (
            "证明后续请求的登录身份和角色",
            "直接保存船员证书图片",
            "替代数据库主键",
            "自动创建岗位需求",
        ),
        "A",
        "后续需要权限的接口会读取 token，识别当前用户和角色。",
    ),
    Question(
        "权限",
        "角色权限校验主要在哪个文件中实现？",
        (
            "backend/app/dependencies.py",
            "backend/app/models.py",
            "backend/app/passwords.py",
            "backend/app/database.py",
        ),
        "A",
        "dependencies.py 里的 require_roles 会判断当前用户角色是否允许访问接口。",
    ),
    Question(
        "船员",
        "创建船员时为什么同时创建 users 和 crews？",
        (
            "users 负责登录权限，crews 负责船员业务档案",
            "为了让数据库表数量变多",
            "因为 FastAPI 要求每个接口写两张表",
            "为了让证书编号自动递增",
        ),
        "A",
        "这是清晰的职责拆分：账号和业务档案分开，并通过 crews.user_id 关联。",
    ),
    Question(
        "船员",
        "crews.user_id 指向哪张表？",
        (
            "users.id",
            "certificates.id",
            "job_demands.id",
            "dispatches.id",
        ),
        "A",
        "crews.user_id 是外键，指向 users.id，形成用户和船员档案的一对一关系。",
    ),
    Question(
        "证书",
        "证书刚录入时默认审核状态是什么？",
        (
            "pending",
            "approved",
            "rejected",
            "offboard",
        ),
        "A",
        "create_certificate 会设置 review_status='pending'，审核通过后才参与匹配。",
    ),
    Question(
        "证书",
        "证书要参与智能匹配，必须满足什么条件？",
        (
            "review_status 为 approved 且 expires_at 没过期",
            "只要录入过就可以",
            "只要 certificate_no 不为空就可以",
            "只要船员是 at_sea 就可以",
        ),
        "A",
        "_valid_certificate_types 只认可审核通过且未过期的证书。",
    ),
    Question(
        "证书",
        "certificate_review_records 表主要保存什么？",
        (
            "每次证书审核的历史记录",
            "船员当前是否在船",
            "每条航线的港口距离",
            "前端登录页面配置",
        ),
        "A",
        "certificates 保存当前状态，certificate_review_records 保存审核过程和历史。",
    ),
    Question(
        "岗位",
        "岗位需求要求多个证书时，为什么要用 job_required_certificates 表？",
        (
            "一个岗位可以对应多个所需证书，单独建表符合一对多关系",
            "因为 certificates 表不能查询",
            "因为前端不能显示数组",
            "因为 token 必须存在这张表里",
        ),
        "A",
        "不要用逗号拼接多值字段，单独子表更符合规范化设计。",
    ),
    Question(
        "匹配",
        "智能匹配满分 100 分中，证书满足度占多少分？",
        (
            "40",
            "10",
            "20",
            "60",
        ),
        "A",
        "_score_match 中岗位匹配 40，证书满足度 40，有效期风险 10，海历经验 10。",
    ),
    Question(
        "匹配",
        "list_matching_crews 为什么只查询 available 船员？",
        (
            "只有在岸可派遣船员适合新派遣",
            "available 表示证书过期",
            "available 表示船东用户",
            "available 表示岗位已关闭",
        ),
        "A",
        "pending、at_sea、inactive 都不应该进入新的派遣推荐。",
    ),
    Question(
        "派遣",
        "派遣正常状态流转顺序是什么？",
        (
            "pending_owner -> confirmed -> onboard -> offboard",
            "approved -> pending -> rejected -> closed",
            "available -> inactive -> onboard -> pending",
            "open -> offboard -> confirmed -> pending_owner",
        ),
        "A",
        "经理创建后待船东确认，确认后上船，最后下船完成。",
    ),
    Question(
        "派遣",
        "确认上船时，后端会自动新增哪类记录？",
        (
            "voyage_records 海历记录",
            "certificate_types 证书类型",
            "ports 港口记录",
            "users 管理员账号",
        ),
        "A",
        "onboard_dispatch 会创建 VoyageRecord，表示真实出海经历开始。",
    ),
    Question(
        "派遣",
        "dispatch_status_logs 和 dispatches 的区别是什么？",
        (
            "dispatches 保存当前状态，dispatch_status_logs 保存状态变化历史",
            "两张表完全一样",
            "dispatch_status_logs 保存证书图片",
            "dispatches 只保存港口",
        ),
        "A",
        "当前状态和历史状态分开，方便追踪流程。",
    ),
    Question(
        "统计",
        "月度派遣趋势主要按哪个字段统计？",
        (
            "dispatches.created_at",
            "users.password_hash",
            "ports.country",
            "certificate_types.validity_months",
        ),
        "A",
        "dashboard_dispatch_trend 按 dispatch.created_at 的年月统计派遣数量。",
    ),
    Question(
        "统计",
        "航线工作量排行主要来自哪张表？",
        (
            "voyage_records",
            "users",
            "operation_logs",
            "certificate_review_records",
        ),
        "A",
        "航线工作量用实际海历 voyage_records 更能体现真实工作量。",
    ),
    Question(
        "日志",
        "operation_logs 主要用于什么？",
        (
            "记录用户关键操作，便于审计",
            "保存 JWT 密钥",
            "保存前端 CSS 样式",
            "保存船舶吨位单位",
        ),
        "A",
        "创建、更新、审核、确认等关键动作都会写入操作日志。",
    ),
    Question(
        "报错",
        "接口返回 403 通常表示什么？",
        (
            "已登录但角色权限不够",
            "端口被占用",
            "数据库字段不存在",
            "请求路径不存在",
        ),
        "A",
        "401 多半是未登录或 token 无效；403 是角色不允许。",
    ),
    Question(
        "报错",
        "sqlite3.OperationalError: no such column 通常说明什么？",
        (
            "ORM 模型字段和数据库实际表结构不一致",
            "密码太短",
            "端口 3000 被占用",
            "浏览器缓存太多",
        ),
        "A",
        "模型新增字段但旧数据库没更新，就可能出现 no such column。",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Interactive backend code quiz.")
    parser.add_argument("--count", type=int, default=10, help="number of questions")
    parser.add_argument("--all", action="store_true", help="ask all questions")
    parser.add_argument("--seed", type=int, default=None, help="shuffle seed")
    return parser.parse_args()


def normalize_answer(value: str) -> str:
    return value.strip().upper()[:1]


def ask(question: Question, index: int, total: int) -> bool:
    labels = ("A", "B", "C", "D")
    print()
    print(f"{index}/{total} [{question.topic}] {question.prompt}")
    for label, choice in zip(labels, question.choices):
        print(f"  {label}. {choice}")

    while True:
        answer = normalize_answer(input("你的答案 A/B/C/D："))
        if answer in labels:
            break
        print("请输入 A、B、C 或 D。")

    correct = answer == question.answer
    if correct:
        print("答对了。")
    else:
        print(f"答错了。正确答案是 {question.answer}。")
    print("解释：" + question.explanation)
    return correct


def main() -> int:
    args = parse_args()
    questions = list(QUESTIONS)
    if args.seed is not None:
        random.seed(args.seed)
    random.shuffle(questions)

    if not args.all:
        questions = questions[: max(1, min(args.count, len(questions)))]

    print("出海船员管理系统后端代码自测")
    print("目标：检查你是否能把接口、service、model 和数据库设计连起来。")

    correct_count = 0
    for index, question in enumerate(questions, start=1):
        if ask(question, index, len(questions)):
            correct_count += 1

    print()
    print(f"得分：{correct_count}/{len(questions)}")
    if correct_count == len(questions):
        print("很好。这一轮很稳，可以尝试对着代码自己讲一遍。")
    elif correct_count >= len(questions) * 0.7:
        print("已经有基础了。把答错的题对应回速查表和代码再看一遍。")
    else:
        print("先别急。建议回到 backend_flow_diagrams.md 和 backend_practice_workbook.md 复习对应模块。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
