from abc import ABC, abstractmethod

from app.profiles.diagnostic_profile import DiagnosticProfile


class ProfileRepository(ABC):

    @abstractmethod
    def save(self, profile: DiagnosticProfile) -> None:
        pass

    @abstractmethod
    def get(self, name: str) -> DiagnosticProfile | None:
        pass

    @abstractmethod
    def list(self) -> list[DiagnosticProfile]:
        pass

    @abstractmethod
    def delete(self, name: str) -> None:
        pass