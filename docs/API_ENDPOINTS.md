# School Management System - API Endpoints

## Base URL
`/api`

## Standard Response Format

**Success Response:**
```json
{
  "success": true,
  "message": "İşlem başarılı",
  "data": {}
}
```

**Error Response:**
```json
{
  "success": false,
  "message": "Hata mesajı",
  "errors": []
}
```

---

## Authentication Endpoints

### POST /api/auth/login
**Description:** User login with email and password  
**Auth:** Public  
**Request Body:**
```json
{
  "email": "string",
  "password": "string"
}
```
**Response:**
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### POST /api/auth/refresh
**Description:** Refresh access token using refresh token  
**Auth:** Public (requires valid refresh token)  
**Request Body:**
```json
{
  "refresh_token": "string"
}
```
**Response:**
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### POST /api/auth/logout
**Description:** Logout user and invalidate refresh token  
**Auth:** Required  
**Request Body:**
```json
{
  "refresh_token": "string"
}
```

### GET /api/auth/me
**Description:** Get current user information  
**Auth:** Required  
**Response:**
```json
{
  "id": "uuid",
  "email": "string",
  "first_name": "string",
  "last_name": "string",
  "roles": [],
  "permissions": [],
  "branches": []
}
```

### POST /api/auth/forgot-password
**Description:** Request password reset email  
**Auth:** Public  
**Request Body:**
```json
{
  "email": "string"
}
```

### POST /api/auth/reset-password
**Description:** Reset password with token  
**Auth:** Public  
**Request Body:**
```json
{
  "token": "string",
  "new_password": "string"
}
```

---

## User Endpoints

### GET /api/users
**Description:** List users with pagination and filters  
**Auth:** Required, Permission: `users.view`  
**Query Params:** `page`, `limit`, `search`, `role_id`, `branch_id`, `status`  
**Response:**
```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "limit": 20
}
```

### POST /api/users
**Description:** Create new user  
**Auth:** Required, Permission: `users.create`  
**Request Body:**
```json
{
  "email": "string",
  "password": "string",
  "first_name": "string",
  "last_name": "string",
  "phone": "string",
  "role_ids": [],
  "branch_ids": []
}
```

### GET /api/users/{id}
**Description:** Get user by ID  
**Auth:** Required, Permission: `users.view`  
**Response:** User object

### PUT /api/users/{id}
**Description:** Update user  
**Auth:** Required, Permission: `users.edit`  
**Request Body:** Partial user object

### DELETE /api/users/{id}
**Description:** Soft delete user  
**Auth:** Required, Permission: `users.delete`

### POST /api/users/{id}/roles
**Description:** Assign roles to user  
**Auth:** Required, Permission: `users.assign_roles`  
**Request Body:**
```json
{
  "role_ids": [],
  "branch_id": "uuid"
}
```

### POST /api/users/{id}/branches
**Description:** Assign branches to user  
**Auth:** Required, Permission: `users.edit`  
**Request Body:**
```json
{
  "branch_ids": [],
  "is_primary": "boolean"
}
```

---

## Organization Endpoints

### GET /api/organizations
**Description:** List organizations  
**Auth:** Required, Permission: `organizations.view` (Super Admin only)  
**Query Params:** `page`, `limit`, `search`, `is_active`

### POST /api/organizations
**Description:** Create new organization  
**Auth:** Required, Permission: `organizations.create` (Super Admin only)  
**Request Body:**
```json
{
  "name": "string",
  "tax_number": "string",
  "tax_office": "string",
  "address": "string",
  "phone": "string",
  "email": "string"
}
```

### GET /api/organizations/{id}
**Description:** Get organization by ID  
**Auth:** Required, Permission: `organizations.view`

### PUT /api/organizations/{id}
**Description:** Update organization  
**Auth:** Required, Permission: `organizations.edit`

### DELETE /api/organizations/{id}
**Description:** Soft delete organization  
**Auth:** Required, Permission: `organizations.delete`

---

## Branch Endpoints

### GET /api/branches
**Description:** List branches  
**Auth:** Required, Permission: `branches.view`  
**Query Params:** `page`, `limit`, `search`, `organization_id`, `is_active`

