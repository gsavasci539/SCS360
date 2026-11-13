# Library reminder API — 13 November 2026

Supersedes the unresolved API defect in `library-reminder-ui-wip-20261113.md`.

`POST /api/library/loans/{loan_id}/remind` now requires `library.write` and returns HTTP 503 with an explicit notification-not-sent message. The feature has no delivery/outbox implementation, so all loan IDs receive the same unavailable response; no record existence is disclosed. The web reminder button remains unavailable. This corrects false acknowledgement; reminder delivery itself is not implemented.

Focused FastAPI acceptance against disposable SQLite: **3 passed, 3 PostgreSQL variants deselected**. Writer receives 503 and `success=false`; reader and student-only writer receive 403; unauthenticated requests receive 401. Both UUID-shaped and malformed identifiers were checked. NotificationJob and Payment tables remain empty. XML evidence stays local at `output/library-reminder-unavailable-20261113.xml`.

The initial sandboxed process produced no test result and was interrupted. The diagnostic execution outside that sandbox passed in 6.58s using fixtures that force temporary DBs and disable delivery. Source-only publisher helper reported zero secret findings. Existing workspace edits/index and publisher unrelated WIP are preserved.

This checkpoint does not establish full mobile/web parity or physical-device/provider/store acceptance. Next internal work: compare native staff leave/duty mutations with the actual web API DTOs, authorization and server readback; keep reminder delivery disabled until a real scoped outbox implementation is accepted.
