/**
 * The content script.
 *
 * Day 2 scope is capture only. There is no marking yet, because there are no verdicts yet: Phase 1 and
 * Phase 3 arrive on day 3. Shipping a marking UI before there is anything behind it would produce exactly
 * the finding-shaped output this project exists to refuse.
 *
 * So the button captures the last answer on the page and hands the JSON to the harness. Nothing on screen
 * claims anything about whether a citation holds up.
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

  button.addEventListener("click", async () => {
    const found = saysWhoFindAnswer(adapter);

    if (!found) {
      // No container matched. Reporting that plainly beats capturing the whole page and calling it an answer.
      say(
        `No answer found on this page.\n\n` +
          `adapter: ${adapter.id}\n` +
          `selectors tried: ${adapter.answerSelectors.join(", ")}\n\n` +
          `The selectors need updating for this product.`
      );
      return;
    }

    const capture = await saysWhoBuildCapture({ adapter, found, product: adapter.id });

    if (capture.citations.length === 0) {
      say(
        `Captured, but this answer has no citations.\n\n` +
          `G0 will return NO_CITATIONS and refuse to score it.\n` +
          `An uncited answer is not a zero percent answer, it is a different object.\n\n` +
          `adapter: ${capture.adapter}\nverified: ${capture.adapter_verified}`
      );
    } else {
      say(
        `Captured.\n\n` +
          `citations: ${capture.citations.length}\n` +
          `chars: ${capture.answer_text.length}\n` +
          `sha256: ${capture.answer_sha256.slice(0, 16)}...\n` +
          `adapter: ${capture.adapter}\n` +
          `verified: ${capture.adapter_verified}` +
          (capture.adapter_verified
            ? ""
            : `\n\nThis adapter has not been checked against the real page. Compare the capture against\n` +
              `what is on screen before trusting anything computed from it.`)
      );
    }

    chrome.runtime.sendMessage({ type: "sayswho:capture", capture });
  });

  document.documentElement.appendChild(toast);
  document.documentElement.appendChild(button);
})();
