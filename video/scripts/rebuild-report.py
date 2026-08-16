"""Rebuild the CO-02 report page from stored day 9 data. No judge call, no network.

Everything report.build needs was written into runs/day9/run.json at the time: the
fetch records, the judgements with their spans, and the split that produced the
claims. So this replays the view; it recomputes no verdict and invents nothing.
The pixels it produces come from the extension's own render.js and render.css.
"""
import dataclasses, json, os, sys
from pathlib import Path

# Runs from anywhere: the repo root is two levels up from video/scripts.
ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
from sayswho import judge, records, report, splits

QUERY = sys.argv[1] if len(sys.argv) > 1 else "CO-02"

run = json.load(open("runs/day9/run.json"))
r = next(x for x in run["runs"] if x["query_id"] == QUERY)

def only_fields(cls, d):
    names = {f.name for f in dataclasses.fields(cls)}
    return cls(**{k: v for k, v in d.items() if k in names})

capture = records.Capture.from_dict(json.load(open(r["capture"])))
fetched = [only_fields(records.FetchRecord, s) for s in r["sources"]]
judgements = [only_fields(judge.Judgement, j) for j in r["judgements"]]
# The split on disk has moved on since the run; its claim ids no longer match the
# stored judgements, and joining against it silently marks every claim
# COULD_NOT_VERIFY. The run kept the split it actually judged, so use that one.
claim_set = splits.StoredSplit.from_dict(
    {
        "answer_sha256": r["answer_sha256"],
        "query_id": r["query_id"],
        "product": r["product"],
        "created_at": run["started_at"],
        "claim_prompt_version": run["claim_prompt_version"],
        "judge_class": run["judge_class"],
        "judge_model": run["judge_model"],
        **r["claims"],
    }
)

built = report.build(
    capture, fetched, claim_set, judgements, split_sha256=r.get("split_sha256", "")
)
out = ROOT / "video" / "public" / "report" / f"{QUERY.lower()}.html"
built.save(out)

p = built.payload
print("wrote", out)
print("claims:", len(p["claims"]))
for c in p["claims"]:
    print(f"  {c['state']:20} {c['text'][:64]}")
print("no_aggregate_rate:", str(p.get("no_aggregate_rate"))[:120])
