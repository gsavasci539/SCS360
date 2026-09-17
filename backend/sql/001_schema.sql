-- EduPanel PostgreSQL Schema v1.0.0
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TYPE user_status AS ENUM ('ACTIVE', 'PASSIVE', 'BLOCKED');
CREATE TYPE student_status AS ENUM ('ACTIVE', 'PASSIVE', 'GRADUATED', 'LEFT');
CREATE TYPE gender_type AS ENUM ('MALE', 'FEMALE', 'OTHER');
CREATE TYPE parent_relation_type AS ENUM ('MOTHER', 'FATHER', 'GUARDIAN', 'OTHER');
CREATE TYPE attendance_status AS ENUM ('PRESENT', 'ABSENT', 'EXCUSED', 'LATE', 'HALF_DAY');
CREATE TYPE debt_status AS ENUM ('UNPAID', 'PARTIALLY_PAID', 'PAID', 'OVERDUE', 'CANCELLED');
CREATE TYPE debt_type AS ENUM ('EDUCATION', 'FOOD', 'SERVICE', 'STATIONERY', 'ACTIVITY', 'OTHER');
CREATE TYPE payment_method AS ENUM ('CASH', 'CREDIT_CARD', 'BANK_TRANSFER', 'EFT', 'OTHER');
CREATE TYPE receipt_status AS ENUM ('ACTIVE', 'CANCELLED');
CREATE TYPE file_category AS ENUM ('IDENTITY', 'HEALTH_REPORT', 'REGISTRATION_CONTRACT', 'PAYMENT_CONTRACT', 'PHOTO', 'OTHER');
CREATE TYPE notification_channel AS ENUM ('EMAIL', 'SMS', 'WHATSAPP');
CREATE TYPE notification_status AS ENUM ('PENDING', 'SENT', 'FAILED', 'CANCELLED');
CREATE TYPE announcement_audience AS ENUM ('ALL_PARENTS', 'BRANCH_PARENTS', 'CLASS_PARENTS', 'SINGLE_STUDENT');
CREATE TYPE announcement_status AS ENUM ('DRAFT', 'SCHEDULED', 'SENT', 'CANCELLED');
CREATE TYPE integration_provider AS ENUM ('SMTP', 'NETGSM', 'TWILIO', 'META_WHATSAPP', 'OTHER');
CREATE TYPE audit_action AS ENUM ('CREATE', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT', 'PAYMENT', 'CANCEL_PAYMENT', 'SEND_NOTIFICATION', 'OTHER');

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    legal_name VARCHAR(255),
    tax_number VARCHAR(50),
    tax_office VARCHAR(100),
    phone VARCHAR(20),
    email VARCHAR(255),
    address TEXT,
    city VARCHAR(100),
    country VARCHAR(100) DEFAULT 'Türkiye',
    logo_url VARCHAR(500),
    website VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    created_by UUID,
    updated_by UUID,
    CONSTRAINT uq_organizations_name UNIQUE (name)
);

CREATE INDEX idx_organizations_active ON organizations (is_active) WHERE deleted_at IS NULL;
CREATE TRIGGER trg_organizations_updated_at BEFORE UPDATE ON organizations FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE branches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50),
    phone VARCHAR(20),
    email VARCHAR(255),
    address TEXT,
    city VARCHAR(100),
    capacity INTEGER NOT NULL DEFAULT 0 CHECK (capacity >= 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    created_by UUID,
    updated_by UUID,
    CONSTRAINT uq_branches_org_code UNIQUE (organization_id, code),
    CONSTRAINT uq_branches_org_name UNIQUE (organization_id, name)
);

CREATE INDEX idx_branches_organization_id ON branches (organization_id);
CREATE TRIGGER trg_branches_updated_at BEFORE UPDATE ON branches FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) NOT NULL,
    description TEXT,
    is_system BOOLEAN NOT NULL DEFAULT FALSE,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_roles_slug_org UNIQUE (slug, organization_id)
);

CREATE TRIGGER trg_roles_updated_at BEFORE UPDATE ON roles FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(150) NOT NULL,
    module VARCHAR(50) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE role_permissions (
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE RESTRICT,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    status user_status NOT NULL DEFAULT 'ACTIVE',
    is_super_admin BOOLEAN NOT NULL DEFAULT FALSE,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    created_by UUID,
    updated_by UUID,
    CONSTRAINT uq_users_email UNIQUE (email),
    CONSTRAINT chk_users_super_admin_org CHECK (
        (is_super_admin = TRUE AND organization_id IS NULL) OR
        (is_super_admin = FALSE AND organization_id IS NOT NULL)
    )
);

CREATE INDEX idx_users_organization_id ON users (organization_id);
CREATE INDEX idx_users_email_active ON users (email) WHERE deleted_at IS NULL;
CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE user_roles (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    assigned_by UUID REFERENCES users(id),
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE user_branches (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    assigned_by UUID REFERENCES users(id),
    PRIMARY KEY (user_id, branch_id)
);

CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    family_id UUID NOT NULL DEFAULT gen_random_uuid(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    replaced_by UUID REFERENCES refresh_tokens(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT
);

CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens (user_id);
CREATE INDEX idx_refresh_tokens_token_hash ON refresh_tokens (token_hash);

CREATE TABLE password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE login_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL,
    ip_address INET,
    user_agent TEXT,
    success BOOLEAN NOT NULL DEFAULT FALSE,
    failure_reason VARCHAR(255),
    attempted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_login_attempts_email_time ON login_attempts (email, attempted_at DESC);

CREATE TABLE classes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE RESTRICT,
    name VARCHAR(150) NOT NULL,
    code VARCHAR(50),
    description TEXT,
    capacity INTEGER NOT NULL DEFAULT 20 CHECK (capacity > 0),
    academic_year VARCHAR(20),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    CONSTRAINT uq_classes_branch_name UNIQUE (branch_id, name)
);

CREATE INDEX idx_classes_branch_id ON classes (branch_id);
CREATE TRIGGER trg_classes_updated_at BEFORE UPDATE ON classes FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE class_teachers (
    class_id UUID NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    assigned_by UUID REFERENCES users(id),
    PRIMARY KEY (class_id, user_id)
);

CREATE TABLE parents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    relation_type parent_relation_type NOT NULL DEFAULT 'GUARDIAN',
    phone VARCHAR(20),
    sms_phone VARCHAR(20),
    whatsapp_phone VARCHAR(20),
    email VARCHAR(255),
    address TEXT,
    receive_notifications BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id)
);

