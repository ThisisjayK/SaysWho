"""The check that runs before a judged run starts, so a failure arrives before the work does.

Two entry points need this and neither should have to import the other. It lived in `server.py` until the
CLI turned out to have the same hole, and importing the HTTP server to run a command line tool would have
made a module of `BaseHTTPRequestHandler` a dependency of every harness run. `server.py` re-exports what it
used to define, so `from sayswho.server import check_judge` keeps working: `tools/break_attempts.py` reads
it from there.

Nothing here knows which provider is running. It builds whichever judge is configured, asks it to prove
itself, and turns a `JudgeUnavailable` kind into the advice for that kind. A third provider means a new
client with a new `probe`, and no edit to this file.
"""

from __future__ import annotations

#: What a judge failing actually means, in the ways it fails. Every one of these used to surface as a raw
#: exception in the middle of a run, after every cited page had been fetched, with the server having
#: reported itself ready and the popup having painted a green light.
#:
#: `{entry}` is the command the reader should run once they have fixed it, which differs by entry point.
JUDGE_ADVICE = {
    "import": (
        "The judge needs the `google-genai` package and the Python running this does not have it.\n"
        "  Either use this repo's virtualenv:\n"
        "      .venv/bin/python -m {entry}\n"
        "  or install it into whichever Python you are using:\n"
        "      python3 -m pip install google-genai"
    ),
    "key": (
        "The judge needs an API key in this shell's environment:\n"
        "      export GEMINI_API_KEY=...\n"
        "  A free key comes from aistudio.google.com. DATA_CONTRACT.md §8: the key is read from the\n"
        "  environment and never written to a file."
    ),
    "rejected": (
        "A key is set in this shell and the provider will not accept it.\n"
        "  The usual cause is the example line from the extension popup pasted whole, which exports the\n"
        "  literal string `your-key-here` and shadows the real key for that shell alone. Look at what this\n"
        "  shell actually has, first characters only rather than the whole secret:\n"
        "      printf '%s...\\n' \"${GEMINI_API_KEY:0:6}\"\n"
        "  Then run it again from a shell that has the real one. A free key comes from aistudio.google.com."
    ),
    "model": (
        "The key works and the model name does not. Model names age, and SAYSWHO_GEMINI_MODEL overrides\n"
        "  the default for the Gemini judge, SAYSWHO_MODEL for the Anthropic one.\n"
        "  List what this key can actually see:\n"
        "      .venv/bin/python -c \"from google import genai;\\\n"
        "          print('\\\\n'.join(m.name for m in genai.Client().models.list()))\"\n"
        "  Gate G4 ties the gold set to the judge, so changing the model is a relabelling decision and not\n"
        "  a thing to do to make one run start."
    ),
    "unreachable": (
        "The provider did not answer, so whether the key works is still unknown.\n"
        "  That is a network or an outage rather than anything in this repo, and the only fix is to try\n"
        "  again. Run without --judge in the meantime: fetching sources and checking they are live needs\n"
        "  no key and no provider."
    ),
}

#: The command named in the `import` advice when the caller does not say. It is the server's, because the
#: server is the path the extension drives and the path a reader is likeliest to be on.
DEFAULT_ENTRY_POINT = "sayswho.server --judge"


def check_judge(provider: str | None = None, entry_point: str = DEFAULT_ENTRY_POINT) -> tuple[bool, str]:
    """Build a judge, make it prove itself against the provider, and throw it away.

    Called before a judged run does any work. Without it the failure arrives two minutes in, having already
    fetched every cited page, and the extension shows a green light the whole time. A tool that reports
    itself ready and is not is the same error this project is about, committed by the tool rather than by
    the thing it audits.

    Building was not enough on its own, and this function claimed otherwise for three days. A client is
    constructed from an environment variable being non-empty, and the example line in the extension popup
    exports the literal string `your-key-here`, which is non-empty. On day 10 a server built its judge on
    that string, printed itself ready, painted the popup green and failed on the first judged claim with
    `API_KEY_INVALID`, having already fetched every source: precisely the failure the paragraph above says
    this function exists to prevent. So the judge is now asked something the provider has to answer.

    The probe is a metadata read rather than a generation. It costs no tokens, enters no run log and moves
    nothing gate G4 reads, so a run that starts has spent nothing on starting.
    """
    from .gemini import build_judge
    from .model import JudgeUnavailable, Meter

    def advice(kind: str) -> str:
        # `replace` rather than `format`, because these strings contain shell braces and one of them is
        # `${GEMINI_API_KEY:0:6}`, which `format` would read as a field name and refuse.
        return JUDGE_ADVICE[kind].replace("{entry}", entry_point)

    try:
        judge = build_judge(provider, meter=Meter())
        judge.probe()
    except ImportError as exc:
        return False, f"{exc}\n\n{advice('import')}"
    except JudgeUnavailable as exc:
        return False, f"{exc}\n\n{advice(exc.kind)}"
    except RuntimeError as exc:
        # A provider client that raises a bare RuntimeError rather than `JudgeUnavailable`. Kept because a
        # missing key was the only way to get here before probing existed, and that reading is still the
        # likeliest one.
        return False, f"{exc}\n\n{advice('key')}"
    except Exception as exc:  # pragma: no cover - provider-specific failures
        return False, f"{type(exc).__name__}: {exc}"
    return True, ""
