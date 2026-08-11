"""Checks on the extension package that do not need a browser.

The browser leg genuinely cannot be exercised here, and pretending otherwise would be worse than the gap.
What these do catch is the class of mistake that makes an extension fail to load at all or fail silently:
a manifest referencing a file that is not there, a script with a syntax error, a stylesheet that would
restyle the product's own page, and a host permission that does not match the endpoint the code calls.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
EXTENSION = REPO / "extension"
MANIFEST = json.loads((EXTENSION / "manifest.json").read_text())

node = shutil.which("node")


def listed_files() -> list[str]:
    files = [MANIFEST["background"]["service_worker"]]
    for entry in MANIFEST.get("content_scripts", []):
        files += entry.get("js", []) + entry.get("css", [])
    return files


@pytest.mark.parametrize("relative", listed_files())
def test_every_file_the_manifest_names_exists(relative):
    assert (EXTENSION / relative).is_file(), f"manifest names {relative} and it is not there"


@pytest.mark.skipif(node is None, reason="node is not installed")
@pytest.mark.parametrize("path", sorted(p.name for p in (EXTENSION / "src").glob("*.js")))
def test_every_script_parses(path):
    done = subprocess.run([node, "--check", str(EXTENSION / "src" / path)], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr


def test_the_renderer_loads_before_the_code_that_calls_it():
    """Content scripts run in order, so render.js has to be listed before audit.js and content.js."""
    js = MANIFEST["content_scripts"][0]["js"]
    assert js.index("src/render.js") < js.index("src/audit.js")
    assert js.index("src/audit.js") < js.index("src/content.js")


def test_the_stylesheet_only_targets_its_own_classes():
    """It is injected into the product's page, so a bare element selector would restyle claude.ai."""
    css = (EXTENSION / "src" / "render.css").read_text()
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    for block in css.split("}"):
        if "{" not in block:
            continue
        for selector in block.split("{")[0].split(","):
            selector = selector.strip()
            if not selector or selector.startswith("@") or selector.startswith(":"):
                continue
            assert selector.startswith(".sw"), f"{selector!r} would apply to the product's own page"


def test_the_host_permission_matches_the_endpoint_the_code_calls():
    """A mismatch here fails at runtime with a CORS error that reads like the server being down."""
    from sayswho.server import HOST, PORT

    endpoint = re.search(r'ENDPOINT = "([^"]+)"', (EXTENSION / "src" / "audit.js").read_text()).group(1)
    assert endpoint == f"http://{HOST}:{PORT}"
    assert f"http://{HOST}:{PORT}/*" in MANIFEST["host_permissions"]


def test_the_products_the_extension_runs_on_are_the_origins_the_server_accepts():
    """The server's allowlist and the manifest's matches are two copies of one list, so they get compared."""
    from sayswho.server import ALLOWED_ORIGINS

    matched = {
        m.split("/*")[0].replace("/search*", "")
        for m in MANIFEST["content_scripts"][0]["matches"]
    }
    assert matched == set(ALLOWED_ORIGINS)


def test_the_audit_script_decides_nothing():
    """`SCOPE.md` §9. If this file started deriving a verdict there would be two implementations of it."""
    source = (EXTENSION / "src" / "audit.js").read_text()
    for token in ("SUPPORTED", "NOT_FOUND_IN_SOURCE", "CONTRADICTED", "span_verified", "auditable"):
        assert token not in source, f"audit.js references {token}, which means it is deciding something"


def test_the_capture_path_still_works_without_the_server():
    """The download is not conditional on the server, so a capture is never lost to it being down."""
    content = (EXTENSION / "src" / "content.js").read_text()
    assert 'chrome.runtime.sendMessage({ type: "sayswho:capture", capture: record })' in content
    audit = content[content.index("async function auditHere"):]
    assert audit.index("const record = await capture()") < audit.index("saysWhoAudit")
