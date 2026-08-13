/**
 * Building a capture record.
 *
 * The output of this file has to deserialise into `sayswho.records.Capture` unchanged, and the hash it
 * computes has to equal the one Python computes over the same text. That is not a nicety: `SCOPE.md` §9
 * requires the extension and the harness to produce identical verdicts on identical inputs, and they cannot
 * do that if they disagree about what the input was.
 *
 * So the hash is sha256 over the UTF-8 bytes of `answer_text`, exactly as `records.sha256` does it, and the
 * Python loader recomputes it on load and rejects any capture whose recorded hash does not match.
 */

async function saysWhoSha256Hex(text) {
  const bytes = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

/**
 * Citation markers and their URLs, in document order.
 *
 * `marker` is the visible text of the link where there is any, because that is what the reader sees next to
 * the sentence. Where a citation is an icon with no text, the marker falls back to its position, which is
 * recorded honestly as a positional marker rather than dressed up as a footnote number.
 */
function saysWhoExtractCitations(adapter, element) {
  const citations = [];
  const excluded = [];
  const seen = new Set();

  for (const selector of adapter.citationSelectors) {
    let found;
    try {
      found = element.querySelectorAll(selector);
    } catch {
      continue;
    }
    for (const anchor of found) {
      // Not `anchor.href`: on Perplexity a citation is a span carrying the URL in an attribute, and there
      // is no anchor on the page at all. One helper, shared with the counter that ranks containers, so the
      // two cannot disagree about what a citation is. See adapters.js.
      const url = saysWhoCitationUrl(anchor, adapter);
      if (!url || !/^https?:/i.test(url)) continue;

      // Page furniture: the "Claude is AI and can make mistakes" link, product help pages, same-origin
      // navigation. Excluded, and counted, so the exclusion is visible rather than silent.
      if (saysWhoIsChrome(url, adapter.excludeHosts)) {
        excluded.push(url);
        continue;
      }

      // "Massachusetts Government\n+1" is one visible chip plus a control meaning "and 1 more source".
      // The newline and the +1 are UI, not part of the marker the reader sees beside the sentence.
      const label = (anchor.innerText || anchor.textContent || "")
        .replace(/\s*\+\d+\s*$/, "")
        .replace(/\s+/g, " ")
        .trim();
      const marker = label.length > 0 && label.length <= 40 ? label : `[pos:${citations.length + 1}]`;
      const key = `${marker}|${url}`;
      if (seen.has(key)) continue;

      seen.add(key);
      citations.push({ marker, url });
    }
    // No `break` here, and the one that used to be is worth a note, because it cost a quarter of the
    // citations in the first real run against the consumer stratum.
    //
    // It read `if (citations.length) break;`, meaning the first selector that matched anything won and the
    // rest were never scanned. Perplexity declares two, `a[href^="http"]` and `[data-pplx-citation-url]`, and
    // renders both shapes in one answer: 13 of 51 inline citations across 24 answers were of the second kind
    // and behind a selector that never ran. The capture looked entirely normal, since what it did find was
    // real.
    //
    // The union is safe because `seen` is keyed on marker and URL together, so a citation matching two
    // selectors is added once. That was already true when the break was written, which means the break was
    // never protecting anything. `sayswho/reextract.py` walks the tree once and takes the union, and the
    // disagreement between the two is what surfaced this.
  }

  return { citations, excluded };
}

/**
 * Citations the page is admitting to and hiding.
 *
 * Both ChatGPT and Perplexity collapse extra sources behind a "+N" control next to a visible chip. Those
 * sources are real citations that the DOM does not expose until the control is used, so a capture taken
 * without expanding them is short by at least the sum of the Ns.
 *
 * This has to be counted rather than ignored. A capture that is quietly short computes a support rate over
 * a subset of the answer and looks completely normal doing it, which is the one failure a citation auditor
 * cannot afford to have.
 *
 * The number is a floor. It counts what the expanders admit to, not what is actually behind them.
 */
function saysWhoCountHiddenCitations(element) {
  let expanders = 0;
  let hidden = 0;

  for (const node of element.querySelectorAll("*")) {
    if (node.children.length) continue;
    const text = (node.textContent || "").trim();
    const match = /^\+(\d{1,3})$/.exec(text);
    if (!match) continue;
    expanders += 1;
    hidden += parseInt(match[1], 10);
  }

  return { expanders, hidden };
}

/**
 * Scroll the answer through the viewport so the browser lays all of it out.
 *
 * A long answer is not fully in the DOM until it has been on screen. Products either keep only the visible
 * part rendered or mark off-screen sections so layout is skipped, and `innerText` reads what was laid out.
 * Text you have not scrolled to is not there to read.
 *
 * Left to the user this becomes "remember to scroll before capturing", and a capture taken without
 * scrolling is short, parses cleanly, and looks entirely normal. The extension does the scrolling instead,
 * and puts the scroll position back where it found it.
 */
function saysWhoScroller(element) {
  let node = element;
  while (node && node !== document.body) {
    const style = getComputedStyle(node);
    const scrolls = /auto|scroll|overlay/.test(style.overflowY);
    if (scrolls && node.scrollHeight > node.clientHeight + 40) return node;
    node = node.parentElement;
  }
  return document.scrollingElement || document.documentElement;
}

async function saysWhoForceRender(element) {
  const scroller = saysWhoScroller(element);
  if (!scroller) return;

  const original = scroller.scrollTop;
  const step = Math.max(200, scroller.clientHeight * 0.8);

  for (let y = 0; y <= scroller.scrollHeight; y += step) {
    scroller.scrollTop = y;
    await new Promise((r) => setTimeout(r, 50));
  }
  scroller.scrollTop = scroller.scrollHeight;
  await new Promise((r) => setTimeout(r, 150));

  scroller.scrollTop = original;
  await new Promise((r) => setTimeout(r, 100));
}

/**
 * Answer text as rendered.
 *
 * `innerText` rather than `textContent`, because textContent includes text from hidden elements and drops
 * the line breaks a reader actually sees. The captured text is what was on screen, since that is the thing
 * the reader trusted.
 */
function saysWhoAnswerText(element) {
  return (element.innerText || "").replace(/\r\n/g, "\n").trim();
}

/**
 * Download the page as it stood at capture time.
 *
 * Written from the content script rather than the service worker, because a service worker cannot resolve a
 * blob URL created in a page and a multi-megabyte data URL is not a reasonable thing to hand the downloads
 * API.
 *
 * The stored page is a record, not a publication. It contains the whole application shell, which on
 * claude.ai includes the sidebar and therefore the titles of every other conversation. Those are real
 * queries from real work, which DATA_CONTRACT.md §9 says get scrubbed before anything is committed. The
 * repo gitignores these files and they never leave the machine.
 */
function saysWhoDownloadPage(filename) {
  const html = "<!doctype html>\n" + document.documentElement.outerHTML;
  const blob = new Blob([html], { type: "text/html" });
  const url = URL.createObjectURL(blob);

  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30000);

  return html.length;
}

