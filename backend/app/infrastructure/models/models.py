import enum
import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Index,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
    JSON,
    TypeDecorator,
    text as sql_text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.core.database import Base


from app.core.uuid_type import CustomUUID

class UserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PASSIVE = "PASSIVE"
    BLOCKED = "BLOCKED"


class StudentStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PASSIVE = "PASSIVE"
    GRADUATED = "GRADUATED"
    LEFT = "LEFT"


class GenderType(str, enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"


class ParentRelationType(str, enum.Enum):
    MOTHER = "MOTHER"
    FATHER = "FATHER"
    GUARDIAN = "GUARDIAN"
    OTHER = "OTHER"


class AttendanceStatus(str, enum.Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    EXCUSED = "EXCUSED"
    LATE = "LATE"
    HALF_DAY = "HALF_DAY"


class DebtStatus(str, enum.Enum):
    UNPAID = "UNPAID"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


class DebtType(str, enum.Enum):
    EDUCATION = "EDUCATION"
    FOOD = "FOOD"
    SERVICE = "SERVICE"
    STATIONERY = "STATIONERY"
    ACTIVITY = "ACTIVITY"
    OTHER = "OTHER"


class PaymentMethod(str, enum.Enum):
    CASH = "CASH"
    CREDIT_CARD = "CREDIT_CARD"
    BANK_TRANSFER = "BANK_TRANSFER"
    EFT = "EFT"
    OTHER = "OTHER"


class ReceiptStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"


class FileCategory(str, enum.Enum):
    IDENTITY = "IDENTITY"
    HEALTH_REPORT = "HEALTH_REPORT"
    REGISTRATION_CONTRACT = "REGISTRATION_CONTRACT"
    PAYMENT_CONTRACT = "PAYMENT_CONTRACT"
    PHOTO = "PHOTO"
    OTHER = "OTHER"


class GradeType(str, enum.Enum):
    EXAM = "EXAM"
    QUIZ = "QUIZ"
    HOMEWORK = "HOMEWORK"
    PROJECT = "PROJECT"
    PARTICIPATION = "PARTICIPATION"
    MIDTERM = "MIDTERM"
    FINAL = "FINAL"


class SubjectType(str, enum.Enum):
    MATHEMATICS = "MATHEMATICS"
    SCIENCE = "SCIENCE"
    TURKISH = "TURKISH"
    SOCIAL_STUDIES = "SOCIAL_STUDIES"
    ENGLISH = "ENGLISH"
    PHYSICAL_EDUCATION = "PHYSICAL_EDUCATION"
    ART = "ART"
    MUSIC = "MUSIC"
    COMPUTER = "COMPUTER"
    RELIGION = "RELIGION"
    OTHER = "OTHER"


class NotificationChannel(str, enum.Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    WHATSAPP = "WHATSAPP"


class NotificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AnnouncementAudience(str, enum.Enum):
    ALL_PARENTS = "ALL_PARENTS"
    BRANCH_PARENTS = "BRANCH_PARENTS"
    CLASS_PARENTS = "CLASS_PARENTS"
    SINGLE_STUDENT = "SINGLE_STUDENT"


class AnnouncementStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    SENT = "SENT"
    CANCELLED = "CANCELLED"


class IntegrationProvider(str, enum.Enum):
    SMTP = "SMTP"
    NETGSM = "NETGSM"
    TWILIO = "TWILIO"
    META_WHATSAPP = "META_WHATSAPP"
    OTHER = "OTHER"


class AuditAction(str, enum.Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    PAYMENT = "PAYMENT"
    CANCEL_PAYMENT = "CANCEL_PAYMENT"
    SEND_NOTIFICATION = "SEND_NOTIFICATION"
    OTHER = "OTHER"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Organization(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    legal_name: Mapped[str | None] = mapped_column(String(255))
    tax_number: Mapped[str | None] = mapped_column(String(50))
    tax_office: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(100), default="Türkiye")
    logo_url: Mapped[str | None] = mapped_column(String(500))
    website: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(CustomUUID)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(CustomUUID)

    branches: Mapped[list["Branch"]] = relationship(back_populates="organization")


class Branch(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "branches"
    __table_args__ = (UniqueConstraint("organization_id", "code"), UniqueConstraint("organization_id", "name"))

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    name: Mapped[str] = mapped_column(String(255))
    code: Mapped[str | None] = mapped_column(String(50))
    phone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(100))
    capacity: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(CustomUUID)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(CustomUUID)

    organization: Mapped["Organization"] = relationship(back_populates="branches")


class Role(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id"))

    permissions: Mapped[list["Permission"]] = relationship(secondary="role_permissions")


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    module: Mapped[str] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id"))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(20))
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    position: Mapped[str | None] = mapped_column(String(100))
    department: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.ACTIVE)
    is_super_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(CustomUUID)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(CustomUUID)

    roles: Mapped[list["Role"]] = relationship(
        secondary="user_roles",
        primaryjoin="User.id == UserRole.user_id",
        secondaryjoin="Role.id == UserRole.role_id",
        foreign_keys="[UserRole.user_id, UserRole.role_id]",
    )
    branches: Mapped[list["Branch"]] = relationship(
        secondary="user_branches",
        primaryjoin="User.id == UserBranch.user_id",
        secondaryjoin="Branch.id == UserBranch.branch_id",
        foreign_keys="[UserBranch.user_id, UserBranch.branch_id]",
    )


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(CustomUUID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[uuid.UUID] = mapped_column(CustomUUID, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(CustomUUID, ForeignKey("users.id"))


class UserBranch(Base):
    __tablename__ = "user_branches"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id", ondelete="CASCADE"), primary_key=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(255))
    family_id: Mapped[uuid.UUID] = mapped_column(CustomUUID, default=uuid.uuid4)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("refresh_tokens.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(Text)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(255))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255))
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(Text)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    failure_reason: Mapped[str | None] = mapped_column(String(255))
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ClassRoom(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "classes"
    __table_args__ = (UniqueConstraint("branch_id", "name"),)

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id"))
    name: Mapped[str] = mapped_column(String(150))
    code: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)
    capacity: Mapped[int] = mapped_column(Integer, default=20)
    academic_year: Mapped[str | None] = mapped_column(String(20))
    teacher_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))

    students: Mapped[list["Student"]] = relationship(back_populates="class_room")


class ClassTeacher(Base):
    __tablename__ = "class_teachers"

    class_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class Parent(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "parents"

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    relation_type: Mapped[ParentRelationType] = mapped_column(
        Enum(ParentRelationType), default=ParentRelationType.GUARDIAN
    )
    phone: Mapped[str | None] = mapped_column(String(20))
    sms_phone: Mapped[str | None] = mapped_column(String(20))
    whatsapp_phone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(Text)
    receive_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class Student(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "students"
    __table_args__ = (UniqueConstraint("organization_id", "student_number"),)

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id"))
    class_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("classes.id"))
    student_number: Mapped[str | None] = mapped_column(String(50))
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    gender: Mapped[GenderType | None] = mapped_column(Enum(GenderType))
    birth_date: Mapped[date | None] = mapped_column(Date)
    enrollment_date: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    address: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[StudentStatus] = mapped_column(Enum(StudentStatus), default=StudentStatus.ACTIVE)
    photo_url: Mapped[str | None] = mapped_column(String(500))
    health_notes: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))

    class_room: Mapped["ClassRoom | None"] = relationship(back_populates="students")
    parents: Mapped[list["Parent"]] = relationship(secondary="student_parents")


class StudentParent(Base):
    __tablename__ = "student_parents"

    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), primary_key=True)
    parent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("parents.id", ondelete="CASCADE"), primary_key=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    is_emergency: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StudentFile(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "student_files"

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id"))
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    category: Mapped[FileCategory] = mapped_column(Enum(FileCategory), default=FileCategory.OTHER)
    file_name: Mapped[str] = mapped_column(String(255))
    original_name: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    file_size: Mapped[int] = mapped_column(BigInteger)
    storage_path: Mapped[str] = mapped_column(String(500))
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class AttendanceRecord(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "attendance_records"
    __table_args__ = (UniqueConstraint("student_id", "attendance_date"),)

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id"))
    class_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("classes.id"))
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"))
    attendance_date: Mapped[date] = mapped_column(Date)
    status: Mapped[AttendanceStatus] = mapped_column(Enum(AttendanceStatus))
    check_in_time: Mapped[time | None] = mapped_column(Time)
    notes: Mapped[str | None] = mapped_column(Text)
    recorded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))


class Expense(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "expenses"

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    branch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("branches.id"))
    description: Mapped[str] = mapped_column(String(500))
    category: Mapped[str] = mapped_column(String(100))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    expense_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[str] = mapped_column(String(50), default="pending")
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class Debt(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "debts"

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id"))
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"))
    debt_type: Mapped[DebtType] = mapped_column(Enum(DebtType))
    description: Mapped[str | None] = mapped_column(String(500))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    status: Mapped[DebtStatus] = mapped_column(Enum(DebtStatus), default=DebtStatus.UNPAID)
    due_date: Mapped[date] = mapped_column(Date)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))

    payments: Mapped[list["Payment"]] = relationship(back_populates="debt")

    @property
    def remaining_amount(self) -> Decimal:
        return self.amount - self.paid_amount


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id"))
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"))
    debt_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("debts.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    payment_method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod))
    payment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[str] = mapped_column(String(50), default="completed")
    notes: Mapped[str | None] = mapped_column(Text)
    received_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    cancel_reason: Mapped[str | None] = mapped_column(Text)

    debt: Mapped["Debt"] = relationship(back_populates="payments")
    receipt: Mapped["Receipt | None"] = relationship(back_populates="payment", uselist=False)


class Receipt(Base, TimestampMixin):
    __tablename__ = "receipts"

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id"))
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"))
    payment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payments.id"), unique=True)
    receipt_number: Mapped[str] = mapped_column(String(30), unique=True)
    status: Mapped[ReceiptStatus] = mapped_column(Enum(ReceiptStatus), default=ReceiptStatus.ACTIVE)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    issued_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    pdf_path: Mapped[str | None] = mapped_column(String(500))
    remaining_debt: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)

    payment: Mapped["Payment"] = relationship(back_populates="receipt")


