# WattsWrong 3D

A browser 3D historical replay of WattsWrong findings for two real REFIT homes, for householders to explore what was found, what it cost and what to check.

## Where usage is measured

**Site**:
One metered home. In plain UI copy, "home".
_Avoid_: house (except in REFIT's own names, e.g. "REFIT House 3"), household (as a data unit)

**Channel**:
One metered power series at a site: the whole-house meter or one appliance meter. In plain UI copy, "meter".
_Avoid_: circuit, line

**Whole-house meter**:
The channel measuring a site's total supply. It shows patterns, never which device caused them. In plain UI copy, "Whole home".
_Avoid_: mains, aggregate (in prose)

**Appliance meter**:
A channel measuring one plugged-in appliance. Only appliance meters justify naming an appliance or listing possible causes.
_Avoid_: circuit, sub-meter, IAM (in prose)

**Historical replay**:
Running the system over past recorded data as if it arrived live, with no look-ahead. WattsWrong is not a live feed.
_Avoid_: live, real-time, simulation

**Replay hour**:
The hour of the historical replay currently being shown. "Right now" in UI copy always means the replay hour, never the present.
_Avoid_: current time, today (unqualified)

## What the system says

**Day-ahead forecast**:
The expected energy for an hour, made only from readings at least 24 hours old. In plain UI copy, "expected use".
_Avoid_: prediction (alone), baseline (that is a different model)

**Finding**:
A sustained positive deviation from the day-ahead forecast on one channel at one site, reported with a category, cost, explanation and one action.
_Avoid_: incident, alert, anomaly (as a noun), fault

**Category**:
The pattern a finding shows. It describes usage, never a diagnosis. In plain UI copy each has its own label:
- **Spike**: "Short burst of extra use".
- **Gradual drift**: "Use slowly creeping up".
- **Baseload creep**: "Higher always-on use".
- **Overnight excess**: "Extra use overnight".
- **Appliance abnormal**: "Appliance using more than usual".
- **Peak-hour excess**: "Extra use in the evening peak".
_Avoid_: fault type, cause, peak-hour waste

**Active finding**:
A finding that has been detected and has not yet ended at the replay hour.
_Avoid_: open finding, ongoing finding (that means no end at all)

**Ongoing finding**:
A finding whose deviation has not yet recovered, so it has no end.
_Avoid_: open finding, active finding

**Ended finding**:
A finding whose deviation has recovered.
_Avoid_: closed, resolved, fixed

**Detection strength**:
A heuristic score of how strong and persistent a finding's deviation is, shown as Low, Medium or High. It is not a probability, and not a likelihood of equipment failure.
_Avoid_: confidence, probability, certainty, Normal (that is a meter state)

**Normal**:
A meter's state when it has no active finding at the replay hour. It is not a detection strength.
_Avoid_: Calm (for a meter), OK, healthy, status (that is the householder's own judgement, in the backend)

**Calm day**:
A day on which no meter of a home had an active finding, judged by what had been detected by then, never with hindsight.
_Avoid_: normal day, good day

**Calm streak**:
The number of calm days in a row for a home, up to and including the replay hour's day.
_Avoid_: streak (alone), record

## Explaining a finding

**Possible cause**:
A common reason for a finding's pattern on an appliance meter, shown as something to check, not a diagnosis.
_Avoid_: cause (alone), diagnosis, fault

**Estimated cause**:
A guess at what kind of device might explain a whole-house finding, made from its average extra power and its timing. It is always shown as something to check, never as which device did it.
_Avoid_: possible cause (that needs an appliance meter), detected device

**Highlight**:
A notable fact about a finding, such as being the largest on its meter or the longest in its home. It is never a reward.
_Avoid_: achievement, award, badge, record

**Confirmation time**:
How long after a finding's start it was detected. It is not detection delay.
_Avoid_: detection delay, time to detect, response time

## Evidence

**Test window**:
The span of recorded data (31 Jan – 31 May 2015) that findings are scored on, after every setting has been fixed.
_Avoid_: test set, holdout

**Frozen run**:
The single scoring of the test window, made with settings fixed before it ran. It is never repeated to improve results.
_Avoid_: rerun, retrain, latest run

**Labelled event**:
A researcher annotation of unusual appliance behaviour in the REFIT anomaly labels. It is evidence of unusual usage, not a confirmed fault.
_Avoid_: anomaly, fault, ground truth

**Matched finding**:
A finding paired one-to-one with a labelled event on the same site, on that event's channel or the whole-house meter, detected between the event's start and 24 hours after its end.

**Unmatched finding**:
A finding not paired with any labelled event. Labels may be incomplete, so it is not a confirmed false alarm.
_Avoid_: false alarm, false positive

**Detection delay**:
Detected time minus the matched labelled event's start, measured only for labelled events that were detected.
_Avoid_: confirmation time (that is measured from the finding's own start)

## Telling the story

**Replay recap**:
A short full-screen story of the whole historical replay, told with counts and single findings only, never costs added across meters.
_Avoid_: year in energy, year in review, wrapped

## Money

**Extra energy**:
Energy used above the day-ahead forecast during a finding, counting only hours with positive deviation.
_Avoid_: excess energy (in UI copy), wasted energy

**Extra cost**:
Estimated cost of the extra energy detected so far: extra energy × tariff.
_Avoid_: excess cost (in UI copy), waste, savings, avoidable cost

**Projected monthly extra cost**:
Estimated extra cost per month if a still-running finding (ongoing, or active at the replay hour) continues at its observed rate. Ended findings have none, and projections are never added across meters.
_Avoid_: monthly waste, potential savings

**Historical extra cost**:
The extra cost of an ended finding. In plain UI copy, "Total extra cost"; "so far" is only for active findings.
_Avoid_: savings, cost avoided, extra cost so far (for an ended finding)

**Tariff**:
The illustrative price per kWh (44.4 sen/kWh, the TNB domestic base rate before incentives, fuel adjustment and taxes). It is not a bill calculator.
