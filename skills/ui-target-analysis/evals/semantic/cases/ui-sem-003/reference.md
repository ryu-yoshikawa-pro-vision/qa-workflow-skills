# 判定根拠

## Source of Truth

- Compare the isolated work copy with the validated base and current canonical snapshot. Accept only the UI-owned label change and draft-key row; convert the explicitly reviewed removal into a retire request.
- Require the UI owner's meaning review, Q06 placement agreement, change-specific evidence, and retirement reason/approval/evidence. Keep review refs as evidence values; do not treat their presence as authentication.
- Return a request for the existing `ui_target_package.py materialize` writer. The helper must not write the canonical package or copy generated files.
- If the local writer and independent readback pass, report that as fixture/local acceptance only. External CAS, authenticated approval, shared-runtime owner verification, and real-provider readback remain blocked.
