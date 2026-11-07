import { lazy, Suspense } from "react";
import { LoadingState } from "./components/ui";
import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";

import { ForgotPasswordPage, LoginPage, ResetPasswordPage } from "./features/auth/AuthPages";

import { ForbiddenPage, NotFoundPage } from "./features/errors/ErrorPages";

import { ProtectedRoute } from "./routes/Guards";
import { PermissionRoute } from "./routes/Guards";
import { resources } from "./config/resources";
import { getHomePath } from "./lib/home";
import { useAuthStore } from "./stores/auth";
import { SubscriptionGuard } from "./routes/SubscriptionGuard";
import { PlatformModeGuard } from "./routes/PlatformModeGuard";

const PlatformPage = lazy(() => import("./features/saas/PlatformPage").then((module) => ({ default: module.PlatformPage })));
const SubscriptionPage = lazy(() => import("./features/saas/SubscriptionPage").then((module) => ({ default: module.SubscriptionPage })));
const MarketingPage = lazy(() => import("./features/marketing/MarketingPage").then((module) => ({ default: module.MarketingPage })));
const SignupPage = lazy(() => import("./features/marketing/SignupPage").then((module) => ({ default: module.SignupPage })));

const AttendancePage = lazy(() => import("./features/attendance/AttendancePage").then((module) => ({ default: module.AttendancePage })));
const StudentAttendancePage = lazy(() => import("./features/attendance/StudentAttendancePage").then((module) => ({ default: module.StudentAttendancePage })));
const BulkAttendancePage = lazy(() => import("./features/attendance/BulkAttendancePage").then((module) => ({ default: module.BulkAttendancePage })));
const MonthlyAttendanceReport = lazy(() => import("./features/attendance/MonthlyAttendanceReport").then((module) => ({ default: module.MonthlyAttendanceReport })));
const AnnouncementsPage = lazy(() => import("./features/communications/CommunicationPages").then((module) => ({ default: module.AnnouncementsPage })));
const AnnouncementFormPage = lazy(() => import("./features/communications/CommunicationPages").then((module) => ({ default: module.AnnouncementFormPage })));
const NotificationsPage = lazy(() => import("./features/communications/CommunicationPages").then((module) => ({ default: module.NotificationsPage })));
const TemplatesPage = lazy(() => import("./features/communications/CommunicationPages").then((module) => ({ default: module.TemplatesPage })));
const AnnouncementDetailPage = lazy(() => import("./features/communications/AnnouncementDetailPage").then((module) => ({ default: module.AnnouncementDetailPage })));
const TemplateFormPage = lazy(() => import("./features/communications/TemplateFormPage").then((module) => ({ default: module.TemplateFormPage })));
const DashboardPage = lazy(() => import("./features/dashboard/DashboardPage").then((module) => ({ default: module.DashboardPage })));
const PaymentDetailPage = lazy(() => import("./features/finance/FinancePages").then((module) => ({ default: module.PaymentDetailPage })));
const PaymentFormPage = lazy(() => import("./features/finance/FinancePages").then((module) => ({ default: module.PaymentFormPage })));
const PaymentsPage = lazy(() => import("./features/finance/FinancePages").then((module) => ({ default: module.PaymentsPage })));
const ReceiptDetailPage = lazy(() => import("./features/finance/FinancePages").then((module) => ({ default: module.ReceiptDetailPage })));
const ReceiptsPage = lazy(() => import("./features/finance/FinancePages").then((module) => ({ default: module.ReceiptsPage })));
const StudentPaymentsPage = lazy(() => import("./features/finance/StudentPaymentsPage").then((module) => ({ default: module.StudentPaymentsPage })));
const ReceiptPrintPage = lazy(() => import("./features/finance/ReceiptPrintPage").then((module) => ({ default: module.ReceiptPrintPage })));
const ReportsPage = lazy(() => import("./features/reports/ReportsPage").then((module) => ({ default: module.ReportsPage })));
const MonthlyPaymentsReport = lazy(() => import("./features/reports/MonthlyPaymentsReport").then((module) => ({ default: module.MonthlyPaymentsReport })));
const DebtReport = lazy(() => import("./features/reports/DebtReport").then((module) => ({ default: module.DebtReport })));
const OverdueDebtsReport = lazy(() => import("./features/reports/OverdueDebtsReport").then((module) => ({ default: module.OverdueDebtsReport })));
const AttendanceReport = lazy(() => import("./features/reports/AttendanceReport").then((module) => ({ default: module.AttendanceReport })));
const RfidCardsPage = lazy(() => import("./features/system/RfidCardsPage").then((module) => ({ default: module.RfidCardsPage })));
const DevicesPage = lazy(() => import("./features/system/DevicesPage").then((module) => ({ default: module.DevicesPage })));
const ClassOccupancyReport = lazy(() => import("./features/reports/ClassOccupancyReport").then((module) => ({ default: module.ClassOccupancyReport })));
const BranchPerformanceReport = lazy(() => import("./features/reports/BranchPerformanceReport").then((module) => ({ default: module.BranchPerformanceReport })));
const DetailPage = lazy(() => import("./features/resources/DetailPage").then((module) => ({ default: module.DetailPage })));
const ResourceFormPage = lazy(() => import("./features/resources/ResourcePages").then((module) => ({ default: module.ResourceFormPage })));
const ResourceListPage = lazy(() => import("./features/resources/ResourcePages").then((module) => ({ default: module.ResourceListPage })));
const RolesPage = lazy(() => import("./features/roles/RolesPage").then((module) => ({ default: module.RolesPage })));
const RolePermissionsPage = lazy(() => import("./features/roles/RolePermissionsPage").then((module) => ({ default: module.RolePermissionsPage })));
const SettingsPage = lazy(() => import("./features/settings/SettingsPage").then((module) => ({ default: module.SettingsPage })));
const StudentFilesPage = lazy(() => import("./features/students/StudentFilesPage").then((module) => ({ default: module.StudentFilesPage })));
const StudentDetailPage = lazy(() => import("./features/students/StudentDetailPage").then((module) => ({ default: module.StudentDetailPage })));
const StudentParentsPage = lazy(() => import("./features/students/StudentParentsPage").then((module) => ({ default: module.StudentParentsPage })));
const StudentsPage = lazy(() => import("./features/students/StudentsPage").then((module) => ({ default: module.StudentsPage })));
const ClassOccupancyPage = lazy(() => import("./features/classes/ClassOccupancyPage").then((module) => ({ default: module.ClassOccupancyPage })));
const AssignStudentsPage = lazy(() => import("./features/classes/AssignStudentsPage").then((module) => ({ default: module.AssignStudentsPage })));
const ClassDetailPage = lazy(() => import("./features/classes/ClassDetailPage").then((module) => ({ default: module.ClassDetailPage })));
const UserDetailPage = lazy(() => import("./features/users/UserDetailPage").then((module) => ({ default: module.UserDetailPage })));
const UsersPage = lazy(() => import("./features/users/UsersPage").then((module) => ({ default: module.UsersPage })));
const UserCreatePage = lazy(() => import("./features/users/UserCreatePage").then((module) => ({ default: module.UserCreatePage })));
const AppointmentsPage = lazy(() => import("./features/communications/AppointmentsPage").then((module) => ({ default: module.AppointmentsPage })));
const ParentNoticesPage = lazy(() => import("./features/communications/ParentNoticesPage").then((module) => ({ default: module.ParentNoticesPage })));
const OutboxPage = lazy(() => import("./features/communications/OutboxPage").then((module) => ({ default: module.OutboxPage })));
const OutboxDetailPage = lazy(() => import("./features/communications/OutboxDetailPage").then((module) => ({ default: module.OutboxDetailPage })));
const DailyReportsPage = lazy(() => import("./features/academic/DailyReportsPage").then((module) => ({ default: module.DailyReportsPage })));
const DailyReportsDetailPage = lazy(() => import("./features/academic/DailyReportsPage").then((module) => ({ default: module.DailyReportsDetailPage })));
const HomeworkPage = lazy(() => import("./features/academic/HomeworkPage").then((module) => ({ default: module.HomeworkPage })));
const HomeworkDetailPage = lazy(() => import("./features/academic/HomeworkPage").then((module) => ({ default: module.HomeworkDetailPage })));
const LibraryPage = lazy(() => import("./features/resources/LibraryPage").then((module) => ({ default: module.LibraryPage })));
const ExpensesPage = lazy(() => import("./features/finance/ExpensesPage").then((module) => ({ default: module.ExpensesPage })));
const OrganizationsPage = lazy(() => import("./features/organizations/OrganizationsPage").then((module) => ({ default: module.OrganizationsPage })));
const OrganizationDetailPage = lazy(() => import("./features/organizations/OrganizationDetailPage").then((module) => ({ default: module.OrganizationDetailPage })));
const BranchesPage = lazy(() => import("./features/branches/BranchesPage").then((module) => ({ default: module.BranchesPage })));
const StaffPage = lazy(() => import("./features/staff/StaffPage").then((module) => ({ default: module.StaffPage })));
const StaffDetailPage = lazy(() => import("./features/staff/StaffDetailPage").then((module) => ({ default: module.StaffDetailPage })));
const CanteenPage = lazy(() => import("./features/operations/CanteenPage").then((module) => ({ default: module.CanteenPage })));
const CardBalancePage = lazy(() => import("./features/operations/CardBalancePage").then((module) => ({ default: module.CardBalancePage })));
const CanteenSalesPage = lazy(() => import("./features/operations/CanteenSalesPage").then((module) => ({ default: module.CanteenSalesPage })));
const BusPage = lazy(() => import("./features/transport/BusPage").then((module) => ({ default: module.BusPage })));
const SecurityPage = lazy(() => import("./features/security/SecurityPage").then((module) => ({ default: module.SecurityPage })));
const DismissalPage = lazy(() => import("./features/security/DismissalPage").then((module) => ({ default: module.DismissalPage })));
const TimetablePage = lazy(() => import("./features/academic/TimetablePage").then((module) => ({ default: module.TimetablePage })));
const ExamsPage = lazy(() => import("./features/academic/ExamsPage").then((module) => ({ default: module.ExamsPage })));
const MaterialsPage = lazy(() => import("./features/academic/MaterialsPage").then((module) => ({ default: module.MaterialsPage })));
const HealthPage = lazy(() => import("./features/health/HealthPage").then((module) => ({ default: module.HealthPage })));
const GuidancePage = lazy(() => import("./features/guidance/GuidancePage").then((module) => ({ default: module.GuidancePage })));
const TutoringPage = lazy(() => import("./features/tutoring/TutoringPage").then((module) => ({ default: module.TutoringPage })));
const ClubsPage = lazy(() => import("./features/clubs/ClubsPage").then((module) => ({ default: module.ClubsPage })));
const PayrollPage = lazy(() => import("./features/payroll/PayrollPage").then((module) => ({ default: module.PayrollPage })));
const InventoryPage = lazy(() => import("./features/inventory/InventoryPage").then((module) => ({ default: module.InventoryPage })));
const SurveysPage = lazy(() => import("./features/surveys/SurveysPage").then((module) => ({ default: module.SurveysPage })));
const StaffSurveysPage = lazy(() => import("./features/parent/ParentSurveys").then((module) => ({ default: module.StaffSurveysPage })));
const ConsentsPage = lazy(() => import("./features/consents/ConsentsPage").then((module) => ({ default: module.ConsentsPage })));
const ParentPortalPage = lazy(() => import("./features/parent/ParentPortalPage").then((module) => ({ default: module.ParentPortalPage })));
const PaymentPage = lazy(() => import("./features/payment/PaymentPage").then((module) => ({ default: module.PaymentPage })));
const SchoolPaymentSettings = lazy(() => import("./features/payment/SchoolPaymentSettings").then((module) => ({ default: module.SchoolPaymentSettings })));
const SchoolPaymentReviewPage = lazy(() => import("./features/payment/SchoolPaymentReviewPage").then((module) => ({ default: module.SchoolPaymentReviewPage })));
const AboutPage = lazy(() => import("./features/marketing/AboutPage").then((module) => ({ default: module.AboutPage })));
const AIAnalyticsPage = lazy(() => import("./features/ai/AIAnalyticsPage").then((module) => ({ default: module.AIAnalyticsPage })));
const ChatbotManagementPage = lazy(() => import("./features/ai/ChatbotManagementPage").then((module) => ({ default: module.ChatbotManagementPage })));
const TeacherPortalPage = lazy(() => import("./features/teacher/TeacherPortalPage"));

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