CREATE INDEX idx_parents_organization_id ON parents (organization_id);
CREATE TRIGGER trg_parents_updated_at BEFORE UPDATE ON parents FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE students (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE RESTRICT,
    class_id UUID REFERENCES classes(id) ON DELETE SET NULL,
    student_number VARCHAR(50),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    gender gender_type,
    birth_date DATE,
    enrollment_date DATE NOT NULL DEFAULT CURRENT_DATE,
    status student_status NOT NULL DEFAULT 'ACTIVE',
    photo_url VARCHAR(500),
    health_notes TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    CONSTRAINT uq_students_org_number UNIQUE (organization_id, student_number)
);

CREATE INDEX idx_students_branch_id ON students (branch_id);
CREATE INDEX idx_students_class_id ON students (class_id);
CREATE TRIGGER trg_students_updated_at BEFORE UPDATE ON students FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE student_parents (
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    parent_id UUID NOT NULL REFERENCES parents(id) ON DELETE CASCADE,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    is_emergency BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (student_id, parent_id)
);

CREATE TABLE student_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE RESTRICT,
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    category file_category NOT NULL DEFAULT 'OTHER',
    file_name VARCHAR(255) NOT NULL,
    original_name VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    file_size BIGINT NOT NULL CHECK (file_size > 0),
    storage_path VARCHAR(500) NOT NULL,
    uploaded_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_student_files_student_id ON student_files (student_id);
CREATE TRIGGER trg_student_files_updated_at BEFORE UPDATE ON student_files FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE attendance_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE RESTRICT,
    class_id UUID NOT NULL REFERENCES classes(id) ON DELETE RESTRICT,
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE RESTRICT,
    attendance_date DATE NOT NULL,
    status attendance_status NOT NULL,
    check_in_time TIME,
    notes TEXT,
    recorded_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_attendance_student_date UNIQUE (student_id, attendance_date)
);

CREATE INDEX idx_attendance_class_date ON attendance_records (class_id, attendance_date);
CREATE TRIGGER trg_attendance_updated_at BEFORE UPDATE ON attendance_records FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE debts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE RESTRICT,
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE RESTRICT,
    debt_type debt_type NOT NULL,
    description VARCHAR(500),
    amount NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    paid_amount NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (paid_amount >= 0),
    remaining_amount NUMERIC(12,2) GENERATED ALWAYS AS (amount - paid_amount) STORED,
    status debt_status NOT NULL DEFAULT 'UNPAID',
    due_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    CONSTRAINT chk_debts_paid_not_exceed CHECK (paid_amount <= amount)
);

CREATE INDEX idx_debts_student_id ON debts (student_id);
CREATE INDEX idx_debts_status ON debts (status);
CREATE TRIGGER trg_debts_updated_at BEFORE UPDATE ON debts FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE RESTRICT,
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE RESTRICT,
    debt_id UUID NOT NULL REFERENCES debts(id) ON DELETE RESTRICT,
    amount NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    payment_method payment_method NOT NULL,
    payment_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notes TEXT,
    received_by UUID NOT NULL REFERENCES users(id),
    cancelled_at TIMESTAMPTZ,
    cancelled_by UUID REFERENCES users(id),
    cancel_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_payments_cancel_consistency CHECK (
        (cancelled_at IS NULL AND cancelled_by IS NULL) OR
        (cancelled_at IS NOT NULL AND cancelled_by IS NOT NULL)
    )
);

CREATE INDEX idx_payments_debt_id ON payments (debt_id);
CREATE INDEX idx_payments_student_id ON payments (student_id);
CREATE TRIGGER trg_payments_updated_at BEFORE UPDATE ON payments FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE SEQUENCE receipt_number_seq START 1;

