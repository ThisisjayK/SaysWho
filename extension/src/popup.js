/**
 * The popup: a control surface.
 *
 * It answers two questions and nothing else. Is this ready to run, and what do I do next. Results go to the
 * panel on the page, because a popup closes the moment focus leaves it and an audit is something you read
 * rather than glance at.
 *
 * **Nothing here decides anything either.** Same rule as `audit.js`. This file reads a health endpoint,
 * reads two values out of storage, and sends two messages. Every verdict, every denominator and every
 * refusal is Python.
 *
 * **The indicator has three states, not two.** `/health` reports whether a judge is configured, and a
 * server running without one is up and cannot produce a single verdict. Painting that green would be the
 * same error this project spends its whole design avoiding: collapsing "we checked" into "we could not
 * check". So: off, running-without-a-judge, and running-with-one.
 */

(() => {
  const ENDPOINT = "http://127.0.0.1:8765";

  // The commands, and there are two of them because the two states need different work.
  //
  // This used to be one line, `python3 -m sayswho.server --judge`, and it did not work. The judge client is
  // the one dependency this project has, so a bare `python3` on a fresh clone fails on a missing module
  // rather than starting. `README.md` has always said venv, install, key, run. The popup said something
  // shorter that read like the same instruction, which is the worse kind of wrong: it looks runnable.
  //
  // Split by state, because a server that is already up does not need its virtualenv rebuilt. It needs a
  // key and a restart, and telling somebody to reinstall to fix a missing key is how a two-minute problem
  // becomes a twenty-minute one.
  const SETUP_COMMAND = [
    "python3 -m venv .venv && .venv/bin/pip install google-genai",
    "export GEMINI_API_KEY=your-key-here",
    ".venv/bin/python -m sayswho.server --judge",
  ].join("\n");

  const JUDGE_COMMAND = [
    "export GEMINI_API_KEY=your-key-here",
    ".venv/bin/python -m sayswho.server --judge",
  ].join("\n");

  // Storage keys. Shared with content.js and background.js, and there is a test that compares the three
  // files, because a typo in one of them silently breaks a toggle rather than raising anything.
  const SHOW_DOCK_KEY = "sayswho.showDock";
  const LAST_CAPTURE_KEY = "sayswho.lastCapture";
  const FIRST_RUN_KEY = "sayswho.firstRun";

  const $ = (id) => document.getElementById(id);

  // ---------------------------------------------------------------- the server

  async function health() {
    // A short timeout: a port that accepts and never answers would otherwise leave this window blank, and
    // "still checking" reads as broken.
    const stop = new AbortController();
    const timer = setTimeout(() => stop.abort(), 1200);
    try {
      const response = await fetch(`${ENDPOINT}/health`, { signal: stop.signal });
      if (!response.ok) return null;
      return await response.json();
    } catch (err) {
      return null;
    } finally {
      clearTimeout(timer);
    }
  }

  function paintServer(state) {
    const dot = $("dot");
    dot.className = "dot";

    if (state === null) {
      $("server-state").textContent = "Audit server not running";
      $("cmd").textContent = SETUP_COMMAND;
      $("cmd-wrap").hidden = false;
      $("audit").disabled = true;
      return false;
    }

    if (!state.judge) {
      dot.classList.add("partial");
      $("server-state").textContent = "Running, no judge";
      $("cmd").textContent = JUDGE_COMMAND;
      $("cmd-wrap").hidden = false;
      $("audit").disabled = false;
      return true;
    }

    dot.classList.add("ok");
    $("server-state").textContent = "Audit server running";
    // Nothing to say when it is working. A line reading "all systems on" makes a small window feel busy
    // without telling anybody anything they can act on.
    $("cmd-wrap").hidden = true;
    $("audit").disabled = false;
    return true;
  }

  // ---------------------------------------------------------------- this page

  async function currentTab() {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    return tab || null;
  }

  function paintSite(tab) {
    let host = "";
    try {
      host = new URL(tab?.url || "").hostname;
    } catch (err) {
      host = "";
    }

    const adapter = host ? saysWhoAdapterFor(host) : null;
    const supported = adapter && adapter.id !== "generic";

    // The page gets one line and only when it is a problem. A supported page needs no commentary: the
    // buttons being enabled says it. What still has to be said is why a button is dead, because a disabled
    // control with no reason is the thing people file bugs about.
    if (!supported) {
      $("action-note").textContent =
        "Not a page SaysWho reads. Works on claude.ai, chatgpt.com, perplexity.ai and Google AI Overviews.";
      $("capture").disabled = true;
      $("audit").disabled = true;
      return;
    }

    $("action-note").textContent = "";
    $("capture").disabled = false;
  }

  // ---------------------------------------------------------------- the last capture

  function paintLastCapture(record) {
    if (!record) return;
    $("last").hidden = false;
    $("last-when").textContent = new Date(record.captured_at).toLocaleTimeString();
    // One line rather than three. The hash and the character counts were the two least actionable things
    // in this window: nobody reads a sha256 off a popup, and the rendered-versus-DOM comparison already
    // speaks through the warning below when it matters.
    $("last-detail").textContent = `${record.product} · ${record.citations} citations`;

    const warnings = [];
    if (record.citations === 0) {
      warnings.push("No citations, so G0 halts on this answer.");
    }
    if (record.text_incomplete) {
      warnings.push("Answer partly unrendered. Scroll to the end and capture again.");
    }
    if (record.citations_hidden) {
      // Not the same problem as truncated text, and not the same fix.
      warnings.push(
        `${record.expanders_seen} "+N" control(s) hide ${record.citations_hidden}+ citations. ` +
        "Expand them and capture again."
      );
    }
    if (!record.adapter_verified) {
      warnings.push("Unchecked selector.");
    }
    $("last-warning").hidden = warnings.length === 0;
    $("last-warning").textContent = warnings.join(" ");
  }

  // ---------------------------------------------------------------- wiring

  async function send(type) {
    const tab = await currentTab();
    if (!tab?.id) return;
    try {
      await chrome.tabs.sendMessage(tab.id, { type });
      // The work continues in the page. This window is about to close, which is exactly why the result was
      // never going to live here.
      window.close();
    } catch (err) {
      $("action-note").textContent =
        "The page has not loaded SaysWho yet. Reload the tab and try again.";
    }
  }

  async function main() {
    $("version").textContent = `v${chrome.runtime.getManifest().version}`;

    const stored = await chrome.storage.local.get([SHOW_DOCK_KEY, LAST_CAPTURE_KEY, FIRST_RUN_KEY]);

    $("show-dock").checked = stored[SHOW_DOCK_KEY] !== false;
    $("show-dock").addEventListener("change", (event) => {
      chrome.storage.local.set({ [SHOW_DOCK_KEY]: event.target.checked });
    });

    // The install badge clears the first time this window is opened. There used to be an explainer panel
    // here that had to be dismissed; opening the popup is the same signal and costs the reader nothing.
    if (stored[FIRST_RUN_KEY]) {
      chrome.storage.local.set({ [FIRST_RUN_KEY]: false });
      chrome.action.setBadgeText({ text: "" });
    }

    paintLastCapture(stored[LAST_CAPTURE_KEY]);
    paintSite(await currentTab());
    // The site check can disable Audit on its own, so the server check runs after it and only ever relaxes
    // a state that the page itself allows.
    const up = paintServer(await health());
    if ($("capture").disabled) $("audit").disabled = true;
    else if (!up) $("audit").disabled = true;

    $("copy").addEventListener("click", async () => {
      // Whatever is on screen, which is why this reads the element rather than a constant: the two states
      // show different commands and copying the wrong one is worse than not offering the button.
      await navigator.clipboard.writeText($("cmd").textContent);
      $("copy").textContent = "Copied";
      setTimeout(() => ($("copy").textContent = "Copy"), 1200);
    });

    $("capture").addEventListener("click", () => send("sayswho:capture-now"));
    $("audit").addEventListener("click", () => send("sayswho:audit-now"));
  }

  main();
})();