### POST /api/branches
**Description:** Create new branch  
**Auth:** Required, Permission: `branches.create`  
**Request Body:**
```json
{
  "organization_id": "uuid",
  "name": "string",
  "code": "string",
  "address": "string",
  "phone": "string",
  "email": "string",
  "capacity": 0
}
```

### GET /api/branches/{id}
**Description:** Get branch by ID  
**Auth:** Required, Permission: `branches.view`

### PUT /api/branches/{id}
**Description:** Update branch  
**Auth:** Required, Permission: `branches.edit`

### DELETE /api/branches/{id}
**Description:** Soft delete branch  
**Auth:** Required, Permission: `branches.delete`

---

## Student Endpoints

### GET /api/students
**Description:** List students with pagination and filters  
**Auth:** Required, Permission: `students.view`  
**Query Params:** `page`, `limit`, `search`, `branch_id`, `class_id`, `status`

### POST /api/students
**Description:** Create new student  
**Auth:** Required, Permission: `students.create`  
**Request Body:**
```json
{
  "branch_id": "uuid",
  "class_id": "uuid",
  "first_name": "string",
  "last_name": "string",
  "date_of_birth": "date",
  "gender": "MALE|FEMALE|OTHER",
  "enrollment_date": "date",
  "address": "string",
  "notes": "string",
  "parents": [
    {
      "first_name": "string",
      "last_name": "string",
      "relationship": "string",
      "phone": "string",
      "whatsapp_number": "string",
      "sms_number": "string",
      "email": "string",
      "address": "string",
      "receive_email_notifications": true,
      "receive_sms_notifications": true,
      "receive_whatsapp_notifications": true
    }
  ]
}
```

### GET /api/students/{id}
**Description:** Get student by ID with full details  
**Auth:** Required, Permission: `students.view`

### PUT /api/students/{id}
**Description:** Update student  
**Auth:** Required, Permission: `students.edit`

### DELETE /api/students/{id}
**Description:** Soft delete student  
**Auth:** Required, Permission: `students.delete`

### GET /api/students/{id}/files
**Description:** List student files  
**Auth:** Required, Permission: `students.view`

### POST /api/students/{id}/files
**Description:** Upload file for student  
**Auth:** Required, Permission: `students.edit`  
**Request:** multipart/form-data  
**Form Data:** `file`, `category`

### DELETE /api/students/{id}/files/{file_id}
**Description:** Delete student file  
**Auth:** Required, Permission: `students.edit`

### GET /api/students/{id}/parents
**Description:** List student parents  
**Auth:** Required, Permission: `students.view`

### POST /api/students/{id}/parents
**Description:** Add parent to student  
**Auth:** Required, Permission: `students.edit`  
**Request Body:** Parent object

### GET /api/students/{id}/payments
**Description:** Get student payment history  
**Auth:** Required, Permission: `students.view` or `payments.view`

### GET /api/students/{id}/attendance
**Description:** Get student attendance history  
**Auth:** Required, Permission: `students.view` or `attendance.view`  
**Query Params:** `start_date`, `end_date`

---

## Class Endpoints

### GET /api/classes
**Description:** List classes  
**Auth:** Required, Permission: `classes.view`  
**Query Params:** `page`, `limit`, `search`, `branch_id`, `teacher_id`, `academic_year`

### POST /api/classes
**Description:** Create new class  
**Auth:** Required, Permission: `classes.create`  
**Request Body:**
```json
{
  "branch_id": "uuid",
  "name": "string",
  "code": "string",
  "capacity": 20,
  "teacher_id": "uuid",
  "academic_year": "string"
}
```

### GET /api/classes/{id}
**Description:** Get class by ID  
**Auth:** Required, Permission: `classes.view`

### PUT /api/classes/{id}
**Description:** Update class  
**Auth:** Required, Permission: `classes.edit`

### DELETE /api/classes/{id}
**Description:** Soft delete class  
**Auth:** Required, Permission: `classes.delete`

