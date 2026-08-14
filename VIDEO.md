# Explainer video: script and shot list

Three to six minutes. The rubric asks for one uncut segment showing a real answer marked live, **including a
claim the tool refuses to score**. That refusal is not a caveat to apologise for at the end. It is the whole
argument, and it belongs in the middle of the demo where nobody can miss it.

Everything below is real and already on disk. No slide claims a number this repo cannot produce.

## The one line the video has to land

Every other tool in `SCOPE.md` §1b answers "is this true" with a confidence score. This one answers a narrower
question, "does the cited page say what this sentence says", and **refuses to answer when it cannot check** on
purpose. The day-6 run is the proof: it judged 24 answers, produced 130 verdicts, and printed no support rate
at all, because no gold set covered those splits. A tool that prints a number in that situation is guessing.

## Shot list

| # | Length | Shot | What is said |
|---|---|---|---|
| 1 | 0:00–0:30 | Screen: a Perplexity answer with footnotes, scrolling | "This answer has nine footnotes. I have never once opened all nine. Nobody has. The footnote does the persuading and nothing does the checking." |
| 2 | 0:30–1:00 | `queries/consumer.toml` on screen, then `freeze_queries.py check` passing | "Twenty-four questions, frozen before any run, hash-checked before every one. If I tuned a question after seeing a result, this command fails." |
| 3 | 1:00–2:30 | **The uncut segment.** Live browser, extension loaded | See below. This is the shot that carries the video. |
| 4 | 2:30–3:15 | Terminal: the day-7 readout, scrolled to `STRATUM RATE withheld` | "Here is the run over all 24. And here is the support rate: there isn't one." |
| 5 | 3:15–4:15 | `FINDINGS.md` item 21 on screen | The four voided spans, and the one that was ours. |
| 6 | 4:15–5:00 | `STATUS.md` blocker row and the not-done rows | "The professional stratum never ran. Here is the row that says so." |

## Shot 3, the uncut segment, in order

Do this in one take. If a step fails, start the take again rather than cutting; a cut here is the thing the
rubric is asking you not to do.

1. Open a captured consumer answer on perplexity.ai. `CO-22` is a good one: utility shutoff protections,
   several cited claims, and a mix of readable and blocked sources.
2. Click **SaysWho: capture**. Say what it did: the answer text, hashed, plus every cited URL.
3. Start the server in a visible terminal: `.venv/bin/python -m sayswho.server --judge`.
4. Click **SaysWho: audit**. Let the panel fill on camera. Do not speed this up.
5. **Point at a green claim.** Hover it so the source's own words appear. Say: "It didn't decide this was true.
   It found the sentence on the page and it will show you where."
6. **Point at the grey one.** This is the shot. A claim whose source came back `SOURCE_BOT_BLOCKED`, marked
   *Could not verify*. Say, out loud:

   > "This one, it will not score. The page refused us, so there is nothing to check against. Every other tool
   > I looked at gives you a number here. A number here is invented."

7. Close on the counter: unauditable claims are excluded from every denominator, and the tool says how many.

## The three sentences to get exactly right

- **On the refusal:** "Not scoring is a feature. The unauditable ones are counted, named, and kept out of
  every rate."
- **On what the verdict means:** "Not supported *by the cited source*. The sentence may be perfectly true and
  cited to the wrong page. That distinction is the product."
- **On what it cannot do:** "It cannot tell you whether the source is right. A well-cited falsehood passes.
  That is the largest limitation and it is in §7 of the design document, not in a footnote here."

## What to say about the gold set, since it will come up

Say it plainly and move on: "Six claims hand-labelled, not the thirty to forty planned. So the tool has no
calibration for this judge, and gate G4 withholds every aggregate rate rather than printing an uncalibrated
one. You just watched it do that."

That is a stronger thirty seconds than any number would have been. The gate firing on the presenter's own run,
on camera, is the demonstration.

## What not to do

- Do not read a support rate off the screen. There isn't one and inventing one on camera would be the exact
  failure the tool exists to catch.
- Do not demo Google AI Overviews. The default judge is a Google model and `rates.py` refuses to put that
  product in a cross-product number; explaining the conflict costs a minute you do not have.
- Do not click audit on an answer you intend to hand-label later. `prior_audit.py` will refuse the blind
  session afterwards, correctly.

## Recording notes

- The panel follows the page's colour scheme, so use light mode; the dark-panel text bug is fixed but light
  reads better on video.
- Long URLs used to widen the panel. Fixed, but keep the window at 1280 wide and it will not come up.
- Start the server **before** recording. It refuses to start without a key and says so, which is good design
  and a bad first ten seconds of a video.
