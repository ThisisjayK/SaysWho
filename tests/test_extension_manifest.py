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
    if MANIFEST.get("action", {}).get("default_popup"):
        files.append(MANIFEST["action"]["default_popup"])
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


def test_the_capture_button_still_downloads():
    """The path that needs nothing running has to keep needing nothing. `download` defaults to true."""
    source = (EXTENSION / "src" / "content.js").read_text()
    assert "async function capture({ download = true } = {})" in source
    assert 'chrome.runtime.sendMessage({ type: "sayswho:capture", capture: record, download })' in source


def test_an_audit_does_not_also_download_a_copy():
    """The server writes the capture to the repo's captures directory, which is where the harness reads
    them from. A second copy in ~/Downloads is clutter, and in the wrong folder."""
    source = (EXTENSION / "src" / "content.js").read_text()
    audit = source[source.index("async function auditHere"):]
    assert "capture({ download: false })" in audit


def test_an_audit_that_stored_nothing_downloads_the_capture_after_all():
    """The promise is that a capture is never lost to the server being down. It is kept here rather than by
    downloading every single time."""
    source = (EXTENSION / "src" / "content.js").read_text()
    audit = source[source.index("async function auditHere"):]
    assert "if (!payload || !payload.saved_to)" in audit
    assert audit.index("saysWhoAudit") < audit.index("download: true")


def test_the_server_writes_every_capture_it_audits():
    """The other half of the same promise, and the reason the browser can stop downloading."""
    server = (REPO / "sayswho" / "server.py").read_text()
    assert "def save_capture" in server
    assert "saved = self.save_capture(capture, payload)" in server


# ---------------------------------------------------------------- the two controls


def content() -> str:
    return (EXTENSION / "src" / "content.js").read_text()


def content_of(name: str) -> str:
    """Any file in extension/src, by name."""
    return (EXTENSION / "src" / name).read_text()


def test_the_controls_are_labelled_with_what_they_do():
    """Two round icon buttons carry no words, so the label has to come from somewhere."""
    source = content()
    for label in ("SaysWho: capture", "SaysWho: audit"):
        assert f'"{label}"' in source, f"no control is labelled {label!r}"


def test_each_control_has_both_an_accessible_name_and_a_tooltip():
    """A hover label is a visual affordance. A screen reader and a keyboard user get the same words."""
    source = content()
    assert 'button.setAttribute("aria-label", label)' in source
    assert "button.title = label" in source


def test_the_controls_sit_side_by_side_rather_than_stacked():
    """They used to be two full-width buttons at bottom:16px and bottom:52px, and they overlapped."""
    source = content()
    dock = source[source.index("const dock = document.createElement"): source.index("const tip =")]
    assert '"display:flex"' in dock
    assert '"flex-direction:row"' in dock
    assert '"gap:8px"' in dock
    assert "bottom:52px" not in source, "the stacked layout is gone"


def test_the_controls_are_round_and_small():
    source = content()
    for rule in ('"width:34px"', '"height:34px"', '"border-radius:50%"'):
        assert rule in source


def test_the_hover_label_is_anchored_to_the_dock_not_the_viewport():
    """Anchored to the viewport it overlapped the button it labelled, and stayed put when the panel opened."""
    source = content()
    tip = source[source.index("const tip = document.createElement"): source.index("function showTip")]
    assert '"position:absolute"' in tip
    assert '"right:100%"' in tip
    assert "dock.appendChild(tip);" in source


def test_the_icons_are_built_through_the_dom_rather_than_written_as_markup():
    """claude.ai enforces Trusted Types, and an innerHTML assignment throws there. The failure is total:
    no buttons at all, on the one product this was screenshotted against."""
    # Comments stripped first: the file explains why it avoids innerHTML, and naming the thing you are
    # avoiding is not using it. Two passes, because one alternation with DOTALL makes `//` swallow the rest
    # of the file, which then passes this test by having no code left in it.
    source = re.sub(r"/\*.*?\*/", "", content(), flags=re.S)
    source = re.sub(r"^\s*//.*$", "", source, flags=re.M)
    assert "innerHTML" not in source
    assert "createElementNS" in source
    for name in ("CAPTURE_ICON", "AUDIT_ICON"):
        assert name in source


