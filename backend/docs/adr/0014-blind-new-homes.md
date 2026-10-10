# 0014 Score two new homes blind on settings tuned elsewhere

This repo's frozen run scores four REFIT homes: Houses 1 and 3 (Homes A and B), plus Houses 10 and 18 (Homes C and D). Every setting in `config/config.json` was tuned on Houses 1 and 3 only and is used unchanged. Houses 10 and 18 are never tuned, inspected for tuning, or given their own settings, so their results are a blind test. They are disclosed whatever they turn out to be, including recall and false-alarm counts worse than those for Houses 1 and 3. Their meters follow the existing rule mechanically: the whole-house meter plus every labelled appliance, with no findings on cycle appliances (0012).

## Considered options

- **Re-tune on all four homes.** Rejected: the test window of Houses 1 and 3 had already been seen, so tuning could no longer be blind (0011).
- **House 16 instead of 18.** Rejected: 36 of its 37 labelled events fall outside the test window, so its recall would rest on a single event. House 18 has 7 in the window, and House 10 has 11.