CREATE TABLE receipts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE RESTRICT,
    payment_id UUID NOT NULL UNIQUE REFERENCES payments(id) ON DELETE RESTRICT,
    receipt_number VARCHAR(30) NOT NULL UNIQUE,
    status receipt_status NOT NULL DEFAULT 'ACTIVE',
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    issued_by UUID NOT NULL REFERENCES users(id),
    pdf_path VARCHAR(500),
    remaining_debt NUMERIC(12,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_receipts_receipt_number ON receipts (receipt_number);
CREATE TRIGGER trg_receipts_updated_at BEFORE UPDATE ON receipts FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE OR REPLACE FUNCTION generate_receipt_number()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.receipt_number IS NULL OR NEW.receipt_number = '' THEN
        NEW.receipt_number := 'RCP-' || TO_CHAR(NOW(), 'YYYYMMDD') || '-' ||
            LPAD(nextval('receipt_number_seq')::TEXT, 6, '0');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_receipts_generate_number BEFORE INSERT ON receipts FOR EACH ROW EXECUTE FUNCTION generate_receipt_number();

CREATE TABLE announcements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    branch_id UUID REFERENCES branches(id) ON DELETE SET NULL,
    class_id UUID REFERENCES classes(id) ON DELETE SET NULL,
    student_id UUID REFERENCES students(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    audience announcement_audience NOT NULL,
    channels notification_channel[] NOT NULL DEFAULT '{EMAIL}',
    status announcement_status NOT NULL DEFAULT 'DRAFT',
    scheduled_at TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TRIGGER trg_announcements_updated_at BEFORE UPDATE ON announcements FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE announcement_recipients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    announcement_id UUID NOT NULL REFERENCES announcements(id) ON DELETE CASCADE,
    parent_id UUID NOT NULL REFERENCES parents(id) ON DELETE CASCADE,
    student_id UUID REFERENCES students(id) ON DELETE SET NULL,
    channel notification_channel NOT NULL,
    status notification_status NOT NULL DEFAULT 'PENDING',
    sent_at TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE message_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    code VARCHAR(100) NOT NULL,
    name VARCHAR(150) NOT NULL,
    channel notification_channel NOT NULL,
    subject VARCHAR(255),
    body_template TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_message_templates_code_org UNIQUE (organization_id, code)
);

CREATE TRIGGER trg_message_templates_updated_at BEFORE UPDATE ON message_templates FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE notification_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    branch_id UUID REFERENCES branches(id) ON DELETE SET NULL,
    channel notification_channel NOT NULL,
    template_code VARCHAR(100),
    subject VARCHAR(255),
    body TEXT NOT NULL,
    status notification_status NOT NULL DEFAULT 'PENDING',
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    scheduled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    reference_type VARCHAR(50),
    reference_id UUID,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notification_jobs_pending ON notification_jobs (status) WHERE status = 'PENDING';
CREATE TRIGGER trg_notification_jobs_updated_at BEFORE UPDATE ON notification_jobs FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE notification_recipients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    notification_job_id UUID NOT NULL REFERENCES notification_jobs(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES parents(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    recipient_name VARCHAR(200),
    recipient_address VARCHAR(255) NOT NULL,
    status notification_status NOT NULL DEFAULT 'PENDING',
    provider_response JSONB,
    error_message TEXT,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_notification_recipients_updated_at BEFORE UPDATE ON notification_recipients FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE integration_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    provider integration_provider NOT NULL,
    config JSONB NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by UUID REFERENCES users(id),
    CONSTRAINT uq_integration_org_provider UNIQUE (organization_id, provider)
);

CREATE TRIGGER trg_integration_settings_updated_at BEFORE UPDATE ON integration_settings FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE app_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    setting_key VARCHAR(100) NOT NULL,
    setting_value JSONB NOT NULL DEFAULT '{}',
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by UUID REFERENCES users(id),
    CONSTRAINT uq_app_settings_key_org UNIQUE (organization_id, setting_key)
);

CREATE TRIGGER trg_app_settings_updated_at BEFORE UPDATE ON app_settings FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    branch_id UUID REFERENCES branches(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action audit_action NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id UUID,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_org ON audit_logs (organization_id, created_at DESC);

-- ==================== NEW MODULES SCHEMA ====================

-- Digital ID & Gate Validator Module
CREATE TYPE gate_direction AS ENUM ('IN', 'OUT');
CREATE TYPE gate_status AS ENUM ('AUTHORIZED', 'UNAUTHORIZED', 'PENDING', 'BLOCKED');
CREATE TYPE id_token_status AS ENUM ('ACTIVE', 'EXPIRED', 'REVOKED');

CREATE TABLE digital_id_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL UNIQUE,
    qr_code_url VARCHAR(500),
    barcode_number VARCHAR(100) UNIQUE,
    status id_token_status NOT NULL DEFAULT 'ACTIVE',
    expires_at TIMESTAMPTZ,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_digital_id_tokens_student ON digital_id_tokens (student_id);
CREATE INDEX idx_digital_id_tokens_token ON digital_id_tokens (token);
CREATE TRIGGER trg_digital_id_tokens_updated_at BEFORE UPDATE ON digital_id_tokens FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE gate_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    branch_id UUID REFERENCES branches(id) ON DELETE SET NULL,
    direction gate_direction NOT NULL,
    status gate_status NOT NULL,
    gate_location VARCHAR(100),
    verified_by UUID REFERENCES users(id) ON DELETE SET NULL,
    verification_method VARCHAR(50) DEFAULT 'QR',
    parent_pickup_permission BOOLEAN DEFAULT TRUE,
    service_permission BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_gate_logs_student ON gate_logs (student_id, created_at DESC);
CREATE INDEX idx_gate_logs_branch ON gate_logs (branch_id, created_at DESC);
CREATE INDEX idx_gate_logs_date ON gate_logs (created_at DESC);

-- Timetable/Schedule Builder Module
CREATE TYPE timetable_day AS ENUM ('MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY');

CREATE TABLE timetable_slots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    day timetable_day NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    is_break BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_timetable_slots_time CHECK (end_time > start_time)
);

CREATE INDEX idx_timetable_slots_day ON timetable_slots (day, start_time);
CREATE TRIGGER trg_timetable_slots_updated_at BEFORE UPDATE ON timetable_slots FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE classroom_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    class_id UUID NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    teacher_id UUID REFERENCES users(id) ON DELETE SET NULL,
    subject_id UUID,
    room_number VARCHAR(50),
    capacity INTEGER DEFAULT 30,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_classroom_assignments_class ON classroom_assignments (class_id);
CREATE INDEX idx_classroom_assignments_teacher ON classroom_assignments (teacher_id);
CREATE TRIGGER trg_classroom_assignments_updated_at BEFORE UPDATE ON classroom_assignments FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE timetables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    class_id UUID NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    slot_id UUID NOT NULL REFERENCES timetable_slots(id) ON DELETE CASCADE,
    classroom_assignment_id UUID REFERENCES classroom_assignments(id) ON DELETE SET NULL,
    academic_year VARCHAR(20) NOT NULL,
    semester VARCHAR(20) DEFAULT 'FALL',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    CONSTRAINT uq_timetables_class_slot UNIQUE (class_id, slot_id, academic_year, semester)
);