### POST /api/classes/{id}/students
**Description:** Assign students to class  
**Auth:** Required, Permission: `classes.assign_students`  
**Request Body:**
```json
{
  "student_ids": []
}
```

### DELETE /api/classes/{id}/students/{student_id}
**Description:** Remove student from class  
**Auth:** Required, Permission: `classes.assign_students`

### GET /api/classes/{id}/occupancy
**Description:** Get class occupancy information  
**Auth:** Required, Permission: `classes.view`  
**Response:**
```json
{
  "total_students": 0,
  "capacity": 20,
  "occupancy_rate": 0.5,
  "available_slots": 10
}
```

---

## Attendance Endpoints

### GET /api/attendance
**Description:** List attendance records  
**Auth:** Required, Permission: `attendance.view`  
**Query Params:** `page`, `limit`, `class_id`, `student_id`, `date`, `status`

### POST /api/attendance
**Description:** Create single attendance record  
**Auth:** Required, Permission: `attendance.create`  
**Request Body:**
```json
{
  "class_id": "uuid",
  "student_id": "uuid",
  "attendance_date": "date",
  "status": "PRESENT|ABSENT|EXCUSED|LATE|HALF_DAY",
  "notes": "string"
}
```

### POST /api/attendance/bulk
**Description:** Create bulk attendance records for a class  
**Auth:** Required, Permission: `attendance.create`  
**Request Body:**
```json
{
  "class_id": "uuid",
  "attendance_date": "date",
  "records": [
    {
      "student_id": "uuid",
      "status": "PRESENT",
      "notes": "string"
    }
  ]
}
```

### PUT /api/attendance/{id}
**Description:** Update attendance record  
**Auth:** Required, Permission: `attendance.edit`

### DELETE /api/attendance/{id}
**Description:** Delete attendance record  
**Auth:** Required, Permission: `attendance.delete`

### GET /api/attendance/reports/monthly
**Description:** Get monthly attendance report  
**Auth:** Required, Permission: `attendance.view` or `reports.attendance`  
**Query Params:** `class_id`, `student_id`, `year`, `month`

---

## Debt Endpoints

### GET /api/debts
**Description:** List debts  
**Auth:** Required, Permission: `debts.view`  
**Query Params:** `page`, `limit`, `student_id`, `branch_id`, `status`, `debt_type`, `due_date_from`, `due_date_to`

### POST /api/debts
**Description:** Create new debt  
**Auth:** Required, Permission: `debts.create`  
**Request Body:**
```json
{
  "student_id": "uuid",
  "debt_type": "EDUCATION|FOOD|SERVICE|STATIONERY|ACTIVITY|OTHER",
  "description": "string",
  "amount": 1000.00,
  "due_date": "date",
  "academic_year": "string"
}
```

### GET /api/debts/{id}
**Description:** Get debt by ID  
**Auth:** Required, Permission: `debts.view`

### PUT /api/debts/{id}
**Description:** Update debt  
**Auth:** Required, Permission: `debts.edit`

### DELETE /api/debts/{id}
**Description:** Soft delete debt  
**Auth:** Required, Permission: `debts.delete`

### POST /api/debts/{id}/recalculate-status
**Description:** Recalculate debt status based on payments  
**Auth:** Required, Permission: `debts.edit`

---

## Payment Endpoints

### GET /api/payments
**Description:** List payments  
**Auth:** Required, Permission: `payments.view`  
**Query Params:** `page`, `limit`, `student_id`, `branch_id`, `payment_method`, `payment_date_from`, `payment_date_to`

### POST /api/payments
**Description:** Create payment  
**Auth:** Required, Permission: `payments.create`  
**Request Body:**
```json
{
  "student_id": "uuid",
  "debt_id": "uuid",
  "amount": 500.00,
  "payment_method": "CASH|CREDIT_CARD|BANK_TRANSFER|EFT|OTHER",
  "payment_date": "date",
  "notes": "string"
}
```

### GET /api/payments/{id}
**Description:** Get payment by ID  
**Auth:** Required, Permission: `payments.view`

### POST /api/payments/{id}/cancel
**Description:** Cancel payment (reverse transaction)  
**Auth:** Required, Permission: `payments.cancel`  
**Request Body:**
```json
{
  "cancellation_reason": "string"
}
```

