/**
 * The service worker.
 *
 * Day 2 scope: take a capture from the content script and write it to disk, so it can be fed to the harness.
 * Fetching cited sources and running the judge move here on days 3 and 4, because a content script is
 * subject to the page's CSP and cannot fetch arbitrary cross-origin URLs. That is the whole architectural
 * reason this is an extension and not a web page.
 */

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
    sendResponse({ ok: true, filename });
  });

  return true;
});