CREATE INDEX idx_timetables_class ON timetables (class_id, academic_year, semester);
CREATE INDEX idx_timetables_slot ON timetables (slot_id);
CREATE INDEX idx_timetables_teacher ON timetables (classroom_assignment_id);
CREATE TRIGGER trg_timetables_updated_at BEFORE UPDATE ON timetables FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Exams & Report Card Generator Module
CREATE TYPE exam_type AS ENUM ('MIDTERM', 'FINAL', 'QUIZ', 'MAKEUP', 'PROJECT', 'OTHER');
CREATE TYPE exam_status AS ENUM ('SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED');
CREATE TYPE grade_scale AS ENUM ('A', 'B', 'C', 'D', 'F', 'PASS', 'FAIL');

CREATE TABLE exams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    class_id UUID NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    subject_id UUID,
    teacher_id UUID REFERENCES users(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    exam_type exam_type NOT NULL,
    status exam_status DEFAULT 'SCHEDULED',
    exam_date DATE NOT NULL,
    start_time TIME,
    duration_minutes INTEGER DEFAULT 60,
    max_score DECIMAL(5,2) DEFAULT 100.00,
    weight DECIMAL(3,2) DEFAULT 1.00,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id)
);

CREATE INDEX idx_exams_class ON exams (class_id, exam_date);
CREATE INDEX idx_exams_teacher ON exams (teacher_id);
CREATE INDEX idx_exams_status ON exams (status);
CREATE TRIGGER trg_exams_updated_at BEFORE UPDATE ON exams FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE exam_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exam_id UUID NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    score DECIMAL(5,2),
    grade_scale grade_scale,
    notes TEXT,
    submitted_by UUID REFERENCES users(id) ON DELETE SET NULL,
    submitted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_exam_results_exam_student UNIQUE (exam_id, student_id)
);

CREATE INDEX idx_exam_results_exam ON exam_results (exam_id);
CREATE INDEX idx_exam_results_student ON exam_results (student_id);
CREATE TRIGGER trg_exam_results_updated_at BEFORE UPDATE ON exam_results FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE report_cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    academic_year VARCHAR(20) NOT NULL,
    semester VARCHAR(20) NOT NULL,
    gpa DECIMAL(3,2),
    class_rank INTEGER,
    total_students INTEGER,
    attendance_rate DECIMAL(5,2),
    teacher_comments TEXT,
    principal_comments TEXT,
    generated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    generated_at TIMESTAMPTZ,
    pdf_url VARCHAR(500),
    is_published BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_report_cards_student_year_semester UNIQUE (student_id, academic_year, semester)
);

CREATE INDEX idx_report_cards_student ON report_cards (student_id, academic_year, semester);
CREATE INDEX idx_report_cards_published ON report_cards (is_published);
CREATE TRIGGER trg_report_cards_updated_at BEFORE UPDATE ON report_cards FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Course Materials & Digital Library Module
CREATE TYPE material_type AS ENUM ('PDF', '_VIDEO', 'AUDIO', 'DOCUMENT', 'PRESENTATION', 'IMAGE', 'OTHER');
CREATE TYPE material_visibility AS ENUM ('PUBLIC', 'CLASS_ONLY', 'TEACHER_ONLY', 'SPECIFIC_STUDENTS');

CREATE TABLE course_materials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    class_id UUID REFERENCES classes(id) ON DELETE CASCADE,
    subject_id UUID,
    teacher_id UUID REFERENCES users(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    material_type material_type NOT NULL,
    file_url VARCHAR(500) NOT NULL,
    file_size BIGINT,
    file_name VARCHAR(255),
    unit_topic VARCHAR(255),
    visibility material_visibility DEFAULT 'CLASS_ONLY',
    visible_from DATE,
    visible_until DATE,
    download_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id)
);

CREATE INDEX idx_course_materials_class ON course_materials (class_id, is_active);
CREATE INDEX idx_course_materials_teacher ON course_materials (teacher_id);
CREATE INDEX idx_course_materials_type ON course_materials (material_type);
CREATE TRIGGER trg_course_materials_updated_at BEFORE UPDATE ON course_materials FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Canteen POS & Dietary Restrictions Module
CREATE TYPE dietary_restriction AS ENUM ('PEANUT', 'DAIRY', 'GLUTEN', 'EGG', 'SOY', 'FISH', 'SHELLFISH', 'TREE_NUT', 'SESAME', 'OTHER');
CREATE TYPE order_status AS ENUM ('PENDING', 'COMPLETED', 'CANCELLED', 'REFUNDED');

CREATE TABLE canteen_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id UUID REFERENCES branches(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    price DECIMAL(10,2) NOT NULL,
    image_url VARCHAR(500),
    is_available BOOLEAN DEFAULT TRUE,
    allergens dietary_restriction[],
    nutritional_info JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id)
);

CREATE INDEX idx_canteen_products_branch ON canteen_products (branch_id, is_available);
CREATE INDEX idx_canteen_products_category ON canteen_products (category);
CREATE TRIGGER trg_canteen_products_updated_at BEFORE UPDATE ON canteen_products FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE canteen_dietary_restrictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    restriction dietary_restriction NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    CONSTRAINT uq_canteen_dietary_student_restriction UNIQUE (student_id, restriction)
);

CREATE INDEX idx_canteen_dietary_student ON canteen_dietary_restrictions (student_id, is_active);
CREATE TRIGGER trg_canteen_dietary_restrictions_updated_at BEFORE UPDATE ON canteen_dietary_restrictions FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE canteen_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    branch_id UUID REFERENCES branches(id) ON DELETE SET NULL,
    product_id UUID NOT NULL REFERENCES canteen_products(id) ON DELETE RESTRICT,
    quantity INTEGER DEFAULT 1,
    unit_price DECIMAL(10,2) NOT NULL,
    total_price DECIMAL(10,2) NOT NULL,
    status order_status DEFAULT 'COMPLETED',
    payment_method VARCHAR(50),
    order_date DATE NOT NULL DEFAULT CURRENT_DATE,
    order_time TIME NOT NULL DEFAULT CURRENT_TIME,
    processed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_canteen_orders_student ON canteen_orders (student_id, order_date DESC);