---

## Receipt Endpoints

### GET /api/receipts/{id}
**Description:** Get receipt by ID  
**Auth:** Required, Permission: `receipts.view`

### GET /api/receipts/{id}/pdf
**Description:** Download receipt as PDF  
**Auth:** Required, Permission: `receipts.download`  
**Response:** PDF file

### GET /api/receipts/{id}/print
**Description:** Get print-friendly HTML of receipt  
**Auth:** Required, Permission: `receipts.print`  
**Response:** HTML

### POST /api/receipts/{id}/send-email
**Description:** Send receipt via email  
**Auth:** Required, Permission: `receipts.download`  
**Request Body:**
```json
{
  "recipient_email": "string"
}
```

### POST /api/receipts/{id}/send-sms
**Description:** Send receipt notification via SMS  
**Auth:** Required, Permission: `receipts.download`

### POST /api/receipts/{id}/send-whatsapp
**Description:** Send receipt notification via WhatsApp  
**Auth:** Required, Permission: `receipts.download`

---

## Announcement Endpoints

### GET /api/announcements
**Description:** List announcements  
**Auth:** Required, Permission: `announcements.view`  
**Query Params:** `page`, `limit`, `branch_id`, `class_id`, `audience`, `status`

### POST /api/announcements
**Description:** Create announcement  
**Auth:** Required, Permission: `announcements.create`  
**Request Body:**
```json
{
  "branch_id": "uuid",
  "class_id": "uuid",
  "student_id": "uuid",
  "title": "string",
  "content": "string",
  "audience": "ALL_PARENTS|BRANCH_PARENTS|CLASS_PARENTS|SINGLE_STUDENT",
  "send_email": true,
  "send_sms": false,
  "send_whatsapp": false,
  "scheduled_for": "datetime"
}
```

### GET /api/announcements/{id}
**Description:** Get announcement by ID  
**Auth:** Required, Permission: `announcements.view`

### PUT /api/announcements/{id}
**Description:** Update announcement  
**Auth:** Required, Permission: `announcements.edit`

### DELETE /api/announcements/{id}
**Description:** Soft delete announcement  
**Auth:** Required, Permission: `announcements.delete`

### POST /api/announcements/{id}/send
**Description:** Send announcement immediately  
**Auth:** Required, Permission: `announcements.send`

---

## Notification Endpoints

### GET /api/notifications
**Description:** List notification jobs  
**Auth:** Required, Permission: `notifications.view`  
**Query Params:** `page`, `limit`, `status`, `channel`, `scheduled_for`

### POST /api/notifications/send
**Description:** Send notification immediately  
**Auth:** Required, Permission: `notifications.send`  
**Request Body:**
```json
{
  "channel": "EMAIL|SMS|WHATSAPP",
  "recipient_type": "parent|user",
  "recipient_id": "uuid",
  "subject": "string",
  "body": "string"
}
```

### GET /api/notifications/{id}
**Description:** Get notification job by ID  
**Auth:** Required, Permission: `notifications.view`

### POST /api/notifications/{id}/retry
**Description:** Retry failed notification  
**Auth:** Required, Permission: `notifications.retry`

### GET /api/notifications/templates
**Description:** List notification templates  
**Auth:** Required, Permission: `notifications.manage_templates`

### POST /api/notifications/templates
**Description:** Create notification template  
**Auth:** Required, Permission: `notifications.manage_templates`  
**Request Body:**
```json
{
  "name": "string",
  "channel": "EMAIL|SMS|WHATSAPP",
  "subject": "string",
  "body": "string"
}
```

### PUT /api/notifications/templates/{id}
**Description:** Update notification template  
**Auth:** Required, Permission: `notifications.manage_templates`

---

## Report Endpoints

### GET /api/reports/monthly-payments
**Description:** Get monthly payment report  
**Auth:** Required, Permission: `reports.finance`  
**Query Params:** `year`, `month`, `branch_id`

