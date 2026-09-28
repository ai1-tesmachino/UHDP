import pytest
from app.runtime.application import Application
from app.runtime.models.status import RuntimeStatus


@pytest.mark.asyncio
async def test_application_starts():
    application = Application()

    assert application.status is RuntimeStatus.INITIALIZING

    await application.start()

    try:
        assert application.status is RuntimeStatus.RUNNING
        assert application.runtime.job_manager.scheduler.running
    finally:
        await application.stop()


@pytest.mark.asyncio
async def test_application_stops():
    application = Application()

    await application.start()
    await application.stop()

    assert application.status is RuntimeStatus.STOPPED
    assert not application.runtime.job_manager.scheduler.running


@pytest.mark.asyncio
async def test_application_start_is_idempotent():
    application = Application()

    await application.start()

    try:
        await application.start()

        assert application.status is RuntimeStatus.RUNNING
    finally:
        await application.stop()


@pytest.mark.asyncio
async def test_application_stop_is_idempotent():
    application = Application()

    await application.start()

    await application.stop()
    await application.stop()

    assert application.status is RuntimeStatus.STOPPED


@pytest.mark.asyncio
async def test_stopped_application_cannot_restart():
    application = Application()

    await application.start()
    await application.stop()

    with pytest.raises(
        RuntimeError,
        match="cannot be restarted",
    ):
        await application.start()