# School Management System - Frontend Pages

## Page Structure

All pages follow the Creative Tim Material Dashboard React template structure with:
- Sidebar navigation
- Top navbar with user info
- Main content area with cards, tables, and forms
- Responsive design (mobile, tablet, desktop)

---

## Authentication Pages

### Login Page
**Route:** `/login`  
**File:** `frontend/src/features/auth/pages/Login.tsx`  
**Components:**
- Email input with validation
- Password input with validation
- Remember me checkbox
- Login button
- Forgot password link
- Error display

**Features:**
- Form validation with Zod
- JWT token storage
- Redirect to dashboard on success
- Error handling with toast notifications

### Forgot Password Page
**Route:** `/forgot-password`  
**File:** `frontend/src/features/auth/pages/ForgotPassword.tsx`  
**Components:**
- Email input
- Submit button
- Back to login link

**Features:**
- Email validation
- API call to request reset
- Success message display

### Reset Password Page
**Route:** `/reset-password/:token`  
**File:** `frontend/src/features/auth/pages/ResetPassword.tsx`  
**Components:**
- New password input
- Confirm password input
- Submit button

**Features:**
- Password strength validation
- Password match validation
- Token-based reset

### 403 Forbidden Page
**Route:** `/403`  
**File:** `frontend/src/features/auth/pages/Forbidden.tsx`  
**Components:**
- Forbidden message
- Back to home button
- Contact admin link

### 404 Not Found Page
**Route:** `/404`  
**File:** `frontend/src/features/auth/pages/NotFound.tsx`  
**Components:**
- Not found message
- Back to home button

---

## Dashboard Pages

### Dashboard Home
**Route:** `/dashboard`  
**File:** `frontend/src/features/dashboard/pages/Dashboard.tsx`  
**Components:**
- Summary cards (Total Students, Active Students, Total Branches, etc.)
- Monthly collection chart
- Debt vs payment comparison chart
- Class occupancy chart
- Attendance trend chart
- Recent activities list

**Features:**
- Role-based data display
- Real-time statistics
- Interactive charts
- Responsive grid layout

---

## Organization Pages

### Organization List
**Route:** `/organizations`  
**File:** `frontend/src/features/organizations/pages/OrganizationList.tsx`  
**Components:**
- Data table with pagination
- Search input
- Filter by status
- Add organization button
- Action buttons (Edit, Delete, View)

**Features:**
- List all organizations (Super Admin only)
- Search and filter
- Pagination
- Delete confirmation modal

### Organization Create/Edit
**Route:** `/organizations/new`  
**Route:** `/organizations/:id/edit`  
**File:** `frontend/src/features/organizations/pages/OrganizationForm.tsx`  
**Components:**
- Name input
- Tax number input
- Tax office input
- Address textarea
- Phone input
- Email input
- Logo upload
- Save/Cancel buttons

**Features:**
- Form validation
- Logo preview
- Create/Update mode

---

## Branch Pages

### Branch List
**Route:** `/branches`  
**File:** `frontend/src/features/branches/pages/BranchList.tsx`  
**Components:**
- Data table with pagination
- Search input
- Filter by organization
- Filter by status
- Add branch button
- Action buttons

**Features:**
- List branches based on user permissions
- Organization filter
- Capacity display
- Status badges

### Branch Create/Edit
**Route:** `/branches/new`  
**Route:** `/branches/:id/edit`  
**File:** `frontend/src/features/branches/pages/BranchForm.tsx`  
**Components:**
- Organization select
- Name input
- Code input
- Address textarea
- Phone input
- Email input
- Capacity input
- Save/Cancel buttons

**Features:**
- Organization selection (Super Admin only)
- Code uniqueness validation
- Capacity validation

### Branch Detail
**Route:** `/branches/:id`  
**File:** `frontend/src/features/branches/pages/BranchDetail.tsx`  
**Components:**
- Branch information card
- Statistics cards
- Classes list
- Students count
- Staff list

**Features:**
- Detailed branch view
- Related data display
- Quick actions

---

## User Pages

### User List
**Route:** `/users`  
**File:** `frontend/src/features/users/pages/UserList.tsx`  
**Components:**
- Data table with pagination
- Search input
- Filter by role
- Filter by branch
- Filter by status
- Add user button
- Action buttons

**Features:**
- List users based on organization/branch scope
- Role badges
- Status badges
- Branch assignment display

