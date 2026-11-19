# Evaluation report template

- Dataset version, manifest hash, code commit, authority hashes, policy
- Layer, split, eligible submissions, excluded cases and reasons
- Provider configuration and execution date if observed
- First-attempt scope and separately reported reruns, human actions and policy variants

| Metric | Numerator | Denominator | Notes |
|---|---:|---:|---|
| Invoice count | | | Unique eligible submissions / unique registered submissions |
| Executed count | | | Executed first attempts / eligible submissions |
| Technical failures | | | Failed or interrupted / executed submissions, Layers B and C |
| Critical-field exact matches | | | Exact / labelled present critical values on attempts with available extraction |
| Missing fields | | | Absent / labelled present values on attempts with available extraction |
| Hallucinated fields | | | Supplied on labelled-absent slots / labelled-absent slots on attempts with available extraction |
| Evidence grounding | | | Correct / labelled evidence judgments on attempts with available extraction |
| Exact decision matches | | | Exact / executed with a labelled business target, including technical failures as misses |
| False-ready | | | Ready against non-ready target / executed with a non-ready target |
| Unnecessary review | | | Review against Ready target / executed with a Ready target |
| Required finding recall | | | Required codes observed / required codes across executed labelled cases |
| Owner matches | | | Correct owners / executed findings or cases with labelled expected owner |
| Model calls per invoice | | | Sum of reported calls / executed invoices with known call count |
| Mean latency | | | Sum measured milliseconds / executed invoices with the same available latency measure |

Report zero-denominator metrics as unavailable. Break down incorrect present values and extra unmapped lines separately from missing values. Include latency scope, coverage and any range or percentile with the sample size. Report unexecuted, ineligible and inconclusive cases individually. Separate trusted-facts and controlled-provider observations from live results.

| Case/track | Target | Observed execution/decision | Fields/evidence | Findings | Owner/action | Calls/time | Verdict or exclusion reason |
|---|---|---|---|---|---|---|---|

Summarize gaps, limitations, and any separately reviewed oracle amendment. Attach per-attempt machine-readable rows conforming to `result_v1.schema.json`. Keep credentials, raw provider responses and full payment details out of result artifacts.
