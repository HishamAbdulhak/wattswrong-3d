# 0009 Chronological split

Status: AGREED by the team on 10 Oct 2026 (chosen from three options), frozen before any tuning.

Train < 2014-08-25, validation < 2015-01-31, test < 2015-05-31 (UTC), the same calendar dates for House 1 and House 3. Merged labelled events: House 1 5/7/8, House 3 31/23/11.

The test ends at the end of annotation (House 3 labels stop on 27 Apr 2015, House 1 on 28 May 2015), so findings in an unlabelled tail are not counted as unmatched. Data after 31 May 2015 is not replayed or exported. Events straddling a boundary are excluded and counted. Events whose end + 24 h follow-up passes test end are censored and counted.