def test_the_panel_steps_the_controls_aside_instead_of_covering_them():
    audit = (EXTENSION / "src" / "audit.js").read_text()
    assert "function moveDock" in audit
    assert 'document.getElementById("sayswho-dock")' in audit
    assert audit.count("moveDock(") >= 3, "opened, closed, and defined"


# ---------------------------------------------------------------- the popup


POPUP = EXTENSION / "src" / "popup.html"


def popup_js() -> str:
    return (EXTENSION / "src" / "popup.js").read_text()


def test_the_toolbar_icon_opens_the_popup():
    assert MANIFEST["action"]["default_popup"] == "src/popup.html"


def test_the_old_click_handler_is_gone():
    """Chrome does not fire `action.onClicked` when a popup is set. Leaving the handler would be dead code
    that reads exactly like working code, which is the worst kind to leave behind."""
    # Comments stripped: background.js explains why the handler is absent, and saying so is not doing it.
    background = re.sub(
        r"/\*.*?\*/", "", (EXTENSION / "src" / "background.js").read_text(), flags=re.S
    )
    background = re.sub(r"^\s*//.*$", "", background, flags=re.M)
    assert "chrome.action.onClicked" not in background


@pytest.mark.parametrize("asset", ["popup.css", "popup.js", "adapters.js"])
def test_everything_the_popup_loads_exists(asset):
    assert asset in POPUP.read_text()
    assert (EXTENSION / "src" / asset).is_file()


def test_the_popup_loads_adapters_before_the_code_that_calls_it():
    html = POPUP.read_text()
    assert html.index('src="adapters.js"') < html.index('src="popup.js"')


STORAGE_KEYS = ["sayswho.showDock", "sayswho.lastCapture", "sayswho.firstRun"]


@pytest.mark.parametrize("key", STORAGE_KEYS)
def test_the_storage_keys_agree_across_the_three_files_that_use_them(key):
    """Three files share these strings. A typo in one silently breaks a toggle rather than raising, so the
    only thing that can catch it is a comparison like this one."""
    users = {
        "popup.js": popup_js(),
        "background.js": (EXTENSION / "src" / "background.js").read_text(),
        "content.js": content(),
    }
    writers = [name for name, source in users.items() if f'"{key}"' in source]
    assert writers, f"{key} is not used by any file, so it is dead"
    if key == "sayswho.showDock":
        assert set(writers) == {"popup.js", "background.js", "content.js"}
    if key == "sayswho.lastCapture":
        assert set(writers) == {"popup.js", "background.js"}


def test_the_popup_decides_nothing():
    """Same rule as audit.js. It reads a health endpoint and sends two messages."""
    source = popup_js()
    for token in ("SUPPORTED", "NOT_FOUND_IN_SOURCE", "CONTRADICTED", "span_verified"):
        assert token not in source


def test_the_popup_talks_to_the_same_endpoint_the_server_listens_on():
    from sayswho.server import HOST, PORT

    assert re.search(r'ENDPOINT = "([^"]+)"', popup_js()).group(1) == f"http://{HOST}:{PORT}"


def test_the_indicator_has_three_states_rather_than_two():
    """A server running without a judge is up and cannot produce a verdict. Painting that green would
    collapse "we checked" into "we could not check", which is the error this whole project is about."""
    source = popup_js()
    assert "Audit server not running" in source
    assert "Running, no judge" in source
    assert "Audit server running" in source
    assert "if (!state.judge)" in source


def test_an_unset_dock_preference_means_shown():
    """A fresh profile has never opened the popup, and an extension that installs invisibly reads as broken."""
    assert "!== false" in content()
    assert "!== false" in popup_js()


