# Eval Input

## Current authoritative specification

The approved product policy says that only administrators may export customer records. This policy is the current Authority and has not been superseded.

## Repository observations

- Frontend repository: branch `release/4.2`, commit `front-842`, checked 2026-09-30. The current export page enables the button for editors as well as administrators.
- Backend repository: branch `release/4.2`, revision `api-219`, checked 2026-09-21. Its export endpoint checks administrator role.
- The earlier analysis package recorded both repository baselines. Only the frontend was rechecked for this update.

## Request

Update the reusable UI target package from the current evidence. Keep policy and implementation observations distinct and preserve the unrefreshed backend baseline.
