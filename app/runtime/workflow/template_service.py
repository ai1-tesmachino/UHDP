from __future__ import annotations


class TemplateService:
    def __init__(
        self,
        template_repository,
    ) -> None:
        self._repository = template_repository

    def save(
        self,
        template,
    ) -> None:
        self._repository.save(
            template,
        )

    def get(
        self,
        template_id: str,
    ):
        return self._repository.load(
            template_id,
        )

    def delete(
        self,
        template_id: str,
    ) -> None:
        self._repository.delete(
            template_id,
        )

    def list(
        self,
    ):
        return self._repository.list()