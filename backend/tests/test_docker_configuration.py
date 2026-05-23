import re
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

    def test_init_sql_uses_hardened_schema_without_plaintext_passwords(self):
        init_sql_path = PROJECT_ROOT / "init.sql"
        sql = init_sql_path.read_text(encoding="utf-8").lower()
        self.assertIn("password_hash", sql)
        self.assertNotIn("password varchar", sql)
        self.assertIn("created_at", sql)
        self.assertIn("updated_at", sql)
        self.assertIn("create table if not exists users", sql)
        self.assertIn("create table if not exists crews", sql)
        self.assertIn("create table if not exists certificates", sql)
        self.assertIn("create table if not exists job_demands", sql)
        self.assertIn("create table if not exists job_required_certificates", sql)
        self.assertIn("create table if not exists dispatches", sql)
        self.assertIn("create table if not exists voyage_records", sql)
        self.assertIn("check (role in", sql)
        self.assertIn("check (status in ('available', 'pending', 'at_sea', 'inactive'))", sql)
        self.assertIn("index idx_certificates_crew_id", sql)
        self.assertIn("index idx_dispatches_status", sql)

    def test_frontend_nginx_declares_utf8_charset(self):
        nginx_config_path = PROJECT_ROOT / "frontend" / "nginx.conf"
        config = nginx_config_path.read_text(encoding="utf-8").lower()
        self.assertIn("charset utf-8;", config)

    def test_frontend_nginx_disables_html_cache_during_development(self):
        nginx_config_path = PROJECT_ROOT / "frontend" / "nginx.conf"
        config = nginx_config_path.read_text(encoding="utf-8").lower()
        self.assertIn('add_header cache-control "no-store, no-cache, must-revalidate" always;', config)
        self.assertIn('add_header pragma "no-cache" always;', config)
        self.assertIn('expires 0;', config)

    def test_crew_table_header_matches_rendered_cell_order(self):
        crew_list_path = PROJECT_ROOT / "frontend" / "crew_list.html"
        html = crew_list_path.read_text(encoding="utf-8")
        headers = re.findall(r"<th>(.*?)</th>", html)
        self.assertEqual(
            ["ID", "账号", "密码", "姓名", "性别", "电话", "状态", "系统角色", "操作"],
            headers,
        )
        self.assertIn('colspan="9"', html)

    def test_admin_page_cache_busts_embedded_frontend_pages(self):
        admin_path = PROJECT_ROOT / "frontend" / "admin.html"
        html = admin_path.read_text(encoding="utf-8")
        self.assertIn('href="crew_list.html?v=2026051902"', html)
        self.assertIn('href="voyage_list.html?v=2026051902"', html)
        self.assertIn('src="crew_list.html?v=2026051902"', html)

    def test_login_redirects_to_cache_busted_admin_page(self):
        index_path = PROJECT_ROOT / "frontend" / "index.html"
        html = index_path.read_text(encoding="utf-8")
        self.assertIn("window.location.href = 'admin.html?v=2026051902';", html)
