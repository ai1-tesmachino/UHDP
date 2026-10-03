from app.reports.report_generator import ReportGenerator
from app.reports.report_storage import ReportStorage


class ReportService:

    def __init__(
        self,
        report_generator: ReportGenerator | None = None,
        report_storage: ReportStorage | None = None,
    ):
        self._report_generator = (
            report_generator
            or ReportGenerator()
        )

        self._report_storage = (
            report_storage
            or ReportStorage()
        )

    def generate_report(
        self,
        session,
    ):

        report = self._report_generator.generate(
            session
        )

        self._report_storage.save(
            report
        )

        return report

    def get_report_json(
        self,
        session_id: str,
    ):

        return self._report_storage.get_json(
            session_id
        )

    def get_report_html(
        self,
        session_id: str,
    ):

        return self._report_storage.get_html(
            session_id
        )

    def list_reports(
        self,
    ):

        return self._report_storage.list_reports()