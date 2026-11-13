# Native/Web library list parity — 13 Nov 2026

## Change
- `/api/library/books` returns a tenant-scoped paginated envelope and accepts both web (`page`, `page_size`, `skip`) and native (`limit`, `offset`) parameters.
- Web search is sent to the API and restarts at page 1; native client reads each API page until the server-reported total is reached.

## Verification
- Backend temporary SQLite catalog regression: 7 passed; PostgreSQL variants not selected.
- Actual Kotlin client against the temporary SQLite API bridge: 1 passed, including a foreign-organization book fixture hidden from the selected tenant.
- Native library UI: 8 passed; web library UI: 3 passed; frontend TypeScript/Vite build succeeded.
- Targeted ESLint and Ruff F821/F823 passed. Broad Ruff scan on touched legacy files reported 112 style/import formatting findings across legacy-heavy touched files; no bulk formatting was performed.
- No real device, payment, message delivery, or production environment.

This checkpoint covers the library list contract only. Next: continue parity review of remaining native operational modules, guardian actions, custom roles, and post-payment refresh.

## Publication
SCS360Mobile `codex/source-sync-20261111`: `1b9447251a4e6a062d1f079a22659639285de796`; SCS360 API/test checkpoint: `d34368bbda886be27412d5ab98ce2bf9cea216ee` (both remote-verified).
