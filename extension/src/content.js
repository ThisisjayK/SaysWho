/**
 * The content script.
 *
 * Capture only, still, and now for a different reason than before. Day 2's reason was that there were no
 * verdicts to show. There are verdicts now, and they are rendered by `report.html` in this extension using
 * the same `render.js` the harness embeds in its standalone report.
 *
 * Two buttons now. "Capture answer" downloads the record for the harness, which is the path that has always
 * worked and needs nothing running. "Audit here" posts the same record to the local server and draws the
 * result in a panel over the page, which removes the terminal step from the loop.
 *
 * Producing a verdict still needs the fetch layer, the gates and the span guard, all of which are Python and
 * stay Python: a JavaScript reimplementation would be a second implementation of the thing the parity check
 * in `SCOPE.md` §9 exists to compare. The second button moves where the audit is *triggered*, not where it
 * is decided.
 *
 * What is still not here is marking the product's own sentences in place. See `audit.js`.
 */

(() => {
  const BUTTON_ID = "sayswho-capture-button";
  if (document.getElementById(BUTTON_ID)) return;

  const adapter = saysWhoAdapterFor(location.hostname);

  const button = document.createElement("button");
  button.id = BUTTON_ID;
  button.type = "button";
  button.textContent = "SaysWho: capture answer";
  button.style.cssText = [
    "position:fixed",
    "right:16px",
    "bottom:16px",
    "z-index:2147483647",
    "padding:8px 12px",
    "font:500 12px/1.2 system-ui,sans-serif",
    "color:#111",
    "background:#f5f3ee",
    "border:1px solid #111",
    "border-radius:6px",
    "cursor:pointer",
  ].join(";");

  const auditButton = document.createElement("button");
  auditButton.id = "sayswho-audit-button";
  auditButton.type = "button";
  auditButton.textContent = "SaysWho: audit here";
  auditButton.style.cssText = button.style.cssText.replace("bottom:16px", "bottom:52px");

  const toast = document.createElement("div");
  toast.style.cssText = [
    "position:fixed",
    "right:16px",
    "bottom:56px",
    "z-index:2147483647",
    "max-width:340px",
    "padding:10px 12px",
    "font:400 12px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace",
    "color:#111",
    "background:#fff",
    "border:1px solid #111",
    "border-radius:6px",
    "white-space:pre-wrap",
    "display:none",
  ].join(";");

  function say(message) {
    toast.textContent = message;
    toast.style.display = "block";
  }

  async function capture() {
    button.textContent = "SaysWho: reading...";
    const found = saysWhoFindAnswer(adapter);

    if (!found) {
      // No container matched. Reporting that plainly beats capturing the whole page and calling it an answer.
      button.textContent = "SaysWho: capture answer";
      say(
        `No answer found on this page.\n\n` +
          `adapter: ${adapter.id}\n` +
          `selectors tried: ${adapter.answerSelectors.join(", ")}\n\n` +
          `The selectors need updating for this product.`
      );
      return;
    }

    const record = await saysWhoBuildCapture({ adapter, found, product: adapter.id });

    console.log(`SaysWho ${record.extension_version} captured ${record.citations.length} citations`);

    if (record.citations.length === 0) {
      say(
        `Captured, but this answer has no citations.\n\n` +
          `G0 will return NO_CITATIONS and refuse to score it.\n` +
          `An uncited answer is not a zero percent answer, it is a different object.\n\n` +
          `adapter: ${record.adapter}\nverified: ${record.adapter_verified}`
      );
    } else {
      say(
        `Captured.  (SaysWho ${record.extension_version})\n\n` +
          `citations: ${record.citations.length}\n` +
          `chars: ${record.rendered_chars} of ${record.dom_chars} in the DOM\n` +
          `chrome links dropped: ${record.chrome_links_excluded}\n` +
          (record.dom_chars > record.rendered_chars * 1.05
            ? `\nINCOMPLETE: ${record.dom_chars - record.rendered_chars} characters are in the page but ` +
              `were never laid out, so they are missing from this capture.\n`
            : "") +
          (record.citations_possibly_hidden
            ? `\nINCOMPLETE: ${record.expanders_seen} "+N" controls hide at least ` +
              `${record.citations_possibly_hidden} more citations.\n` +
              `Expand them and capture again, or this answer is audited over a subset of its sources.\n`
            : "") +
          `sha256: ${record.answer_sha256.slice(0, 16)}...\n` +
          `adapter: ${record.adapter}\n` +
          `verified: ${record.adapter_verified}` +
          (record.adapter_verified
            ? ""
            : `\n\nThis adapter has not been checked against the real page. Compare the capture against\n` +
              `what is on screen before trusting anything computed from it.`)
      );
    }

    button.textContent = "SaysWho: capture answer";
    chrome.runtime.sendMessage({ type: "sayswho:capture", capture: record });
    return record;
  }

  async function auditHere() {
    // The capture is downloaded either way, before anything is posted. If the server is not running, or
    // the audit fails, the record still exists on disk and nothing has been lost.
    const record = await capture();
    if (!record) return;

    auditButton.textContent = "SaysWho: auditing...";
    try {
      await window.saysWhoAudit(record, (status) => {
        auditButton.textContent = `SaysWho: ${status}`;
      });
    } finally {
      auditButton.textContent = "SaysWho: audit here";
    }
  }

  button.addEventListener("click", capture);
  auditButton.addEventListener("click", auditHere);

  // The toolbar icon routes here too, so the icon and the in-page button do the same thing.
  chrome.runtime.onMessage.addListener((message) => {
    if (message?.type === "sayswho:capture-now") capture();
  });

  document.documentElement.appendChild(toast);
  document.documentElement.appendChild(button);
  document.documentElement.appendChild(auditButton);
})();
