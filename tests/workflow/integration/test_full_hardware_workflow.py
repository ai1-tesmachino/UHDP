from app.core.config import get_settings
from app.persistence.local.database import SQLiteDatabase
from app.workflows.templates.full_hardware_test_template import (
    create_full_hardware_test_workflow,
)
from app.workflows.workflow_context import (
    WorkflowContext,
)
from app.workflows.workflow_engine import (
    WorkflowEngine,
)


def test_full_hardware_workflow(
    monkeypatch,
    tmp_path,
):
    data_directory = tmp_path / "data"
    monkeypatch.setenv("DATA_DIR", str(data_directory))
    monkeypatch.setenv("SQLITE_DATABASE_PATH", str(data_directory / "uhdp.sqlite3"))
    monkeypatch.setenv("STORAGE_BACKEND", "sqlite")
    get_settings.cache_clear()

    try:
        workflow = create_full_hardware_test_workflow()

        context = WorkflowContext()

        result = WorkflowEngine().execute(workflow, context)

        assert context.exists("cpu_result")
        assert context.exists("memory_result")
        assert context.exists("storage_result")
        assert context.exists("network_result")
        assert context.exists("cpu_validation")
        assert context.exists("memory_validation")
        assert context.exists("storage_validation")
        assert context.exists("network_validation")
        assert context.exists("diagnostic_report")
        assert context.get("report_saved") is True
        assert result.status.value == "success"

        database = SQLiteDatabase()
        payload = database.get_report_json("full_hardware_test")
        assert payload is not None
        assert payload["data"]["network_result"]
        assert database.get_report_html("full_hardware_test")
        export_directory = (
            data_directory / "Reports/full_hardware_test/REV_000001"
        )
        assert (export_directory / "report.json").is_file()
        assert (export_directory / "report.html").is_file()
    finally:
        get_settings.cache_clear()