class Announcement(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "announcements"

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    branch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("branches.id"))
    class_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("classes.id"))
    student_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("students.id"))
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    audience: Mapped[AnnouncementAudience] = mapped_column(Enum(AnnouncementAudience))
    channels: Mapped[list] = mapped_column(JSON)
    status: Mapped[AnnouncementStatus] = mapped_column(Enum(AnnouncementStatus), default=AnnouncementStatus.DRAFT)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))


class AnnouncementRecipient(Base):
    __tablename__ = "announcement_recipients"

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    announcement_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("announcements.id", ondelete="CASCADE"))
    parent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("parents.id", ondelete="CASCADE"))
    student_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("students.id"))
    channel: Mapped[NotificationChannel] = mapped_column(Enum(NotificationChannel))
    status: Mapped[NotificationStatus] = mapped_column(Enum(NotificationStatus), default=NotificationStatus.PENDING)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MessageTemplate(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "message_templates"
    __table_args__ = (UniqueConstraint("organization_id", "code"),)

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id"))
    code: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(150))
    channel: Mapped[NotificationChannel] = mapped_column(Enum(NotificationChannel))
    subject: Mapped[str | None] = mapped_column(String(255))
    body_template: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class NotificationJob(Base, TimestampMixin):
    __tablename__ = "notification_jobs"

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    branch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("branches.id"))
    channel: Mapped[NotificationChannel] = mapped_column(Enum(NotificationChannel))
    template_code: Mapped[str | None] = mapped_column(String(100))
    subject: Mapped[str | None] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[NotificationStatus] = mapped_column(Enum(NotificationStatus), default=NotificationStatus.PENDING)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lock_token: Mapped[uuid.UUID | None] = mapped_column(CustomUUID)
    reference_type: Mapped[str | None] = mapped_column(String(50))
    reference_id: Mapped[uuid.UUID | None] = mapped_column(CustomUUID)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))

    recipients: Mapped[list["NotificationRecipient"]] = relationship(back_populates="job")