CREATE INDEX idx_canteen_orders_branch ON canteen_orders (branch_id, order_date DESC);
CREATE INDEX idx_canteen_orders_status ON canteen_orders (status);
CREATE TRIGGER trg_canteen_orders_updated_at BEFORE UPDATE ON canteen_orders FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ==================== PHASE 2: ADVANCED MODULES SCHEMA ====================

-- Infirmary & Medication Log Module
CREATE TYPE medication_status AS ENUM ('SCHEDULED', 'GIVEN', 'SKIPPED', 'CANCELLED');
CREATE TYPE visit_severity AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'EMERGENCY');
CREATE TYPE medication_instruction AS ENUM ('BEFORE_MEAL', 'AFTER_MEAL', 'WITH_MEAL', 'EMPTY_STOMACH');

CREATE TABLE health_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    blood_type VARCHAR(5),
    allergies TEXT,
    chronic_conditions TEXT,
    emergency_contact_name VARCHAR(255),
    emergency_contact_phone VARCHAR(20),
    emergency_contact_relation VARCHAR(50),
    insurance_info JSONB,
    last_checkup_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by UUID REFERENCES users(id)
);

CREATE INDEX idx_health_records_student ON health_records (student_id);
CREATE TRIGGER trg_health_records_updated_at BEFORE UPDATE ON health_records FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE medication_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    medication_name VARCHAR(255) NOT NULL,
    dosage VARCHAR(100) NOT NULL,
    frequency VARCHAR(100) NOT NULL,
    instruction medication_instruction DEFAULT 'AFTER_MEAL',
    start_date DATE NOT NULL,
    end_date DATE,
    parent_notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id)
);

