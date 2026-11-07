# Legacy data: preservation-first next step

Read-only evidence collected on local Main revision 036, 5 November 2026. No data repair, normalization, deletion, merge, renumbering, synthetic parent creation or constraint change was performed.

## What the additional row comparison establishes

`legacy-profile-comparison-20261105.json` compares the 25 canonical `(organization_id, student_number)` collision groups with one read-only snapshot. All 25 contain two different student UUIDs, one active row and one soft-deleted row. After UUID formatting is normalized for comparison only, all inspected business columns agree except `deleted_at`; creation/update timestamps also differ. Every member has declared inbound references. Deleting either record or merging the IDs would therefore affect existing relationships. Equal personal/business fields do not independently establish real-world identity or authorize a merge.

The 25 malformed child identifiers from the source-provenance manifest all exist in Main. Every parent identifier listed in those source templates matches the corresponding Main value. These are ten debts, ten notification jobs and five announcements. This strengthens the source-template association; it does not prove that the rows are currently disposable test data. No personal field values or row payload hashes were exported.

## Smallest remaining decisions to investigate on a clone

1. **Active versus archived student uniqueness.** Inspect current create/import/update/restore contracts and PostgreSQL behavior before choosing a schema policy. The import service explicitly considers `deleted_at IS NULL`, while the physical unique key includes archived rows. A partial unique index limited to active students could preserve both different IDs and all relationships without renumbering; it is only a candidate, not an implemented or accepted policy. It requires SQLite table/foreign-key-safe migration design, equivalent PostgreSQL semantics, duplicate-active preflight, historical lookup and restore-conflict tests. Do not remove global uniqueness or assume this index alone repairs any missing parent.
2. **Formatting-only closure.** On an expendable consistent clone, propose the complete valid-UUID PK/FK transform manifest only after all uniqueness predicates are resolved. Preserve non-UUID literals, NULLs and every unrelated typed value. Check exact row counts, credentials, role/permission links, financial identities and all constraints with enforcement enabled. Current application binds use hyphenated UUIDs; this does not authorize isolated PK edits or disabling FK validation.
3. **Missing parent identities and malformed IDs.** Keep the 21 absent parent keys / 96 references and 43 invalid UUID cells distinct. Restoring a source template would fabricate an active account or institution if the source is merely an example. No available backup contains those missing keys. Preserve originals and define a reversible, explicit restore/legacy-identity/quarantine plan before any DML; do not choose a default user or institution.
4. **Release gate.** The existing `release_preflight.py` checks environment, provider configuration and Alembic head, but not stored data relationships or malformed UUIDs. Add a read-only, count-only integrity gate with fresh SQLite/PostgreSQL and dirty-clone regression coverage in a separate phase; a current migration version alone must not establish data acceptance. No gate implementation has been started by this evidence collection.

## Boundaries and acceptance

Main remains unchanged by this investigation. Existing local application availability does not establish sale/production data acceptance. Continue independent internal API/UI fixes while preparing the concrete clone repair plan. Ask for user data ownership/classification information only when a demonstrated ambiguity blocks the chosen repair; no price/provider-key question is needed again. Do not claim only external-provider acceptance remains.
