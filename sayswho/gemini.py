"""A Gemini judge, for running on a free tier.

`sayswho/model.py` holds the Anthropic client. This is the alternative, chosen because the free tier makes
the run cost nothing, which is a hard constraint on this project rather than a preference. Both satisfy the
same `JudgeClient` protocol, so the pipeline, the gates and the span guard are unchanged by the swap. That
protocol existed before this file did, which is the only reason adding a second provider is a new module
rather than a refactor.

**Three things the swap costs, recorded here because they belong in the writeup.**

*A conflict of interest on one product.* `SCOPE.md` §10 audits Google AI Overviews alongside Claude, ChatGPT
and Perplexity. A Gemini judge scoring a Google product is a vendor grading its own homework. That is not
fatal, but it cannot be silent: either AI Overviews is dropped from the audited set, or its per-product
result is reported with the conflict stated beside it. The other three products have no such problem, and a
judge from outside all of them is arguably *more* independent than one from inside.

*Calibration is per judge.* Gate G4 ties the gold set to the judge and the prompt version together. Labelling
against this judge means the numbers are about this judge. Switching later means relabelling.

*The free tier has real limits.* Requests are rate limited per minute and per day, so a run pauses rather
than failing, and the pauses are recorded. A run that hits the daily cap halts and says so, the same way the
budget cap does, rather than finishing with fewer claims audited.

**What does not change: the span guard.** It is a substring check against the fetched document and knows
nothing about which model produced the span. A weaker judge quotes worse, `JUDGE_FABRICATED_SPAN` fires more
often, and that rate is published as a finding about the judge. `SCOPE.md` §5 already treats it that way.
"""

from __future__ import annotations

import json
import os
import time

from .model import Meter, ModelCall, ModelRefused, now_iso

#: Free-tier model. Configurable, because which models carry a free tier changes and this default will age.
DEFAULT_GEMINI_MODEL = os.environ.get("SAYSWHO_GEMINI_MODEL", "gemini-3.5-flash-lite")

#: Finish reasons that mean the model declined rather than answered. Recorded, never scored.
REFUSAL_REASONS = {"SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "RECITATION"}


class GeminiJudge:
    """A `JudgeClient` backed by the Gemini free tier.

    The `cached_context` and `question` split is preserved even though this path does not pay for implicit
    caching the way the Anthropic client does. Keeping the shape identical is what makes the two clients
    substitutable, and it keeps the source document ahead of the claim so a caching layer can exploit the
    shared prefix if one appears later.
    """

    def __init__(
        self,
        model: str = DEFAULT_GEMINI_MODEL,
        meter: Meter | None = None,
        max_output_tokens: int = 8000,
        max_retries: int = 5,
        sleep=time.sleep,
    ):
        from google import genai

        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "set GEMINI_API_KEY. A free key comes from aistudio.google.com; it is not the same as an "
                "Anthropic key and SaysWho does not read one from the other."
            )

        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.meter = meter or Meter()
        self.max_output_tokens = max_output_tokens
        self.max_retries = max_retries
        self._sleep = sleep
        #: Seconds spent waiting out rate limits. Reported, because a run that waited eleven minutes for its
        #: free tier is a different run from one that did not, and the writeup should be able to say so.
        self.rate_limit_waits = 0.0

    # ------------------------------------------------------------------ the call

    def complete_json(
        self, *, system: str, cached_context: str, question: str, schema: dict, purpose: str,
        prompt_version: str, subject: str = "",
    ) -> dict:
        from google.genai import errors, types

        self.meter.check()

        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            # The raw JSON Schema the pipeline already defines, passed through unchanged. Using the same
            # schema object on both providers is what stops the two judges from being asked subtly
            # different questions.
            response_json_schema=schema,
            max_output_tokens=self.max_output_tokens,
        )

        attempt = 0
        while True:
            attempt += 1
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=[cached_context, question],
                    config=config,
                )
                break
            except errors.ClientError as exc:
                if getattr(exc, "code", None) != 429 or attempt > self.max_retries:
                    # Provider error, raised through unchanged. There is deliberately no rate-limit
                    # exception of our own: a caller that caught one would have to name a provider to do
                    # anything with it, and the point of `JudgeClient` is that no caller knows which
                    # provider is running. The halt vocabulary the pipeline does read, `BudgetExceeded` and
                    # `ModelRefused`, lives in `model.py` and is shared by both clients.
                    raise
                # Free-tier rate limit. Wait it out rather than dropping the claim: a claim skipped because
                # of a quota is a hole in the denominator, and holes are what this project refuses.
                delay = min(60.0, 2.0 ** attempt)
                self.rate_limit_waits += delay
                self._sleep(delay)
            except errors.ServerError:
                if attempt > self.max_retries:
                    raise
                delay = min(60.0, 2.0**attempt)
                self._sleep(delay)

        usage = response.usage_metadata
        candidate = (response.candidates or [None])[0]
        finish = str(getattr(candidate, "finish_reason", "") or "").rsplit(".", 1)[-1]

        self.meter.record(
            ModelCall(
                at=now_iso(),
                purpose=purpose,
                model=response.model_version or self.model,
                prompt_version=prompt_version,
                input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
                output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
                cache_read_tokens=getattr(usage, "cached_content_token_count", 0) or 0,
                subject=subject,
                stop_reason=finish,
            )
        )

        if finish in REFUSAL_REASONS:
            raise ModelRefused(f"the judge declined to answer: finish_reason {finish}")

        if finish == "MAX_TOKENS":
            # A truncated answer is not a verdict. Better a void than a half-parsed one.
            raise ModelRefused(
                f"the judge ran out of output tokens at {self.max_output_tokens}; the answer was truncated"
            )

        text = response.text or ""
        if not text.strip():
            raise ModelRefused(f"the judge returned no text (finish_reason {finish or 'unknown'})")

        return json.loads(text)


def build_judge(provider: str | None = None, meter: Meter | None = None):
    """Pick a judge. `SAYSWHO_JUDGE` is `gemini` or `anthropic`.

    Whichever is chosen is recorded in the run log with every call, because gate G4 calibrates a gold set
    against a specific judge and a specific prompt version, and a run that cannot say which judge produced it
    cannot be checked against any gold set at all.
    """
    provider = (provider or os.environ.get("SAYSWHO_JUDGE", "gemini")).lower()

    if provider == "gemini":
        return GeminiJudge(meter=meter)
    if provider == "anthropic":
        from .model import AnthropicJudge

        return AnthropicJudge(meter=meter)
    raise ValueError(f"unknown judge provider {provider!r}; use 'gemini' or 'anthropic'")