def test_the_dock_toggle_takes_effect_without_a_reload():
    assert "chrome.storage.onChanged.addListener" in content()


def test_the_popup_can_trigger_both_paths():
    source = popup_js()
    assert "sayswho:capture-now" in source
    assert "sayswho:audit-now" in source
    assert "sayswho:audit-now" in content(), "the page has to answer what the popup sends"


def test_the_toast_is_mounted_even_when_the_dock_is_hidden():
    """With the buttons hidden, the toast is the only feedback a capture happened at all."""
    source = content()
    mount = source[source.index("dock.appendChild(tip);"):]
    assert "document.documentElement.appendChild(toast);" in mount
    assert mount.index("appendChild(toast)") < mount.index("function mountDock")


# ---------------------------------------------------------------- the toast and the overflow


def test_the_toast_can_be_dismissed_and_dismisses_itself():
    """It used to sit on the page until a reload, which on a product you keep working in means an hour."""
    source = content()
    assert "function hideToast" in source
    assert 'toast.addEventListener("click", hideToast)' in source
    assert "setTimeout(hideToast" in source
    assert "window.saysWhoHideToast = hideToast" in source


def test_opening_the_panel_clears_the_toast():
    """The panel supersedes whatever the toast was saying, so leaving both up is two answers to one thing."""
    assert "window.saysWhoHideToast?.()" in (EXTENSION / "src" / "audit.js").read_text()


def test_long_unbroken_strings_cannot_widen_the_panel():
    """URLs, sha256 digests and CSS selectors have no spaces in them, so they set the minimum width of the
    box, the box grows past the panel, and the text runs off the right of the screen."""
    css = (EXTENSION / "src" / "render.css").read_text()
    assert "overflow-wrap: break-word" in css
    assert "min-width: 0" in css and "max-width: 100%" in css
    meta = css[css.index(".sw-meta {"): css.index(".sw-banner")]
    assert "flex-wrap: wrap" in meta
    assert "white-space: nowrap" not in meta, "nowrap on the meta line is what pushed it off the panel"
    assert "overflow-x:hidden" in (EXTENSION / "src" / "audit.js").read_text()


def test_a_run_with_no_claims_shows_no_counters():
    """Five counters reading zero is what a fetch-only run produces, and it reads as a result."""
    render = (EXTENSION / "src" / "render.js").read_text()
    assert "if (payload.counts.claims > 0)" in render
    assert "nothing to count" in render


def test_the_no_judge_warning_comes_before_the_counts():
    audit = (EXTENSION / "src" / "audit.js").read_text()
    assert "body.insertBefore(note, body.firstChild)" in audit
    assert "not because nothing checked out" in audit


# ---------------------------------------------------------------- the panel's own chrome


def audit_js() -> str:
    return (EXTENSION / "src" / "audit.js").read_text()


def test_the_close_control_is_an_icon_with_a_name():
    """The word "close" was a light pill inheriting the host page's text colour, so on claude.ai it was
    white on near-white."""
    source = audit_js()
    assert 'close.textContent = "close"' not in source
    assert 'close.className = "sw-panel-close"' in source
    assert 'close.setAttribute("aria-label", "Close the audit panel")' in source
    assert "Close the audit panel (Esc)" in source
    assert "createElementNS" in source, "the icon is built, not written, for the same Trusted Types reason"


def test_every_injected_control_sets_both_a_colour_and_a_background():
    """The rule the close button broke. A background with no colour inherits whatever the product uses,
    and half the products this runs on are dark."""
    css = (EXTENSION / "src" / "render.css").read_text()
    block = css[css.index(".sw-panel-close {"): css.index(".sw-panel-close:hover")]
    assert "color:" in block and "background:" in block

    content_js = content()
    for name in ("roundButton", "const tip ="):
        chunk = content_js[content_js.index(name): content_js.index(name) + 1200]
        assert "color:" in chunk and "background:" in chunk, f"{name} sets one colour and not the other"