### User Create/Edit
**Route:** `/users/new`  
**Route:** `/users/:id/edit`  
**File:** `frontend/src/features/users/pages/UserForm.tsx`  
**Components:**
- Email input
- Password input (create only)
- First name input
- Last name input
- Phone input
- Role multi-select
- Branch multi-select
- Status toggle
- Save/Cancel buttons

**Features:**
- Email uniqueness validation
- Password strength validation
- Role assignment
- Branch assignment
- Status management

### User Detail
**Route:** `/users/:id`  
**File:** `frontend/src/features/users/pages/UserDetail.tsx`  
**Components:**
- User information card
- Roles list
- Branches list
- Activity log
- Edit/Delete buttons

**Features:**
- Detailed user view
- Role management
- Branch management
- Activity history

### Role List
**Route:** `/roles`  
**File:** `frontend/src/features/users/pages/RoleList.tsx`  
**Components:**
- Data table
- Role name
- Description
- Permission count
- Edit button

**Features:**
- List all roles
- Permission count display
- System role badges

### Role Permission Matrix
**Route:** `/roles/:id/permissions`  
**File:** `frontend/src/features/users/pages/RolePermissions.tsx`  
**Components:**
- Permission matrix table
- Module-based grouping
- Checkboxes for permissions
- Save button

**Features:**
- Visual permission matrix
- Module grouping
- Bulk permission assignment
- Save changes

---

## Student Pages

### Student List
**Route:** `/students`  
**File:** `frontend/src/features/students/pages/StudentList.tsx`  
**Components:**
- Data table with pagination
- Search input
- Filter by branch
- Filter by class
- Filter by status
- Add student button
- Action buttons

**Features:**
- Photo display
- Name search
- Status badges
- Class assignment display
- Export button

### Student Create/Edit
**Route:** `/students/new`  
**Route:** `/students/:id/edit`  
**File:** `frontend/src/features/students/pages/StudentForm.tsx`  
**Components:**
- Branch select
- Class select
- First name input
- Last name input
- Date of birth picker
- Gender radio
- Photo upload
- Enrollment date picker
- Address textarea
- Notes textarea
- Parents section (dynamic)
- Save/Cancel buttons

**Features:**
- Photo upload with preview
- Parent management (add/remove)
- Class assignment
- Form validation

### Student Detail
**Route:** `/students/:id`  
**File:** `frontend/src/features/students/pages/StudentDetail.tsx`  
**Components:**
- Student profile card
- Photo display
- Personal information
- Parents list
- Class information
- Tabs: Files, Payments, Attendance, Notes
- Edit/Delete buttons

**Features:**
- Comprehensive student view
- Tabbed interface
- Quick actions
- Related data display

### Student Files
**Route:** `/students/:id/files`  
**File:** `frontend/src/features/students/pages/StudentFiles.tsx`  
**Components:**
- File list table
- File category filter
- Upload button
- Download button
- Delete button
- File preview modal

**Features:**
- File upload
- File preview
- Category filtering
- Download/delete actions

### Student Parents
**Route:** `/students/:id/parents`  
**File:** `frontend/src/features/students/pages/StudentParents.tsx`  
**Components:**
- Parents list
- Add parent button
- Parent form modal
- Contact information display
- Notification preferences

**Features:**
- Parent management
- Contact info display
- Notification preferences
- Primary parent selection

---

## Class Pages

### Class List
**Route:** `/classes`  
**File:** `frontend/src/features/classes/pages/ClassList.tsx`  
**Components:**
- Data table with pagination
- Search input
- Filter by branch
- Filter by teacher
- Filter by academic year
- Add class button
- Action buttons

**Features:**
- Class code display
- Teacher assignment
- Capacity display
- Occupancy rate
- Status badges

### Class Create/Edit
**Route:** `/classes/new`  
**Route:** `/classes/:id/edit`  
**File:** `frontend/src/features/classes/pages/ClassForm.tsx`  
**Components:**
- Branch select
- Name input
- Code input
- Capacity input
- Teacher select
- Academic year input
- Save/Cancel buttons

**Features:**
- Code uniqueness validation
- Teacher assignment
- Capacity validation
- Academic year selection

### Class Detail
**Route:** `/classes/:id`  
**File:** `frontend/src/features/classes/pages/ClassDetail.tsx`  
**Components:**
- Class information card
- Teacher information
- Statistics cards
- Students list
- Occupancy chart
- Assign students button
- Take attendance button

**Features:**
- Detailed class view
- Student list
- Occupancy visualization
- Quick actions

### Class Occupancy
**Route:** `/classes/:id/occupancy`  
**File:** `frontend/src/features/classes/pages/ClassOccupancy.tsx`  
**Components:**
- Occupancy chart
- Student list
- Available slots
- Capacity information