### GET /api/reports/debts
**Description:** Get debt report  
**Auth:** Required, Permission: `reports.finance`  
**Query Params:** `branch_id`, `status`, `debt_type`, `date_from`, `date_to`

### GET /api/reports/overdue-debts
**Description:** Get overdue debt report  
**Auth:** Required, Permission: `reports.finance`  
**Query Params:** `branch_id`, `days_overdue`

### GET /api/reports/attendance
**Description:** Get attendance report  
**Auth:** Required, Permission: `reports.attendance`  
**Query Params:** `class_id`, `student_id`, `year`, `month`

### GET /api/reports/class-occupancy
**Description:** Get class occupancy report  
**Auth:** Required, Permission: `reports.view`  
**Query Params:** `branch_id`, `academic_year`

### GET /api/reports/branch-performance
**Description:** Get branch performance report  
**Auth:** Required, Permission: `reports.view`  
**Query Params:** `year`, `month`

### GET /api/reports/export/csv
**Description:** Export report as CSV  
**Auth:** Required, Permission: `reports.export`  
**Query Params:** `report_type`, `filters`  
**Response:** CSV file

### GET /api/reports/export/excel
**Description:** Export report as Excel  
**Auth:** Required, Permission: `reports.export`  
**Query Params:** `report_type`, `filters`  
**Response:** Excel file

---

## Dashboard Endpoints

### GET /api/dashboard/summary
**Description:** Get dashboard summary statistics  
**Auth:** Required  
**Response:**
```json
{
  "total_students": 0,
  "active_students": 0,
  "total_branches": 0,
  "total_classes": 0,
  "absent_today": 0,
  "collection_this_month": 0.00,
  "pending_debts": 0.00,
  "overdue_debts": 0.00
}
```

### GET /api/dashboard/charts
**Description:** Get dashboard chart data  
**Auth:** Required  
**Query Params:** `period` (month, quarter, year)  
**Response:**
```json
{
  "monthly_collection": [],
  "debt_vs_payment": [],
  "class_occupancy": [],
  "attendance_trend": []
}
```

---

## Settings Endpoints

### GET /api/settings
**Description:** Get application settings  
**Auth:** Required, Permission: `settings.view`

### PUT /api/settings
**Description:** Update application settings  
**Auth:** Required, Permission: `settings.edit`  
**Request Body:**
```json
{
  "school_name": "string",
  "default_currency": "string",
  "academic_year": "string",
  "max_upload_size_mb": 10,
  "allowed_file_types": "string"
}
```

### GET /api/settings/integrations
**Description:** Get integration settings  
**Auth:** Required, Permission: `settings.manage_integrations`

### PUT /api/settings/integrations
**Description:** Update integration settings  
**Auth:** Required, Permission: `settings.manage_integrations`  
**Request Body:**
```json
{
  "integration_type": "smtp|sms|whatsapp",
  "provider_name": "string",
  "settings": {}
}
```

---

## Health Endpoints

### GET /health
**Description:** Health check endpoint  
**Auth:** Public  
**Response:**
```json
{
  "status": "healthy",
  "timestamp": "datetime"
}
```

### GET /ready
**Description:** Readiness check endpoint  
**Auth:** Public  
**Response:**
```json
{
  "status": "ready",
  "database": "connected",
  "timestamp": "datetime"
}
```

---

## Security Headers

All API endpoints include:
- `Authorization: Bearer {access_token}` header for authenticated requests
- `X-Organization-ID: {organization_id}` header for multi-tenant requests (optional, extracted from token)
- `X-Branch-ID: {branch_id}` header for branch-scoped requests (optional)

## Rate Limiting

- Auth endpoints: 10 requests per minute per IP
- Public endpoints: 20 requests per minute per IP
- Authenticated endpoints: 100 requests per minute per user

## Pagination

All list endpoints support:
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20, max: 100)

## Filtering

Most list endpoints support:
- `search`: Text search across relevant fields
- Entity-specific filters (e.g., `status`, `branch_id`, `class_id`)
- Date range filters (e.g., `date_from`, `date_to`)

## Sorting

All list endpoints support:
- `sort_by`: Field to sort by
- `sort_order`: `asc` or `desc`
