# Main UUID / constraint read-only diagnosis — 5 November 2026

Whole-database UUID canonicalization is currently blocked by **25 natural-key collision groups affecting 50 different student UUIDs**. Single-column UUID primary-key uniqueness does not establish that the data can be normalized without violating other constraints or changing business identities.

Only a local diagnostic helper and output reports were created. Main and pre-035 backup connections used SQLite URI `mode=ro`, `PRAGMA query_only=ON`, and one read transaction per database. No schema, data, `.env`, application source, migration, or provider change was made. Model inspection used an isolated subprocess configured with an in-memory engine; it did not connect, start the app, create tables, or run migrations. No row bodies, student numbers, personal fields, credentials, or tokens were exported.

## Constraint inventory

| Measure | Current Main 035 | Pre-035 backup 034 |
|---|---:|---:|
| Tables | 108 | 107 |
| Composite primary keys | 5 | 5 |
| Unique indexes including PK indexes | 144 | 142 |
| Unique constraints excluding PK | 33 | 33 |
| Explicit unique indexes | 3 | 2 |
| UUID-containing constraints/indexes including PK | 129 | 127 |
| UUID-containing unique constraints/indexes excluding PK | 22 | 21 |
| Candidate normalized UUID collision groups | **25** | **25** |
| Rows in those groups | **50** | **50** |
| Unsupported expression/collation/predicate cases | 0 | 0 |

All collision groups belong to `students` unique key `(organization_id, student_number)`, index `sqlite_autoindex_students_2`. Two physical UUID spellings of the same organization currently allow the same student number to appear in different rows. These rows have **50 distinct valid student UUIDs**, not alternative spellings of 25 student primary keys. Changing either all parent references to 32-character or all to 36-character storage collapses the organization key and reaches the same unique-key conflict. Deleting one row, merging people, renumbering students, `INSERT OR REPLACE`, or dropping uniqueness would change the preservation problem; none was done or implicitly approved.

Collision normalized-key sets are identical between current Main and the pre-035 backup: zero new or removed groups. JSON contains row locators, canonical UUID identifiers and key fingerprints; non-UUID unique-key values are not exported.

All five composite PKs were checked with zero semantic collisions:

| Table | Key columns | Rows |
|---|---|---:|
| class_teachers | class_id, user_id | 1 |
| role_permissions | role_id, permission_id | 1,113 |
| student_parents | student_id, parent_id | 50 |
| user_branches | user_id, branch_id | 4 |
| user_roles | user_id, role_id | 14 |

The current unique partial index `uq_school_payment_merchant_current_org` was evaluated only over its actual predicate. Current indexes contain no expression keys or non-BINARY collations. The helper reports such unsupported cases rather than silently claiming coverage if future schemas introduce them. NULL-bearing unique keys are excluded from collision groups according to SQLite uniqueness behavior.

## Invalid UUID identities are a separate issue

The model-based scan checked **358 existing UUID-mapped PK/FK columns**. It found **43 non-NULL invalid UUID literal cells in 8 columns**, of which **25 are primary keys**. Current and backup have the same counts.

| Column | Invalid cells | Category |
|---|---:|---|
| debts.id | 10 | UUID-length strings containing invalid UUID characters |
| announcements.id | 5 | UUID-length strings containing invalid UUID characters |
| notification_jobs.id | 10 | UUID-length strings containing invalid UUID characters |
| branches.organization_id | 1 | Integer-looking TEXT literal |
| users.organization_id | 1 | Integer-looking TEXT literal |
| classes.organization_id | 1 | Integer-looking TEXT literal |
| parents.organization_id | 10 | Integer-looking TEXT literal |
| ai_chat_audit_logs.organization_id | 5 | Integer-looking TEXT literal |

Numeric-looking legacy organization text, including the previously identified missing parent key `1`, is not a valid UUID and must remain a distinct category. It is not converted into a UUID or treated as restored merely because a raw organization row could be inserted. The 25 malformed primary keys were not covered by the earlier 1,438-valid-single-PK result. No automatic identity mapping is proposed.

The full column-drift expansion below identifies eight missing model columns; this is an independent diagnostic finding only. No repair or expanded endpoint investigation was performed.

## Full model-column / physical-column comparison

The actual `app.main` module-registration graph was inspected with an in-memory database URL and no lifespan, server startup, SQL connection or migration. It has **107 application tables / 1,271 model columns**; Main's additional table is Alembic bookkeeping.

| Missing physical column | Model SQLite type | Nullable | Server default | Client default | Foreign key |
|---|---|---|---|---|---|
| integration_settings.integration_type | VARCHAR(50) | No | None | None | None |
| integration_settings.provider_name | VARCHAR(100) | No | None | None | None |
| integration_settings.settings | VARCHAR | No | None | None | None |
| app_settings.key | VARCHAR(100) | No | None | None | None |
| app_settings.value | VARCHAR | No | None | None | None |
| student_teacher_assignments.updated_at | DATETIME | No | CURRENT_TIMESTAMP | None | None |
| timetables.created_by | VARCHAR(36) / CustomUUID | **Yes** | None | None | users.id |
| timetables.updated_by | VARCHAR(36) / CustomUUID | **Yes** | None | None | users.id |

The timetable names are **created_by and updated_by**, not updated_at. Domain Timetable defines both as nullable and the actual timetable router imports that domain class through `app.domain.entities`. The infrastructure model also defines the same table, and `extend_existing` allows the domain definition to extend its metadata.

There are **four physical columns absent from registered metadata**: `alembic_version.version_num` (expected migration bookkeeping), `chat_messages.receiver_id`, `grades.created_by`, `grades.updated_by`. No such column was dropped.

