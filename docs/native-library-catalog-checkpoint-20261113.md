# Native library catalog CRUD — 13 Nov 2026

## Scope
- Android native book detail, versioned edit, confirmed delete.
- Existing canonical API routes `/api/library/books/{id}`; no local-only catalogue success.
- Delete with any loan history remains server-protected.

## Evidence
- Android UI target: 7 passed, 0 failed; debug unit-test task succeeded.
- Real native client + temporary SQLite API bridge: 1 passed, 0 failed.
- Verified persisted detail/edit; stale `updated_at` rejected with 409; no-history delete persisted; delete after loan history rejected with 409; reader edit/delete rejected with 403; cross-tenant student rejected; return restored stock.
- Fixture side effects: payment rows 0; notification jobs 0; real message delivery 0.
- Detailed local report: `output/native-library-real-api-20261113.json` (not published).

## Limits / next
This is a focused module checkpoint, not whole-app acceptance. No physical A26, iOS, store, payment provider or production test. Next: assess catalogue filtering/page behavior and uncertain-response recovery against web/API semantics, then continue remaining operations modules.

## Published source
Pending verification of isolated source-only pushes on `codex/source-sync-20261111`.
