# Remaining six missing model columns — consumer analysis

The five settings columns are **shadow-mapper metadata pollution**, while `student_teacher_assignments.updated_at` is a **live ORM projection mismatch**. They need different remedies. Adding all six physical columns would not be a preservation-safe interpretation of the metadata inventory.

Evidence was collected with `app.main` registered in a subprocess configured with an in-memory engine, without app startup, server, provider calls or migrations. Main access used URI `mode=ro` + `query_only=ON` + one read transaction. Only schema/count queries and compiled `SELECT ... LIMIT 0` were executed. INSERT statements were compiled only, never executed. No row bodies or settings/configuration values were read or exported.

The later snapshot reports Main revision **036**; the prior constraint inventory was taken at 035. This agent made no Main/schema/Core changes. Counts in the later snapshot: `app_settings=2`, `integration_settings=0`, `student_teacher_assignments=0`.

## Settings: actual registered consumers use canonical physical columns

| Registered path | Handler | Imported ORM model | Actual mapper attributes |
|---|---|---|---|
| GET /api/settings | dashboard_reports.get_settings | infrastructure AppSetting | setting_key, setting_value |
| PUT /api/settings | dashboard_reports.update_settings | infrastructure AppSetting | setting_key, setting_value |
| GET /api/settings/integrations | dashboard_reports.get_integrations | infrastructure IntegrationSetting | provider, config |
| PUT /api/settings/integrations | dashboard_reports.update_integrations | infrastructure IntegrationSetting | provider, config |

Source evidence:

- `backend/app/main.py:137` registers `dashboard_reports`; it does not import/register `routers.settings`.
- `backend/app/routers/dashboard_reports.py:21` and `:28` import the two **infrastructure** classes. Registered settings GET/PUT are at `:1320` and `:1333`; integration GET is at `:1363`, integration PUT at `:916`.
- `backend/app/infrastructure/models/models.py:639` defines IntegrationSetting with provider enum + JSON config, unique `(organization_id, provider)`.
- `backend/app/infrastructure/models/models.py:651` defines AppSetting with setting_key + JSON setting_value, unique `(organization_id, setting_key)`.

`inspect(class).column_attrs` confirms both canonical mappers omit the five disputed columns. On Main, both complete canonical ORM SELECTs with `LIMIT 0` succeed. Registered update source constructs these same canonical classes and assigns `setting_value` or `config`; it does not read/write `key`, `value`, `integration_type`, `provider_name`, or `settings`.

Compiled canonical inserts, with placeholders only:

```sql
INSERT INTO app_settings (id, organization_id, setting_key, setting_value)
VALUES (?, ?, ?, ?)

INSERT INTO integration_settings (id, organization_id, provider, config, is_active)
VALUES (?, ?, ?, ?, ?)
```

These statements were **not executed**. They demonstrate the canonical path does not supply the shadow required columns. Blindly adding those five NOT NULL/defaultless columns would impose new requirements that the registered canonical insert path does not satisfy. `create_all` built from the combined polluted Table metadata can also require those unsupplied columns on fresh databases; this is a concrete reason to test settings writes during the later model cleanup rather than treating missing Main columns as the sole problem.

## Why the combined metadata contains five extra settings columns

`backend/app/domain/entities/__init__.py:19–20` imports two separate declarative classes:

- `domain/entities/app_setting.py:10` defines a second AppSetting on `app_settings`, adding required string fields `key` and `value`.
- `domain/entities/integration_setting.py:10` defines a second IntegrationSetting on `integration_settings`, adding required string fields `integration_type`, `provider_name`, `settings`.

The shared Base's `extend_existing` behavior lets these classes extend the **same Table objects**, while the infrastructure mappers keep their original mapped-property subsets. Thus table metadata and a particular mapper's SELECT projection are not interchangeable evidence.

The domain AppSetting mapper maps both old and shadow columns; its Main SELECT fails at `app_settings.key`. The domain IntegrationSetting mapper likewise fails at `integration_settings.integration_type`. These failures were observed only through read-only `LIMIT 0` probes, not through public APIs.

The only application-source consumer of the domain AppSetting is `backend/app/routers/settings.py:36` and its legacy CRUD functions. That router is not loaded by `app.main` and none of its endpoints are registered. No active router/service consumer of the domain IntegrationSetting was found beyond its package export. The actual registry confirms the dashboard handlers above own all four live settings routes.