**Features:**
- Visual occupancy display
- Student count
- Available slots
- Capacity warning

### Assign Students to Class
**Route:** `/classes/:id/assign-students`  
**File:** `frontend/src/features/classes/pages/AssignStudents.tsx`  
**Components:**
- Available students list
- Assigned students list
- Search input
- Transfer buttons (add/remove)
- Save button

**Features:**
- Dual list selection
- Search functionality
- Capacity validation
- Bulk assignment

---

## Attendance Pages

### Attendance List
**Route:** `/attendance`  
**File:** `frontend/src/features/attendance/pages/AttendanceList.tsx`  
**Components:**
- Date picker
- Class select
- Student select
- Status filter
- Data table
- Export button

**Features:**
- Date filtering
- Class-based view
- Student-based view
- Status filtering
- Export functionality

### Take Attendance (Daily)
**Route:** `/attendance/take`  
**File:** `frontend/src/features/attendance/pages/TakeAttendance.tsx`  
**Components:**
- Date picker
- Class select
- Student list with radio buttons
- Status options (Present, Absent, Excused, Late, Half Day)
- Notes field
- Save button

**Features:**
- Class-based attendance
- Quick status selection
- Notes per student
- Duplicate prevention
- Bulk save

### Bulk Attendance
**Route:** `/attendance/bulk`  
**File:** `frontend/src/features/attendance/pages/BulkAttendance.tsx`  
**Components:**
- Date picker
- Class select
- Student table with status dropdowns
- Notes column
- Save button

**Features:**
- Table-based entry
- Status dropdowns
- Notes per student
- Bulk save
- Validation

### Student Attendance History
**Route:** `/attendance/student/:id`  
**File:** `frontend/src/features/attendance/pages/StudentAttendance.tsx`  
**Components:**
- Student info card
- Date range picker
- Attendance calendar
- Statistics cards
- Attendance list

**Features:**
- Calendar view
- Statistics summary
- Date range filtering
- History list

### Monthly Attendance Report
**Route:** `/attendance/reports/monthly`  
**File:** `frontend/src/features/attendance/pages/MonthlyReport.tsx`  
**Components:**
- Month/year picker
- Class select
- Report table
- Summary cards
- Export buttons (PDF, Excel)

**Features:**
- Monthly summary
- Class-based report
- Statistics
- Export options

---

## Finance Pages

### Debt List
**Route:** `/finance/debts`  
**File:** `frontend/src/features/finance/pages/DebtList.tsx`  
**Components:**
- Data table with pagination
- Search input
- Filter by student
- Filter by branch
- Filter by status
- Filter by type
- Date range picker
- Add debt button
- Action buttons

**Features:**
- Amount display
- Status badges
- Type badges
- Due date display
- Overdue highlighting

### Debt Create/Edit
**Route:** `/finance/debts/new`  
**Route:** `/finance/debts/:id/edit`  
**File:** `frontend/src/features/finance/pages/DebtForm.tsx`  
**Components:**
- Student select
- Debt type select
- Description input
- Amount input
- Due date picker
- Academic year input
- Save/Cancel buttons

**Features:**
- Student search
- Type selection
- Amount validation
- Due date validation

### Payment List
**Route:** `/finance/payments`  
**File:** `frontend/src/features/finance/pages/PaymentList.tsx`  
**Components:**
- Data table with pagination
- Search input
- Filter by student
- Filter by branch
- Filter by method
- Date range picker
- Take payment button
- Action buttons

**Features:**
- Payment amount display
- Method badges
- Date display
- Receipt link
- Cancel button

### Take Payment
**Route:** `/finance/payments/new`  
**File:** `frontend/src/features/finance/pages/TakePayment.tsx`  
**Components:**
- Student select
- Debt select
- Amount input
- Payment method select
- Payment date picker
- Notes textarea
- Save/Cancel buttons

**Features:**
- Student debt display
- Remaining amount calculation
- Payment method selection
- Auto-receipt generation

### Student Payment History
**Route:** `/finance/payments/student/:id`  
**File:** `frontend/src/features/finance/pages/StudentPayments.tsx`  
**Components:**
- Student info card
- Debt summary
- Payment list
- Receipt links
- Export button

**Features:**
- Debt vs payment summary
- Payment history
- Receipt access
- Export functionality

---

## Receipt Pages

