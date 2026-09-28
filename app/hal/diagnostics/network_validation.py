import psutil

from app.hal.models.validation_check import (
    ValidationCheck,
)


class NetworkValidation:

    def validate(
        self,
    ) -> list[ValidationCheck]:
        checks = []

        interfaces = (
            psutil.net_if_addrs()
        )

        checks.append(
            ValidationCheck(
                name="adapter_present",
                passed=len(
                    interfaces
                ) > 0,
                message=str(
                    len(
                        interfaces
                    )
                ),
            )
        )

        has_address = False

        for addresses in (
            interfaces.values()
        ):
            if len(addresses) > 0:
                has_address = True
                break

        checks.append(
            ValidationCheck(
                name="address_assigned",
                passed=has_address,
                message=str(
                    has_address,
                ),
            )
        )

        return checks