/**
 * The service worker.
 *
 * Takes a capture from the content script, writes it to disk, and records a summary the popup can show.
 * Fetching cited sources and running the judge move here on days 3 and 4, because a content script is
 * subject to the page's CSP and cannot fetch arbitrary cross-origin URLs. That is the whole architectural
 * reason this is an extension and not a web page.
 */

// Storage keys, shared with popup.js and content.js. A test compares the three files, because a typo in
// one of them silently breaks a toggle rather than raising anything.
const SHOW_DOCK_KEY = "sayswho.showDock";
const LAST_CAPTURE_KEY = "sayswho.lastCapture";
const FIRST_RUN_KEY = "sayswho.firstRun";

/**
 * Clicking the toolbar icon opens the popup, which the manifest handles. There is deliberately no
 * `chrome.action.onClicked` listener here: Chrome does not fire it when a popup is set, so keeping the old
 * capture-on-click handler would leave dead code that reads exactly like working code.
 *
 * On install, a badge and a one-time flag. The popup shows its two-paragraph introduction the first time it
 * is opened and clears both. A coach mark pointing at the in-page buttons was the alternative and would
 * have taught nothing: those buttons already name themselves on hover. What a first-time user does not know
 * is that capture needs nothing and verdicts need a terminal, which is a sentence, not an arrow.
 */
chrome.runtime.onInstalled.addListener(({ reason }) => {
  if (reason !== "install") return;
  chrome.storage.local.set({ [FIRST_RUN_KEY]: true, [SHOW_DOCK_KEY]: true });
  chrome.action.setBadgeText({ text: "1" });
  chrome.action.setBadgeBackgroundColor({ color: "#1f6f43" });
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type !== "sayswho:capture") return;

  const capture = message.capture;
  const stamp = capture.captured_at.replace(/[:+]/g, "").replace(/\..*$/, "");
  const filename = `sayswho/capture-${capture.product}-${stamp}.json`;
  const json = JSON.stringify(capture, null, 2);

  // A data URL rather than a blob URL: MV3 service workers have no DOM, so URL.createObjectURL is not
  // available here.
  const url = "data:application/json;base64," + btoa(unescape(encodeURIComponent(json)));

  chrome.downloads.download({ url, filename, saveAs: false }, (id) => {
    if (chrome.runtime.lastError) {
      console.error("SaysWho: download failed", chrome.runtime.lastError.message);
      sendResponse({ ok: false, error: chrome.runtime.lastError.message });
      return;
    }
    console.log(`SaysWho: wrote ${filename} (download ${id})`);

    // A summary for the popup. The in-page toast says all of this and then disappears, and "this capture
    // did not hold the whole answer" is the one thing about a capture that must not be easy to miss.
    chrome.storage.local.set({
      [LAST_CAPTURE_KEY]: {
        product: capture.product,
        captured_at: capture.captured_at,
        answer_sha256: capture.answer_sha256,
        citations: capture.citations.length,
        rendered_chars: capture.rendered_chars,
        dom_chars: capture.dom_chars,
        adapter_verified: capture.adapter_verified,
        incomplete:
          capture.citations_possibly_hidden > 0 ||
          (capture.dom_chars > 0 && capture.dom_chars > capture.rendered_chars * 1.05),
        filename,
      },
    });

    sendResponse({ ok: true, filename });
  });

  return true;
});
