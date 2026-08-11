/**
 * The marking view. One renderer, two surfaces.
 *
 * The harness embeds this file into a standalone HTML report; the extension's report page loads the same
 * file and calls the same function. `SCOPE.md` §9 requires the extension and the harness to agree, and the
 * cheapest way to guarantee that for the view is to have one of it.
 *
 * This file decides nothing. Every state, every offset and every label arrives in the payload already
 * computed by `sayswho/report.py`. If this file started deriving a verdict, there would be two
 * implementations of the thing the parity check exists to compare.
 */

(function () {
  "use strict";

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  /** Verdict names as the reader sees them. The record keeps the raw code; this is only the surface. */
  const VERDICT_WORDS = {
    SUPPORTED: "states this",
    PARTIALLY_SUPPORTED: "states part of this",
    NOT_FOUND_IN_SOURCE: "does not state this",
    CONTRADICTED: "states the opposite",
  };

  /** Why a verdict was thrown out. Each of these means no verdict, never a weaker one. */
  const VOID_WORDS = {
    JUDGE_FABRICATED_SPAN:
      "The quote the judge gave is not on the page, so the verdict was thrown out. Nothing here says " +
      "the claim is wrong.",
    SPAN_ADDED_AFTER_GENERATION:
      "The quoted passage was added to the page after this answer was written, so the model could not " +
      "have read it.",
    EXTRACTION_SUSPECT:
      "This claim's own numbers appear in the page but not in the text we managed to extract, so our " +
      "reader is the likelier failure, not the source.",
    JUDGE_REFUSED: "The judge declined to answer, so this claim was not scored.",
  };

  /** Why a source could not be read. Never phrased as a fact about the claim. */
  const SOURCE_WORDS = {
    SOURCE_UNREACHABLE: "the page could not be fetched",
    SOURCE_DEAD_LINK: "the link is dead: the server says there is no such page",
    SOURCE_BOT_BLOCKED: "the site refused an automated request. Clicking the link yourself may well work",
    SOURCE_EMPTY: "the page returned no readable text",
    SOURCE_PAYWALLED: "a paywall or consent wall blocked the text",
    SOURCE_ROBOTS_EXCLUDED: "robots.txt asked us not to fetch it, so we did not",
    SOURCE_NOT_HTML: "the citation is in a format this tool cannot read",
    SOURCE_NO_TEXT_LAYER:
      "the citation is a scan or a picture, so its words are in an image and cannot be read here. " +
      "Opening it yourself may well show the passage",
    SOURCE_UNREADABLE_ENCODING:
      "the document has a text layer this tool could not decode, which is a limitation here rather than a " +
      "problem with the source",
    SOURCE_DRIFTED: "the page is no longer the document that was cited",
  };

  function sourceRow(row, labels) {
    const wrap = el("div", "sw-source");
    wrap.appendChild(el("span", "sw-url", row.url));

    if (row.source_code && row.source_code !== "SOURCE_OK") {
      wrap.appendChild(
        el("div", "sw-verdict", "Could not read this source: " + (SOURCE_WORDS[row.source_code] || row.source_code))
      );
      if (row.source_detail) wrap.appendChild(el("div", "sw-note", row.source_detail));
      return wrap;
    }

    if (!row.judged) {
      wrap.appendChild(el("div", "sw-verdict", "Not judged."));
      return wrap;
    }

    if (row.voided) {
      wrap.appendChild(el("div", "sw-void", "No verdict."));
      wrap.appendChild(el("div", "sw-note", VOID_WORDS[row.void_reason] || row.void_reason));
      return wrap;
    }

    wrap.appendChild(el("div", "sw-verdict", "This source " + (VERDICT_WORDS[row.verdict] || row.verdict) + "."));

    // What the source attaches that the claim does not. "States part of this" without saying which part
    // hands the checking work back to the reader, which is the same failure as a 500-character span.
    if (row.missing_qualifiers && row.missing_qualifiers.length) {
      const list = el("ul", "sw-qualifiers");
      list.appendChild(el("li", "sw-qualifiers-head", "The source also says:"));
      row.missing_qualifiers.forEach(function (q) {
        list.appendChild(el("li", null, q));
      });
      wrap.appendChild(list);
    } else if (row.partial_without_qualifiers) {
      wrap.appendChild(
        el("div", "sw-note",
          "The judge did not say which part is unsupported, so this verdict is weaker than it looks. " +
          "Counted and reported as such.")
      );
    }

    if (row.span) {
      // The span guard already confirmed this string is present in the fetched page, so quoting it here
      // cannot show the reader a sentence the source does not contain.
      //
      // The whole span is always shown. `span_focus` arrives from report.py and marks the sentence that
      // bears on the claim, because the judge quotes generously and a 500-character span with "Like us on
      // Facebook" in it hands the checking job back to the reader. Nothing is truncated: a shortened span
      // is not evidence.
      const quote = el("blockquote", "sw-span");
      const focus = row.span_focus;
      if (focus && focus.length === 2) {
        quote.appendChild(document.createTextNode(row.span.slice(0, focus[0])));
        quote.appendChild(el("b", "sw-focus", row.span.slice(focus[0], focus[1])));
        quote.appendChild(document.createTextNode(row.span.slice(focus[1])));
      } else {
        quote.textContent = row.span;
      }
      wrap.appendChild(quote);
      if (row.span_predates_generation === null) {
        wrap.appendChild(
          el("div", "sw-note", "No archived copy of this page from around the time the answer was written, " +
            "so we cannot tell whether this passage was there then.")
        );
      }
    }
    return wrap;
  }

  function card(claim, payload) {
    const box = el("div", "sw-card");
    box.appendChild(el("h3", null, payload.labels[claim.state] || claim.state));
    box.appendChild(el("p", "sw-help", payload.help[claim.state] || ""));

    if (!claim.sources.length) {
      box.appendChild(el("div", "sw-note", "This sentence carries no citation."));
    }
    claim.sources.forEach(function (row) {
      box.appendChild(sourceRow(row, payload.labels));
    });

    box.appendChild(el("div", "sw-note", "Claim id " + claim.id + ". Claim splitting and the verdict are model inference."));
    return box;
  }

  /** Place the card near its mark and keep it inside the viewport. */
  function position(box, mark, host) {
    const m = mark.getBoundingClientRect();
    const h = host.getBoundingClientRect();
    box.style.left = "0px";
    box.style.top = "0px";
    const width = box.offsetWidth;
    let left = m.left - h.left;
    if (left + width > host.clientWidth) left = Math.max(0, host.clientWidth - width);
    box.style.left = left + "px";
    box.style.top = m.bottom - h.top + 6 + "px";
  }

  function markedAnswer(payload) {
    const host = el("div", "sw-answer");
    host.style.position = "relative";

    const located = payload.claims
      .filter(function (c) { return c.start !== null && c.end !== null; })
      .sort(function (a, b) { return a.start - b.start; });

    let cursor = 0;
    let open = null;

    located.forEach(function (claim) {
      // Overlapping claims: the splitter can return a sentence and a clause inside it. Marking both would
      // nest spans, so the first one wins and the second stays in the list below.
      if (claim.start < cursor) return;
      if (claim.start > cursor) host.appendChild(document.createTextNode(payload.answer.slice(cursor, claim.start)));

      const mark = el("mark", "sw-mark sw-" + claim.state, payload.answer.slice(claim.start, claim.end));
      mark.tabIndex = 0;
      mark.setAttribute("aria-label", (payload.labels[claim.state] || claim.state) + ": " + claim.text);

      function show() {
        if (open) open.remove();
        open = card(claim, payload);
        host.appendChild(open);
        position(open, mark, host);
      }
      function hide() {
        if (open) { open.remove(); open = null; }
      }
      mark.addEventListener("mouseenter", show);
      mark.addEventListener("focus", show);
      mark.addEventListener("mouseleave", hide);
      mark.addEventListener("blur", hide);

      host.appendChild(mark);
      cursor = claim.end;
    });

    if (cursor < payload.answer.length) {
      host.appendChild(document.createTextNode(payload.answer.slice(cursor)));
    }
    return host;
  }

  function legend(payload) {
    const wrap = el("div", "sw-legend");
    Object.keys(payload.labels).forEach(function (state) {
      const n = (payload.counts.states || {})[state] || 0;
      const chip = el("span", "sw-chip sw-" + state);
      chip.appendChild(el("span", "sw-dot sw-" + state));
      chip.appendChild(el("span", null, payload.labels[state]));
      chip.appendChild(el("b", null, n));
      wrap.appendChild(chip);
    });
    return wrap;
  }

  function list(rows) {
    const wrap = el("div", "sw-list");
    rows.forEach(function (row) {
      const line = el("div", "sw-row");
      line.appendChild(el("code", null, row[0]));
      line.appendChild(el("span", null, row[1]));
      wrap.appendChild(line);
    });
    return wrap;
  }

  function details(summaryText, node) {
    const box = el("details");
    box.appendChild(el("summary", null, summaryText));
    box.appendChild(node);
    return box;
  }

  window.saysWhoRender = function (root, payload) {
    root.textContent = "";
    root.className = "sw";

    root.appendChild(el("h1", null, "Citation audit: " + payload.meta.product + " answer"));

    const meta = el("div", "sw-meta");
    [
      ["answer", payload.meta.answer_sha256.slice(0, 16)],
      ["split", (payload.meta.split_sha256 || "none").slice(0, 16)],
      ["generated", payload.meta.generated_at],
      ["adapter", payload.meta.adapter + (payload.meta.adapter_verified ? " (verified)" : " (unverified)")],
    ].forEach(function (pair) {
      meta.appendChild(el("span", null, pair[0] + " " + pair[1]));
    });
    root.appendChild(meta);

    // Five counters reading zero is what a fetch-only run produces, and it reads as "nothing checked out"
    // rather than "nothing was checked". With no claims there is nothing to count, so nothing is shown.
    if (payload.counts.claims > 0) {
      root.appendChild(legend(payload));
    } else {
      root.appendChild(el("p", "sw-meta", "No claims in this run, so there is nothing to count."));
    }

    const g4 = el("div", "sw-banner");
    g4.appendChild(el("strong", null, "No overall score. "));
    g4.appendChild(document.createTextNode(payload.no_aggregate_rate));
    root.appendChild(g4);

    if (payload.meta.capture_is_known_incomplete) {
      const warn = el("div", "sw-banner sw-warn");
      warn.appendChild(el("strong", null, "This capture is incomplete. "));
      warn.appendChild(document.createTextNode(
        "The page showed citations or text this capture could not reach, so anything below covers part of " +
        "the answer rather than all of it."
      ));
      root.appendChild(warn);
    }

    if (payload.counts.unlocatable) {
      const warn = el("div", "sw-banner sw-warn");
      warn.appendChild(el("strong", null, payload.counts.unlocatable + " claims are not marked below. "));
      warn.appendChild(document.createTextNode(
        "Their text could not be found in the answer, which happens when the splitter quotes across a " +
        "table. They are audited and listed under All claims; they are simply not highlighted."
      ));
      root.appendChild(warn);
    }

    root.appendChild(el("h2", null, "The answer, marked"));
    root.appendChild(markedAnswer(payload));

    root.appendChild(el("h2", null, "All claims"));
    root.appendChild(
      list(payload.claims.map(function (c) {
        return [payload.labels[c.state] || c.state, c.text];
      }))
    );

    root.appendChild(el("h2", null, "Sources"));
    root.appendChild(
      list(payload.sources.map(function (s) {
        return [s.code, s.url + (s.detail ? "  (" + s.detail + ")" : "")];
      }))
    );

    root.appendChild(el("h2", null, "Skipped by gate G1"));
    const skipped = el("div", "sw-skipped");
    const n = payload.counts.skipped;
    const lines = n === 1 ? "1 line was" : n + " lines were";
    skipped.appendChild(el("p", null,
      lines + " not treated as a factual claim. They are listed rather than " +
      "discarded, because a tool that quietly drops what it cannot handle is lying by omission."));
    skipped.appendChild(details(
      "Show " + (n === 1 ? "1 skipped line" : n + " skipped lines"),
      list(payload.skipped.map(function (s) { return [s.reason, s.text]; }))
    ));
    root.appendChild(skipped);

    const foot = el("div", "sw-foot");
    foot.textContent =
      "SaysWho checks whether a cited page says what the answer attributes to it. It cannot tell you " +
      "whether a claim is true, whether the source is any good, or what the answer left out. Claim " +
      "splitting and verdicts are model inference; source outcomes and quoted-passage checks are script " +
      "output.";
    root.appendChild(foot);
  };
})();