class NotificationRecipient(Base, TimestampMixin):
    __tablename__ = "notification_recipients"

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    notification_job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("notification_jobs.id", ondelete="CASCADE"))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("parents.id"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    recipient_name: Mapped[str | None] = mapped_column(String(200))
    recipient_address: Mapped[str] = mapped_column(String(255))
    status: Mapped[NotificationStatus] = mapped_column(Enum(NotificationStatus), default=NotificationStatus.PENDING)
    provider_response: Mapped[dict | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    job: Mapped["NotificationJob"] = relationship(back_populates="recipients")


class IntegrationSetting(Base, TimestampMixin):
    __tablename__ = "integration_settings"
    __table_args__ = (UniqueConstraint("organization_id", "provider"),)

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    provider: Mapped[IntegrationProvider] = mapped_column(Enum(IntegrationProvider))
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class AppSetting(Base, TimestampMixin):
    __tablename__ = "app_settings"
    __table_args__ = (UniqueConstraint("organization_id", "setting_key"),)

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id"))
    setting_key: Mapped[str] = mapped_column(String(100))
    setting_value: Mapped[dict] = mapped_column(JSON, default=dict)
    description: Mapped[str | None] = mapped_column(Text)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id"))
    branch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("branches.id"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[AuditAction] = mapped_column(Enum(AuditAction))
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(CustomUUID)
    old_values: Mapped[dict | None] = mapped_column(JSON)
    new_values: Mapped[dict | None] = mapped_column(JSON)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CardType(str, enum.Enum):
    STUDENT = "STUDENT"
    STAFF = "STAFF"


class CardStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    BLOCKED = "BLOCKED"


class CardNumberStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    ASSIGNED = "ASSIGNED"
    DAMAGED = "DAMAGED"
    LOST = "LOST"


class CardNumber(Base, TimestampMixin):
    __tablename__ = "card_numbers"
    __table_args__ = (UniqueConstraint("card_number", "organization_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    branch_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    card_number: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="AVAILABLE")  # AVAILABLE, ASSIGNED, DAMAGED, LOST
    notes: Mapped[str | None] = mapped_column(Text)
    purchased_date: Mapped[date | None] = mapped_column(Date)
    supplier: Mapped[str | None] = mapped_column(String(255))


class DeviceStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    MAINTENANCE = "MAINTENANCE"
    BROKEN = "BROKEN"


class DeviceType(str, enum.Enum):
    TURNSTILE = "TURNSTILE"
    CARD_READER = "CARD_READER"
    DOOR_LOCK = "DOOR_LOCK"
    ATTENDANCE_KIOSK = "ATTENDANCE_KIOSK"
    CANTEEN_TERMINAL = "CANTEEN_TERMINAL"


class Device(Base, TimestampMixin):
    __tablename__ = "devices"
    __table_args__ = (UniqueConstraint("serial_number", "organization_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    branch_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    device_type: Mapped[str] = mapped_column(String(50), nullable=False)  # TURNSTILE, CARD_READER, DOOR_LOCK, ATTENDANCE_KIOSK, CANTEEN_TERMINAL
    serial_number: Mapped[str] = mapped_column(String(100), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(50))
    location: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")  # ACTIVE, INACTIVE, MAINTENANCE, BROKEN
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime)
    notes: Mapped[str | None] = mapped_column(Text)



class RfidCard(Base, TimestampMixin):
    __tablename__ = "rfid_cards"
    __table_args__ = (UniqueConstraint("card_number", "organization_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    branch_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    card_number: Mapped[str] = mapped_column(String(50), nullable=False)
    card_type: Mapped[str] = mapped_column(String(20), nullable=False)  # STUDENT or STAFF
    holder_id: Mapped[str] = mapped_column(String(100), nullable=False)
    holder_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")  # ACTIVE, INACTIVE, BLOCKED
    issue_date: Mapped[date | None] = mapped_column(Date)
    expiry_date: Mapped[date | None] = mapped_column(Date)


class DailyDevelopmentReport(Base, TimestampMixin):
    __tablename__ = "daily_development_reports"
    __table_args__ = (UniqueConstraint("student_id", "date", name="unique_student_date_report"),)

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    class_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"))
    date: Mapped[date] = mapped_column(Date, nullable=False)
    meal_status: Mapped[str | None] = mapped_column(String(30))  # ALL, HALF, NONE
    sleep_status: Mapped[str | None] = mapped_column(String(30))  # SLEPT_WELL, SHORT, NO_SLEEP
    mood: Mapped[str | None] = mapped_column(String(50))  # HAPPY, CALM, UNSETTLED, TIRED
    activities: Mapped[list[str] | None] = mapped_column(JSON)
    teacher_notes: Mapped[str | None] = mapped_column(Text)
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class ChatMessage(Base, TimestampMixin):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("chat_conversations.id", ondelete="CASCADE"))
    sender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    sender_role: Mapped[str | None] = mapped_column(String(20))  # 'PARENT', 'TEACHER', 'SYSTEM'
    recipient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    class_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_url: Mapped[str | None] = mapped_column(String(500))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ChatConversation(Base, TimestampMixin):
    __tablename__ = "chat_conversations"

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    parent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    teacher_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    subject_context: Mapped[str] = mapped_column(String(150), nullable=False)
    last_message: Mapped[str | None] = mapped_column(Text)
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    parent_unread_count: Mapped[int] = mapped_column(Integer, default=0)
    teacher_unread_count: Mapped[int] = mapped_column(Integer, default=0)
    created_via: Mapped[str] = mapped_column(String(30), default="CHATBOT")  # 'CHATBOT' or 'DIRECT'
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class StudentTeacherAssignment(Base):
    __tablename__ = "student_teacher_assignments"
    __table_args__ = (UniqueConstraint("student_id", "teacher_id", "subject_name"),)

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    teacher_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    subject_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_primary_adviser: Mapped[bool] = mapped_column(Boolean, default=False)
    office_hours: Mapped[str | None] = mapped_column(String(50), default="08:30 - 17:30")
    academic_year: Mapped[str | None] = mapped_column(String(20), default="2025-2026")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TimetableSlot(Base, TimestampMixin):
    __tablename__ = "timetable_slots"

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    day: Mapped[str] = mapped_column(String(20), nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_break: Mapped[bool] = mapped_column(Boolean, default=False)


class ClassroomAssignment(Base, TimestampMixin):
    __tablename__ = "classroom_assignments"

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    class_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"))
    teacher_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    subject_id: Mapped[str | None] = mapped_column(String(32))
    room_number: Mapped[str | None] = mapped_column(String(50))
    capacity: Mapped[int] = mapped_column(Integer, default=30)


class Timetable(Base, TimestampMixin):
    __tablename__ = "timetables"

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    class_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"))
    slot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("timetable_slots.id", ondelete="CASCADE"))
    classroom_assignment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("classroom_assignments.id", ondelete="SET NULL"))
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False)
    semester: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Grade(Base, TimestampMixin):
    __tablename__ = "grades"
    __table_args__ = (UniqueConstraint("student_id", "subject", "grade_type", "exam_date"),)

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id"))
    class_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("classes.id"))
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"))
    teacher_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    subject: Mapped[SubjectType] = mapped_column(Enum(SubjectType))
    grade_type: Mapped[GradeType] = mapped_column(Enum(GradeType))
    score: Mapped[Decimal] = mapped_column(Numeric(5, 2))  # 0.00 to 100.00
    max_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=100)
    exam_date: Mapped[date] = mapped_column(Date)
    term: Mapped[str | None] = mapped_column(String(20))  # e.g., "2024-2025", "Fall 2024"
    notes: Mapped[str | None] = mapped_column(Text)


class SentimentType(str, enum.Enum):
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    QUESTION = "QUESTION"
    CRITICAL = "CRITICAL"


class FeedbackStatus(str, enum.Enum):
    VERIFIED = "VERIFIED"
    CORRECTED = "CORRECTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class AiChatAuditLog(Base, TimestampMixin):
    """Chatbot conversation audit log for LLM fine-tuning and analytics."""
    __tablename__ = "ai_chat_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    user_query: Mapped[str] = mapped_column(Text, nullable=False)
    ai_response: Mapped[str] = mapped_column(Text, nullable=False)
    detected_intent: Mapped[str] = mapped_column(String(50), nullable=True)
    topic_category: Mapped[str] = mapped_column(String(100), nullable=True)
    sentiment: Mapped[SentimentType] = mapped_column(Enum(SentimentType), default=SentimentType.NEUTRAL)
    quality_rating: Mapped[int] = mapped_column(Integer, default=0)  # 1-5 rating
    feedback_status: Mapped[FeedbackStatus] = mapped_column(Enum(FeedbackStatus), default=FeedbackStatus.NEEDS_REVIEW)
    corrected_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    is_fine_tuning_ready: Mapped[bool] = mapped_column(Boolean, default=False)
    meta_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class LibraryBook(Base, TimestampMixin):
    __tablename__ = "library_books"
    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    title: Mapped[str] = mapped_column(String(255))
    author: Mapped[str] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(100))
    isbn: Mapped[str | None] = mapped_column(String(32))
    barcode: Mapped[str | None] = mapped_column(String(100))
    total_copies: Mapped[int] = mapped_column(Integer, default=1)
    available_copies: Mapped[int] = mapped_column(Integer, default=1)
    publisher: Mapped[str | None] = mapped_column(String(255))
    publication_year: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(255))


class LibraryLoan(Base, TimestampMixin):
    __tablename__ = "library_loans"
    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    book_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("library_books.id"))
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"))
    borrow_date: Mapped[date] = mapped_column(Date, default=date.today)
    due_date: Mapped[date] = mapped_column(Date)
    return_date: Mapped[date | None] = mapped_column(Date)
    loaned_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    returned_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    borrowed_date = synonym("borrow_date")
    returned_date = synonym("return_date")


