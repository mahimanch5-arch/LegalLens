"""Dev-only endpoints — registered only when LL_ENV is dev or test."""

from fastapi import APIRouter, Response, status

from app.api.deps import DB, CurrentUser
from app.core.ratelimit import limiter
from app.runtime import RuntimeDep
from app.services import documents
from app.services.scenario import Scenario, ScenarioPatch, scenario

router = APIRouter(prefix="/api/dev", tags=["dev"])


@router.get("/scenario", response_model=Scenario)
async def get_scenario(_user: CurrentUser) -> Scenario:
    return scenario.current


@router.put("/scenario", response_model=Scenario)
async def set_scenario(body: ScenarioPatch, _user: CurrentUser) -> Scenario:
    """Forces the next reply (refusal, llm_unavailable, rate_limited, timeout, interrupted), the stream
    speed, or a failing next upload — the same switches as the frontend's ScenarioSwitcher."""
    return scenario.update(body)


@router.post("/reset", status_code=status.HTTP_204_NO_CONTENT)
async def reset(db: DB, rt: RuntimeDep, user: CurrentUser) -> Response:
    """Empties the workspace and resets the scenario and rate limits. Run scripts/seed_demo.py to reseed."""
    await documents.delete_workspace(db, rt, user.id)
    scenario.reset()
    limiter.reset()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