There are **225 existing columns with at least one literal DDL difference**: **171 nullability**, **28 declared type**, and **28 server-default text** differences, with some columns differing in more than one category. For example, `timetables.semester` is VARCHAR(20) in the domain metadata and INTEGER physically; `classroom_assignments.subject_id` is model VARCHAR(36) and physical VARCHAR(32). These are observational comparisons, not 225 demonstrated endpoint failures. SQLite affinity, application compatibility paths, client defaults, and equivalent SQL default spellings require separate evaluation before choosing a migration.

All missing-column definitions, all existing-column differences, actual physical-only definitions, default presence, model FK declarations, and affected table row counts are recorded under JSON `current.model_column_drift`. This scan compares table columns; it does not claim a complete model-versus-physical CHECK/trigger/index-equivalence proof. The physical PK/unique inventory is covered separately above. In particular, the five missing NOT NULL settings columns have **no model fallback**; filling their values or treating them as harmless nullable additions needs actual source/business evidence. No default value was invented.

## Current writer/storage facts

- Actual registered model metadata contains **374 UUID-mapped columns, all `CustomUUID`**. All 374 SQLite bind processors return 36-character hyphenated strings. `BusRoute.id`, `branch_id`, `driver_id`, and `updated_by` also use `CustomUUID`; there is no native SQLAlchemy `Uuid` writer in the inspected current model metadata.
- Every one of the 358 existing mapped PK/FK columns has physical declaration `VARCHAR(36)`. That declaration does not establish that existing stored strings have 36 characters; SQLite does not enforce the declared VARCHAR length.
- `backend/app/core/database.py` maps the Python UUID annotation to `CustomUUID`. `backend/app/core/uuid_type.py` uses native PostgreSQL UUIDs and string storage on SQLite. Valid SQLite binds are formatted with `str(uuid.UUID(...))`. Invalid input is kept as a string; invalid result values return `None`.
- SQLite ORM equality/membership compatibility strips hyphens for comparisons. This can make application reads work while raw SQLite FK equality still reports mismatches. It does not repair storage or prove raw constraints are valid; invalid IDs becoming `None` are also not a restoration.
- Revisions 002, 013, and 014 create tables from current shared metadata; many older migrations use raw `String(36)` columns. Revision 035 explicitly preserves old identifiers and only writes the new merchant scope. There is no evidence here that 035 caused these legacy differences; the collision set and invalid literal counts already exist in its backup.
- Existing ad hoc helpers demonstrate multiple historical formatting paths. `backend/scripts/normalize_sqlite_uuids.py` hardcodes Main, disables FK enforcement, deletes duplicate `class_teachers` relations, and only rewrites selected users/class-teacher values. Other legacy scripts rewrite isolated PKs or specific relationships. **None was run.** Their presence alone does not prove which historical script created a particular row.

## Minimum preservation proof before any clone DML

1. Keep Main read-only for the repair work. Use a verified consistent backup/clone and record its version, schema/constraint inventory, row counts, typed row multiset hashes, and the existing FK/invalid-literal manifests. Keep credential and personal row bodies out of reports. Account/role/permission and financial identity hashes must remain separately checkable.
2. Produce a proposed transform manifest limited to schema-approved UUID identity/reference columns and **complete 32-hex or 36-character UUID strings**. Preserve NULLs and all non-UUID literal types exactly. Include the entire FK reference closure; changing only a PK or selected tables cannot establish referential preservation.
3. Resolve the **25 natural-key collision groups** with evidence before claiming a whole-database canonical transform is executable. Each group has two different student IDs. A business identity decision or a separately reviewed schema/legacy-identity strategy is needed; automatic row deletion, merging, renumbering, constraint dropping, or silently ignoring an update is not a preservation proof.
4. Keep the **43 invalid UUID cells / 25 malformed PKs** and the **21 missing parent keys / 96 unresolved references** as explicit unresolved categories. Formatting alone cannot recover absent parents or valid UUID identities. Restoration/quarantine needs source evidence and a reversible identity/relationship manifest.
5. On a clone only, prove exact row/cardinality preservation and semantic UUID identity preservation for every changed cell; prove all other typed values unchanged. Re-evaluate every PK, unique constraint, partial index, and FK. Expected formatting-only FK improvements must be distinguished from truly missing parents. No success claim may be based on disabled FK checks or changed uniqueness rules.
6. Verify future inserts/updates using the actual current model binders with FK enforcement enabled, plus role/institution/child access, financial replay/ledger behavior, and clone restore/rollback. These are future acceptance steps, not tests run by this diagnostic task.

Storage-only canonicalization can be rehearsed for conflict-free components on an expendable clone, with a complete reversible manifest. It does not solve the student natural-key collisions, malformed primary keys or missing parents. Choosing 32 versus 36 characters alone does not remove any of those semantic blockers. A reviewed identity/alias or grandfathered natural-key strategy would be a separate schema/business change and is not applied here.

## Artifacts

- Helper: `.codex-build/local/audit-uuid-constraints-20261105.py`
- Full metadata/counts/UUID-only locator evidence: `output/main-uuid-constraint-inventory-20261105.json`
- Compact run output: `output/main-uuid-constraint-inventory-20261105.log`
- This review: `output/main-uuid-constraint-review-20261105.md`

The helper's normalization key preserves non-UUID literal types as distinct. Its proof applies to the inventoried current schema; future expression indexes or custom collations require additional SQL-equivalence review, and concurrent live writes require a fresh consistent snapshot before a repair rehearsal.
