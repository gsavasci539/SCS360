import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { AttendancePage } from "./features/attendance/AttendancePage";
import { StudentAttendancePage } from "./features/attendance/StudentAttendancePage";
import { BulkAttendancePage } from "./features/attendance/BulkAttendancePage";
import { MonthlyAttendanceReport } from "./features/attendance/MonthlyAttendanceReport";
import { ForgotPasswordPage, LoginPage, ResetPasswordPage } from "./features/auth/AuthPages";
import { AnnouncementsPage, AnnouncementFormPage, NotificationsPage, TemplatesPage } from "./features/communications/CommunicationPages";
import { AnnouncementDetailPage } from "./features/communications/AnnouncementDetailPage";
import { TemplateFormPage } from "./features/communications/TemplateFormPage";
import { DashboardPage } from "./features/dashboard/DashboardPage";
import { ForbiddenPage, NotFoundPage } from "./features/errors/ErrorPages";
import { PaymentDetailPage, PaymentFormPage, PaymentsPage, ReceiptDetailPage, ReceiptsPage } from "./features/finance/FinancePages";
import { StudentPaymentsPage } from "./features/finance/StudentPaymentsPage";
import { ReceiptPrintPage } from "./features/finance/ReceiptPrintPage";
import { ReportsPage } from "./features/reports/ReportsPage";
import { MonthlyPaymentsReport } from "./features/reports/MonthlyPaymentsReport";
import { DebtReport } from "./features/reports/DebtReport";
import { OverdueDebtsReport } from "./features/reports/OverdueDebtsReport";
import { AttendanceReport } from "./features/reports/AttendanceReport";
import { RfidCardsPage } from "./features/system/RfidCardsPage";
import { DevicesPage } from "./features/system/DevicesPage";
import { ClassOccupancyReport } from "./features/reports/ClassOccupancyReport";
import { BranchPerformanceReport } from "./features/reports/BranchPerformanceReport";
import { DetailPage } from "./features/resources/DetailPage";
import { ResourceFormPage, ResourceListPage } from "./features/resources/ResourcePages";
import { RolesPage } from "./features/roles/RolesPage";
import { RolePermissionsPage } from "./features/roles/RolePermissionsPage";
import { SettingsPage } from "./features/settings/SettingsPage";
import { StudentFilesPage } from "./features/students/StudentFilesPage";
import { StudentDetailPage } from "./features/students/StudentDetailPage";
import { StudentParentsPage } from "./features/students/StudentParentsPage";
import { StudentsPage } from "./features/students/StudentsPage";
import { ClassOccupancyPage } from "./features/classes/ClassOccupancyPage";
import { AssignStudentsPage } from "./features/classes/AssignStudentsPage";
import { UserDetailPage } from "./features/users/UserDetailPage";
import { UsersPage } from "./features/users/UsersPage";
import { UserCreatePage } from "./features/users/UserCreatePage";
import { AppointmentsPage } from "./features/communications/AppointmentsPage";
import { ParentNoticesPage } from "./features/communications/ParentNoticesPage";
import { OutboxPage } from "./features/communications/OutboxPage";
import { OutboxDetailPage } from "./features/communications/OutboxDetailPage";
import { DailyReportsPage, DailyReportsDetailPage } from "./features/academic/DailyReportsPage";
import { HomeworkPage, HomeworkDetailPage } from "./features/academic/HomeworkPage";
import { LibraryPage } from "./features/resources/LibraryPage";
import { ExpensesPage } from "./features/finance/ExpensesPage";
import { OrganizationsPage } from "./features/organizations/OrganizationsPage";
import { OrganizationDetailPage } from "./features/organizations/OrganizationDetailPage";
import { BranchesPage } from "./features/branches/BranchesPage";
import { StaffPage } from "./features/staff/StaffPage";
import { StaffDetailPage } from "./features/staff/StaffDetailPage";
import { CanteenPage } from "./features/operations/CanteenPage";
import { CardBalancePage } from "./features/operations/CardBalancePage";
import { CanteenSalesPage } from "./features/operations/CanteenSalesPage";
import { BusPage } from "./features/transport/BusPage";
import { SecurityPage } from "./features/security/SecurityPage";
import { TimetablePage } from "./features/academic/TimetablePage";
import { ExamsPage } from "./features/academic/ExamsPage";
import { MaterialsPage } from "./features/academic/MaterialsPage";
import { HealthPage } from "./features/health/HealthPage";
import { GuidancePage } from "./features/guidance/GuidancePage";
import { TutoringPage } from "./features/tutoring/TutoringPage";
import { ClubsPage } from "./features/clubs/ClubsPage";
import { PayrollPage } from "./features/payroll/PayrollPage";
import { InventoryPage } from "./features/inventory/InventoryPage";
import { SurveysPage } from "./features/surveys/SurveysPage";
import { ConsentsPage } from "./features/consents/ConsentsPage";
import { ParentPortalPage } from "./features/parent/ParentPortalPage";
import TeacherPortalPage from "./features/teacher/TeacherPortalPage";
import { PaymentPage } from "./features/payment/PaymentPage";
import { AIAnalyticsPage } from "./features/ai/AIAnalyticsPage";
import { ProtectedRoute } from "./routes/Guards";
import { PermissionRoute } from "./routes/Guards";
import { resources } from "./config/resources";

