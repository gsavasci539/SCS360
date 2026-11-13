# Parent and custom-role parity checkpoint — 13 Nov 2026

Acceptance evidence from `output/native-parent-branch-accepted-20261113.json`:
- **21/21** affected/new Android tests passed across four classes; 15 affected existing cases plus six new role-union/canonical-payload cases. The unchanged 123-case regression was retained, not rerun.
- Actual native login through FastAPI with temporary SQLite passed: branch-limited custom-role access, teacher/class scope, scoped student options, cross-class/foreign-student rejection, unlinked contacts hidden (101), atomic contact/student linking, and reload/edit visibility. Payment rows and notification jobs remained zero.
- A signed **debug** APK was produced; this is not physical-device or release acceptance.
- Read-only comparison confirms the 17 parent/navigation source and test files named in the checkpoint match the current published Mobile branch by normalized text. The artifact's recorded Mobile/API SHAs are not current branch heads. Current verified heads: Mobile `1b3a93a55e6aa7b6466c4d59c78eeb16b831e9dc`; SCS360 `9b3fa1057035c9d2a805f5eb0526684a0a07bf81`.

Remaining: operational modules and legacy role administration still need canonical web/API/native parity. Physical A26, iOS, HTTPS/provider, store, and release acceptance remain separate. No production DB, real payment/message, deployment, main merge, or force push was used.
