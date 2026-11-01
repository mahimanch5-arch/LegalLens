"""Dev-only switches that force states that are hard to reach naturally — the backend twin of the
frontend's ScenarioSwitcher. Process-local; only reachable through /api/dev when LL_ENV=dev."""

from typing import Literal

from app.schemas.common import CamelModel

NextReply = Literal["normal", "refusal", "llm_unavailable", "rate_limited", "timeout", "interrupted"]
StreamSpeed = Literal["fast", "normal", "slow"]


class Scenario(CamelModel):
    next_reply: NextReply = "normal"
    sticky: bool = False
    speed: StreamSpeed = "normal"
    next_upload_fails: bool = False


class ScenarioPatch(CamelModel):
    next_reply: NextReply | None = None
    sticky: bool | None = None
    speed: StreamSpeed | None = None
    next_upload_fails: bool | None = None


class ScenarioState:
    def __init__(self) -> None:
        self.current = Scenario()

    def update(self, patch: ScenarioPatch) -> Scenario:
        self.current = self.current.model_copy(update=patch.model_dump(exclude_none=True))
        return self.current

    def reset(self) -> None:
        self.current = Scenario()

    def consume_reply(self) -> NextReply:
        reply = self.current.next_reply
        if reply != "normal" and not self.current.sticky:
            self.current = self.current.model_copy(update={"next_reply": "normal"})
        return reply

    def consume_upload_failure(self) -> bool:
        fails = self.current.next_upload_fails
        if fails:
            self.current = self.current.model_copy(update={"next_upload_fails": False})
        return fails

    def token_delay_ms(self, base_ms: int) -> int:
        return {"fast": max(1, base_ms // 4), "normal": base_ms, "slow": base_ms * 3}[self.current.speed]


scenario = ScenarioState()
