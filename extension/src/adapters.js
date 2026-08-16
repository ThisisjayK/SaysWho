/**
 * Per-product DOM adapters.
 *
 * Every adapter carries `verified` until it has been run against the real logged-in page and the capture it
 * produced has been checked by eye against the answer on screen. That flag is written into every capture this
 * extension emits, so a capture made with an unverified adapter is labelled as such rather than silently
 * trusted.
 *
 * This matters more than it looks. If a selector misses the citation markers, the pipeline sees an answer
 * with fewer citations than it had, G0 may even pass, and the support rate is computed over a subset of the
 * answer while looking completely normal. A capture bug does not announce itself downstream. It just makes
 * the number wrong.
 */

/** Links that are page furniture rather than citations. Excluded, and counted so the exclusion is visible. */
const SAYSWHO_CHROME_HOSTS = [
  "support.anthropic.com",
  "claude.ai",
  "chatgpt.com",
  "chat.openai.com",
  "help.openai.com",
  "www.perplexity.ai",
  "perplexity.ai",
  "policies.google.com",
  "support.google.com",
  "accounts.google.com",
];

const SAYSWHO_ADAPTERS = [
  {
    id: "claude",
    hosts: ["claude.ai"],
    // Verification is per selector, not per adapter. Exercising one path says nothing about the other, and
    // a capture is only as trustworthy as the selector that produced it.
    //
    // .bg-surface-3 .standard-markdown, verified 2026-08-08: captured a Research report, read the text end
    // to end against the screen, confirmed it starts at the title and ends at the last caveat, confirmed
    // the single citation against a DOM probe showing two external anchors on the whole page of which one
    // was the support-link furniture, and confirmed re-extraction from the stored page yields the same
    // citation set.
    verifiedSelectors: [".bg-surface-3 .standard-markdown"],
    answerSelectors: [
      // The artifact panel, where a Research report lives. Listed first because when it is open it holds
      // the cited content and the chat message beside it holds only a summary.
      ".bg-surface-3 .standard-markdown",
      // An ordinary assistant turn in the chat column.
      ".font-claude-response",
      "[data-testid='chat-stale-nav-inert'] .standard-markdown",
    ],
    citationSelectors: ['a[href^="http"]'],
    excludeHosts: SAYSWHO_CHROME_HOSTS,
  },
  {
    id: "chatgpt",
    // Verified 2026-08-16 against the ten stored pages behind the day 9 gold set, which is ten answers
    // rather than the one the Claude row was verified on. Three checks, each over all ten:
    //
    //   1. Every external anchor on the whole page is inside the chosen container. 0 outside, across all
    //      ten, so the selector is neither missing a rendered citation nor picking up chrome furniture.
    //      This is the check that could have failed and the reason the other two are worth anything.
    //   2. Exactly one [data-message-author-role="assistant"] node per page, its text starting where the
    //      captured answer starts and ending where it ends, with the user's own turn outside it.
    //   3. Re-extraction from the stored bytes yields the identical citation set, 10 of 10, via
    //      `python3 -m sayswho.reextract <page> --capture <capture>`. Weakest of the three on its own,
    //      since both sides run this same selector list, which is why check 1 carries the argument.
    //
    // **This verifies the selector, not the completeness of the capture.** ChatGPT collapses part of its
    // citation list behind "+N" controls and those sources are never in the DOM, so the pages hold 33
    // citations and at least 20 more were never rendered. Check 1 confirms that is the product's behaviour
    // rather than this selector's fault: there was nothing on the page left to find. `citations_hidden`
    // travels with every capture and warns separately, and FINDINGS.md item 23 carries the limitation.
    //
    // Not retroactive. The ten day 9 captures were written with adapter_verified false and still say so,
    // because that is what was true when they were made, and the gold set built on them inherits it.
    verifiedSelectors: ['[data-message-author-role="assistant"]'],
    hosts: ["chatgpt.com", "chat.openai.com"],
    answerSelectors: [
      '[data-message-author-role="assistant"]',
      "div.markdown.prose",
    ],
    citationSelectors: ['a[href^="http"]'],
    excludeHosts: SAYSWHO_CHROME_HOSTS,
  },
  {
    id: "perplexity",
    // Still unverified, and now for a much narrower reason than before. The citation mechanism is
    // established: probed against a live answer page on 2026-08-11, `.prose` was the only match on the
    // page and held all five citations, every one of them a span carrying an absolute URL in
    // `data-pplx-citation-url`, and the document contained no `<a href>` at all.
    //
    // What has not been done is the rest of what verification means here: reading a captured answer end to
    // end against the screen on a logged-in page, and seeing what the "+N" chip does when one sentence
    // cites several sources. Until both, a capture from this adapter is labelled unverified.
    verifiedSelectors: [],
    hosts: ["www.perplexity.ai", "perplexity.ai"],
    answerSelectors: [".prose", '[class*="answer"]'],
    // Anchors first, because Perplexity may go back to them, and a real anchor is better evidence than an
    // attribute. The data attribute is the fallback that actually fires today.
    citationSelectors: ['a[href^="http"]', "[data-pplx-citation-url]"],
    citationUrlAttrs: ["data-pplx-citation-url"],
    excludeHosts: SAYSWHO_CHROME_HOSTS,
  },
  {
    id: "google-ai-overviews",
    verifiedSelectors: [],
    hosts: ["www.google.com"],
    answerSelectors: ['[data-attrid*="AIOverview"]', "#rcnt div[data-async-type]"],
    citationSelectors: ['a[href^="http"]'],
    excludeHosts: SAYSWHO_CHROME_HOSTS,
  },
];

