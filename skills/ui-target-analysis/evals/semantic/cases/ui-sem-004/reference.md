# 判定根拠

## Source of Truth

- Preserve the human work copy, invalid canonical package, and validated base as separate evidence. Do not repair or overwrite the canonical Manifest by hand.
- Block writes while the canonical package is invalid. Resume only after the canonical root is restored from the independently validated baseline and the proposal is prepared again against that snapshot with current review.
- Replay an uncertain commit with the same snapshot and identical writer request/fingerprint, then use independent inspect/readback to determine whether it already committed. Do not create a fresh draft key or duplicate ID.
- Preserve `ui-target-v1`, the conditional-file applicability, surviving stable IDs, Manifest, and changelog lifecycle. A local writer lock/readback does not prove remote CAS or multi-host history.
