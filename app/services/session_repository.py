from abc import ABC
from abc import abstractmethod


class SessionRepository(ABC):

    @abstractmethod
    def save(
        self,
        session: dict,
    ) -> None:
        pass

    @abstractmethod
    def get(
        self,
        session_id: str,
    ) -> dict | None:
        pass

    @abstractmethod
    def list_all(
        self,
    ) -> list[dict]:
        pass

    @abstractmethod
    def delete(
        self,
        session_id: str,
    ) -> None:
        pass