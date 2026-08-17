# Explainer video: script and shot list

Three to six minutes. The rubric asks for one uncut segment showing a real answer marked live, **including a
claim the tool refuses to score**. That refusal is not a caveat to apologise for at the end. It is the whole
argument, and it belongs in the middle of the demo where nobody can miss it.

**Every number below is from the day 9 run and checkable in `runs/day9/`.** Updated 2026-08-16, after that run
landed. Nothing here is rounded in a flattering direction and nothing is quoted without its n.

## What was delivered, 2026-08-16

**`site/media/sayswho.mp4`, 5:20, narrated, published at
[thisisjayk.github.io/SaysWho](https://thisisjayk.github.io/SaysWho/).** Inside the three to six minute
window. Everything below is the plan it was cut from, kept because the departures are worth reading, not
because it describes the file.

Three departures, all deliberate:

1. **It is one film, not two.** The Remotion short and the live walkthrough were separate embeds until the
   page stopped asking a reader to pick. The short runs to its closing card, the walkthrough runs without
   the title and closing cards it had borrowed from it, and that closing card ends the whole thing.
   `video/scripts/consolidate.py`.
2. **The shot list below is six shots. The walkthrough is seven.** The extra one is `FINDINGS.md`, and the
   order differs: the answer, the frozen query set, the auditor starting, the whole audit in one take, the
   run readout, `FINDINGS.md`, then `STATUS.md`.
3. **`CO-02` is a new conversation, not the archived one behind `runs/day9/`.** Ten claims and a verdict mix
   of its own. Nothing in the demo reads a figure off that recording; every number spoken comes from day 9,
   and the two that describe what is on screen, three grey claims and six of twelve uncited, are checked
   against `reports/report-chatgpt-20260816T2304300000.json`.
4. **Step 8 of the segment below, "then the second refusal", is not how the film says it.** That wording
   needs the claim level refusal to come first, and in this recording the panel puts the answer level one at
   the top of the report and never scrolls back to it, so saying it in plan order meant saying it forty five
   seconds after its box had gone. The refusal is now spoken while that box is up, which puts it before the
   grey claims rather than after them. Both refusals are still in the middle of the take, which is what this
   document actually cares about. The framing was spent deliberately and is recorded in `STATUS.md`.

The fifteen narration lines live in `video/scripts/explainer.py` with the offset each one is measured
against, and `video/scripts/explainer_tts.py` regenerates the audio from them. The rule at the top of the
next section is enforced there rather than remembered: the kappa line was regenerated shorter when it
outgrew its shot, and it kept the interval and the n while losing its wind-up.

## The one line the video has to land

Every other tool in `SCOPE.md` §1b answers "is this true" with a confidence score. This one answers a narrower
question, "does the cited page say what this sentence says", and **refuses to answer when it cannot check**.
The day 9 run is the proof: it judged ten answers, produced 139 model calls' worth of verdicts, published
per-answer and per-domain rates, and still refused the headline stratum rate because one answer of the ten had
more than half its cited claims unreadable.

## The numbers you are allowed to say

| Figure | Value | Never say it without |
|---|---|---|
| Judge against human, Cohen's kappa | **0.304** | the interval, 0.004 to 0.604, n=35 |
| `NOT_FOUND_IN_SOURCE` agreement | precision and recall both 77.3% | n=22 |
| `PARTIALLY_SUPPORTED` precision | 16.7% | n=6 |
| Hand-labelled pairs | 45 blind, 36 comparable | that 35 had a standing verdict to compare |
| Citations captured from ChatGPT | 33 | that at least 20 more were hidden, a 37.7% floor |
| Span guard firings | 1 of 76 span-bearing verdicts | that 0 of 76 were this tool's fault |
| Run cost | 139 calls, 817,995 tokens, no cost | that it is a free tier, not an efficiency claim |

**The one sentence that would sink the video:** quoting 0.30 without the interval. The lower bound is 0.004.
At this sample size the run cannot rule out that the agreement between the judge and the labeller is chance,
and saying the number alone would be doing exactly what the tool exists to prevent.

## Shot list

| # | Length | Shot | What is said |
|---|---|---|---|
| 1 | 0:00 to 0:30 | Screen: a ChatGPT answer with citation chips, scrolling | "This answer cites five sources. I have never once opened all five. Nobody has. The chip does the persuading and nothing does the checking." |
| 2 | 0:30 to 1:00 | `queries/consumer.toml`, then `freeze_queries.py check` passing | "Twenty-four questions, frozen before any run, hash-checked before every one. If I tuned a question after seeing a result, this command fails." |
| 3 | 1:00 to 2:30 | **The uncut segment.** Live browser, extension loaded | See below. This is the shot that carries the video. |
| 4 | 2:30 to 3:30 | Terminal: the day 9 readout in `runs/day9/`, at `STRATUM RATE withheld`, then `JUDGE AGAINST HUMAN` | "Here is the run over ten answers. Here is the support rate: there isn't one, and here is the gate saying why. And here is what happened when I checked the judge against myself." |
| 5 | 3:30 to 4:15 | `FINDINGS.md` items 23 and 25 | The third of ChatGPT's citations the tool cannot see, and the two contradictions that turned out to be conflations. |
| 6 | 4:15 to 5:00 | `STATUS.md`, the blocker row and the not-done rows | "The professional stratum never ran. Here is the row that says so." |

## Shot 3, the uncut segment, in order

Do this in one take. If a step fails, start the take again rather than cutting; a cut here is the thing the
rubric is asking you not to do.

**Use `CO-02`, the colon cancer screening question.** It was `CO-22` in the old script, when the demo was
Perplexity and `CO-22` had blocked sources. On ChatGPT all five of `CO-22`'s sources came back `SOURCE_OK`, so
it has no claim the tool refuses to score and cannot carry this shot. `CO-02` cites two sources, one of them
a genuine 404, and it is the answer that trips `INSUFFICIENT_EVIDENCE`.

1. Open the `CO-02` conversation on chatgpt.com.
2. Click **SaysWho: capture**. Say what it did: the answer text, hashed, plus every cited URL.
3. **The capture will print `INCOMPLETE` on camera. Do not talk over it, point at it.** ChatGPT hides some
   citations behind "+N" controls and the extension counts what it could not reach. Say: "It just told me it
   cannot see all of this answer's citations. Across ten answers that is at least twenty missing out of
   fifty-three. A tool that did not count them would look more accurate and be less honest."
4. Start the server in a visible terminal: `.venv/bin/python -m sayswho.server --judge`.
5. Click **SaysWho: audit**. Let the panel fill on camera. Do not speed this up.
6. **Point at a green claim.** Hover it so the source's own words appear. Say: "It didn't decide this was
   true. It found the sentence on the page and it will show you where."
7. **Point at the grey one. This is the shot.** A claim whose only source came back `SOURCE_DEAD_LINK`, marked
   *Could not verify*. Say, out loud:

   > "This one, it will not score. The citation points at a page that is gone, so there is nothing to check
   > against. Every other tool I looked at gives you a number here. A number here is invented."

8. **Then the second refusal, which is the better one.** Scroll to the answer-level result: no support rate at
   all, because more than half this answer's cited claims produced no verdict that stands. Say: "It won't
   score the answer either. Half of it is unreadable, so a rate over the other half would be a rate over
   whichever half happened to load."

## The three sentences to get exactly right

- **On the refusal:** "Not scoring is a feature. The unauditable ones are counted, named, and kept out of
  every rate."
- **On what the verdict means:** "Not supported *by the cited source*. The sentence may be perfectly true and
  cited to the wrong page. That distinction is the product."
- **On what it cannot do:** "It cannot tell you whether the source is right. A well-cited falsehood passes.
  That is the largest limitation and it is in §7 of the design document, not in a footnote here."

## What to say about the gold set, since it will come up

Rewritten 2026-08-16, because the run happened and the earlier paragraph said six labels and no calibration.
Say this:

> "Forty-five claims hand-labelled by me, blind, before the judge saw any of them. Thirty-five could be
> compared with a verdict. Cohen's kappa is 0.30, and the confidence interval runs from 0.004 to 0.60. That
> lower bound is the honest part: at this sample size I cannot rule out that the agreement between me and the
> judge is chance. So the tool now reports its own verdicts as worth about that much."

If there is time for one more sentence, make it this one, because it is the most useful thing the calibration
found:

> "It agrees with me best on 'the page does not say this', 77 per cent both ways. It agrees with me worst on
> 'the page partly says this': when the judge said that, I agreed one time in six."

## What not to do

- **Do not say 0.30 without the interval.** See above. This is the one that matters.
- Do not read a stratum support rate off the screen. There isn't one, and inventing one on camera would be
  the exact failure the tool exists to catch. Per-answer and per-domain rates are real and may be read, with
  their n.
- Do not describe the two `CONTRADICTED` verdicts as catches. Both were read by hand and both look like the
  judge confusing an adjacent category with the claim's. `FINDINGS.md` item 25.
- Do not demo Google AI Overviews. The default judge is a Google model and `rates.py` refuses to put that
  product in a cross-product number; explaining the conflict costs a minute you do not have.
- Do not claim the citation capture is complete. It is not, by a measured floor of 37.7 per cent, and the
  number is in the run rather than in a caveat.

## Recording notes

- The panel follows the page's colour scheme, so use light mode; the dark-panel text bug is fixed but light
  reads better on video.
- Long URLs used to widen the panel. Fixed, but keep the window at 1280 wide and it will not come up.
- Start the server **before** recording. It refuses to start without a key and says so, which is good design
  and a bad first ten seconds of a video.
- The ChatGPT answers were captured 2026-08-15 and the pages behind them have been fetched since, so the
  audit runs from cache and will fill faster on camera than a cold one would.
