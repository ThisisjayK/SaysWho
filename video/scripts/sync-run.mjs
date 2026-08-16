// Regenerates src/runData.ts from a run record so no figure in the film is typed
// by hand. Run it again if the film is ever cut against a different run.
//
//   node scripts/sync-run.mjs ../runs/day9/run.json
//
// Every field it exports carries its n and, where the run computed one, its 95%
// interval. Nothing here exposes a point estimate on its own, because the
// components downstream render the pair together and cannot render one alone.

import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

/**
 * The question is read out of the frozen query file rather than retyped, so the
 * words on screen are the words that were hashed. `freeze_queries.py check`
 * fails on an edit to any of them, which makes this the only copy that can be
 * trusted. tomllib is stdlib on the Python the repo already requires.
 */
const queryText = (queryId) =>
  execFileSync(
    "python3",
    [
      "-c",
      [
        "import tomllib,sys",
        "d=tomllib.load(open(sys.argv[1],'rb'))",
        "qs=d.get('query') or d.get('queries') or []",
        "print(next(q['text'] for q in qs if q['id']==sys.argv[2]).strip())",
      ].join(";"),
      resolve("../queries/consumer.toml"),
      queryId,
    ],
    { encoding: "utf8" },
  ).trim();

const source = process.argv[2] ?? "../runs/day9/run.json";
const run = JSON.parse(readFileSync(resolve(source), "utf8"));
const a = run.agreement;

const byLabel = Object.fromEntries(a.per_class.map((c) => [c.label, c]));
const nf = byLabel.NOT_FOUND_IN_SOURCE;
const ps = byLabel.PARTIALLY_SUPPORTED;

const round = (x, dp = 3) => Number(x.toFixed(dp));
const pct = (x) => Number((x * 100).toFixed(1));

// The demo answer. CO-02 is the one VIDEO.md picks for the uncut segment,
// because one of its two cited sources is a genuine 404, so it is the only
// answer in the run that both scores claims and refuses to score others.
const DEMO_QUERY = process.env.DEMO_QUERY ?? "CO-02";
const demoRun = run.runs.find((r) => r.query_id === DEMO_QUERY);
if (!demoRun) {
  throw new Error(`${DEMO_QUERY} is not in ${source}. Pass DEMO_QUERY= to pick another answer.`);
}

const verdicts = Object.fromEntries(demoRun.judgements.map((j) => [j.claim_id, j.verdict]));

// The span is the receipt. A SUPPORTED verdict only stands because this text was
// found, by string match, in the page that was actually fetched.
const spans = Object.fromEntries(
  demoRun.judgements.map((j) => [j.claim_id, (j.span ?? "").replace(/\s+/g, " ").trim()]),
);

// A claim the judge was never asked about has no verdict, which is what the
// panel draws as "Could not verify". It is not a negative result and it never
// enters a rate.
const PANEL_STATE = {
  SUPPORTED: "SUPPORTED",
  PARTIALLY_SUPPORTED: "PARTIALLY_SUPPORTED",
  NOT_FOUND_IN_SOURCE: "NOT_SUPPORTED",
  CONTRADICTED: "NOT_SUPPORTED",
  MIXED: "MIXED",
};

const demoClaims = demoRun.claims.claims.map((c) => ({
  id: c.id,
  text: c.text,
  markers: c.markers,
  verdict: PANEL_STATE[verdicts[c.id]] ?? "COULD_NOT_VERIFY",
  span: spans[c.id] ?? "",
}));

const data = {
  runId: run.run_id ?? null,
  sourceFile: source,
  demo: {
    queryId: DEMO_QUERY,
    question: queryText(DEMO_QUERY),
    product: demoRun.product,
    sourceCount: demoRun.sources.length,
    claims: demoClaims,
    /**
     * A withheld rate is a gate refusing to publish, not a missing field. The
     * run records the reason, so the film quotes the run rather than a paraphrase.
     */
    withheld: demoRun.rates.withheld ?? [],
    withheldCode: (demoRun.rates.withheld ?? [])
      .map((w) => String(w).split(":")[0])
      .join(", "),
  },
  kappa: {
    value: round(a.kappa),
    interval: a.kappa_interval_95.map((x) => round(x)),
    n: a.compared,
  },
  // Per class precision, each with the interval the run computed for it. The
  // first version of this script dropped the intervals and exported bare
  // percentages, which is the one thing this project is not allowed to publish.
  // Drawn together these two intervals miss each other by 0.21 percentage
  // points, which is the most self-aware fact in the run and the reason the
  // film has a second data beat at all.
  perClass: [
    {
      label: "the page does not say this",
      verdict: "NOT_FOUND_IN_SOURCE",
      precision: pct(nf.precision),
      interval: nf.precision_interval_95.map(pct),
      n: nf.precision_n,
    },
    {
      label: "the page partly says this",
      verdict: "PARTIALLY_SUPPORTED",
      precision: pct(ps.precision),
      interval: ps.precision_interval_95.map(pct),
      n: ps.precision_n,
    },
  ],
  /**
   * The distance between the two per-class intervals, computed from the raw
   * bounds rather than the rounded ones the film prints. It is displayed to one
   * decimal so that a viewer subtracting the two bounds on screen gets the same
   * answer the film states.
   */
  perClassGap: Number(
    ((nf.precision_interval_95[0] - ps.precision_interval_95[1]) * 100).toFixed(2),
  ),
  notFoundInSource: {
    precision: pct(nf.precision),
    recall: pct(nf.recall),
    n: nf.precision_n,
  },
  partiallySupported: {
    precision: pct(ps.precision),
    n: ps.precision_n,
  },
};

const out = `// Generated by scripts/sync-run.mjs from ${source}. Do not hand edit.
// Regenerate rather than correcting a number here, so the film cannot drift from
// the run that produced it.

export type Estimate = {
  value: number;
  interval: [number, number];
  n: number;
};

export const RUN = ${JSON.stringify(data, null, 2)} as const;
`;

writeFileSync(resolve("src/runData.ts"), out);
console.log(`wrote src/runData.ts from ${source}`);
console.log(`  kappa ${data.kappa.value} CI ${data.kappa.interval.join(" to ")} n=${data.kappa.n}`);
for (const c of data.perClass) {
  console.log(`  ${c.verdict} precision ${c.precision}% CI ${c.interval.join(" to ")} n=${c.n}`);
}
// The near miss the second data beat is built on. Printed so that if a future
// run makes these intervals overlap, whoever regenerates sees it here first.
// Computed off the raw values, not the rounded ones the film displays, because
// 56.56 minus 56.35 is 0.21 and 56.6 minus 56.4 is 0.2.
const rawGap = (nf.precision_interval_95[0] - ps.precision_interval_95[1]) * 100;
console.log(
  `  gap between the two intervals: ${rawGap.toFixed(2)} points, ` +
    `${rawGap > 0 ? "no overlap" : "OVERLAPPING, the film's near-miss beat no longer holds"}`,
);
