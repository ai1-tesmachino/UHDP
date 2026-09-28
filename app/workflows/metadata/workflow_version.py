from __future__ import annotations

from dataclasses import dataclass


@dataclass(
    slots=True,
    frozen=True,
)
class WorkflowVersion:
    major: int = 1

    minor: int = 0

    patch: int = 0

    def __str__(
        self,
    ) -> str:
        return (
            f"{self.major}."
            f"{self.minor}."
            f"{self.patch}"
        )