/** The generic fallback. Used when no product adapter matches, and always unverified. */
const SAYSWHO_GENERIC_ADAPTER = {
  id: "generic",
  verifiedSelectors: [],
  hosts: [],
  answerSelectors: ["article", "main", "body"],
  citationSelectors: ['a[href^="http"]'],
  excludeHosts: SAYSWHO_CHROME_HOSTS,
};

function saysWhoAdapterFor(hostname) {
  const host = String(hostname).toLowerCase();
  for (const adapter of SAYSWHO_ADAPTERS) {
    if (adapter.hosts.some((h) => host === h || host.endsWith(`.${h}`))) {
      return adapter;
    }
  }
  return SAYSWHO_GENERIC_ADAPTER;
}

function saysWhoIsChrome(url, excludeHosts) {
  try {
    return (excludeHosts || []).includes(new URL(url).hostname.toLowerCase());
  } catch {
    return true;
  }
}

/**
 * The URL a citation element points at, whether or not it is a link.
 *
 * Perplexity renders every inline citation as
 * `<span class="citation inline" data-pplx-citation-url="https://...">`, with no anchor anywhere on the
 * page. Probed against a live answer on 2026-08-11: five citations in the answer, five spans carrying the
 * attribute, zero `<a href>` elements in the entire document. So an extractor that only knows about
 * anchors does not find "roughly a third" of Perplexity's citations. It finds none of them, and reports a
 * clean capture with zero citations, which G0 then treats as an uncited answer.
 *
 * One function, used by the counter below and by the extractor in capture.js, because container selection
 * ranks containers by citation count and the two disagreeing would pick the wrong container.
 */
function saysWhoCitationUrl(element, adapter) {
  if (element.href) return element.href;
  for (const attr of adapter.citationUrlAttrs || []) {
    const value = element.getAttribute && element.getAttribute(attr);
    if (value && /^https?:\/\//i.test(value)) return value;
  }
  return "";
}

function saysWhoCountCitations(element, adapter) {
  let count = 0;
  for (const selector of adapter.citationSelectors) {
    let found;
    try {
      found = element.querySelectorAll(selector);
    } catch {
      continue;
    }
    for (const node of found) {
      const url = saysWhoCitationUrl(node, adapter);
      if (url && !saysWhoIsChrome(url, adapter.excludeHosts)) count += 1;
    }
    if (count) break;
  }
  return count;
}

/**
 * The answer element, chosen by how many citations it contains rather than by selector order.
 *
 * Order alone was wrong on Claude: with the artifact panel open, both the chat summary and the report match
 * a selector, and only one of them holds the citations. Picking by citation count gets the container that
 * actually has something to audit, and falls back to the longest text when nothing is cited, so an
 * uncited answer still reaches G0 and gets refused there rather than here.
 *
 * Returns null when nothing matches. A wrong container is worse than no container, because it produces a
 * capture that looks fine.
 */
function saysWhoFindAnswer(adapter, root = document) {
  const candidates = [];

  for (const selector of adapter.answerSelectors) {
    let nodes;
    try {
      nodes = root.querySelectorAll(selector);
    } catch {
      continue;
    }
    for (let i = 0; i < nodes.length; i++) {
      const element = nodes[i];
      const text = (element.innerText || "").trim();
      if (!text) continue;
      candidates.push({
        element,
        selector,
        index: i,
        citations: saysWhoCountCitations(element, adapter),
        length: text.length,
      });
    }
  }

  if (!candidates.length) return null;

  candidates.sort((a, b) => b.citations - a.citations || b.length - a.length);
  return candidates[0];
}
