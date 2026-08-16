"""The model client, and the meter that watches it.

`SCOPE.md` §4 puts Phase 1 and Phase 3 on the model-inference side of the boundary table. Everything in this
module is therefore judgment, not record, and every output that comes through it is labelled as such
downstream.

Two things live here that are not about calling the API. The first is metering: `DATA_CONTRACT.md` §8 requires
every call logged with its model, prompt version, token counts and cost, and requires a run that hits its
budget cap to **halt and record that it halted** rather than quietly finish with fewer claims audited. A
truncated run reported as a complete one puts a wrong denominator under every rate.

The second is the seam for tests. `JudgeClient` is a protocol, so the whole pipeline runs offline against a
fake. The span-guard test in particular has to be able to hand the pipeline a fabricated span on demand, and
it cannot do that against a live model.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

#: Default judge model. Configurable, because the cost of the run is a real constraint on this project and
#: the choice belongs to whoever is paying for it.
DEFAULT_MODEL = os.environ.get("SAYSWHO_MODEL", "claude-opus-5")

#: USD per million tokens, for the run log. A recorded estimate, not a bill.
PRICING = {
    "claude-opus-5": (5.00, 25.00),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
}


class BudgetExceeded(Exception):
    """Raised when a run reaches its token budget.

    The run stops here and the halt is recorded. It does not finish with fewer claims audited, because a
    partial run reported as a whole one is a wrong denominator rather than a smaller sample.
    """


@dataclass
class ModelCall:
    at: str
    purpose: str
    model: str
    prompt_version: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: float = 0.0
    subject: str = ""
    stop_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Meter:
    """Records every model call, and stops the run at the budget cap."""

    budget_tokens: int = 2_000_000
    calls: list[ModelCall] = field(default_factory=list)
    halted: bool = False
    halt_reason: str = ""

    @property
    def total_tokens(self) -> int:
        return sum(c.input_tokens + c.output_tokens for c in self.calls)

    @property
    def total_cost_usd(self) -> float:
        return sum(c.cost_usd for c in self.calls)

    def check(self) -> None:
        if self.total_tokens >= self.budget_tokens:
            self.halted = True
            self.halt_reason = f"budget cap of {self.budget_tokens:,} tokens reached after {len(self.calls)} calls"
            raise BudgetExceeded(self.halt_reason)

    def record(self, call: ModelCall) -> ModelCall:
        rate_in, rate_out = PRICING.get(call.model, (0.0, 0.0))
        call.cost_usd = round(
            (call.input_tokens * rate_in + call.output_tokens * rate_out) / 1_000_000, 6
        )
        self.calls.append(call)
        return call

    def to_dict(self) -> dict[str, Any]:
        return {
            "calls": len(self.calls),
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(self.total_cost_usd, 4),
            "budget_tokens": self.budget_tokens,
            "halted": self.halted,
            "halt_reason": self.halt_reason,
        }

    def write(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps({**self.to_dict(), "log": [c.to_dict() for c in self.calls]}, indent=2) + "\n"
        )


class JudgeUnavailable(RuntimeError):
    """The judge cannot do its job, established before any claim was sent to it.

    Part of the shared halt vocabulary in this module rather than a provider's own exception type, for the
    reason `gemini.py` gives about rate limits: a caller that had to name a provider to read an error would
    undo the point of `JudgeClient`. `kind` is what the caller acts on, and it is deliberately about the
    situation rather than about an HTTP code, because the two providers number their failures differently and
    the person reading the message does not care which number came back.

    `kind` is one of:

    ``key``
        No key in the environment at all.
    ``rejected``
        A key is there and the provider will not accept it.
    ``model``
        The key works and the configured model name does not.
    ``unreachable``
        The provider did not answer, so nothing about the key is known either way.
    """

    def __init__(self, message: str, *, kind: str):
        super().__init__(message)
        self.kind = kind


class JudgeClient(Protocol):
    """What the pipeline needs from a model.

    A protocol rather than a class so the whole pipeline runs offline in tests. The span guard's own test has
    to hand it a fabricated span deliberately, which is not something a real model can be asked for.
    """

    def complete_json(
        self, *, system: str, cached_context: str, question: str, schema: dict, purpose: str,
        prompt_version: str, subject: str = "",
    ) -> dict: ...

    def probe(self) -> None:
        """Prove to a caller that this client can reach its provider, before a run depends on it.

        Every provider answers a different question here, which is why it belongs on the client and not in
        `server.check_judge`: adding a third provider means writing its probe next to its `complete_json`,
        and no caller learns a provider's name either way.

        Two rules hold for every implementation. It costs no tokens, so it never touches the meter, never
        enters a run log and cannot move the budget or anything gate G4 reads. And it raises
        `JudgeUnavailable` with a `kind`, never a provider's own exception.
        """
        ...


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class AnthropicJudge:
    """The real client.

    `cached_context` is the fetched source document and goes in its own content block with a cache
    breakpoint, ahead of the varying question. Several claims usually cite the same page, so the expensive
    part of the prompt is written once and read back at a tenth of the price on every claim after the first.
    """

    def __init__(self, model: str = DEFAULT_MODEL, meter: Meter | None = None, max_tokens: int = 8000):
        import anthropic

        self.client = anthropic.Anthropic()
        self.model = model
        self.meter = meter or Meter()
        self.max_tokens = max_tokens

    def probe(self) -> None:
        """Retrieve the model's metadata, which authenticates without generating anything."""
        import anthropic

        try:
            self.client.models.retrieve(self.model)
        except anthropic.RateLimitError:
            # Rate limited before a single claim was judged. That is a quota problem for the run to deal
            # with when it gets there, and it is also proof the key authenticated, which is the whole
            # question this probe was asking.
            return
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as exc:
            raise JudgeUnavailable(f"the provider rejected the key: {exc}", kind="rejected") from exc
        except anthropic.NotFoundError as exc:
            raise JudgeUnavailable(
                f"the key works and the provider has no model called {self.model!r}", kind="model"
            ) from exc
        except Exception as exc:
            raise JudgeUnavailable(
                f"the provider could not be reached: {type(exc).__name__}: {exc}", kind="unreachable"
            ) from exc

    def complete_json(
        self, *, system: str, cached_context: str, question: str, schema: dict, purpose: str,
        prompt_version: str, subject: str = "",
    ) -> dict:
        self.meter.check()

        response = self.client.beta.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=system,
            output_config={"format": {"type": "json_schema", "schema": schema}},
            messages=[
                {
                    "role": "user",
                    "content": [
                        # Stable prefix: the source document. Cached, so the next claim citing the same page
                        # reads it back instead of paying for it again.
                        {
                            "type": "text",
                            "text": cached_context,
                            "cache_control": {"type": "ephemeral"},
                        },
                        # Varying suffix: the claim being judged.
                        {"type": "text", "text": question},
                    ],
                }
            ],
        )

        usage = response.usage
        self.meter.record(
            ModelCall(
                at=now_iso(),
                purpose=purpose,
                model=response.model,
                prompt_version=prompt_version,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
                cache_write_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
                subject=subject,
                stop_reason=response.stop_reason or "",
            )
        )

        if response.stop_reason == "refusal":
            # A safety refusal is not a verdict. It is recorded and the claim goes unjudged rather than
            # being counted as anything.
            raise ModelRefused(
                f"the judge refused to answer: {getattr(response.stop_details, 'category', None)}"
            )

        text = next((b.text for b in response.content if b.type == "text"), "")
        return json.loads(text)


class ModelRefused(Exception):
    """The model declined to answer. Recorded, and the claim is left unjudged rather than scored."""
