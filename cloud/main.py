from __future__ import annotations

from contextlib import asynccontextmanager
import os

from fastapi import FastAPI

from cloud.api import router
from cloud.config import CloudSettings
from cloud.database import CloudDatabase


def _create_object_storage():
    endpoint = os.environ.get("OBJECT_STORAGE_ENDPOINT")
    bucket = os.environ.get("OBJECT_STORAGE_BUCKET")
    access_key = os.environ.get("OBJECT_STORAGE_ACCESS_KEY")
    secret_key = os.environ.get("OBJECT_STORAGE_SECRET_KEY")
    if not any((endpoint, bucket, access_key, secret_key)):
        return None
    if not all((endpoint, bucket, access_key, secret_key)):
        raise RuntimeError("All OBJECT_STORAGE_* settings are required together.")
    if not endpoint.startswith("https://") and os.environ.get(
        "OBJECT_STORAGE_ALLOW_HTTP"
    ) != "true":
        raise RuntimeError(
            "Object storage must use HTTPS. HTTP is allowed only with "
            "OBJECT_STORAGE_ALLOW_HTTP=true on an isolated development network."
        )
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("Install cloud requirements to enable object storage.") from exc
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=os.environ.get("OBJECT_STORAGE_REGION", "us-east-1"),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = CloudSettings.from_env()
    database = CloudDatabase(settings)
    database.migrate()
    app.state.settings = settings
    app.state.database = database
    app.state.object_storage = _create_object_storage()
    app.state.object_storage_bucket = os.environ.get("OBJECT_STORAGE_BUCKET")
    yield


app = FastAPI(
    title="UHDP Cloud Management API",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(router)
