/**
 * Per-product DOM adapters.
 *
 * Every adapter carries `verified: false` until it has been run against the real logged-in page and the
 * capture it produced has been checked by eye against the answer on screen. That flag is written into every
 * capture this extension emits, so a capture made with an unverified adapter is labelled as such rather than
 * silently trusted.
 *
 * This matters more than it looks. If a selector misses the citation markers, the pipeline sees an answer
 * with fewer citations than it had, G0 may even pass, and the support rate is computed over a subset of the
 * answer while looking completely normal. A capture bug does not announce itself downstream. It just makes
 * the number wrong.
 *
 * Selectors are lists tried in order, so fixing a product means editing a list rather than the logic.
 */

const SAYSWHO_ADAPTERS = [
  {
    id: "claude",
    verified: false,
    hosts: ["claude.ai"],
    answerSelectors: [
      '[data-testid="assistant-message"]',
      ".font-claude-message",
      '[data-message-author-role="assistant"]',
    ],
    citationSelectors: ['a[href^="http"]'],
  },
  {
    id: "chatgpt",
    verified: false,
    hosts: ["chatgpt.com", "chat.openai.com"],
    answerSelectors: [
      '[data-message-author-role="assistant"]',
      "div.markdown.prose",
    ],
    citationSelectors: ['a[href^="http"]'],
  },
  {
    id: "perplexity",
    verified: false,
    hosts: ["www.perplexity.ai", "perplexity.ai"],
    answerSelectors: [".prose", '[class*="answer"]'],
    citationSelectors: ['a[href^="http"]'],
  },
  {
    id: "google-ai-overviews",
    verified: false,
    hosts: ["www.google.com"],
    answerSelectors: ['[data-attrid*="AIOverview"]', "#rcnt div[data-async-type]"],
    citationSelectors: ['a[href^="http"]'],
  },
];

/** The generic fallback. Used when no product adapter matches, and always marked unverified. */
const SAYSWHO_GENERIC_ADAPTER = {
  id: "generic",
  verified: false,
  hosts: [],
  answerSelectors: ["article", "main", "body"],
  citationSelectors: ['a[href^="http"]'],
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

/**
 * The last answer element on the page, plus which selector found it.
 *
 * Returns null rather than guessing when nothing matches. A wrong container is worse than no container,
 * because it produces a capture that looks fine.
 */
function saysWhoFindAnswer(adapter, root = document) {
  for (const selector of adapter.answerSelectors) {
    let nodes;
    try {
      nodes = root.querySelectorAll(selector);
    } catch {
      continue;
    }
    if (nodes && nodes.length) {
      return { element: nodes[nodes.length - 1], selector, index: nodes.length - 1 };
    }
  }
  return null;
}
