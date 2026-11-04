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

    def find_asset(self, asset_id: str) -> dict | None:
        for session in self.list_all():
            if session.get("asset_id") != asset_id:
                continue
            asset = session.get("asset")
            return asset if isinstance(asset, dict) else {"asset_id": asset_id}
        return None

    @abstractmethod
    def delete(
        self,
        session_id: str,
    ) -> None:
        pass