### Receipt Detail
**Route:** `/finance/receipts/:id`  
**File:** `frontend/src/features/receipts/pages/ReceiptDetail.tsx`  
**Components:**
- Receipt card
- Organization info
- Branch info
- Student info
- Payment details
- Remaining debt display
- Download PDF button
- Print button
- Send email button

**Features:**
- Professional receipt layout
- All payment details
- PDF download
- Print functionality
- Email sending

### Receipt Print View
**Route:** `/finance/receipts/:id/print`  
**File:** `frontend/src/features/receipts/pages/ReceiptPrint.tsx`  
**Components:**
- Print-optimized layout
- Organization header
- Receipt details
- Payment breakdown
- Footer
- Print button

**Features:**
- A4 print layout
- Professional design
- Auto-print option
- Close button

---

## Announcement Pages

### Announcement List
**Route:** `/announcements`  
**File:** `frontend/src/features/announcements/pages/AnnouncementList.tsx`  
**Components:**
- Data table with pagination
- Search input
- Filter by audience
- Filter by status
- Date range picker
- Create announcement button
- Action buttons

**Features:**
- Title display
- Audience badges
- Channel indicators
- Scheduled date
- Sent status
- View details

### Announcement Create/Edit
**Route:** `/announcements/new`  
**Route:** `/announcements/:id/edit`  
**File:** `frontend/src/features/announcements/pages/AnnouncementForm.tsx`  
**Components:**
- Title input
- Content rich text editor
- Audience select (All Parents, Branch Parents, Class Parents, Single Student)
- Branch select (conditional)
- Class select (conditional)
- Student select (conditional)
- Channel checkboxes (Email, SMS, WhatsApp)
- Schedule datetime picker
- Send now/Schedule buttons
- Preview button

**Features:**
- Rich text editing
- Conditional fields based on audience
- Channel selection
- Scheduling
- Preview functionality

### Announcement Detail
**Route:** `/announcements/:id`  
**File:** `frontend/src/features/announcements/pages/AnnouncementDetail.tsx`  
**Components:**
- Announcement card
- Content display
- Target audience info
- Channel info
- Sending status
- Recipients list
- Send results
- Retry failed button

**Features:**
- Full announcement view
- Sending status
- Recipient list
- Send results per channel
- Retry failed sends

---

## Notification Pages

### Notification Log
**Route:** `/notifications`  
**File:** `frontend/src/features/notifications/pages/NotificationLog.tsx`  
**Components:**
- Data table with pagination
- Search input
- Filter by channel
- Filter by status
- Filter by date range
- Retry failed button
- View details button

**Features:**
- Channel badges
- Status badges
- Recipient info
- Error display
- Retry functionality

### Notification Templates
**Route:** `/notifications/templates`  
**File:** `frontend/src/features/notifications/pages/NotificationTemplates.tsx`  
**Components:**
- Template list table
- Channel filter
- Create template button
- Edit button
- Delete button

**Features:**
- Template name
- Channel badge
- Subject preview
- Body preview
- Active status

### Template Create/Edit
**Route:** `/notifications/templates/new`  
**Route:** `/notifications/templates/:id/edit`  
**File:** `frontend/src/features/notifications/pages/TemplateForm.tsx`  
**Components:**
- Name input
- Channel select
- Subject input (Email only)
- Body textarea with variable hints
- Active toggle
- Save/Cancel buttons

**Features:**
- Variable placeholder hints
- Channel-specific fields
- Preview functionality
- Validation

---

## Report Pages

### Monthly Payment Report
**Route:** `/reports/monthly-payments`  
**File:** `frontend/src/features/reports/pages/MonthlyPayments.tsx`  
**Components:**
- Month/year picker
- Branch select
- Summary cards
- Chart
- Data table
- Export buttons (CSV, Excel, PDF)

**Features:**
- Monthly summary
- Branch comparison
- Chart visualization
- Export options

### Debt Report
**Route:** `/reports/debts`  
**File:** `frontend/src/features/reports/pages/DebtReport.tsx`  
**Components:**
- Date range picker
- Branch select
- Status filter
- Type filter
- Summary cards
- Data table
- Export buttons

**Features:**
- Debt summary
- Status breakdown
- Type breakdown
- Export options

### Overdue Debt Report
**Route:** `/reports/overdue-debts`  
**File:** `frontend/src/features/reports/pages/OverdueDebts.tsx`  
**Components:**
- Days overdue filter
- Branch select
- Summary cards
- Data table
- Export buttons
- Send reminder button

**Features:**
- Overdue summary
- Days overdue grouping
- Reminder sending
- Export options

