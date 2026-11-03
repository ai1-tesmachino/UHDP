from app.core.config import get_settings
from app.persistence.supabase_repositories import (
    SupabaseReportRepository,
    SupabaseReportStorage,
    SupabaseSessionRepository,
)
from app.persistence.local import (
    SQLiteReportRepository,
    SQLiteReportStorage,
    SQLiteSessionRepository,
)
from app.services.file_session_repository import FileSessionRepository
from app.reports.report_storage import ReportStorage
from app.workflows.reporting.file_report_repository import FileReportRepository


def create_session_repository():
    if get_settings().STORAGE_BACKEND == "supabase":
        return SupabaseSessionRepository()
    if get_settings().STORAGE_BACKEND == "sqlite":
        return SQLiteSessionRepository()
    return FileSessionRepository()


def create_report_repository():
    if get_settings().STORAGE_BACKEND == "supabase":
        return SupabaseReportRepository()
    if get_settings().STORAGE_BACKEND == "sqlite":
        return SQLiteReportRepository()
    return FileReportRepository()


def create_report_storage():
    if get_settings().STORAGE_BACKEND == "supabase":
        return SupabaseReportStorage()
    if get_settings().STORAGE_BACKEND == "sqlite":
        return SQLiteReportStorage()
    return ReportStorage()