def test_no_injected_text_carries_a_hardcoded_colour_in_an_inline_style():
    """The general form of the same mistake, which I made twice: once on the close button and once on the
    panel's message text. An inline colour cannot have a dark-mode variant, and every one of these surfaces
    sits on a product that is dark by default. Colours belong in render.css.

    The dock is the deliberate exception, and it is exempt by name rather than by accident: it sits on the
    product's own background rather than on one of ours, so it carries its own light chip colours and sets
    both halves of every pair.
    """
    exempt = ("content.js",)
    for path in sorted((EXTENSION / "src").glob("*.js")):
        if path.name in exempt or path.name == "popup.js":
            continue
        source = re.sub(r"/\*.*?\*/", "", path.read_text(), flags=re.S)
        source = re.sub(r"^\s*//.*$", "", source, flags=re.M)
        for style in re.findall(r'cssText\s*=\s*([^;]*?"[^"]*");', source, flags=re.S):
            assert "color:#" not in style.replace(" ", ""), (
                f"{path.name} hardcodes a text colour in an inline style: {style[:120]}"
            )


def test_the_panel_chrome_has_a_dark_variant():
    """It sits on claude.ai and chatgpt.com, which are dark by default."""
    css = (EXTENSION / "src" / "render.css").read_text()
    dark = css[css.index("@media (prefers-color-scheme: dark)"):]
    assert ".sw-panel {" in dark
    assert ".sw-panel-close {" in dark


def test_the_panel_frame_is_thin():
    """The panel's padding sits between its background and the content's, so anything generous reads as a
    wide border around the audit rather than as breathing room."""
    padding = re.search(r'"padding:([^"]+)"', audit_js()).group(1)
    values = [int(v.replace("px", "")) for v in padding.split()]
    assert max(values[:2]) <= 10, f"the frame is {padding}, which shows as a border"


def test_the_panel_closes_on_escape():
    source = audit_js()
    assert 'event.key === "Escape"' in source
    assert 'document.addEventListener("keydown", onKey)' in source
    assert 'document.removeEventListener("keydown", onKey)' in source, "or every audit leaves a listener"


def test_the_close_control_cannot_be_painted_over():
    """It used to be a sticky float, and the rendered content's own backgrounds covered it."""
    css = (EXTENSION / "src" / "render.css").read_text()
    block = css[css.index(".sw-panel-close {"): css.index(".sw-panel-close:hover")]
    assert "position: fixed" in block
    assert "z-index: 2147483647" in block


# ---------------------------------------------------------------- citations that are not links


def adapters_js() -> str:
    return (EXTENSION / "src" / "adapters.js").read_text()


def test_both_sides_look_for_the_same_citation_attributes():
    """`SCOPE.md` §9: a citation the extension records and the Python cannot re-extract is a parity
    failure. These two lists are the rule, written twice in two languages, so they get compared."""
    from sayswho.reextract import CITATION_URL_ATTRS

    in_js = set(re.findall(r'citationUrlAttrs:\s*\[([^\]]*)\]', adapters_js()))
    attrs = {a.strip().strip('"\'') for group in in_js for a in group.split(",") if a.strip()}
    assert attrs, "no adapter declares a citation URL attribute"
    assert attrs == set(CITATION_URL_ATTRS)


def test_the_url_of_a_citation_is_read_in_one_place():
    """Container selection ranks containers by citation count, so the counter and the extractor disagreeing
    about what a citation is would pick the wrong container and then extract from it."""
    js = adapters_js()
    assert "function saysWhoCitationUrl" in js
    assert "saysWhoCitationUrl(node, adapter)" in js, "the counter uses it"
    assert "saysWhoCitationUrl(anchor, adapter)" in (EXTENSION / "src" / "capture.js").read_text()