# Both established API spellings use the same persistent records.
Book = LibraryBook
BookLoan = LibraryLoan


class Appointment(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "appointments"
    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    teacher_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"))
    parent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    slot_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[str] = mapped_column(String(30), default="CONFIRMED")
    parent_note: Mapped[str | None] = mapped_column(Text)
    teacher_note: Mapped[str | None] = mapped_column(Text)


class TimeSlot(Base, TimestampMixin):
    __tablename__ = "appointment_time_slots"
    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    teacher_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)


class OperationalRecord(Base, TimestampMixin):
    __tablename__ = "operational_records"
    __table_args__ = (UniqueConstraint("organization_id", "kind", "reference_key"),)

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    branch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("branches.id"))
    class_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("classes.id"))
    staff_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(String(30))
    reference_key: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class StudentWallet(Base, TimestampMixin):
    __tablename__ = "student_wallets"

    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"), primary_key=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    daily_limit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    spent_date: Mapped[date | None] = mapped_column(Date)
    today_spent: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    restricted_categories: Mapped[list] = mapped_column(JSON, default=list)
    restricted_allergens: Mapped[list] = mapped_column(JSON, default=list)


class UserDeviceToken(Base, TimestampMixin):
    __tablename__ = "user_device_tokens"

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    token: Mapped[str] = mapped_column(Text)


