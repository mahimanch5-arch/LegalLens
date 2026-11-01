"""Process-wide services, built once in the app lifespan and reached through ``get_runtime``."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request

from app.core.config import Settings
from app.ingestion.blob_store import BlobStore
from app.ingestion.worker import JobQueue
from app.orchestrator.interface import Orchestrator


@dataclass
class Runtime:
    settings: Settings
    blobs: BlobStore
    queue: JobQueue
    orchestrator: Orchestrator


def get_runtime(request: Request) -> Runtime:
    runtime: Runtime = request.app.state.runtime
    return runtime


RuntimeDep = Annotated[Runtime, Depends(get_runtime)]
