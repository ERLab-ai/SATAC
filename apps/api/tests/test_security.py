"""Disposable DB security assertions, run against the actual reader identity."""
import os
import unittest
from unittest.mock import patch
import psycopg
from fastapi.testclient import TestClient
from apps.api.main import app

class PublicSecurity(unittest.TestCase):
    def setUp(self):
        self.client=TestClient(app)
    def test_no_store_and_security_headers_on_success_and_errors(self):
        for path,status in [("/health",200),("/api/v1/releases",200),("/api/v1/map/features?bbox=bad",422),
                            ("/api/v1/claims/00000000-0000-0000-0000-000000000099",404),("/internal",404)]:
            with self.subTest(path=path):
                r=self.client.get(path,headers={"Origin":"https://untrusted.invalid"})
                self.assertEqual(r.status_code,status,r.text)
                for name,value in {"cache-control":"no-store","x-content-type-options":"nosniff","x-frame-options":"DENY",
                                   "referrer-policy":"no-referrer","cross-origin-resource-policy":"same-origin"}.items():
                    self.assertEqual(r.headers.get(name),value)
                self.assertNotIn("access-control-allow-origin",r.headers)
    def test_missing_configuration_is_sanitized(self):
        with patch.dict(os.environ,{"SATAC_READER_DSN":""}):
            r=self.client.get("/health")
        self.assertEqual(r.status_code,503)
        self.assertEqual(r.json(),{"error":{"code":"database_unavailable"}})
        self.assertEqual(r.headers.get("cache-control"),"no-store")
    def test_no_public_write_route(self):
        for method in ("POST","PUT","PATCH","DELETE"):
            r=self.client.request(method,"/api/v1/releases",json={"release":"bad"})
            self.assertEqual(r.status_code,405)
            self.assertEqual(r.headers.get("cache-control"),"no-store")
    def test_predefined_role_rejected_even_without_private_schema(self):
        with psycopg.connect(os.environ["SATAC_ADMIN_TEST_DSN"]) as admin:
            admin.execute("GRANT pg_read_all_settings TO satac_api_test")
            admin.commit()
            try:
                r=self.client.get("/health")
                self.assertEqual(r.status_code,503)
                self.assertEqual(r.json(),{"error":{"code":"reader_configuration_invalid"}})
            finally:
                admin.execute("REVOKE pg_read_all_settings FROM satac_api_test")
                admin.commit()
        self.assertEqual(self.client.get("/health").status_code,200)
    def test_reader_cannot_access_private_tables_or_mutate(self):
        with psycopg.connect(os.environ["SATAC_READER_DSN"]) as conn:
            for stmt in ("SELECT * FROM knowledge.release_member LIMIT 1",
                         "SELECT * FROM knowledge.source_revocation LIMIT 1",
                         "SELECT knowledge.verify_release(gen_random_uuid())",
                         "UPDATE public_read.release_claims SET payload='{}'::jsonb WHERE false",
                         "CREATE TABLE public.security_fixture(id int)"):
                with self.subTest(stmt=stmt):
                    with self.assertRaises((psycopg.errors.InsufficientPrivilege,psycopg.errors.ObjectNotInPrerequisiteState,psycopg.errors.FeatureNotSupported)):
                        with conn.transaction():
                            conn.execute(stmt)
            self.assertGreater(conn.execute("SELECT count(*) FROM public_read.release_claims").fetchone()[0],0)