def test_the_extractor_no_longer_reads_href_directly():
    """`anchor.href` is undefined on a span, which is what every Perplexity citation is."""
    capture = (EXTENSION / "src" / "capture.js").read_text()
    assert "const url = anchor.href;" not in capture


def test_perplexity_looks_for_the_attribute_it_actually_uses():
    js = adapters_js()
    block = js[js.index('id: "perplexity"'): js.index('id: "perplexity"') + 1400]
    assert '"[data-pplx-citation-url]"' in block
    assert '"data-pplx-citation-url"' in block
    assert "verifiedSelectors: []" in block, "the citation path is evidence-based; the capture is not verified yet"


@pytest.mark.skipif(node is None, reason="node is not installed")
def test_the_url_helper_reads_an_attribute_when_there_is_no_href():
    """Run the real function, in node, rather than asserting about the shape of the file."""
    script = """
      const vm = require("node:vm");
      const fs = require("node:fs");
      const box = { console };
      vm.createContext(box);
      vm.runInContext(fs.readFileSync(process.argv[1], "utf8"), box);
      const adapter = { citationUrlAttrs: ["data-pplx-citation-url"] };
      const span = { getAttribute: (n) => n === "data-pplx-citation-url" ? "https://example.org/a" : null };
      const anchor = { href: "https://example.org/b", getAttribute: () => null };
      const plain = { getAttribute: () => null };
      const relative = { getAttribute: () => "/not-absolute" };
      console.log(JSON.stringify([
        box.saysWhoCitationUrl(span, adapter),
        box.saysWhoCitationUrl(anchor, adapter),
        box.saysWhoCitationUrl(plain, adapter),
        box.saysWhoCitationUrl(relative, adapter),
        box.saysWhoCitationUrl(span, {}),
      ]));
    """
    done = subprocess.run(
        [node, "-e", script, str(EXTENSION / "src" / "adapters.js")],
        capture_output=True, text=True, cwd=REPO,
    )
    assert done.returncode == 0, done.stderr
    span, anchor, plain, relative, unconfigured = json.loads(done.stdout)
    assert span == "https://example.org/a"
    assert anchor == "https://example.org/b", "a real anchor still wins"
    assert plain == ""
    assert relative == "", "a relative value is not a citation URL"
    assert unconfigured == "", "an adapter that declares no attribute reads none"


def test_the_download_depends_on_whether_the_capture_was_stored_not_on_success():
    """An audit can fail after the server has already written the capture: the server saves before it
    fetches anything, so a judge that cannot be built still leaves the file on disk. Keying the download
    off `payload.error` downloaded a second copy of exactly that case."""
    source = content()
    audit = source[source.index("async function auditHere"):]
    assert "if (!payload || !payload.saved_to)" in audit
    assert "payload.error" not in audit, "success is not the question; storage is"


# ---------------------------------------------------------------- the two character counts


def test_both_character_counts_measure_the_same_thing():
    """innerText inserts separators textContent has no equivalent for: between two table cells textContent
    yields "ab" and innerText yields "a\\tb". Collapsing whitespace is not enough, because the collapsed
    separator is still a character on one side and nothing on the other. On a real Perplexity answer with a
    table that reported 7912 rendered characters against 7835 in the DOM, a subset larger than its own set.

    The display bug is the small half. The real one is that an inflated rendered count can swallow a genuine
    gap and report a truncated capture as complete."""
    source = content_of("capture.js")
    assert "const withoutSpace = (value) => (value || \"\").replace(/\\s+/g, \"\")" in source
    assert "withoutSpace(found.element.textContent).length" in source
    assert "withoutSpace(answerText).length" in source
    assert '.replace(/\\s+/g, " ").trim().length' not in source, "the collapsing version is the broken one"


