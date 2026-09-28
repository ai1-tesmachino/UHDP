from app.runtime.registry import RuntimeRegistry

registry = RuntimeRegistry()

service = object()

registry.register(
    "demo-service",
    service,
)

print(
    registry.get("demo-service")
)