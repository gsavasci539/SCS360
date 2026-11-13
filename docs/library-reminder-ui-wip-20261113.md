# Kütüphane hatırlatma web arayüzü WIP — 13 Kasım 2026

`OperationPages.LibraryPage` used to call `/api/library/loans/{loan_id}/remind`, whose handler only returned a success message and created no notification job. The page also claimed SMS/push delivery. Removed that button, call, and delivery wording. The native catalogue detail/edit/delete and borrow/return paths are unchanged.

Focused frontend test: `src/test/library-reminder-availability.test.tsx` — **1 passed**. The initial Vitest launch hit an EPERM while renaming a sandbox temporary file and ran no tests; retry with `TEMP`/`TMP` under `.codex-build/vitest-temp` passed.

This is a web UI correction only. Direct API calls still reach the legacy misleading-success handler; this WIP does not resolve that backend defect. No message/job/payment was created. Next: test the API with a temporary SQLite DB and make its response honest while no real outbox/provider is configured. This is not full mobile parity or sales acceptance.

Initial WIP push: SCS360 `codex/source-sync-20261111` SHA `49e800e2d154c3b3a9304055785d436c95b4bd7d` (verified with `git ls-remote`).
