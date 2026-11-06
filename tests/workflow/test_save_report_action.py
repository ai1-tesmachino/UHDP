from app.core.config import get_settings
from app.persistence.local.database import SQLiteDatabase
from app.workflows.actions.save_report_action import (
    SaveReportAction,
)
from app.workflows.reporting.diagnostic_report import (
    DiagnosticReport,
)
from app.workflows.workflow_context import (
    WorkflowContext,
)


def test_save_report_action(
    monkeypatch,
    tmp_path,
):
    data_directory = tmp_path / "data"
    monkeypatch.setenv("DATA_DIR", str(data_directory))
    monkeypatch.setenv("SQLITE_DATABASE_PATH", str(data_directory / "uhdp.sqlite3"))
    monkeypatch.setenv("STORAGE_BACKEND", "sqlite")
    get_settings.cache_clear()

    try:
        context = WorkflowContext()

        context.set(
            "diagnostic_report",
            DiagnosticReport(
                data={
                    "result": "ok",
                }
            ),
        )

        action = SaveReportAction("hardware_test")
        action.execute(context)

        database = SQLiteDatabase()
        assert context.get("report_saved") is True
        assert database.get_report_json("hardware_test")["data"]["result"] == "ok"
        assert "UHDP Diagnostic Report" in database.get_report_html("hardware_test")
        export_directory = data_directory / "Reports/hardware_test/REV_000001"
        assert (export_directory / "report.json").is_file()
        assert (export_directory / "report.html").is_file()
    finally:
        get_settings.cache_clear()
