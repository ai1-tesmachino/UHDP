from app.core.config import get_settings
from app.persistence.supabase_repositories import (
    SupabaseReportRepository,
    SupabaseReportStorage,
    SupabaseSessionRepository,
)
from app.services.file_session_repository import FileSessionRepository
from app.reports.report_storage import ReportStorage
from app.workflows.reporting.file_report_repository import FileReportRepository


def create_session_repository():
    if get_settings().STORAGE_BACKEND == "supabase":
        return SupabaseSessionRepository()
    return FileSessionRepository()


def create_report_repository():
    if get_settings().STORAGE_BACKEND == "supabase":
        return SupabaseReportRepository()
    return FileReportRepository()


def create_report_storage():
    if get_settings().STORAGE_BACKEND == "supabase":
        return SupabaseReportStorage()
    return ReportStorage()