function RoleHomeRedirect() {
  const user = useAuthStore((state) => state.user);
  return <Navigate to={getHomePath(user)} replace />;
}

export default function App() {
  return <Routes>
    <Route path="/" element={<Suspense fallback={<LoadingState label="SCS360 yükleniyor" />}><MarketingPage /></Suspense>} />
    <Route path="/fiyatlandirma" element={<Suspense fallback={<LoadingState label="Paketler yükleniyor" />}><MarketingPage pricing /></Suspense>} />
    <Route path="/hakkimizda" element={<Suspense fallback={<LoadingState label="Sayfa yükleniyor" />}><AboutPage /></Suspense>} />
    <Route path="/kayit" element={<Suspense fallback={<LoadingState label="Üyelik yükleniyor" />}><SignupPage /></Suspense>} />
    <Route path="/login" element={<LoginPage />} />
    <Route path="/forgot-password" element={<ForgotPasswordPage />} />
    <Route path="/reset-password" element={<ResetPasswordPage />} />
    <Route element={<ProtectedRoute />}>
      <Route path="/subscription" element={<Suspense fallback={<LoadingState label="Üyelik yükleniyor" />}><SubscriptionPage /></Suspense>} />
      <Route element={<SubscriptionGuard />}>
      <Route element={<PlatformModeGuard />}>
      <Route path="/forbidden" element={<ForbiddenPage />} />
      <Route element={<AppShell />}>
        <Route path="settings/payments" element={<SchoolPaymentSettings />} />
        <Route element={<PermissionRoute permission="finance.read" alternativePermissions={["finance.write"]} />}><Route path="finance/online-payments" element={<SchoolPaymentReviewPage />} /></Route>
        <Route element={<PermissionRoute permission="super_admin" />}><Route path="platform" element={<PlatformPage />} /></Route>
        <Route path="app" element={<RoleHomeRedirect />} />
        <Route element={<PermissionRoute permission="dashboard.read" />}><Route path="dashboard" element={<DashboardPage />} /></Route>
        <Route element={<PermissionRoute permission="dashboard.read" />}><Route path="ai-analytics" element={<AIAnalyticsPage />} /></Route>
        <Route element={<PermissionRoute permission="super_admin" />}><Route path="ai/analytics" element={<AIAnalyticsPage />} /></Route>
        <Route element={<PermissionRoute permission="super_admin" />}><Route path="ai/chatbot" element={<ChatbotManagementPage />} /></Route>
        <Route element={<PermissionRoute permission="parent.view_children" />}><Route path="parent/dashboard" element={<ParentPortalPage view="dashboard" />} /><Route path="parent/children" element={<ParentPortalPage view="children" />} /><Route path="parent/schedule" element={<ParentPortalPage view="schedule" />} /><Route path="parent/homework" element={<ParentPortalPage view="homework" />} /><Route path="parent/materials" element={<ParentPortalPage view="materials" />} /><Route path="parent/communication" element={<ParentPortalPage view="communication" />} /><Route path="parent/announcements" element={<ParentPortalPage view="announcements" />} /><Route path="parent/activities" element={<ParentPortalPage view="activities" />} /><Route path="parent/consents" element={<ParentPortalPage view="consents" />} /><Route path="parent/surveys" element={<ParentPortalPage view="surveys" />} /><Route path="parent/reports" element={<ParentPortalPage view="reports" />} /><Route path="parent/chat" element={<ParentPortalPage view="chat" />} /></Route>
        <Route element={<PermissionRoute permission="parent.view_children" />}><Route path="parent/academic" element={<ParentPortalPage view="academic" />} /></Route>
        <Route element={<PermissionRoute permission="teacher.view_classes" />}><Route path="teacher" element={<TeacherPortalPage />} /></Route>
        <Route element={<PermissionRoute permission="parent.view_attendance" />}><Route path="parent/attendance" element={<ParentPortalPage view="attendance" />} /></Route>
        <Route element={<PermissionRoute permission="parent.view_finances" />}><Route path="parent/finances" element={<ParentPortalPage view="finances" />} /></Route>
        <Route element={<PermissionRoute permission="parent.view_children" />}><Route path="parent/health" element={<ParentPortalPage view="health" />} /></Route>
        <Route element={<PermissionRoute permission="org.read" />}><Route path="organizations" element={<OrganizationsPage />} /><Route path="organizations/:id" element={<OrganizationDetailPage />} /></Route>
        <Route element={<PermissionRoute permission="org.write" />}><Route path="organizations/:id/edit" element={<ResourceFormPage resourceKey="organizations" />} /></Route>
        <Route element={<PermissionRoute permission="branch.read" />}><Route path="branches" element={<BranchesPage />} /></Route>
        <Route element={<PermissionRoute permission="branch.read" />}><Route path="branches/:id" element={<DetailPage resourceKey="branches" />} /></Route>
        <Route element={<PermissionRoute permission="branch.write" />}><Route path="branches/new" element={<ResourceFormPage resourceKey="branches" />} /><Route path="branches/:id/edit" element={<ResourceFormPage resourceKey="branches" />} /></Route>
        <Route element={<PermissionRoute permission="user.read" />}><Route path="staff" element={<StaffPage />} /><Route path="staff/:id" element={<StaffDetailPage />} /></Route>
        <Route element={<PermissionRoute permission="user.read" />}><Route path="users" element={<UsersPage />} /></Route>
        <Route element={<PermissionRoute permission="user.write" />}><Route path="users/new" element={<UserCreatePage />} /></Route>
        <Route path="users">{ResourceRoutes({ keyName: "users" })}<Route element={<PermissionRoute permission="user.read" />}><Route path=":id" element={<UserDetailPage />} /></Route></Route>
        <Route element={<PermissionRoute permission="user.read" />}><Route path="roles" element={<RolesPage />} /></Route>
        <Route element={<PermissionRoute permission="user.write" />}><Route path="roles/:id/permissions" element={<RolePermissionsPage />} /></Route>
        <Route path="parents">{ResourceRoutes({ keyName: "parents", details: true })}</Route>
        <Route path="classes">{ResourceRoutes({ keyName: "classes", details: false })}<Route element={<PermissionRoute permission="class.read" />}><Route path=":id" element={<ClassDetailPage />} /><Route path=":id/occupancy" element={<ClassOccupancyPage />} /></Route><Route element={<PermissionRoute permission="class.write" />}><Route path=":id/assign-students" element={<AssignStudentsPage />} /></Route></Route>
        <Route element={<PermissionRoute permission="attendance.read" />}><Route path="attendance" element={<AttendancePage />} /><Route path="attendance/student/:id" element={<StudentAttendancePage />} /><Route path="attendance/reports/monthly" element={<MonthlyAttendanceReport />} /></Route>
        <Route element={<PermissionRoute permission="attendance.write" />}><Route path="attendance/bulk" element={<BulkAttendancePage />} /></Route>
        <Route element={<PermissionRoute permission="students.read" />}><Route path="students" element={<StudentsPage />} /><Route path="students/:id" element={<StudentDetailPage />} /><Route path="students/:id/files" element={<StudentFilesPage />} /><Route path="students/:id/parents" element={<StudentParentsPage />} /></Route>
        <Route element={<PermissionRoute permission="students.write" />}><Route path="students/new" element={<ResourceFormPage resourceKey="students" />} /><Route path="students/:id/edit" element={<ResourceFormPage resourceKey="students" />} /></Route>
        <Route element={<PermissionRoute permission="homework.read" />}><Route path="homework" element={<HomeworkPage />} /><Route path="homework/:id" element={<HomeworkDetailPage />} /></Route>
        <Route element={<PermissionRoute permission="library.read" />}><Route path="library" element={<LibraryPage />} /><Route path="library/books/:id" element={<DetailPage resourceKey="libraryBooks" />} /></Route>
        <Route element={<PermissionRoute permission="library.write" />}><Route path="library/books/new" element={<ResourceFormPage resourceKey="libraryBooks" />} /><Route path="library/books/:id/edit" element={<ResourceFormPage resourceKey="libraryBooks" />} /></Route>
        <Route element={<PermissionRoute permission="daily_reports.read" />}><Route path="daily-reports" element={<DailyReportsPage />} /><Route path="daily-reports/:id" element={<DailyReportsDetailPage />} /></Route>
        <Route element={<PermissionRoute permission="parent_notices.read" />}><Route path="parent-notices" element={<ParentNoticesPage />} /><Route path="parent-notices/:id" element={<ParentNoticesPage />} /></Route>
        <Route element={<PermissionRoute permission="appointments.read" />}><Route path="appointments" element={<AppointmentsPage />} /><Route path="appointments/:id" element={<AppointmentsPage />} /></Route>
        <Route element={<PermissionRoute permission="outbox.read" />}><Route path="outbox" element={<OutboxPage />} /><Route path="outbox/:id" element={<OutboxDetailPage />} /></Route>
        <Route element={<PermissionRoute permission="security.read" />}><Route path="security" element={<SecurityPage />} /></Route>
        <Route element={<PermissionRoute permission="dismissal.read" />}><Route path="dismissal" element={<DismissalPage />} /></Route>
        <Route element={<PermissionRoute permission="academic.read" />}><Route path="timetable" element={<TimetablePage />} /><Route path="materials" element={<MaterialsPage />} /></Route>
        <Route element={<PermissionRoute permission="exam.read" alternativePermissions={["exam.write"]} />}><Route path="exams" element={<ExamsPage />} /></Route>
        <Route element={<PermissionRoute permission="health.read" />}><Route path="health" element={<HealthPage />} /></Route>
        <Route element={<PermissionRoute permission="guidance.read" />}><Route path="guidance" element={<GuidancePage />} /></Route>
        <Route element={<PermissionRoute permission="bus.read" />}><Route path="transport" element={<BusPage />} /></Route>
        <Route element={<PermissionRoute permission="tutoring.read" />}><Route path="tutoring" element={<TutoringPage />} /></Route>
        <Route element={<PermissionRoute permission="clubs.read" />}><Route path="clubs" element={<ClubsPage />} /></Route>
        <Route element={<PermissionRoute permission="payroll.read" />}><Route path="payroll" element={<PayrollPage />} /></Route>
        <Route element={<PermissionRoute permission="inventory.read" />}><Route path="inventory" element={<InventoryPage />} /></Route>
        <Route element={<PermissionRoute permission="survey.read" />}><Route path="surveys" element={<SurveysPage />} /></Route>
        <Route element={<PermissionRoute permission="surveys.respond" />}><Route path="my-surveys" element={<StaffSurveysPage />} /></Route>
        <Route element={<PermissionRoute permission="consent.read" />}><Route path="consents" element={<ConsentsPage />} /></Route>
        <Route path="finance/debts">{ResourceRoutes({ keyName: "debts", details: true })}</Route>
        <Route element={<PermissionRoute permission="finance.read" />}><Route path="finance/payments" element={<PaymentsPage />} /><Route path="finance/payments/:id" element={<PaymentDetailPage />} /><Route path="finance/payments/student/:id" element={<StudentPaymentsPage />} /><Route path="finance/expenses" element={<ExpensesPage />} /></Route>
        <Route element={<PermissionRoute permission="canteen.read" />}><Route path="canteen" element={<CanteenPage />} /><Route path="canteen/card-balance" element={<CardBalancePage />} /><Route path="canteen/sales" element={<CanteenSalesPage />} /></Route>
        <Route element={<PermissionRoute permission="finance.write" alternativePermissions={["finance.collect_payment"]} />}><Route path="finance/payments/new" element={<PaymentFormPage />} /></Route>
        <Route element={<PermissionRoute permission="finance.read" />}><Route path="finance/expenses/:id" element={<DetailPage resourceKey="expenses" />} /></Route>
        <Route element={<PermissionRoute permission="finance.write" />}><Route path="finance/expenses/:id/edit" element={<ResourceFormPage resourceKey="expenses" />} /></Route>
        <Route element={<PermissionRoute permission="receipt.read" />}><Route path="finance/receipts" element={<ReceiptsPage />} /><Route path="finance/receipts/:id" element={<ReceiptDetailPage />} /><Route path="finance/receipts/:id/print" element={<ReceiptPrintPage />} /></Route>
        <Route element={<PermissionRoute permission="announcement.read" />}><Route path="announcements" element={<AnnouncementsPage />} /><Route path="announcements/:id" element={<AnnouncementDetailPage />} /></Route>
        <Route element={<PermissionRoute permission="announcement.write" />}><Route path="announcements/new" element={<AnnouncementFormPage />} /><Route path="announcements/:id/edit" element={<AnnouncementFormPage />} /></Route>
        <Route element={<PermissionRoute permission="notification.read" />}><Route path="notifications" element={<NotificationsPage />} /><Route path="notifications/templates" element={<TemplatesPage />} /></Route>
        <Route element={<PermissionRoute permission="notification.write" />}><Route path="notifications/templates/new" element={<TemplateFormPage />} /><Route path="notifications/templates/:id/edit" element={<TemplateFormPage />} /></Route>
        <Route element={<PermissionRoute permission="notification.read" />}><Route path="notifications/:id" element={<DetailPage resourceKey="notificationJobs" />} /></Route>
        <Route element={<PermissionRoute permission="report.read" />}><Route path="reports" element={<ReportsPage />} /><Route path="reports/monthly-payments" element={<MonthlyPaymentsReport />} /><Route path="reports/debts" element={<DebtReport />} /><Route path="reports/overdue-debts" element={<OverdueDebtsReport />} /><Route path="reports/attendance" element={<AttendanceReport />} /><Route path="reports/class-occupancy" element={<ClassOccupancyReport />} /><Route path="reports/branch-performance" element={<BranchPerformanceReport />} /></Route>
        <Route element={<PermissionRoute permission="settings.read" />}><Route path="settings" element={<SettingsPage />} /><Route path="settings/general" element={<SettingsPage initialSection="general" />} /><Route path="settings/integrations" element={<SettingsPage initialSection="integrations" />} /><Route path="settings/uploads" element={<SettingsPage initialSection="uploads" />} /><Route path="settings/notifications" element={<SettingsPage initialSection="notifications" />} /><Route path="rfid-cards" element={<RfidCardsPage />} /><Route path="rfid-cards/:id" element={<RfidCardsPage />} /><Route path="rfid-cards/:id/edit" element={<RfidCardsPage />} /><Route path="devices" element={<DevicesPage />} /><Route path="devices/:id" element={<DevicesPage />} /><Route path="devices/:id/edit" element={<DevicesPage />} /></Route>
      </Route>
      <Route path="/payment/:debtId/:amount" element={<Suspense fallback={<LoadingState label="Sayfa yükleniyor" />}><PaymentPage /></Suspense>} />
      <Route path="/payment" element={<Suspense fallback={<LoadingState label="Sayfa yükleniyor" />}><PaymentPage /></Suspense>} />
      <Route path="*" element={<NotFoundPage />} />
      </Route>
      </Route>
    </Route>
  </Routes>;
}
