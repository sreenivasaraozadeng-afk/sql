from pathlib import Path
from unittest import TestCase


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class DockerConfigurationTests(TestCase):
    def test_compose_defines_frontend_backend_and_database(self):
        compose_path = PROJECT_ROOT / "docker-compose.yml"
        self.assertTrue(compose_path.exists(), "docker-compose.yml should exist")
        text = compose_path.read_text(encoding="utf-8")
        self.assertIn("db:", text)
        self.assertIn("backend:", text)
        self.assertIn("frontend:", text)
        self.assertIn("./init.sql:/docker-entrypoint-initdb.d/01-init.sql:ro", text)
        self.assertIn("3000:3000", text)
        self.assertIn("8080:80", text)
        self.assertIn(
            "mysql+pymysql://root:123456@db:3306/SeafarerDB?charset=utf8mb4",
            text,
        )

    def test_docker_build_files_exist(self):
        expected_files = [
            PROJECT_ROOT / "backend" / "Dockerfile",
            PROJECT_ROOT / "frontend" / "Dockerfile",
            PROJECT_ROOT / "frontend" / "nginx.conf",
            PROJECT_ROOT / ".dockerignore",
        ]
        for path in expected_files:
            self.assertTrue(
                path.exists(),
                f"{path.relative_to(PROJECT_ROOT)} should exist",
            )

    def test_backend_dependencies_support_mysql8_authentication(self):
        requirements_path = PROJECT_ROOT / "backend" / "requirements.txt"
        requirements = requirements_path.read_text(encoding="utf-8").lower()
        self.assertIn("cryptography", requirements)

    def test_database_initialization_uses_utf8_client_encoding(self):
        init_sql_path = PROJECT_ROOT / "init.sql"
        first_statement = init_sql_path.read_text(encoding="utf-8").lstrip().splitlines()[0]
        self.assertEqual("SET NAMES utf8mb4;", first_statement)

    def test_init_sql_contains_expanded_schema_views_and_seed_data(self):
        sql = (PROJECT_ROOT / "init.sql").read_text(encoding="utf-8").lower()
        for table in [
            "users",
            "ship_companies",
            "ships",
            "ports",
            "routes",
            "positions",
            "certificate_types",
            "crews",
            "certificates",
            "certificate_review_records",
            "job_demands",
            "job_required_certificates",
            "dispatches",
            "dispatch_status_logs",
            "voyage_records",
            "operation_logs",
        ]:
            self.assertIn(f"create table if not exists {table}", sql)
        for view in [
            "v_crew_certificate_status",
            "v_dispatch_flow_stats",
            "v_route_workload",
            "v_job_match_overview",
        ]:
            self.assertIn(f"view {view}", sql)
        self.assertIn("check (role in", sql)
        self.assertIn("idx_certificates_review_status", sql)
        self.assertIn("idx_operation_logs_created_at", sql)
        self.assertIn("crew08", sql)

    def test_frontend_pages_for_expanded_workflow_exist(self):
        for filename in [
            "dashboard.html",
            "certificate_review.html",
            "fleet.html",
            "jobs.html",
            "dispatches.html",
            "operation_logs.html",
        ]:
            self.assertTrue((PROJECT_ROOT / "frontend" / filename).exists())

    def test_frontend_nginx_declares_utf8_charset_and_no_cache(self):
        config = (PROJECT_ROOT / "frontend" / "nginx.conf").read_text(encoding="utf-8").lower()
        self.assertIn("charset utf-8;", config)
        self.assertIn('add_header cache-control "no-store, no-cache, must-revalidate" always;', config)
        self.assertIn('add_header pragma "no-cache" always;', config)
        self.assertIn('expires 0;', config)

    def test_admin_and_login_use_current_cache_busting_version(self):
        admin_html = (PROJECT_ROOT / "frontend" / "admin.html").read_text(encoding="utf-8")
        index_html = (PROJECT_ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="dashboard.html?v=2026052901"', admin_html)
        self.assertIn('href="jobs.html?v=2026052901"', admin_html)
        self.assertIn('src="dashboard.html?v=2026052901"', admin_html)
        self.assertIn("admin.html?v=2026052901", index_html)
