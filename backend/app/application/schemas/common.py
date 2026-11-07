from typing import TypeVar, Literal
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.application.schemas.cash_payments import CashPaymentCreate as PaymentCreate, CashPaymentCancel as PaymentCancel

T = TypeVar("T")


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    search: str | None = None
    sort_by: str | None = None
    sort_order: str = "desc"


class RegistryFields(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("name", "country", "capacity", "is_active", check_fields=False)
    @classmethod
    def registry_required_when_provided(cls, value):
        if value is None:
            raise ValueError("Alan boş olamaz")
        return value

    @field_validator("legal_name", "tax_number", "tax_office", "code", "phone", "email", "address", "city", mode="before", check_fields=False)
    @classmethod
    def blank_contact_is_empty(cls, value):
        return value.strip() or None if isinstance(value, str) else value


class OrganizationCreate(RegistryFields):
    name: str = Field(min_length=2, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    tax_number: str | None = Field(default=None, max_length=50)
    tax_office: str | None = Field(default=None, max_length=100)
    country: str = Field(default="Türkiye", min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=255)
    address: str | None = None
    city: str | None = Field(default=None, max_length=100)


class OrganizationUpdate(RegistryFields):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    tax_number: str | None = Field(default=None, max_length=50)
    tax_office: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=255)
    address: str | None = None
    city: str | None = Field(default=None, max_length=100)
    is_active: bool | None = Field(default=None, description="Kurum hesabının erişim durumu; yalnız ana platform yöneticisi değiştirebilir.")


class BranchCreate(RegistryFields):
    organization_id: str
    name: str = Field(min_length=2, max_length=255)
    code: str | None = Field(default=None, max_length=50)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=255)
    address: str | None = None
    city: str | None = Field(default=None, max_length=100)
    capacity: int = Field(default=0, ge=0, le=2147483647)
    is_active: bool = True

    @field_validator("organization_id")
    @classmethod
    def valid_branch_organization(cls, value):
        return str(UUID(value))


class BranchUpdate(RegistryFields):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    code: str | None = Field(default=None, max_length=50)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=255)
    address: str | None = None
    city: str | None = Field(default=None, max_length=100)
    capacity: int | None = Field(default=None, ge=0, le=2147483647)
    is_active: bool | None = None


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=8, max_length=4096)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    position: str | None = Field(default=None, max_length=100)
    department: str | None = Field(default=None, max_length=100)
    organization_id: str | None = None

    @field_validator("organization_id")
    @classmethod
    def valid_organization(cls, value):
        if not value:
            return None
        from uuid import UUID
        return str(UUID(value))