### Suggested canonical settings remedy — separate authorized implementation

Prefer the existing infrastructure classes and physical columns. Replace the duplicate domain declarative definitions with reexports of those canonical classes, consistent with other compatibility wrappers. Do **not** add the five shadow columns merely to satisfy polluted metadata.

If an actual compatibility consumer later needs `key`/`value`, a mapper synonym can alias `key -> setting_key` and `value -> setting_value` without adding physical fields. Preserve the existing JSON value semantics; the unused legacy router's string-only DTO is not evidence that stored JSON should be converted to text. There is no proven independent meaning for `integration_type`, and provider enum semantics must not be guessed from arbitrary `provider_name` strings. With no active consumers, a simple canonical reexport is the smaller choice; additional integration aliases require an actual caller contract.

Later acceptance should cover canonical settings/integration GET and PUT on both an existing-schema clone and fresh SQLite/PostgreSQL databases, exact JSON value preservation, institution permissions and current secret masking. No such write tests were run in this analysis.

## StudentTeacherAssignment.updated_at is used by live SQL

`backend/app/infrastructure/models/models.py:808` inherits `TimestampMixin` (`:177–181`). Its actual mapper includes both `created_at` and `updated_at`. Unlike the settings shadows, the missing timestamp is in the **canonical live mapper**. Main's full mapped SELECT with `LIMIT 0` fails with `no such column: student_teacher_assignments.updated_at`, even with zero rows.

Affected registered flow, after its ordinary access checks:

- `GET /api/v1/chatbot/students/{student_id}/teachers`: `routers/chatbot.py:705`; selects whole StudentTeacherAssignment objects joined to User at `:733`.
- `POST /api/v1/chatbot/chat/conversations/connect-teacher`: `routers/chatbot.py:807`; selects a whole assignment at `:895`.
- Teacher branch of `verify_student_access` (`chatbot.py:382`) selects a whole assignment and is used by those flows.
- Parent chatbot context (`application/services/chatbot/context_service.py:134`) also selects whole assignments. Its broad catch at `:175` logs the error and returns an empty teacher list, so this can degrade context rather than become a visible HTTP 500. Both ordinary and parent chatbot entrypoints call the shared query/context builder.

This is not a claim that every teacher-related route fails. `parent_data_service.py:167`, `core/student_access.py:73`, and teacher class scoping use scalar `teacher_id`, `student_id`, or `id` projections and do not select updated_at. The modern `/api/parent/child/{student_id}/teachers` endpoint delegates to the scalar-projection parent service (`parent_portal.py:611–618`). Existing institution/child/teacher authorization must remain unchanged.

Historical schema intent matters: migration `019_add_chatbot_teacher_integration.py:33–51` creates assignments with **created_at only**. The Pydantic `domain/entities/student_teacher.py:25–38` exposes created_at, not updated_at. No application writer/reader specifically consuming assignment.updated_at was found; whole-object reads inherit it accidentally through the generic mixin.

### Two bounded options, neither applied

1. **Model-only alignment:** if assignment modification timestamps are not a required feature, replace the inherited two-timestamp mixin for this one model with an explicit created_at mapping matching revision 019. This removes the accidental SELECT requirement without inventing history or touching Main data. Check every consumer and fresh database expectation in the implementation phase.
2. **Data-preserving additive migration:** if updated_at is intentionally part of the domain contract, add it with a reviewed default/nullability policy and clone-backed verification. Current Main has zero assignment rows, but other installations may have history; their last-modified times cannot be inferred. Existing rows should not silently receive fabricated historical update times. Any SQLite ALTER/batch strategy, default handling and rollback require dedicated acceptance before Main changes.

Rewriting only a few SELECTs to scalar projections could avoid this particular read error but would leave the canonical model/schema discrepancy and future full-object paths unresolved. Adding the five settings shadow fields does not address it.

## Artifacts and limits

- `.codex-build/local/analyze-drift-consumers-20261105.py`
- `output/drift-consumer-analysis-20261105.json`: mapper attributes versus combined Table columns, physical columns, complete read-only SELECT results, compiled-but-unexecuted INSERTs, actual registered handler/source-line inventory.
- `output/drift-consumer-analysis-20261105.log`: compact results.

This diagnostic neither changes the unresolved legacy FK/UUID/natural-key findings nor proves real end-to-end HTTP behavior. It distinguishes active SQL projection failures from unused shadow definitions so the next implementation can preserve existing data and permissions.