class SchoolPaymentMerchant(Base, TimestampMixin):
    __tablename__ = "school_payment_merchants"
    __table_args__ = (Index("uq_school_payment_merchant_current_org", "organization_id", unique=True,
        sqlite_where=sql_text("is_current = 1"), postgresql_where=sql_text("is_current IS TRUE")),)

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    environment: Mapped[str] = mapped_column(String(10))
    credentials_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    updated_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))


class PaymentCheckout(Base, TimestampMixin):
    __tablename__ = "payment_checkouts"
    __table_args__ = (UniqueConstraint("merchant_scope", "provider_payment_id", name="uq_payment_checkout_merchant_provider"),)

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    debt_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("debts.id"))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="TRY")
    token_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    provider_payment_id: Mapped[str | None] = mapped_column(String(100))
    payment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("payments.id"), unique=True)
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    merchant_account_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("school_payment_merchants.id"), nullable=True)
    merchant_scope: Mapped[str | None] = mapped_column(String(100), nullable=True)
    merchant_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    checkout_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_transaction_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    paid_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    paid_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    verified_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    review_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ParentNotice(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "parent_notices"

    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"))
    type: Mapped[str] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))


class Homework(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "homework"
    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    class_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("classes.id"))
    title: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    due_date: Mapped[date | None] = mapped_column(Date)
    attachment_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))


class HomeworkSubmission(Base, TimestampMixin):
    __tablename__ = "homework_submissions"
    __table_args__ = (UniqueConstraint("homework_id", "student_id"),)
    id: Mapped[uuid.UUID] = mapped_column(CustomUUID, primary_key=True, default=uuid.uuid4)
    homework_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("homework.id"))
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"))
    submission_text: Mapped[str | None] = mapped_column(Text)
    attachment_file_name: Mapped[str | None] = mapped_column(String(255))
    attachment_file_size_mb: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[str] = mapped_column(String(30), default="SUBMITTED")
    score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    teacher_feedback: Mapped[str | None] = mapped_column(Text)
