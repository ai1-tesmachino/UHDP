import uuid
from typing import Any

from app.hal.diagnostic_status import DiagnosticStatus
from app.hal.models.diagnostic_result_collection import (
    DiagnosticResultCollection,
)
from app.workflows.reporting.diagnostic_report import (
    DiagnosticReport,
)
from app.workflows.workflow_context import (
    WorkflowContext,
)


class ReportBuilder:

    RESULT_KEYS = (

            "cpu_result",
            "memory_result",
            "storage_result",
            "network_result",
            "system_result",
            "cpu_stress_result",
            "memory_stress_result",

            "battery_result",
            "display_result",
            "webcam_result",
            "keyboard_result",
            "speaker_result",

            "usb_result",
            "usb_c_result",

            "hdmi_result",
            "vga_result",

            "wifi_result",
            "bluetooth_result",

            "cpu_validation",
            "memory_validation",
            "storage_validation",
            "network_validation",

        )

    def build(
        self,
        context: WorkflowContext,
    ) -> DiagnosticReport:

        data: dict[str, Any] = {}

        collection = (
            DiagnosticResultCollection()
        )

        for key in self.RESULT_KEYS:
            value = context.get(key)

            if value is not None:
                data[key] = value

                if self._is_diagnostic_result(value):
                    collection.add(value)

            if len(collection) > 0:
                data["diagnostic_summary"] = (
                    collection.summary()
                )

        device_id = context.get(
            "device_id",
            "unknown-device",
        )

        status = self._calculate_status(data)

        return DiagnosticReport(
            report_id=str(uuid.uuid4()),
            device_id=str(device_id),
            status=status,
            data=data,
        )

    def _is_diagnostic_result(
        self,
        value: Any,
    ) -> bool:
        return (
            hasattr(value, "diagnostic_id")
            and hasattr(value, "diagnostic_type")
            and hasattr(value, "status")
        )

    def _calculate_status(
        self,
        data: dict[str, Any],
    ) -> str:

        results = [
            value
            for value in data.values()
            if hasattr(value, "status")
            and hasattr(value, "diagnostic_id")
        ]

        if not results:
            return DiagnosticStatus.PENDING.value

        statuses = [
            result.status
            for result in results
        ]

        if any(
            status == DiagnosticStatus.ERROR
            for status in statuses
        ):
            return DiagnosticStatus.ERROR.value

        if any(
            status == DiagnosticStatus.FAILED
            for status in statuses
        ):
            return DiagnosticStatus.FAILED.value

        if all(
            status in {
                DiagnosticStatus.PASSED,
                DiagnosticStatus.NOT_APPLICABLE,
            }
            for status in statuses
        ) and any(status == DiagnosticStatus.PASSED for status in statuses):
            return DiagnosticStatus.PASSED.value

        if any(
            status == DiagnosticStatus.UNSUPPORTED
            for status in statuses
        ):
            return DiagnosticStatus.UNSUPPORTED.value

        return DiagnosticStatus.PENDING.value