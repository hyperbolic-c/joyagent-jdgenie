import sys
import unittest
from pathlib import Path


GENIE_SQL_ROOT = Path(__file__).resolve().parents[1]


def add_genie_sql_to_path() -> None:
    sys.path.insert(0, str(GENIE_SQL_ROOT))


class GenieSQLServiceTests(unittest.TestCase):
    def test_genie_sql_service_files_exist(self):
        self.assertTrue(GENIE_SQL_ROOT.exists())
        self.assertTrue((GENIE_SQL_ROOT / "pyproject.toml").exists())
        self.assertTrue((GENIE_SQL_ROOT / "server.py").exists())
        self.assertTrue((GENIE_SQL_ROOT / "genie_sql" / "api" / "tool.py").exists())

    def test_genie_sql_exports_only_nl2sql_route(self):
        add_genie_sql_to_path()

        from server import create_app

        app = create_app()
        paths = {route.path for route in app.routes}

        self.assertIn("/v1/tool/nl2sql", paths)
        self.assertNotIn("/v1/tool/deepsearch", paths)
        self.assertNotIn("/v1/tool/table_rag", paths)
        self.assertNotIn("/v1/tool/report", paths)
        self.assertNotIn("/v1/file_tool/upload", paths)

    def test_genie_sql_prompt_loading_and_request_aliases(self):
        add_genie_sql_to_path()

        from genie_sql.model.protocal import NL2SQLRequest
        from genie_sql.util.prompt_util import get_prompt

        prompt = get_prompt("nl2sql")
        self.assertIn("rewrite_prompt", prompt)
        self.assertIn("think_prompt", prompt)
        self.assertIn("nl2sql_prompt", prompt)

        request = NL2SQLRequest.model_validate(
            {
                "requestId": "req-1",
                "query": "销量最高的国家",
                "currentDateInfo": "当前时间信息：2025-09-12,星期五",
                "modelCodeList": ["sales"],
                "schemaInfo": [],
                "stream": False,
                "dbType": "mysql",
            }
        )

        self.assertEqual("req-1", request.request_id)
        self.assertEqual(["sales"], request.table_id_list)
        self.assertEqual("mysql", request.dialect)


if __name__ == "__main__":
    unittest.main()
