from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import MultipleResultsFound
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.middleware import (
    RequestLoggingMiddleware,
    app_exception_handler,
    generic_exception_handler,
    http_exception_handler,
    request_validation_handler,
    setup_logging,
)
from app.core.rate_limit import limiter
from app.core.routing import RouterRegistry
from app.routers import (
    admin_crud,
    attendance_editor_routes,
    appointments,
    auth,
    bus,
    canteen,
    card_numbers,
    chatbot,
    clubs,
    communications,
    consents,
    core_modules,
    dashboard,
    dashboard_reports,
    daily_reports,
    devices,
    debts,
    exams,
    expenses,
    files_receipts,
    guidance,
    hardware,
    hq,
    homework,
    data_import,
    infirmary,
    inventory,
    library,
    materials,
    messages,
    operations,
    organizations,
    platform,
    public_saas,
    subscription_payments,
    school_payment_merchant,
    school_payment_review,
    outbox,
    parent_notices,
    parent_portal,
    parents,
    payroll,
    payments,
    pickup,
    rfid_cards,
    security,
    staff_operations,
    surveys,
    teacher,
    timetable,
    tutoring,
    users,
    health,
    ai_analytics,
    students,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    yield


app = FastAPI(
    title="SCS360 API",
    description="Anaokulu, kreş, etüt ve kurs merkezleri yönetim sistemi",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)
app.add_exception_handler(MultipleResultsFound, generic_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, request_validation_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)


@app.get("/health", tags=["Health"], include_in_schema=False)
async def public_health_check():
    """Health endpoint used by the container probe and external load balancers."""
    return await health.health()


router_registry = RouterRegistry(app)
router_registry.include(health.router)
router_registry.include(auth.router)
router_registry.include(organizations.router)
router_registry.include(platform.router)
router_registry.include(public_saas.router)
router_registry.include(subscription_payments.router)
router_registry.include(school_payment_merchant.router)
router_registry.include(school_payment_review.router)
router_registry.include(users.router)
router_registry.include(staff_operations.router)
router_registry.include(admin_crud.router)
router_registry.include(attendance_editor_routes.router)
router_registry.include(core_modules.router)
router_registry.include(dashboard.router)
router_registry.include(dashboard_reports.router)
router_registry.include(daily_reports.router)
router_registry.include(homework.router)
router_registry.include(data_import.router)
router_registry.include(rfid_cards.router)
router_registry.include(card_numbers.router)
router_registry.include(devices.router)
router_registry.include(files_receipts.router)
router_registry.include(parent_notices.router)
router_registry.include(outbox.router)
router_registry.include(operations.router)
router_registry.include(expenses.router)
router_registry.include(security.router)
router_registry.include(timetable.router)
router_registry.include(exams.router)
router_registry.include(materials.router)
router_registry.include(canteen.router)
router_registry.include(infirmary.router)
router_registry.include(guidance.router)
router_registry.include(bus.router)
router_registry.include(pickup.router)
router_registry.include(communications.router)
router_registry.include(hq.router)
router_registry.include(tutoring.router)
router_registry.include(clubs.router)
router_registry.include(payroll.router)
router_registry.include(inventory.router)
router_registry.include(surveys.router)
router_registry.include(consents.router)
router_registry.include(messages.router)
router_registry.include(parent_portal.router)
router_registry.include(parents.router)
router_registry.include(payments.router)
router_registry.include(debts.router)
router_registry.include(teacher.router)
router_registry.include(appointments.router)
router_registry.include(library.router)
router_registry.include(hardware.router)
router_registry.include(ai_analytics.router)
router_registry.include(students.router)
router_registry.include(chatbot.router)
