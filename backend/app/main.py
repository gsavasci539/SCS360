from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.middleware import (
    RequestLoggingMiddleware,
    app_exception_handler,
    generic_exception_handler,
    setup_logging,
)
from app.core.rate_limit import limiter
from app.routers import (
    admin_crud,
    appointments,
    auth,
    bus,
    canteen,
    card_numbers,
    clubs,
    communications,
    consents,
    core_modules,
    dashboard,
    dashboard_reports,
    daily_reports,
    devices,
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
    outbox,
    parent_notices,
    parent_portal,
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
    title="EduPanel API",
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(organizations.router)
app.include_router(users.router)
app.include_router(staff_operations.router)
app.include_router(admin_crud.router)
app.include_router(core_modules.router)
app.include_router(dashboard.router)
app.include_router(dashboard_reports.router)
app.include_router(daily_reports.router)
app.include_router(homework.router)
app.include_router(data_import.router)
app.include_router(rfid_cards.router)
app.include_router(card_numbers.router)
app.include_router(devices.router)
app.include_router(files_receipts.router)
app.include_router(operations.router)
app.include_router(expenses.router)
app.include_router(parent_notices.router)
app.include_router(outbox.router)
app.include_router(security.router)
app.include_router(timetable.router)
app.include_router(exams.router)
app.include_router(materials.router)
app.include_router(canteen.router)
app.include_router(infirmary.router)
app.include_router(guidance.router)
app.include_router(bus.router)
app.include_router(pickup.router)
app.include_router(communications.router)
app.include_router(hq.router)
app.include_router(tutoring.router)
app.include_router(clubs.router)
app.include_router(payroll.router)
app.include_router(inventory.router)
app.include_router(surveys.router)
app.include_router(consents.router)
app.include_router(messages.router)
app.include_router(parent_portal.router)
app.include_router(payments.router)
app.include_router(teacher.router)
app.include_router(appointments.router)
app.include_router(library.router)
app.include_router(hardware.router)
app.include_router(ai_analytics.router)
app.include_router(students.router)
