from typing import TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    search: str | None = None
    sort_by: str | None = None
    sort_order: str = "desc"


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    legal_name: str | None = None
    tax_number: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    city: str | None = None


class OrganizationUpdate(BaseModel):
    name: str | None = None
    legal_name: str | None = None
    tax_number: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    city: str | None = None
    is_active: bool | None = None


class BranchCreate(BaseModel):
    organization_id: str
    name: str = Field(min_length=2, max_length=255)
    code: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    city: str | None = None
    capacity: int = Field(default=0, ge=0)


class BranchUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    city: str | None = None
    capacity: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class UserCreate(BaseModel):
    email: str
    password: str = Field(min_length=8)
    first_name: str
    last_name: str
    phone: str | None = None
    organization_id: str | None = None


class UserUpdate(BaseModel):
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    status: str | None = None
    password: str | None = Field(default=None, min_length=8)


class StudentCreate(BaseModel):
    organization_id: str
    branch_id: str
    class_id: str | None = None
    student_number: str | None = None
    first_name: str
    last_name: str
    gender: str | None = None
    birth_date: str | None = None
    date_of_birth: str | None = None
    enrollment_date: str | None = None
    status: str = "ACTIVE"
    address: str | None = None
    health_notes: str | None = None
    notes: str | None = None


class StudentUpdate(BaseModel):
    branch_id: str | None = None
    class_id: str | None = None
    student_number: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    gender: str | None = None
    birth_date: str | None = None
    date_of_birth: str | None = None
    status: str | None = None
    health_notes: str | None = None
    notes: str | None = None
    address: str | None = None


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


class ClassCreate(BaseModel):
    organization_id: str
    branch_id: str
    name: str
    code: str | None = None
    description: str | None = None
    capacity: int = Field(default=20, gt=0)
    academic_year: str | None = None


class ClassUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    description: str | None = None
    capacity: int | None = Field(default=None, gt=0)
    academic_year: str | None = None
    is_active: bool | None = None


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


class DebtCreate(BaseModel):
    student_id: str
    debt_type: str
    description: str | None = None
    amount: str
    due_date: str


class DebtUpdate(BaseModel):
    description: str | None = None
    amount: str | None = None
    due_date: str | None = None
    status: str | None = None


class PaymentCreate(BaseModel):
    debt_id: str
    amount: str
    payment_method: str
    notes: str | None = None


class PaymentCancel(BaseModel):
    cancel_reason: str | None = None


class AnnouncementCreate(BaseModel):
    title: str
    content: str
    audience: str
    channels: list[str]
    branch_id: str | None = None
    class_id: str | None = None
    student_id: str | None = None


class RoleAssignRequest(BaseModel):
    role_ids: list[str]


class BranchAssignRequest(BaseModel):
    branch_ids: list[str]


class ExpenseCreate(BaseModel):
    branch_id: str
    category: str
    title: str
    amount: str
    date: str
    receipt_url: str | None = None


class AppointmentCreate(BaseModel):
    teacher_id: str
    teacher_name: str
    subject: str
    date: str
    time_slot: str
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
