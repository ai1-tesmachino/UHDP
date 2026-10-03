from app.discovery.discovery_result import DiscoveryResult
from app.discovery.device_registry import DeviceRegistry
from app.discovery.discovery_provider import DiscoveryProvider
from app.discovery.providers.cpu_provider import CPUProvider
from app.discovery.providers.memory_provider import MemoryProvider
from app.discovery.providers.storage_provider import StorageProvider
from app.discovery.providers.display_provider import DisplayProvider
from app.discovery.providers.system_provider import SystemProvider
from app.discovery.providers.motherboard_provider import MotherboardProvider
from app.discovery.providers.network_provider import NetworkProvider
from app.discovery.providers.battery_provider import BatteryProvider
from app.discovery.providers.gpu_provider import GPUProvider


class DiscoveryService:

    def __init__(
        self,
        providers: list[DiscoveryProvider] | None = None,
        registry: DeviceRegistry | None = None,
    ) -> None:

        self._providers = (
            providers
            if providers is not None
            else [
                CPUProvider(),
                MemoryProvider(),
                StorageProvider(),
                DisplayProvider(),
                SystemProvider(),
                MotherboardProvider(),
                NetworkProvider(),
                BatteryProvider(),
                GPUProvider(),
            ]
        )

        self._registry = (
            registry
            if registry is not None
            else DeviceRegistry()
        )

    @property
    def registry(self) -> DeviceRegistry:
        return self._registry

    def discover(self) -> DiscoveryResult:

        result = DiscoveryResult()

        self._registry.clear()

        for provider in self._providers:

            provider_result = provider.discover()

            for device in provider_result.devices:
                result.add_device(device)
                self._registry.register(device)

        return result

    def get_devices(self) -> list:
        return self._registry.all()

    def get_device(
        self,
        device_id: str,
    ):
        return self._registry.get(device_id)


discovery_service = DiscoveryService()