CREATE INDEX idx_medication_schedules_student ON medication_schedules (student_id, is_active);
CREATE TRIGGER trg_medication_schedules_updated_at BEFORE UPDATE ON medication_schedules FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE medication_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_id UUID NOT NULL REFERENCES medication_schedules(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    scheduled_time TIME NOT NULL,
    given_time TIMESTAMPTZ,
    status medication_status DEFAULT 'SCHEDULED',
    given_by UUID REFERENCES users(id) ON DELETE SET NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_medication_logs_student ON medication_logs (student_id, scheduled_time DESC);
CREATE INDEX idx_medication_logs_status ON medication_logs (status);

CREATE TABLE infirmary_visits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    branch_id UUID REFERENCES branches(id) ON DELETE SET NULL,
    visit_date DATE NOT NULL DEFAULT CURRENT_DATE,
    visit_time TIME NOT NULL DEFAULT CURRENT_TIME,
    complaint TEXT,
    temperature DECIMAL(4,1),
    blood_pressure_systolic INTEGER,
    blood_pressure_diastolic INTEGER,
    severity visit_severity DEFAULT 'LOW',
    treatment_given TEXT,
    follow_up_required BOOLEAN DEFAULT FALSE,
    follow_up_notes TEXT,
    parent_notified BOOLEAN DEFAULT FALSE,
    notification_method VARCHAR(50),
    examined_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_infirmary_visits_student ON infirmary_visits (student_id, visit_date DESC);
CREATE INDEX idx_infirmary_visits_date ON infirmary_visits (visit_date DESC);

-- Guidance & Counseling (PDR) Module
CREATE TYPE session_type AS ENUM ('INDIVIDUAL', 'GROUP', 'FAMILY', 'CRISIS');
CREATE TYPE confidentiality_level AS ENUM ('STANDARD', 'RESTRICTED', 'CONFIDENTIAL');
CREATE TYPE incident_severity AS ENUM ('MINOR', 'MODERATE', 'SEVERE', 'CRITICAL');

CREATE TABLE guidance_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    counselor_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_type session_type DEFAULT 'INDIVIDUAL',
    session_date DATE NOT NULL,
    start_time TIME,
    end_time TIME,
    summary TEXT,
    action_plan TEXT,
    confidentiality_level confidentiality_level DEFAULT 'STANDARD',
    follow_up_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_guidance_sessions_student ON guidance_sessions (student_id, session_date DESC);
CREATE INDEX idx_guidance_sessions_counselor ON guidance_sessions (counselor_id, session_date DESC);
CREATE TRIGGER trg_guidance_sessions_updated_at BEFORE UPDATE ON guidance_sessions FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE behavioral_incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    reported_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    incident_date DATE NOT NULL,
    incident_time TIME,
    location VARCHAR(255),
    description TEXT NOT NULL,
    severity incident_severity DEFAULT 'MINOR',
    witnesses TEXT,
    action_taken TEXT,
    parent_notified BOOLEAN DEFAULT FALSE,
    resolved BOOLEAN DEFAULT FALSE,
    resolution_date DATE,
    resolution_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_behavioral_incidents_student ON behavioral_incidents (student_id, incident_date DESC);
CREATE INDEX idx_behavioral_incidents_severity ON behavioral_incidents (severity);
CREATE TRIGGER trg_behavioral_incidents_updated_at BEFORE UPDATE ON behavioral_incidents FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE guidance_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    counselor_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    note_type VARCHAR(50) DEFAULT 'OBSERVATION',
    content TEXT NOT NULL,
    confidentiality_level confidentiality_level DEFAULT 'STANDARD',
    tags TEXT[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_guidance_notes_student ON guidance_notes (student_id, created_at DESC);
CREATE TRIGGER trg_guidance_notes_updated_at BEFORE UPDATE ON guidance_notes FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Live Bus Telemetry Module
CREATE TYPE bus_status AS ENUM ('ACTIVE', 'MAINTENANCE', 'OUT_OF_SERVICE');

CREATE TABLE bus_routes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    route_name VARCHAR(255) NOT NULL,
    route_number VARCHAR(50),
    description TEXT,
    driver_id UUID REFERENCES users(id) ON DELETE SET NULL,
    vehicle_plate VARCHAR(20),
    capacity INTEGER DEFAULT 40,
    status bus_status DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by UUID REFERENCES users(id)
);

CREATE INDEX idx_bus_routes_branch ON bus_routes (branch_id, status);
CREATE TRIGGER trg_bus_routes_updated_at BEFORE UPDATE ON bus_routes FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE bus_stops (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    route_id UUID NOT NULL REFERENCES bus_routes(id) ON DELETE CASCADE,
    stop_name VARCHAR(255) NOT NULL,
    stop_order INTEGER NOT NULL,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    estimated_arrival TIME,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_bus_stops_route ON bus_stops (route_id, stop_order);

CREATE TABLE bus_telemetry_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    route_id UUID NOT NULL REFERENCES bus_routes(id) ON DELETE CASCADE,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    speed DECIMAL(5, 2),
    heading DECIMAL(5, 2),
    ignition_status BOOLEAN DEFAULT TRUE,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_bus_telemetry_route ON bus_telemetry_logs (route_id, recorded_at DESC);

CREATE TABLE bus_attendance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    route_id UUID NOT NULL REFERENCES bus_routes(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    stop_id UUID REFERENCES bus_stops(id) ON DELETE SET NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    pickup_time TIME,
    dropoff_time TIME,
    status VARCHAR(20) DEFAULT 'PRESENT',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_bus_attendance_student ON bus_attendance (student_id, date DESC);
CREATE INDEX idx_bus_attendance_route ON bus_attendance (route_id, date DESC);

-- Student Pickup/Dismissal Desk Module
CREATE TYPE pickup_authorization_status AS ENUM ('ACTIVE', 'EXPIRED', 'REVOKED');

CREATE TABLE pickup_authorizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    authorized_person_name VARCHAR(255) NOT NULL,
    authorized_person_id VARCHAR(50),
    relationship VARCHAR(100),
    photo_url VARCHAR(500),
    phone VARCHAR(20),
    valid_from DATE NOT NULL,
    valid_until DATE,
    status pickup_authorization_status DEFAULT 'ACTIVE',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id)
);

CREATE INDEX idx_pickup_authorizations_student ON pickup_authorizations (student_id, status);
CREATE TRIGGER trg_pickup_authorizations_updated_at BEFORE UPDATE ON pickup_authorizations FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE pickup_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    authorization_id UUID REFERENCES pickup_authorizations(id) ON DELETE SET NULL,
    pickup_person_name VARCHAR(255) NOT NULL,
    pickup_person_id VARCHAR(50),
    verified_by UUID NOT NULL REFERENCES users(id) ON DELETE SET NULL,
    pickup_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    verification_method VARCHAR(50) DEFAULT 'ID_CARD',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pickup_logs_student ON pickup_logs (student_id, pickup_time DESC);
CREATE INDEX idx_pickup_logs_date ON pickup_logs (pickup_time DESC);

-- Omnichannel Communication Module
CREATE TYPE broadcast_status AS ENUM ('DRAFT', 'QUEUED', 'SENDING', 'COMPLETED', 'FAILED', 'CANCELLED');
CREATE TYPE delivery_status AS ENUM ('PENDING', 'SENT', 'DELIVERED', 'FAILED', 'BOUNCED');

CREATE TABLE sms_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_name VARCHAR(100) NOT NULL,
    api_endpoint VARCHAR(500),
    api_key_encrypted TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sms_providers_active ON sms_providers (is_active, priority);
CREATE TRIGGER trg_sms_providers_updated_at BEFORE UPDATE ON sms_providers FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE broadcast_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    message_content TEXT NOT NULL,
    target_audience VARCHAR(50) NOT NULL,
    target_class_id UUID REFERENCES classes(id) ON DELETE SET NULL,
    target_branch_id UUID REFERENCES branches(id) ON DELETE SET NULL,
    channel VARCHAR(50) DEFAULT 'SMS',
    scheduled_for TIMESTAMPTZ,
    status broadcast_status DEFAULT 'DRAFT',
    total_recipients INTEGER DEFAULT 0,
    sent_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at TIMESTAMPTZ
);

CREATE INDEX idx_broadcast_jobs_status ON broadcast_jobs (status, scheduled_for);
CREATE INDEX idx_broadcast_jobs_created_by ON broadcast_jobs (created_by, created_at DESC);
CREATE TRIGGER trg_broadcast_jobs_updated_at BEFORE UPDATE ON broadcast_jobs FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE delivery_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    broadcast_job_id UUID NOT NULL REFERENCES broadcast_jobs(id) ON DELETE CASCADE,
    recipient_phone VARCHAR(20) NOT NULL,
    recipient_name VARCHAR(255),
    status delivery_status DEFAULT 'PENDING',
    provider_response TEXT,
    error_message TEXT,
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_delivery_reports_job ON delivery_reports (broadcast_job_id, status);
CREATE INDEX idx_delivery_reports_status ON delivery_reports (status);

-- Multi-Branch HQ Analytics Module
CREATE TABLE branch_financial_summary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    period VARCHAR(20) NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER,
    total_revenue DECIMAL(15,2) DEFAULT 0,
    total_expenses DECIMAL(15,2) DEFAULT 0,
    net_profit DECIMAL(15,2) DEFAULT 0,
    collection_rate DECIMAL(5,2),
    overdue_debt DECIMAL(15,2) DEFAULT 0,
    student_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_branch_financial_summary UNIQUE (branch_id, period, year, month)
);

