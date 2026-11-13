# Remote push discrepancy — expense notes checkpoint — 13 Nov 2026

The local artifact `output/native-expense-notes-remotes-20261113.json` records Mobile `fe7eb2d8e9e3eeae8622c63419f928cd7f2c2043` and API `5db96b43a544744e296f84034855e3749e50a926` as pushed. Direct `git ls-remote` verification of `codex/source-sync-20261111` instead returned Mobile `1b3a93a55e6aa7b6466c4d59c78eeb16b831e9dc` and API `c6b5fd06a6bab095ddcd2ef38a66637a69a57040`; the recorded SHAs are not the current branch heads.

The acceptance manifest's hashes also no longer match three dependent Android files in the local source: `Models.kt`, `NativeCashCollectionDialog.kt`, and `FinanceScreen.kt`. The wider backend/frontend/mobile worktree has unreviewed modifications. Do not publish a partial expense checkpoint or claim the recorded SHAs are on the branch. Reconcile the tested source snapshot with current files, rerun only affected acceptance tests against temporary SQLite and isolated providers, then prepare an explicit source-only normal push and verify `ls-remote` before updating the record.

No tests, build, or source changes were made in this verification. No main merge, force push, payment, or deployment.

### Follow-up verification — 13 Kasım, 13:56

The claimed `fe7e…`/`5db9…` commits are not current branch heads, but the source is present: the source-sync helper copied the exact accepted 12 Android and 8 API/web expense files into the isolated publisher checkouts, after which both checkouts remained clean. Thus no code delta was needed; `git ls-remote` confirmed current heads Mobile `1b3a93a55e6aa7b6466c4d59c78eeb16b831e9dc`, SCS360 `cc3c88ac3f8951ae3757d760be303738aaa2f8f4`.

Affected regressions after the three Android file changes: backend temporary-SQLite expense contract **9 passed, 9 skipped** (PostgreSQL-specific cases); frontend expense form **8 passed**; Android `FinanceScopeUiTest` **3**, `NativeExpenseClientTest` **3**, and `NativeExpenseUiTest` **4** passed (10 total, Gradle BUILD SUCCESSFUL). No production DB or delivery provider was used. This verifies these focused contracts, not all mobile modules or physical A26 acceptance.

Next: continue parent/custom-role and remaining module API/DTO parity; track physical device, iOS, provider and store acceptance separately.