class UserUpdate(BaseModel):
    email: str | None = Field(default=None, min_length=3, max_length=255, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    position: str | None = Field(default=None, max_length=100)
    department: str | None = Field(default=None, max_length=100)
    status: Literal["ACTIVE", "PASSIVE", "BLOCKED"] | None = None
    password: str | None = Field(default=None, min_length=8, max_length=4096)

    @field_validator("email", "first_name", "last_name", "status")
    @classmethod
    def required_when_provided(cls, value, info):
        if value is None:
            raise ValueError("Alan boş olamaz")
        return value.lower() if info.field_name == "email" else value


class StudentFields(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("organization_id", "branch_id", "class_id", check_fields=False)
    @classmethod
    def valid_reference(cls, value, info):
        if info.field_name == "class_id" and not value:
            return None
        if value is None:
            raise ValueError("Alan boş olamaz")
        return str(UUID(value))

    @field_validator("first_name", "last_name", "status", check_fields=False)
    @classmethod
    def required_student_field(cls, value):
        if value is None:
            raise ValueError("Alan boş olamaz")
        return value

    @field_validator("birth_date", "date_of_birth", "enrollment_date", check_fields=False)
    @classmethod
    def valid_day(cls, value):
        return date.fromisoformat(value).isoformat() if value is not None else None

    @field_validator("gender", "status", mode="before", check_fields=False)
    @classmethod
    def normalized_enum(cls, value):
        return value.strip().upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def consistent_birth_date(self):
        if self.birth_date and self.date_of_birth and self.birth_date != self.date_of_birth:
            raise ValueError("Doğum tarihi alanları eşleşmiyor")
        return self


class StudentCreate(StudentFields):
    organization_id: str
    branch_id: str
    class_id: str | None = None
    student_number: str | None = Field(default=None, max_length=50)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    gender: Literal["MALE", "FEMALE", "OTHER"] | None = None
    birth_date: str | None = None
    date_of_birth: str | None = None
    enrollment_date: str | None = None
    status: Literal["ACTIVE", "PASSIVE", "GRADUATED", "LEFT"] = "ACTIVE"
    address: str | None = Field(default=None, max_length=500)
    health_notes: str | None = None
    notes: str | None = None


class StudentUpdate(StudentFields):
    branch_id: str | None = None
    class_id: str | None = None
    student_number: str | None = Field(default=None, max_length=50)
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    gender: Literal["MALE", "FEMALE", "OTHER"] | None = None
    birth_date: str | None = None
    date_of_birth: str | None = None
    enrollment_date: str | None = None
    status: Literal["ACTIVE", "PASSIVE", "GRADUATED", "LEFT"] | None = None
    health_notes: str | None = None
    notes: str | None = None
    address: str | None = Field(default=None, max_length=500)

    @field_validator("enrollment_date")
    @classmethod
    def enrollment_cannot_be_empty(cls, value):
        if value is None:
            raise ValueError("Kayıt tarihi boş olamaz")
        return value


class ParentCreate(BaseModel):
    first_name: str
    last_name: str
    relation_type: str = "GUARDIAN"
    phone: str | None = None
    sms_phone: str | None = None
    whatsapp_phone: str | None = None
    email: str | None = None
    address: str | None = None
    receive_notifications: bool = True
    is_primary: bool = False
    is_emergency: bool = False


class ExistingParentLink(BaseModel):
    parent_id: str
    is_primary: bool = False
    is_emergency: bool = False


class ClassFields(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("organization_id", "branch_id", "teacher_id", check_fields=False)
    @classmethod
    def valid_class_reference(cls, value, info):
        if info.field_name == "teacher_id" and not value:
            return None
        if value is None:
            raise ValueError("Alan boş olamaz")
        return str(UUID(value))

    @field_validator("name", "capacity", "is_active", check_fields=False)
    @classmethod
    def class_required_when_provided(cls, value):
        if value is None:
            raise ValueError("Alan boş olamaz")
        return value


class ClassCreate(ClassFields):
    organization_id: str
    branch_id: str
    name: str = Field(min_length=1, max_length=150)
    code: str | None = Field(default=None, max_length=50)
    description: str | None = None
    capacity: int = Field(default=20, gt=0, le=2147483647)
    academic_year: str | None = Field(default=None, max_length=20)
    teacher_id: str | None = None
    is_active: bool = True


class ClassUpdate(ClassFields):
    organization_id: str | None = None
    branch_id: str | None = None
    name: str | None = Field(default=None, min_length=1, max_length=150)
    code: str | None = Field(default=None, max_length=50)
    description: str | None = None
    capacity: int | None = Field(default=None, gt=0, le=2147483647)
    academic_year: str | None = Field(default=None, max_length=20)
    teacher_id: str | None = None
    is_active: bool | None = None


class ClassStudentAssign(BaseModel):
    student_id: UUID


class ClassStudentsAssign(BaseModel):
    student_ids: list[UUID] = Field(min_length=1, max_length=1000)

    @field_validator("student_ids")
    @classmethod
    def unique_students(cls, values):
        return list(dict.fromkeys(values))


class ClassTransferRequest(ClassStudentsAssign):
    target_class_id: UUID


class AttendanceCreate(BaseModel):
    class_id: str
    student_id: str
    attendance_date: str
    status: str
    check_in_time: str | None = None
    notes: str | None = None


class BulkAttendanceCreate(BaseModel):
    class_id: str
    attendance_date: str
    records: list[dict]


class AttendanceUpdate(BaseModel):
    status: str | None = None
    check_in_time: str | None = None
    notes: str | None = None


class DebtFields(BaseModel):
    @field_validator("student_id", check_fields=False)
    @classmethod
    def valid_debt_student(cls, value):
        return str(UUID(value)) if value is not None else value

    @field_validator("due_date", check_fields=False)
    @classmethod
    def valid_debt_day(cls, value):
        if value is None:
            raise ValueError("Vade tarihi boş olamaz")
        return date.fromisoformat(value).isoformat()

    @field_validator("amount", check_fields=False)
    @classmethod
    def debt_amount_required(cls, value):
        if value is None:
            raise ValueError("Tutar boş olamaz")
        return value


class DebtCreate(DebtFields):
    student_id: str
    debt_type: Literal["EDUCATION", "FOOD", "SERVICE", "STATIONERY", "ACTIVITY", "OTHER"]
    description: str | None = None
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2, allow_inf_nan=False)
    due_date: str


class DebtUpdate(DebtFields):
    student_id: str | None = None
    debt_type: Literal["EDUCATION", "FOOD", "SERVICE", "STATIONERY", "ACTIVITY", "OTHER"] | None = None
    description: str | None = None
    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2, allow_inf_nan=False)
    due_date: str | None = None
    status: Literal["UNPAID", "PARTIALLY_PAID", "PAID", "OVERDUE", "CANCELLED"] | None = None

    @field_validator("status")
    @classmethod
    def debt_status_required(cls, value):
        if value is None:
            raise ValueError("Borç durumu boş olamaz")
        return value


class AnnouncementCreate(BaseModel):
    title: str
    content: str
    audience: str
    channels: list[str]
    branch_id: str | None = None
    class_id: str | None = None
    student_id: str | None = None


class RoleAssignRequest(BaseModel):
    role_ids: list[str] = Field(max_length=1000)

    @field_validator("role_ids")
    @classmethod
    def valid_roles(cls, values):
        from uuid import UUID
        return list(dict.fromkeys(str(UUID(value)) for value in values))


class BranchAssignRequest(BaseModel):
    branch_ids: list[str] = Field(max_length=1000)

    @field_validator("branch_ids")
    @classmethod
    def valid_branches(cls, values):
        from uuid import UUID
        return list(dict.fromkeys(str(UUID(value)) for value in values))


class ExpenseCreate(BaseModel):
    branch_id: str
    category: str
    title: str
    amount: str
    date: str
    receipt_url: str | None = None


class AppointmentCreate(BaseModel):
    teacher_id: str
    slot_datetime: datetime | None = None
    duration_minutes: int = Field(default=30, ge=15, le=120)
    parent_note: str | None = None
    teacher_name: str | None = None
    student_id: str | None = None
    subject: str | None = None
    # The administration page submits appointment_date/appointment_time;
    # operational screens submit date/time_slot.  Accept both contracts.
    date: str | None = None
    appointment_date: str | None = None
    time_slot: str | None = None
    appointment_time: str | None = None
    type: str = "IN_PERSON"
    notes: str | None = None


class AppointmentStatusUpdate(BaseModel):
    status: str
    feedback_notes: str | None = None


class BusRouteCreate(BaseModel):
    branch_id: str
    route_name: str
    plate_number: str
    driver_name: str
    driver_phone: str
    hostess_name: str
    hostess_phone: str


class BusTelemetryUpdate(BaseModel):
    current_lat: float
    current_lng: float
    speed_kmh: int
    last_passed_stop: str
    next_stop: str
    estimated_arrival_minutes: int


class BusCheckInRequest(BaseModel):
    student_id: str
    is_morning: bool = True
    is_boarded: bool = True


class CanteenProductCreate(BaseModel):
    name: str
    category: str
    price: float
    is_available: bool = True
    barcode: str | None = None


class CanteenTopupRequest(BaseModel):
    student_id: str
    amount: float
    payment_method: str = "CREDIT_CARD"


class CanteenRestrictionUpdate(BaseModel):
    student_id: str
    daily_limit: float
    restricted_categories: list[str] = []
    restricted_allergens: list[str] = []


class CanteenPOSPurchaseRequest(BaseModel):
    student_id: str
    item_name: str
    price: float
    quantity: int = 1
    category: str = "Kantin"


class HomeworkCreate(BaseModel):
    class_id: str
    title: str
    subject: str
    description: str
    due_date: str
    attachment_url: str | None = None


class HomeworkSubmitRequest(BaseModel):
    homework_id: str
    student_id: str
    submission_text: str | None = None
    file_name: str | None = None
    file_size_mb: float = 0.0


class HomeworkGradeRequest(BaseModel):
    score: int
    teacher_feedback: str | None = None


class LibraryBookCreate(BaseModel):
    title: str
    author: str
    category: str
    isbn: str | None = None
    barcode: str | None = None
    total_copies: int = 1


class LibraryBorrowRequest(BaseModel):
    book_id: str
    student_id: str
    student_name: str
    student_number: str
    class_name: str
    duration_days: int = 14


class DutyRosterCreate(BaseModel):
    branch_id: str
    teacher_id: str
    teacher_name: str
    day_of_week: str
    duty_location: str
    start_time: str = "08:00"
    end_time: str = "17:00"


class StaffLeaveRequestCreate(BaseModel):
    staff_id: str
    staff_name: str
    leave_type: str
    start_date: str
    end_date: str
    days_count: int
    reason: str


class StaffLeaveReviewRequest(BaseModel):
    status: str
    admin_comment: str | None = None


class DailyReportCreate(BaseModel):
    student_id: str
    date: str
    meal_breakfast: str = "TAM"
    meal_lunch: str = "TAM"
    meal_snack: str = "TAM"
    sleep_status: str = "UYUDU"
    mood: str = "MUTLU"
    activities: str | None = None
    teacher_notes: str | None = None


class BulkDailyReportCreate(BaseModel):
    class_id: str
    date: str
    meal_breakfast: str = "TAM"
    meal_lunch: str = "TAM"
    meal_snack: str = "TAM"
    sleep_status: str = "UYUDU"
    mood: str = "MUTLU"
    activities: str | None = None
    teacher_notes: str | None = None


class ParentNoticeCreate(BaseModel):
    student_id: str
    type: str  # MEDICINE, LEAVE, PICKUP
    title: str
    content: str
    details: dict = {}


class ParentNoticeStatusUpdate(BaseModel):
    status: str
    response_notes: str | None = None


class ClassScheduleUpdate(BaseModel):
    schedule_data: list[dict]