CREATE INDEX idx_branch_financial_summary_branch ON branch_financial_summary (branch_id, year DESC, month DESC);
CREATE TRIGGER trg_branch_financial_summary_updated_at BEFORE UPDATE ON branch_financial_summary FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE branch_academic_summary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    period VARCHAR(20) NOT NULL,
    year INTEGER NOT NULL,
    semester VARCHAR(20),
    average_attendance_rate DECIMAL(5,2),
    average_exam_score DECIMAL(5,2),
    total_students INTEGER DEFAULT 0,
    total_teachers INTEGER DEFAULT 0,
    student_retention_rate DECIMAL(5,2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_branch_academic_summary UNIQUE (branch_id, period, year, semester)
);

CREATE INDEX idx_branch_academic_summary_branch ON branch_academic_summary (branch_id, year DESC, semester);
CREATE TRIGGER trg_branch_academic_summary_updated_at BEFORE UPDATE ON branch_academic_summary FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Phase 3: Etüt & Birebir Ders Yönetimi (Tutoring Sessions)
CREATE TABLE tutoring_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    subject VARCHAR(100),
    session_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    location VARCHAR(255),
    status VARCHAR(20) DEFAULT 'SCHEDULED',
    notes TEXT,
    attendance_status VARCHAR(20),
    progress_score INTEGER CHECK (progress_score >= 0 AND progress_score <= 100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tutoring_sessions_teacher ON tutoring_sessions (teacher_id, session_date);
CREATE INDEX idx_tutoring_sessions_student ON tutoring_sessions (student_id, session_date);
CREATE TRIGGER trg_tutoring_sessions_updated_at BEFORE UPDATE ON tutoring_sessions FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE tutoring_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    teacher_id UUID REFERENCES users(id) ON DELETE SET NULL,
    subject VARCHAR(100),
    requested_date DATE NOT NULL,
    preferred_time_start TIME,
    preferred_time_end TIME,
    reason TEXT,
    status VARCHAR(20) DEFAULT 'PENDING',
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMPTZ,
    rejection_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tutoring_requests_student ON tutoring_requests (student_id, status);
CREATE INDEX idx_tutoring_requests_teacher ON tutoring_requests (teacher_id, status);
CREATE TRIGGER trg_tutoring_requests_updated_at BEFORE UPDATE ON tutoring_requests FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE teacher_availability (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    day_of_week INTEGER NOT NULL CHECK (day_of_week >= 0 AND day_of_week <= 6),
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    is_available BOOLEAN DEFAULT TRUE,
    max_students INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_teacher_availability UNIQUE (teacher_id, day_of_week, start_time)
);

CREATE INDEX idx_teacher_availability_teacher ON teacher_availability (teacher_id);
CREATE TRIGGER trg_teacher_availability_updated_at BEFORE UPDATE ON teacher_availability FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Phase 3: Kulüpler & Sosyal Etkinlikler (Clubs & Social Activities)
CREATE TABLE school_clubs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    club_name VARCHAR(255) NOT NULL,
    description TEXT,
    advisor_teacher_id UUID REFERENCES users(id) ON DELETE SET NULL,
    max_members INTEGER DEFAULT 30,
    current_members INTEGER DEFAULT 0,
    meeting_day VARCHAR(20),
    meeting_time TIME,
    meeting_location VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_school_clubs_branch ON school_clubs (branch_id, is_active);
CREATE TRIGGER trg_school_clubs_updated_at BEFORE UPDATE ON school_clubs FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE club_memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    club_id UUID NOT NULL REFERENCES school_clubs(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    joined_date DATE NOT NULL DEFAULT CURRENT_DATE,
    role VARCHAR(50) DEFAULT 'MEMBER',
    status VARCHAR(20) DEFAULT 'ACTIVE',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_club_membership UNIQUE (club_id, student_id)
);

CREATE INDEX idx_club_memberships_club ON club_memberships (club_id, status);
CREATE INDEX idx_club_memberships_student ON club_memberships (student_id, status);
CREATE TRIGGER trg_club_memberships_updated_at BEFORE UPDATE ON club_memberships FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE club_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    club_id UUID NOT NULL REFERENCES school_clubs(id) ON DELETE CASCADE,
    event_name VARCHAR(255) NOT NULL,
    event_date DATE NOT NULL,
    event_time TIME,
    location VARCHAR(255),
    description TEXT,
    max_participants INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_club_events_club ON club_events (club_id, event_date);
CREATE TRIGGER trg_club_events_updated_at BEFORE UPDATE ON club_events FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE student_certificates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    certificate_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    issue_date DATE NOT NULL DEFAULT CURRENT_DATE,
    issued_by UUID REFERENCES users(id) ON DELETE SET NULL,
    event_id UUID REFERENCES club_events(id) ON DELETE SET NULL,
    template_id VARCHAR(100),
    pdf_url VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_student_certificates_student ON student_certificates (student_id, issue_date);
CREATE INDEX idx_student_certificates_type ON student_certificates (certificate_type);

-- Phase 3: Personel Bordro & Puantaj (Payroll & Timesheet)
CREATE TABLE staff_timesheets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    check_in_time TIMESTAMPTZ,
    check_out_time TIMESTAMPTZ,
    work_hours DECIMAL(5,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'PRESENT',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_staff_timesheet UNIQUE (staff_id, date)
);

CREATE INDEX idx_staff_timesheets_staff ON staff_timesheets (staff_id, date DESC);
CREATE TRIGGER trg_staff_timesheets_updated_at BEFORE UPDATE ON staff_timesheets FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE additional_course_hours (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    period VARCHAR(20) NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER,
    total_hours DECIMAL(5,2) DEFAULT 0,
    hourly_rate DECIMAL(10,2),
    total_amount DECIMAL(15,2) DEFAULT 0,
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_additional_course_hours UNIQUE (staff_id, period, year, month)
);

CREATE INDEX idx_additional_course_hours_staff ON additional_course_hours (staff_id, year DESC, month);
CREATE TRIGGER trg_additional_course_hours_updated_at BEFORE UPDATE ON additional_course_hours FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE payroll_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    period VARCHAR(20) NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER,
    base_salary DECIMAL(15,2) DEFAULT 0,
    additional_course_payment DECIMAL(15,2) DEFAULT 0,
    bonus DECIMAL(15,2) DEFAULT 0,
    advance_payment DECIMAL(15,2) DEFAULT 0,
    deductions DECIMAL(15,2) DEFAULT 0,
    net_salary DECIMAL(15,2) DEFAULT 0,
    payment_date DATE,
    payment_method VARCHAR(50),
    bank_account VARCHAR(50),
    status VARCHAR(20) DEFAULT 'DRAFT',
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_payroll_record UNIQUE (staff_id, period, year, month)
);