### Attendance Report
**Route:** `/reports/attendance`  
**File:** `frontend/src/features/reports/pages/AttendanceReport.tsx`  
**Components:**
- Date range picker
- Class select
- Student select
- Summary cards
- Chart
- Data table
- Export buttons

**Features:**
- Attendance summary
- Status breakdown
- Trend analysis
- Export options

### Class Occupancy Report
**Route:** `/reports/class-occupancy`  
**File:** `frontend/src/features/reports/pages/ClassOccupancyReport.tsx`  
**Components:**
- Branch select
- Academic year select
- Summary cards
- Chart
- Data table
- Export buttons

**Features:**
- Occupancy summary
- Branch comparison
- Visual chart
- Export options

### Branch Performance Report
**Route:** `/reports/branch-performance`  
**File:** `frontend/src/features/reports/pages/BranchPerformance.tsx`  
**Components:**
- Date range picker
- Summary cards
- Charts (Revenue, Students, Attendance)
- Data table
- Export buttons

**Features:**
- Multi-metric comparison
- Revenue tracking
- Student growth
- Attendance rates
- Export options

---

## Settings Pages

### General Settings
**Route:** `/settings/general`  
**File:** `frontend/src/features/settings/pages/GeneralSettings.tsx`  
**Components:**
- School name input
- Tax number input
- Tax office input
- Address textarea
- Phone input
- Email input
- Logo upload
- Default currency select
- Academic year input
- Save button

**Features:**
- Organization settings
- Logo upload
- Currency selection
- Academic year management

### Integration Settings
**Route:** `/settings/integrations`  
**File:** `frontend/src/features/settings/pages/IntegrationSettings.tsx`  
**Components:**
- Tab navigation (SMTP, SMS, WhatsApp)
- SMTP settings form
- SMS settings form
- WhatsApp settings form
- Test connection button
- Save button

**Features:**
- SMTP configuration
- SMS provider configuration
- WhatsApp provider configuration
- Connection testing
- Secure storage

### File Upload Settings
**Route:** `/settings/uploads`  
**File:** `frontend/src/features/settings/pages/UploadSettings.tsx`  
**Components:**
- Max upload size input
- Allowed file types input
- Storage path input
- Save button

**Features:**
- Size limit configuration
- File type restrictions
- Storage path management

### Notification Settings
**Route:** `/settings/notifications`  
**File:** `frontend/src/features/settings/pages/NotificationSettings.tsx`  
**Components:**
- Default sender email
- Default sender name
- SMS sender ID
- Retry count input
- Retry interval input
- Save button

**Features:**
- Default sender configuration
- Retry policy
- Notification preferences

---

## Common Components

### Layout Components
- `DashboardLayout` - Main layout with sidebar and navbar
- `AuthLayout` - Authentication page layout
- `Sidebar` - Navigation sidebar with role-based menu
- `Navbar` - Top navigation with user info

### Common UI Components
- `DataTable` - Reusable data table with pagination
- `SearchInput` - Search input component
- `FilterPanel` - Filter panel with multiple filters
- `ConfirmModal` - Confirmation modal for destructive actions
- `LoadingSpinner` - Loading indicator
- `EmptyState` - Empty state display
- `ErrorState` - Error state display
- `Toast` - Toast notification component
- `Card` - Material UI card wrapper
- `Button` - Styled button component
- `FormInput` - Form input with validation
- `FormSelect` - Form select with validation
- `DatePicker` - Date picker component
- `FileUpload` - File upload component
- `Badge` - Status badge component
- `StatusChip` - Status chip with colors

---

## Route Guards

### ProtectedRoute
**File:** `frontend/src/routes/ProtectedRoute.tsx`  
**Purpose:** Protect routes requiring authentication  
**Behavior:** Redirect to login if not authenticated

### RoleBasedRoute
**File:** `frontend/src/routes/RoleBasedRoute.tsx`  
**Purpose:** Protect routes based on user roles  
**Behavior:** Redirect to 403 if user lacks required role

### PermissionBasedRoute
**File:** `frontend/src/routes/PermissionBasedRoute.tsx`  
**Purpose:** Protect routes based on user permissions  
**Behavior:** Redirect to 403 if user lacks required permission

---

## Error Handling

### ErrorBoundary
**File:** `frontend/src/components/ErrorBoundary.tsx`  
**Purpose:** Catch React component errors  
**Behavior:** Display error page with retry option

### Global Error Handler
**File:** `frontend/src/utils/errorHandler.ts`  
**Purpose:** Handle API errors globally  
**Behavior:** Display toast notifications, redirect on auth errors
