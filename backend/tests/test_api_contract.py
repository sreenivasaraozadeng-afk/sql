from datetime import UTC, datetime, timedelta
from unittest import TestCase

from fastapi.testclient import TestClient

from app.main import create_app


class ExpandedApiContractTests(TestCase):
    def setUp(self):
        self.app = create_app(
            database_url="sqlite:///:memory:",
            create_tables=True,
            seed_demo=True,
        )
        self.client = TestClient(self.app)

    def tearDown(self):
        self.client.close()
        self.app.state.engine.dispose()

    def login(self, username="manager", password="manager123") -> str:
        response = self.client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["data"]["access_token"]

    def auth(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def create_crew(self, token: str, username="crew_test", position="水手") -> dict:
        id_suffix = sum(ord(char) for char in username) % 10000
        response = self.client.post(
            "/api/crews",
            headers=self.auth(token),
            json={
                "username": username,
                "password": "123456",
                "name": f"船员{username}",
                "gender": "男",
                "id_card": f"11010119900101{id_suffix:04d}",
                "phone": "13800000001",
                "position": position,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["data"]

    def add_certificate(
        self,
        token: str,
        crew_id: int,
        certificate_type="STCW",
        expires_in_days=120,
        review=True,
    ) -> dict:
        response = self.client.post(
            "/api/certificates",
            headers=self.auth(token),
            json={
                "crew_id": crew_id,
                "certificate_type": certificate_type,
                "certificate_no": f"{certificate_type}-{crew_id}-{expires_in_days}",
                "issued_at": "2026-01-01",
                "expires_at": (
                    datetime.now(UTC).date() + timedelta(days=expires_in_days)
                ).isoformat(),
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        certificate = response.json()["data"]
        self.assertEqual(certificate["review_status"], "pending")
        if review:
            review_response = self.client.put(
                f"/api/certificates/{certificate['id']}/review",
                headers=self.auth(token),
                json={"review_status": "approved", "remark": "测试通过"},
            )
            self.assertEqual(review_response.status_code, 200, review_response.text)
            certificate = review_response.json()["data"]
        return certificate

    def create_job(self, token: str, required_certificates=None) -> dict:
        required_certificates = required_certificates or ["STCW"]
        response = self.client.post(
            "/api/jobs",
            headers=self.auth(token),
            json={
                "title": "远洋水手",
                "ship_name": "东方一号",
                "route": "青岛港-新加坡港",
                "required_position": "水手",
                "required_certificates": required_certificates,
                "headcount": 1,
                "onboard_at": "2026-06-01T08:00:00",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["data"]

    def test_login_returns_token_and_role_permissions_are_enforced(self):
        response = self.client.post(
            "/api/auth/login",
            json={"username": "manager", "password": "manager123"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["token_type"], "bearer")
        self.assertGreater(len(body["data"]["access_token"].split(".")), 2)
        self.assertEqual(body["data"]["user"]["role"], "manager")
        self.assertIn("charset=utf-8", response.headers["content-type"].lower())

        bad_response = self.client.post(
            "/api/auth/login",
            json={"username": "manager", "password": "wrong"},
        )
        self.assertEqual(bad_response.status_code, 401)
        self.assertFalse(bad_response.json()["success"])

        owner_token = self.login("owner", "owner123")
        forbidden = self.client.post(
            "/api/crews",
            headers=self.auth(owner_token),
            json={
                "username": "crew_forbidden",
                "password": "123456",
                "name": "无权新增",
                "gender": "男",
                "id_card": "110101199001019999",
                "position": "水手",
            },
        )
        self.assertEqual(forbidden.status_code, 403)

    def test_dictionary_ship_and_dashboard_interfaces_exist(self):
        manager_token = self.login()
        owner_token = self.login("owner", "owner123")

        for path in [
            "/api/positions",
            "/api/certificate-types",
            "/api/ports",
            "/api/routes",
        ]:
            response = self.client.get(path, headers=self.auth(manager_token))
            self.assertEqual(response.status_code, 200, response.text)
            self.assertTrue(response.json()["success"])
            self.assertGreaterEqual(len(response.json()["data"]), 1)

        ship_response = self.client.post(
            "/api/ships",
            headers=self.auth(owner_token),
            json={
                "name": "测试一号",
                "company_name": "测试航运",
                "ship_type": "散货船",
                "tonnage": 50000,
                "capacity": 24,
            },
        )
        self.assertEqual(ship_response.status_code, 200, ship_response.text)

        summary_response = self.client.get(
            "/api/dashboard/summary",
            headers=self.auth(manager_token),
        )
        self.assertEqual(summary_response.status_code, 200, summary_response.text)
        summary = summary_response.json()["data"]
        self.assertIn("total_crews", summary)
        self.assertIn("pending_certificate_reviews", summary)
        self.assertIn("total_ships", summary)

    def test_legacy_login_and_old_frontend_shape_still_work(self):
        login_response = self.client.post(
            "/api/login",
            json={"username": "admin", "password": "admin123"},
        )

        self.assertEqual(login_response.status_code, 200, login_response.text)
        login_body = login_response.json()
        self.assertTrue(login_body["success"])
        self.assertEqual(login_body["role"], "admin")
        self.assertIn("token", login_body)

        list_response = self.client.get("/api/crews")
        self.assertEqual(list_response.status_code, 200, list_response.text)
        self.assertEqual(list_response.json()["data"], [])

        create_response = self.client.post(
            "/api/crews",
            json={
                "username": "legacy_crew",
                "password": "123456",
                "name": "旧页面船员",
                "gender": "男",
                "id_card": "110101199001018888",
                "phone": "13800008888",
                "role": "user",
            },
        )
        self.assertEqual(create_response.status_code, 200, create_response.text)

        legacy_crew = self.client.get("/api/crews").json()["data"][0]
        self.assertEqual(legacy_crew["username"], "legacy_crew")
        self.assertEqual(legacy_crew["role"], "user")
        self.assertEqual(legacy_crew["password"], "******")
        self.assertEqual(legacy_crew["is_at_sea"], 0)

    def test_certificate_review_alerts_and_matching_score(self):
        manager_token = self.login()
        cert_token = self.login("cert_admin", "cert123")
        owner_token = self.login("owner", "owner123")
        eligible = self.create_crew(manager_token, username="eligible")
        expired = self.create_crew(manager_token, username="expired")
        missing = self.create_crew(manager_token, username="missing")

        self.add_certificate(cert_token, eligible["id"], "STCW", expires_in_days=120)
        self.add_certificate(cert_token, expired["id"], "STCW", expires_in_days=-1)
        self.add_certificate(cert_token, missing["id"], "GMDSS", expires_in_days=120)
        self.add_certificate(cert_token, eligible["id"], "健康证", expires_in_days=15)

        alerts_response = self.client.get(
            "/api/certificates/alerts",
            headers=self.auth(cert_token),
        )
        self.assertEqual(alerts_response.status_code, 200)
        alerts = alerts_response.json()["data"]
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["certificate_type"], "健康证")

        job = self.create_job(owner_token, required_certificates=["STCW"])
        response = self.client.get(
            f"/api/jobs/{job['id']}/matches",
            headers=self.auth(manager_token),
        )

        self.assertEqual(response.status_code, 200)
        matches = response.json()["data"]
        self.assertEqual([item["id"] for item in matches], [eligible["id"]])
        self.assertIn("match_score", matches[0])
        self.assertIn("match_reasons", matches[0])

    def test_dispatch_flow_writes_status_logs_operation_logs_and_voyage_state(self):
        manager_token = self.login()
        cert_token = self.login("cert_admin", "cert123")
        owner_token = self.login("owner", "owner123")
        crew = self.create_crew(manager_token)
        self.add_certificate(cert_token, crew["id"], "STCW", expires_in_days=120)
        job = self.create_job(owner_token, required_certificates=["STCW"])

        dispatch_response = self.client.post(
            "/api/dispatches",
            headers=self.auth(manager_token),
            json={"job_id": job["id"], "crew_id": crew["id"]},
        )
        self.assertEqual(dispatch_response.status_code, 200, dispatch_response.text)
        dispatch = dispatch_response.json()["data"]
        self.assertEqual(dispatch["status"], "pending_owner")

        confirm_response = self.client.put(
            f"/api/dispatches/{dispatch['id']}/confirm",
            headers=self.auth(owner_token),
        )
        self.assertEqual(confirm_response.status_code, 200)
        self.assertEqual(confirm_response.json()["data"]["status"], "confirmed")

        onboard_response = self.client.put(
            f"/api/dispatches/{dispatch['id']}/onboard",
            headers=self.auth(manager_token),
        )
        self.assertEqual(onboard_response.status_code, 200)
        self.assertEqual(onboard_response.json()["data"]["status"], "onboard")

        detail_response = self.client.get(
            f"/api/dispatches/{dispatch['id']}",
            headers=self.auth(manager_token),
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertGreaterEqual(len(detail_response.json()["data"]["status_logs"]), 3)

        offboard_response = self.client.put(
            f"/api/dispatches/{dispatch['id']}/offboard",
            headers=self.auth(manager_token),
        )
        self.assertEqual(offboard_response.status_code, 200)
        self.assertEqual(offboard_response.json()["data"]["status"], "offboard")
        crew_after_offboard = self.client.get(
            f"/api/crews/{crew['id']}",
            headers=self.auth(manager_token),
        ).json()["data"]
        self.assertEqual(crew_after_offboard["status"], "available")

        logs_response = self.client.get(
            "/api/operation-logs",
            headers=self.auth(manager_token),
        )
        self.assertEqual(logs_response.status_code, 200)
        actions = [item["action"] for item in logs_response.json()["data"]]
        self.assertIn("create", actions)
        self.assertIn("confirm", actions)
        self.assertIn("onboard", actions)
        self.assertIn("offboard", actions)
