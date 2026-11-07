# Next internal phase: recorded canteen consumers

Prepared by read-only review while the full backend suite was running. **Not implemented.** Run only after that suite finishes and a fresh usage check permits new development; no additional user approval is required for this already authorized defect correction.

Existing `app/application/services/recorded_canteen.py` has 18 service cases plus two bulk cases. It remains unwired. Do not confuse that with API/chatbot acceptance.

## Smallest source scope

- `backend/app/routers/ai_analytics.py`: the first `/canteen-analysis` registration (near996) is active; the duplicate near1800 is dead/fake-zero. Keep one canonical route using existing `AnalysisPermission(canteen.read)` and `Query(days, ge=1, le=365)`. Return `success_response(await get_recorded_canteen_summary(db, tenant, days=days, purpose='analysis'))`. Preserve service503 errors rather than catching to fake zero/raw exception text.
- `backend/app/application/services/chatbot/handlers.py`: replace the CanteenHandler's fabricated36% profit with the same service. Pass current `db.info['tenant_context']`, explicit selected student, `purpose='chatbot'`, date start and **inclusive end + one day** as exclusive end. Existing DateRange fields are already `date`; do not call `.date()`.
- `backend/app/routers/chatbot.py`: only CANTEEN intent date resolution needs a fresh `DateResolutionService(context.current_date)`. The import-time global captures a stale school date. No-period handler fallback should use `school_today()`. Do not broadly change unrelated intents during this phase.
- `frontend/src/features/canteen/CanteenSalesPage.tsx`: existing canonical string-or-null `total_sales` and `daily_average` are accepted by `recordedAmount`. Show actual period/as-of/observed days. Distinguish wallet DEBIT/direct SALE, wallet CREDIT top-ups and **separate legacy catalog orders**. Label catalog values as excluded from recorded sales; never sum the two sources. `order_count` is catalog record count, not payment receipt count. Do not restore fake product totals, confidence, profit, stock or trends. The main CanteenPage already derives product/restriction counts from real arrays; it needs no analytics-placeholder replacement.

## Access and actions

Retain native canteen permission, institution/branch scope, strict Parent purpose, selected own-child checks and Parent finance permission inside the service. Never create a wallet just to read analytics.

Old NAV_POS/FINANCE/WALLET/STOCK action tags have no mapping in Chatbot.tsx. Use existing authorized actions: native staff with canteen.read can receive VIEW_CANTEEN (/canteen); strict Parent with parent.view_finances can receive VIEW_PAYMENTS (/parent/finances). Native finance navigation additionally requires finance.read. Do not invent a new action tag, route, top-up command or stock button. Parent paths currently have no VIEW_CANTEEN mapping.

## Meaningful consumer acceptance

1. Actual SQLite/PostgreSQL HTTP: recorded sales35, top-up100, separate catalog22; one registered route; invalid days422.
2. Native canteen versus finance-only, explicit Root workspace, institution/branch boundaries.
3. Actual Parent chatbot with controlled intent: selected child, two children, mixed-role Parent purpose and missing Parent rights.
4. School-midnight/import-date staleness, inclusive/exclusive dates, year rollover and future exclusion.
5. Query503 propagates safely; no fake zero, profit or non-finite amounts.
6. UI real0/null/source labels/period/separate catalog; actual detail actions reach allowed pages without posting payment/messages.

Keep Main data unchanged, use disposable databases and no real provider/payment/message calls. Archive source/service/UI results separately; direct service/bulk results alone do not establish consumer correctness.