function ResourceRoutes({ keyName, details = false }: { keyName: string; details?: boolean }) {
  const config = resources[keyName];
  return <>
    <Route element={<PermissionRoute permission={config.permissionRead} />}>
      <Route index element={<ResourceListPage resourceKey={keyName} />} />
      {details && <Route path=":id" element={<DetailPage resourceKey={keyName} />} />}
    </Route>
    <Route element={<PermissionRoute permission={config.permissionWrite} />}>
      <Route path="new" element={<ResourceFormPage resourceKey={keyName} />} />
      <Route path=":id/edit" element={<ResourceFormPage resourceKey={keyName} />} />
    </Route>
  </>;
}

export default function App() {
  return <Routes>
    <Route path="/login" element={<LoginPage />} />
    <Route path="/forgot-password" element={<ForgotPasswordPage />} />
    <Route path="/reset-password" element={<ResetPasswordPage />} />
    <Route element={<ProtectedRoute />}>
      <Route path="/forbidden" element={<ForbiddenPage />} />
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route element={<PermissionRoute permission="dashboard.read" />}><Route path="dashboard" element={<DashboardPage />} /></Route>
        <Route element={<PermissionRoute permission="dashboard.read" />}><Route path="ai-analytics" element={<AIAnalyticsPage />} /></Route>
        <Route element={<PermissionRoute permission="parent.view_children" />}><Route path="parent/dashboard" element={<ParentPortalPage view="dashboard" />} /><Route path="parent/children" element={<ParentPortalPage view="children" />} /><Route path="parent/academic" element={<ParentPortalPage view="academic" />} /><Route path="parent/schedule" element={<ParentPortalPage view="schedule" />} /><Route path="parent/homework" element={<ParentPortalPage view="homework" />} /><Route path="parent/materials" element={<ParentPortalPage view="materials" />} /><Route path="parent/communication" element={<ParentPortalPage view="communication" />} /><Route path="parent/announcements" element={<ParentPortalPage view="announcements" />} /><Route path="parent/activities" element={<ParentPortalPage view="activities" />} /><Route path="parent/reports" element={<ParentPortalPage view="reports" />} /><Route path="parent/chat" element={<ParentPortalPage view="chat" />} /></Route>
        <Route path="teacher" element={<TeacherPortalPage />} />
        <Route element={<PermissionRoute permission="parent.view_attendance" />}><Route path="parent/attendance" element={<ParentPortalPage view="attendance" />} /></Route>
        <Route element={<PermissionRoute permission="parent.view_finances" />}><Route path="parent/finances" element={<ParentPortalPage view="finances" />} /></Route>
        <Route element={<PermissionRoute permission="parent.view_children" />}><Route path="parent/health" element={<ParentPortalPage view="health" />} /></Route>
        <Route element={<PermissionRoute permission="org.read" />}><Route path="organizations" element={<OrganizationsPage />} /><Route path="organizations/:id" element={<OrganizationDetailPage />} /></Route>
        <Route element={<PermissionRoute permission="branch.read" />}><Route path="branches" element={<BranchesPage />} /></Route>
        <Route element={<PermissionRoute permission="user.read" />}><Route path="staff" element={<StaffPage />} /><Route path="staff/:id" element={<StaffDetailPage />} /></Route>
        <Route element={<PermissionRoute permission="user.read" />}><Route path="users" element={<UsersPage />} /></Route>
        <Route element={<PermissionRoute permission="user.write" />}><Route path="users/new" element={<UserCreatePage />} /></Route>
        <Route path="users">{ResourceRoutes({ keyName: "users" })}<Route element={<PermissionRoute permission="user.read" />}><Route path=":id" element={<UserDetailPage />} /></Route></Route>
        <Route element={<PermissionRoute permission="user.read" />}><Route path="roles" element={<RolesPage />} /></Route>
        <Route element={<PermissionRoute permission="user.write" />}><Route path="roles/:id/permissions" element={<RolePermissionsPage />} /></Route>
        <Route path="parents">{ResourceRoutes({ keyName: "parents", details: true })}</Route>
        <Route path="classes">{ResourceRoutes({ keyName: "classes", details: true })}<Route element={<PermissionRoute permission="class.read" />}><Route path=":id/occupancy" element={<ClassOccupancyPage />} /></Route><Route element={<PermissionRoute permission="class.write" />}><Route path=":id/assign-students" element={<AssignStudentsPage />} /></Route></Route>
        <Route element={<PermissionRoute permission="attendance.read" />}><Route path="attendance" element={<AttendancePage />} /><Route path="attendance/student/:id" element={<StudentAttendancePage />} /><Route path="attendance/reports/monthly" element={<MonthlyAttendanceReport />} /></Route>
        <Route element={<PermissionRoute permission="attendance.write" />}><Route path="attendance/bulk" element={<BulkAttendancePage />} /></Route>
        <Route element={<PermissionRoute permission="students.read" />}><Route path="students" element={<StudentsPage />} /><Route path="students/:id" element={<StudentDetailPage />} /><Route path="students/:id/files" element={<StudentFilesPage />} /><Route path="students/:id/parents" element={<StudentParentsPage />} /></Route>
        <Route element={<PermissionRoute permission="students.write" />}><Route path="students/new" element={<ResourceFormPage resourceKey="students" />} /><Route path="students/:id/edit" element={<ResourceFormPage resourceKey="students" />} /></Route>
        <Route element={<PermissionRoute permission="homework.read" />}><Route path="homework" element={<HomeworkPage />} /><Route path="homework/:id" element={<HomeworkDetailPage />} /></Route>
        <Route element={<PermissionRoute permission="library.read" />}><Route path="library" element={<LibraryPage />} /></Route>
        <Route element={<PermissionRoute permission="daily_reports.read" />}><Route path="daily-reports" element={<DailyReportsPage />} /><Route path="daily-reports/:id" element={<DailyReportsDetailPage />} /></Route>
        <Route element={<PermissionRoute permission="parent_notices.read" />}><Route path="parent-notices" element={<ParentNoticesPage />} /></Route>
        <Route element={<PermissionRoute permission="appointments.read" />}><Route path="appointments" element={<AppointmentsPage />} /></Route>
        <Route element={<PermissionRoute permission="outbox.read" />}><Route path="outbox" element={<OutboxPage />} /><Route path="outbox/:id" element={<OutboxDetailPage />} /></Route>
        <Route element={<PermissionRoute permission="security.read" />}><Route path="security" element={<SecurityPage />} /></Route>
        <Route element={<PermissionRoute permission="academic.read" />}><Route path="timetable" element={<TimetablePage />} /><Route path="exams" element={<ExamsPage />} /><Route path="materials" element={<MaterialsPage />} /></Route>
        <Route element={<PermissionRoute permission="health.read" />}><Route path="health" element={<HealthPage />} /></Route>
        <Route element={<PermissionRoute permission="guidance.read" />}><Route path="guidance" element={<GuidancePage />} /></Route>
        <Route element={<PermissionRoute permission="bus.read" />}><Route path="transport" element={<BusPage />} /></Route>
        <Route element={<PermissionRoute permission="tutoring.read" />}><Route path="tutoring" element={<TutoringPage />} /></Route>
        <Route element={<PermissionRoute permission="clubs.read" />}><Route path="clubs" element={<ClubsPage />} /></Route>
        <Route element={<PermissionRoute permission="payroll.read" />}><Route path="payroll" element={<PayrollPage />} /></Route>
        <Route element={<PermissionRoute permission="inventory.read" />}><Route path="inventory" element={<InventoryPage />} /></Route>
        <Route element={<PermissionRoute permission="survey.read" />}><Route path="surveys" element={<SurveysPage />} /></Route>
        <Route element={<PermissionRoute permission="consent.read" />}><Route path="consents" element={<ConsentsPage />} /></Route>
        <Route path="finance/debts">{ResourceRoutes({ keyName: "debts", details: true })}</Route>
        <Route element={<PermissionRoute permission="dashboard.view" />}><Route path="finance/payments" element={<PaymentsPage />} /><Route path="finance/payments/:id" element={<PaymentDetailPage />} /><Route path="finance/payments/student/:id" element={<StudentPaymentsPage />} /><Route path="finance/expenses" element={<ExpensesPage />} /></Route>
        <Route element={<PermissionRoute permission="canteen.read" />}><Route path="canteen" element={<CanteenPage />} /><Route path="canteen/card-balance" element={<CardBalancePage />} /><Route path="canteen/sales" element={<CanteenSalesPage />} /></Route>
        <Route element={<PermissionRoute permission="finance.write" />}><Route path="finance/payments/new" element={<PaymentFormPage />} /></Route>
        <Route element={<PermissionRoute permission="receipt.read" />}><Route path="finance/receipts" element={<ReceiptsPage />} /><Route path="finance/receipts/:id" element={<ReceiptDetailPage />} /><Route path="finance/receipts/:id/print" element={<ReceiptPrintPage />} /></Route>
        <Route element={<PermissionRoute permission="announcement.read" />}><Route path="announcements" element={<AnnouncementsPage />} /><Route path="announcements/:id" element={<AnnouncementDetailPage />} /></Route>
        <Route element={<PermissionRoute permission="announcement.write" />}><Route path="announcements/new" element={<AnnouncementFormPage />} /><Route path="announcements/:id/edit" element={<AnnouncementFormPage />} /></Route>
        <Route element={<PermissionRoute permission="notification.read" />}><Route path="notifications" element={<NotificationsPage />} /><Route path="notifications/templates" element={<TemplatesPage />} /></Route>
        <Route element={<PermissionRoute permission="notification.write" />}><Route path="notifications/templates/new" element={<TemplateFormPage />} /><Route path="notifications/templates/:id/edit" element={<TemplateFormPage />} /></Route>
        <Route element={<PermissionRoute permission="report.read" />}><Route path="reports" element={<ReportsPage />} /><Route path="reports/monthly-payments" element={<MonthlyPaymentsReport />} /><Route path="reports/debts" element={<DebtReport />} /><Route path="reports/overdue-debts" element={<OverdueDebtsReport />} /><Route path="reports/attendance" element={<AttendanceReport />} /><Route path="reports/class-occupancy" element={<ClassOccupancyReport />} /><Route path="reports/branch-performance" element={<BranchPerformanceReport />} /></Route>
        <Route element={<PermissionRoute permission="settings.read" />}><Route path="settings" element={<SettingsPage />} /><Route path="settings/general" element={<SettingsPage initialSection="general" />} /><Route path="settings/integrations" element={<SettingsPage initialSection="integrations" />} /><Route path="settings/uploads" element={<SettingsPage initialSection="uploads" />} /><Route path="settings/notifications" element={<SettingsPage initialSection="notifications" />} /><Route path="rfid-cards" element={<RfidCardsPage />} /><Route path="rfid-cards/:id" element={<RfidCardsPage />} /><Route path="rfid-cards/:id/edit" element={<RfidCardsPage />} /><Route path="devices" element={<DevicesPage />} /><Route path="devices/:id" element={<DevicesPage />} /><Route path="devices/:id/edit" element={<DevicesPage />} /></Route>
      </Route>
      <Route path="/payment/:debtId/:amount" element={<PaymentPage />} />
      <Route path="*" element={<NotFoundPage />} />
    </Route>
  </Routes>;
}