CREATE INDEX idx_payroll_records_staff ON payroll_records (staff_id, year DESC, month);
CREATE INDEX idx_payroll_records_status ON payroll_records (status);
CREATE TRIGGER trg_payroll_records_updated_at BEFORE UPDATE ON payroll_records FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Phase 3: Demirbaş & Envanter Yönetimi (Inventory & Asset Management)
CREATE TABLE inventory_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    item_code VARCHAR(50) UNIQUE NOT NULL,
    item_name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    description TEXT,
    purchase_date DATE,
    purchase_price DECIMAL(15,2),
    current_value DECIMAL(15,2),
    location_id UUID,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    condition VARCHAR(50),
    qr_code VARCHAR(255),
    barcode VARCHAR(255),
    warranty_expiry DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_inventory_items_branch ON inventory_items (branch_id, status);
CREATE INDEX idx_inventory_items_category ON inventory_items (category);
CREATE TRIGGER trg_inventory_items_updated_at BEFORE UPDATE ON inventory_items FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE inventory_locations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    location_name VARCHAR(255) NOT NULL,
    location_type VARCHAR(50),
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_inventory_locations_branch ON inventory_locations (branch_id);
CREATE TRIGGER trg_inventory_locations_updated_at BEFORE UPDATE ON inventory_locations FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE asset_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id UUID NOT NULL REFERENCES inventory_items(id) ON DELETE CASCADE,
    assigned_to UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assigned_date DATE NOT NULL DEFAULT CURRENT_DATE,
    return_date DATE,
    status VARCHAR(20) DEFAULT 'ASSIGNED',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_asset_assignments_item ON asset_assignments (item_id, status);
CREATE INDEX idx_asset_assignments_user ON asset_assignments (assigned_to, status);
CREATE TRIGGER trg_asset_assignments_updated_at BEFORE UPDATE ON asset_assignments FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE maintenance_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id UUID NOT NULL REFERENCES inventory_items(id) ON DELETE CASCADE,
    reported_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    issue_description TEXT NOT NULL,
    priority VARCHAR(20) DEFAULT 'MEDIUM',
    status VARCHAR(20) DEFAULT 'PENDING',
    assigned_to UUID REFERENCES users(id) ON DELETE SET NULL,
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_maintenance_requests_item ON maintenance_requests (item_id, status);
CREATE INDEX idx_maintenance_requests_status ON maintenance_requests (status);
CREATE TRIGGER trg_maintenance_requests_updated_at BEFORE UPDATE ON maintenance_requests FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Phase 3: Anket & Geri Bildirim Sistemi (Surveys & Feedback)
CREATE TABLE surveys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    target_audience VARCHAR(50),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_anonymous BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) DEFAULT 'DRAFT',
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_surveys_status ON surveys (status);
CREATE INDEX idx_surveys_dates ON surveys (start_date, end_date);
CREATE TRIGGER trg_surveys_updated_at BEFORE UPDATE ON surveys FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE survey_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    survey_id UUID NOT NULL REFERENCES surveys(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    question_type VARCHAR(50) NOT NULL,
    options JSONB,
    is_required BOOLEAN DEFAULT TRUE,
    order_index INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_survey_questions_survey ON survey_questions (survey_id, order_index);

CREATE TABLE survey_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    survey_id UUID NOT NULL REFERENCES surveys(id) ON DELETE CASCADE,
    respondent_id UUID REFERENCES users(id) ON DELETE SET NULL,
    response_data JSONB NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_address INET,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_survey_responses_survey ON survey_responses (survey_id);
CREATE INDEX idx_survey_responses_respondent ON survey_responses (respondent_id);

-- Phase 3: KVKK & Veli Onay Masası (GDPR & Consent Manager)
CREATE TABLE consent_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    document_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    version VARCHAR(20) DEFAULT '1.0',
    effective_date DATE NOT NULL DEFAULT CURRENT_DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_consent_documents_type ON consent_documents (document_type, is_active);
CREATE TRIGGER trg_consent_documents_updated_at BEFORE UPDATE ON consent_documents FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE student_consents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    consent_document_id UUID NOT NULL REFERENCES consent_documents(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES parents(id) ON DELETE SET NULL,
    consent_status VARCHAR(20) DEFAULT 'PENDING',
    consent_method VARCHAR(50),
    consented_at TIMESTAMPTZ,
    ip_address INET,
    user_agent TEXT,
    signature_data TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_student_consent UNIQUE (student_id, consent_document_id)
);

CREATE INDEX idx_student_consents_student ON student_consents (student_id, consent_status);
CREATE INDEX idx_student_consents_document ON student_consents (consent_document_id);
CREATE TRIGGER trg_student_consents_updated_at BEFORE UPDATE ON student_consents FOR EACH ROW EXECUTE FUNCTION set_updated_at();