def test_hidden_citations_and_truncated_text_are_separate_warnings():
    """Two problems with two different fixes: scroll the answer, or expand the "+N" chips. One flag saying
    "this capture did not hold the whole answer" sends you looking for missing text that is all present."""
    background = content_of("background.js")
    assert "text_incomplete:" in background
    assert "citations_hidden:" in background
    # The conflated key, not merely the substring: `text_incomplete` contains it.
    assert not re.search(r"^\s*incomplete:", background, re.M), "the conflated flag is gone"

    popup = content_of("popup.js")
    assert "record.text_incomplete" in popup
    assert "record.citations_hidden" in popup
    assert "Scroll to the end" in popup
    assert "Expand them and capture again" in popup


# ---------------------------------------------------------------- the popup's size


def test_the_popup_width_is_set_on_the_root_element():
    """Chrome sizes a popup from `html`, not from `body`. With no width on the root it fills to the 800px
    maximum, which gave a 780px window with 340px of content sitting in the corner of it.

    Easy to reintroduce by "tidying" the selector list, so it is asserted rather than remembered."""
    css = content_of("popup.css")
    rule = re.search(r"(html,\s*\n?body\s*\{[^}]*\})", css)
    assert rule, "html and body must share the width rule"
    assert re.search(r"width:\s*\d+px", rule.group(1)), "the shared rule must carry the width"


def test_the_popup_declares_one_width_and_not_two():
    """Two different widths on html and body is the same bug with extra steps: the window would size to one
    and the content to the other."""
    css = content_of("popup.css")
    rule = re.search(r"html,\s*\n?body\s*\{([^}]*)\}", css).group(1)
    # Not preceded by a comma, so this finds the standalone `body {` rule rather than the shared one.
    body_only = re.search(r"(?<!,)\nbody\s*\{([^}]*)\}", css).group(1)
    assert "width" not in body_only, "a second width on body would size the content differently"
    assert len(set(re.findall(r"width:\s*(\d+)px", rule))) == 1


def test_the_citation_extractor_scans_every_selector_rather_than_stopping_at_the_first():
    """The bug that cost a quarter of the citations in the first real run against the consumer stratum.

    `saysWhoExtractCitations` looped over `adapter.citationSelectors` and ended with
    `if (citations.length) break;`, so the first selector that matched anything won and the rest never ran.
    Perplexity declares two, `a[href^="http"]` and `[data-pplx-citation-url]`, and renders both shapes in one
    answer: 13 of 51 inline citations across 24 captured answers were of the second kind. The capture looked
    completely normal, because everything it did find was real.

    Asserted against the source rather than by running the extractor, which would need a DOM. That makes this
    a weaker test than the one that should exist, and the one that should exist is on `TODO.md`: run the
    extension's extractor in node against the same markup Python re-extracts from, and compare. `FINDINGS.md`
    item 20."""
    source = (EXTENSION / "src" / "capture.js").read_text()
    start = source.index("function saysWhoExtractCitations")
    end = source.index("function ", start + 10)
    body = source[start:end]

    # Comments stripped first. The fix left a long note explaining what the removed break did and why it was
    # wrong, and that note quotes the statement, so a naive scan finds the very sentence describing its
    # absence. A check that fails on its own explanation is not a check.
    code = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
    code = re.sub(r"//[^\n]*", "", code)

    assert "citationSelectors" in code, "the extractor should still be the thing that loops over selectors"
    assert "break" not in code, (
        "saysWhoExtractCitations must not break out of the selector loop. The dedup set is keyed on marker "
        "and URL together, so scanning every selector cannot double-count, and stopping early silently drops "
        "every citation shape after the first that matched."
    )


def test_the_perplexity_adapter_still_declares_both_citation_shapes():
    """The other half of the same finding. If this drops to one selector the fix above is moot, and the two
    shapes are not interchangeable: the spans carry the URL in an attribute and the page can contain no
    anchors at all."""
    adapters = (EXTENSION / "src" / "adapters.js").read_text()
    perplexity = adapters[adapters.index('id: "perplexity"'):]
    perplexity = perplexity[:perplexity.index("},")]
    assert 'a[href^="http"]' in perplexity
    assert "[data-pplx-citation-url]" in perplexity