async function saysWhoBuildCapture({ adapter, found, product, modelId, queryId }) {
  await saysWhoForceRender(found.element);

  const answerText = saysWhoAnswerText(found.element);

  // innerText is what was laid out. textContent is what is in the DOM whether laid out or not. A large gap
  // between them means the browser skipped rendering part of the answer and the capture is short, so the
  // numbers are recorded and the gap is reported rather than left to be noticed later.
  //
  // Whitespace is removed from both rather than collapsed, which is not fussiness. innerText inserts
  // separators that textContent has no equivalent for: between two table cells textContent yields "ab"
  // and innerText yields "a\tb". On a Perplexity answer containing a table that produced 7912 rendered
  // characters against 7835 in the DOM, a subset larger than the set it came from, which reads as a bug
  // and, worse, means the gap could be inflated past a real one and hide it. Comparing the two counts only
  // means anything if they count the same thing.
  const withoutSpace = (value) => (value || "").replace(/\s+/g, "");
  const domChars = withoutSpace(found.element.textContent).length;
  const renderedChars = withoutSpace(answerText).length;
  const { citations, excluded } = saysWhoExtractCitations(adapter, found.element);
  const { expanders, hidden } = saysWhoCountHiddenCitations(found.element);
  const now = new Date().toISOString().replace(/\.\d{3}Z$/, "+00:00");
  const stamp = now.replace(/[:+]/g, "").replace(/\..*$/, "");
  const pageFile = `sayswho-page-${product || adapter.id}-${stamp}.html`;
  const pageBytes = saysWhoDownloadPage(pageFile);

  return {
    query_id: queryId || "UNASSIGNED",
    product: product || adapter.id,
    model_id: modelId || "unknown",
    // The page does not tell us when the answer was generated. Capture time is the closest honest proxy and
    // it is labelled as capture time, not as generation time, everywhere it is used.
    generated_at: now,
    captured_at: now,
    source: "dom",
    // Which build produced this capture. A capture with no version, or an old one, was made by a stale
    // content script: Chrome keeps running the old code in already-open tabs until the page is reloaded.
    // Two captures that differ only because the extension changed underneath them are not comparable.
    extension_version: (chrome.runtime.getManifest && chrome.runtime.getManifest().version) || "unknown",
    adapter: `${adapter.id}:${found.selector}`,
    // True only when the selector that actually produced this capture has been checked against the screen.
    adapter_verified: (adapter.verifiedSelectors || []).indexOf(found.selector) >= 0,
    // How many links in the answer were dropped as page furniture. Published rather than hidden: if this
    // number is large, the exclusion list is eating real citations.
    chrome_links_excluded: excluded.length,
    // Citations the page showed behind a "+N" control and this capture did not reach. A floor.
    citations_possibly_hidden: hidden,
    expanders_seen: expanders,
    // Characters laid out versus characters present in the DOM. A shortfall means unrendered text.
    rendered_chars: renderedChars,
    dom_chars: domChars,
    // The page as it stood, saved next to this record so a selector fix can be re-run over the same bytes
    // instead of re-running the query and getting a different answer.
    page_file: pageFile,
    page_bytes: pageBytes,
    answer_text: answerText,
    answer_sha256: await saysWhoSha256Hex(answerText),
    citations,
  };
}
