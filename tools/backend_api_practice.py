"""Small practice runner for the Seafarer Management backend API.

Run this after starting the backend with:

    cd backend
    python run_sqlite.py

Then, from the project root:

    python tools/backend_api_practice.py
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "http://127.0.0.1:3000"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"


class ApiPracticeError(Exception):
    pass


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def request_json(
    base_url: str,
    method: str,
    path: str,
    token: str | None = None,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        data = _json_bytes(body)
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(
        base_url.rstrip("/") + path,
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=8) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise ApiPracticeError(f"{method} {path} -> HTTP {exc.code}: {raw}") from exc
    except URLError as exc:
        raise ApiPracticeError(
            f"Cannot connect to {base_url}. Start the backend with: cd backend; python run_sqlite.py"
        ) from exc

    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ApiPracticeError(f"{method} {path} returned non-JSON: {raw[:200]}") from exc


def describe_data(data: Any) -> str:
    if isinstance(data, list):
        return f"list count={len(data)}"
    if isinstance(data, dict):
        keys = ", ".join(list(data.keys())[:8])
        return f"object keys={keys}"
    return type(data).__name__


def print_step(name: str, result: dict[str, Any]) -> None:
    success = result.get("success")
    message = result.get("message", "")
    data = result.get("data")
    summary = describe_data(data)
    print(f"[OK] {name}: success={success} {message} | {summary}")


def run_practice(base_url: str, username: str, password: str) -> None:
    print("Backend API practice runner")
    print(f"Base URL: {base_url}")
    print()

    health = request_json(base_url, "GET", "/health")
    print_step("GET /health", health)

    login = request_json(
        base_url,
        "POST",
        "/api/auth/login",
        body={"username": username, "password": password},
    )
    print_step("POST /api/auth/login", login)
    token = login.get("data", {}).get("access_token")
    if not token:
        raise ApiPracticeError("Login succeeded but no access_token was returned.")

    summary = request_json(base_url, "GET", "/api/dashboard/summary", token=token)
    print_step("GET /api/dashboard/summary", summary)
    if isinstance(summary.get("data"), dict):
        for key, value in summary["data"].items():
            print(f"    {key}: {value}")

    for path in [
        "/api/crews",
        "/api/certificates",
        "/api/jobs",
        "/api/dispatches",
        "/api/operation-logs",
    ]:
        result = request_json(base_url, "GET", path, token=token)
        print_step(f"GET {path}", result)

        if path == "/api/jobs":
            jobs = result.get("data") or []
            if jobs:
                job_id = jobs[0]["id"]
                matches = request_json(base_url, "GET", f"/api/jobs/{job_id}/matches", token=token)
                print_step(f"GET /api/jobs/{job_id}/matches", matches)
                for item in (matches.get("data") or [])[:3]:
                    name = item.get("name")
                    score = item.get("match_score")
                    reasons = " / ".join(item.get("match_reasons") or [])
                    print(f"    match: {name} score={score} reasons={reasons}")

    print()
    print("Practice complete. Now open the matching service code and trace one request:")
    print("  backend/app/routers/matching.py -> services.list_matching_crews -> services._score_match")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Practice core backend API calls.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--username", default=DEFAULT_USERNAME)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        run_practice(args.base_url, args.username, args.password)
    except ApiPracticeError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
