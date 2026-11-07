import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.core.database import Base
from app.infrastructure.models import models  # noqa: F401
from app.domain.entities.saas import SubscriptionPlan, OrganizationSubscription, SubscriptionInvoice, SubscriptionCheckout  # noqa: F401
from app.domain.entities.bus import BusRoute, BusStop, BusTelemetryLog, BusAttendance  # noqa: F401
from app.domain.entities.canteen import CanteenProduct, CanteenDietaryRestriction, CanteenOrder, CanteenWalletTransaction  # noqa: F401
from app.domain.entities.health import HealthRecord, MedicationSchedule, MedicationLog, InfirmaryVisit  # noqa: F401
from app.domain.entities.guidance import GuidanceSession, BehavioralIncident, GuidanceNote  # noqa: F401
from app.domain.entities.pickup import PickupAuthorization, PickupLog  # noqa: F401
from app.domain.entities.exams import Exam, ExamResult, ReportCard  # noqa: F401
from app.domain.entities.materials import CourseMaterial  # noqa: F401
from app.domain.entities.security import DigitalIdToken, GateLog  # noqa: F401
from app.domain.entities.communications import SMSProvider, BroadcastJob, DeliveryReport  # noqa: F401
from app.domain.entities.hq import BranchFinancialSummary, BranchAcademicSummary  # noqa: F401
from app.domain.entities.tutoring import TutoringSession, TutoringRequest, TeacherAvailability  # noqa: F401
from app.domain.entities.clubs import SchoolClub, ClubMembership, ClubEvent, StudentCertificate  # noqa: F401
from app.domain.entities.payroll import StaffTimesheet, AdditionalCourseHours, PayrollRecord  # noqa: F401
from app.domain.entities.inventory import InventoryItem, InventoryLocation, AssetAssignment, MaintenanceRequest  # noqa: F401
from app.domain.entities.surveys import Survey, SurveyQuestion, SurveyResponse  # noqa: F401
from app.domain.entities.consents import ConsentDocument, StudentConsent  # noqa: F401

config = context.config
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
