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
  const COMMAND = "python3 -m sayswho.server --judge";

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
      $("server-detail").textContent = "Capture still works. For verdicts, start the server:";
      $("cmd-wrap").hidden = false;
      $("audit").disabled = true;
      $("action-note").textContent = "Audit is unavailable until the server is running.";
      return false;
    }

    if (!state.judge) {
      dot.classList.add("partial");
      $("server-state").textContent = "Running, no judge";
      $("server-detail").textContent =
        "It will report which cited pages could be read, and nothing about whether they support anything. " +
        "For verdicts:";
      $("cmd-wrap").hidden = false;
      $("audit").disabled = false;
      $("action-note").textContent = "Audit will check the sources are reachable, and stop there.";
      return true;
    }

    dot.classList.add("ok");
    $("server-state").textContent = "Audit server running";
    $("server-detail").textContent = "Fetch, claim splitting, judge and quoted-passage check all on.";
    $("cmd-wrap").hidden = true;
    $("audit").disabled = false;
    $("action-note").textContent = "";
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

    if (!supported) {
      $("site-product").textContent = "not a supported page";
      $("site-detail").textContent =
        "SaysWho runs on claude.ai, chatgpt.com, perplexity.ai and Google search results.";
      $("capture").disabled = true;
      $("audit").disabled = true;
      return;
    }

    const total = adapter.answerSelectors.length;
    const verified = adapter.verifiedSelectors.length;
    $("site-product").textContent = adapter.id;
    $("site-detail").textContent =
      verified === 0
        ? "No selector here has been checked against a real page, so a capture may be missing citations " +
          "and is labelled unverified."
        : `${verified} of ${total} selectors checked against a real page. A capture through an unchecked ` +
          `one is labelled unverified rather than quietly trusted.`;
    $("capture").disabled = false;
  }

  // ---------------------------------------------------------------- the last capture

  function paintLastCapture(record) {
    if (!record) return;
    $("last").hidden = false;
    $("last-when").textContent = new Date(record.captured_at).toLocaleTimeString();
    $("last-detail").textContent =
      `${record.product}  ${record.citations} citation(s)\n` +
      `${record.rendered_chars} of ${record.dom_chars} characters rendered\n` +
      `sha256 ${String(record.answer_sha256).slice(0, 16)}`;

    const warnings = [];
    if (record.citations === 0) {
      warnings.push("No citations. G0 halts on this answer: it is a different object, not a zero result.");
    }
    if (record.text_incomplete) {
      warnings.push("Part of this answer was never laid out. Scroll to the end and capture again.");
    }
    if (record.citations_hidden) {
      // Not the same problem as truncated text, and not the same fix.
      warnings.push(
        `${record.expanders_seen} "+N" control(s) hide at least ${record.citations_hidden} more ` +
        "citation(s), so this covers a subset of the sources. Expand them and capture again."
      );
    }
    if (!record.adapter_verified) {
      warnings.push("Made with an unchecked selector.");
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
    $("cmd").textContent = COMMAND;

    const stored = await chrome.storage.local.get([SHOW_DOCK_KEY, LAST_CAPTURE_KEY, FIRST_RUN_KEY]);

    $("show-dock").checked = stored[SHOW_DOCK_KEY] !== false;
    $("show-dock").addEventListener("change", (event) => {
      chrome.storage.local.set({ [SHOW_DOCK_KEY]: event.target.checked });
    });

    if (stored[FIRST_RUN_KEY]) {
      $("onboard").hidden = false;
      $("onboard-done").addEventListener("click", () => {
        $("onboard").hidden = true;
        chrome.storage.local.set({ [FIRST_RUN_KEY]: false });
        chrome.action.setBadgeText({ text: "" });
      });
    }

    paintLastCapture(stored[LAST_CAPTURE_KEY]);
    paintSite(await currentTab());
    // The site check can disable Audit on its own, so the server check runs after it and only ever relaxes
    // a state that the page itself allows.
    const up = paintServer(await health());
    if ($("capture").disabled) $("audit").disabled = true;
    else if (!up) $("audit").disabled = true;

    $("copy").addEventListener("click", async () => {
      await navigator.clipboard.writeText(COMMAND);
      $("copy").textContent = "copied";
      setTimeout(() => ($("copy").textContent = "copy"), 1200);
    });

    $("capture").addEventListener("click", () => send("sayswho:capture-now"));
    $("audit").addEventListener("click", () => send("sayswho:audit-now"));
  }

  main();
})();
