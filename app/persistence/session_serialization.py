from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from app.hal.diagnostic_evaluation import DiagnosticEvaluation
from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus
from app.hal.evaluation_status import EvaluationStatus
from app.hal.models.diagnostic_result_collection import DiagnosticResultCollection
from app.hal.models.diagnostic_summary import DiagnosticSummary
from app.workflows.reporting.diagnostic_report import DiagnosticReport


def json_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value):
        return json_value(asdict(value))
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    return value


def parse_datetime(value: Any) -> datetime | Any:
    if not isinstance(value, str):
        return value
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return value


def _restore_result(item: dict[str, Any]) -> DiagnosticResult:
    result_data = dict(item)
    try:
        result_data["status"] = DiagnosticStatus(result_data.get("status"))
    except (ValueError, TypeError):
        pass
    result_data["created_at"] = parse_datetime(result_data.get("created_at"))
    evaluation = result_data.get("evaluation")
    if isinstance(evaluation, dict):
        evaluation_data = dict(evaluation)
        try:
            evaluation_data["status"] = EvaluationStatus(
                evaluation_data.get("status")
            )
        except (ValueError, TypeError):
            pass
        result_data["evaluation"] = DiagnosticEvaluation(**evaluation_data)
    return DiagnosticResult(**result_data)


def _restore_summary(summary: dict[str, Any]) -> DiagnosticSummary:
    allowed = DiagnosticSummary.__dataclass_fields__
    return DiagnosticSummary(
        **{key: value for key, value in summary.items() if key in allowed}
    )


def restore_session(payload: dict[str, Any]) -> dict[str, Any]:
    session = dict(payload)
    session["created_at"] = parse_datetime(session.get("created_at"))

    results = session.get("diagnostic_results")
    if isinstance(results, dict):
        collection = DiagnosticResultCollection()
        for item in results.get("results", []):
            if not isinstance(item, dict):
                continue
            collection.add(_restore_result(item))
        session["diagnostic_results"] = collection

    summary = session.get("diagnostic_summary")
    if isinstance(summary, dict):
        session["diagnostic_summary"] = _restore_summary(summary)

    report = session.get("report")
    if isinstance(report, dict):
        report_data = dict(report)
        report_data["created_at"] = parse_datetime(report_data.get("created_at"))
        report_data["data"] = dict(report_data.get("data") or {})
        for key, value in list(report_data["data"].items()):
            if key == "diagnostic_summary" and isinstance(value, dict):
                report_data["data"][key] = _restore_summary(value)
            elif (
                isinstance(value, dict)
                and {"diagnostic_id", "diagnostic_type", "device_id", "status"}
                <= value.keys()
            ):
                report_data["data"][key] = _restore_result(value)
        allowed = DiagnosticReport.__dataclass_fields__
        session["report"] = DiagnosticReport(
            **{key: value for key, value in report_data.items() if key in allowed}
        )
    return session
