/**
 * The content script.
 *
 * Capture only, still, and now for a different reason than before. Day 2's reason was that there were no
 * verdicts to show. There are verdicts now, and they are rendered by `report.html` in this extension using
 * the same `render.js` the harness embeds in its standalone report.
 *
 * What is not here is marking on claude.ai itself, and that is a limitation rather than a decision made and
 * finished. Producing a verdict needs the fetch layer, the gates and the span guard, all of which are Python
 * and stay Python: a JavaScript reimplementation would be a second implementation of the thing the parity
 * check in `SCOPE.md` §9 exists to compare. So the extension captures and renders, and the audit runs
 * locally in between.
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
  }

  button.addEventListener("click", capture);

  // The toolbar icon routes here too, so the icon and the in-page button do the same thing.
  chrome.runtime.onMessage.addListener((message) => {
    if (message?.type === "sayswho:capture-now") capture();
  });

  document.documentElement.appendChild(toast);
  document.documentElement.appendChild(button);
})();
