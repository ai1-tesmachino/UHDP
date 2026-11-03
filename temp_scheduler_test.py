import asyncio
from app.runtime.managers.job_manager import JobManager

async def main():
    jm = JobManager()

    print("INITIAL")
    print("running =", jm.scheduler.running)
    print("state   =", jm.scheduler.state)

    await jm.start()

    print("AFTER_START")
    print("running =", jm.scheduler.running)
    print("state   =", jm.scheduler.state)

    await jm.stop()

    print("AFTER_STOP")
    print("running =", jm.scheduler.running)
    print("state   =", jm.scheduler.state)

asyncio.run(main())
