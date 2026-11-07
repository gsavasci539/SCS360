"""Feature permissions for analytics, including every domain in combined reports."""
from fastapi import Depends
from app.core.dependencies import get_tenant_context
from app.core.exceptions import ForbiddenException
from app.core.tenant import TenantContext

A = ["attendance.read", "teacher.view_attendance"]
SCHOOL = [["report.read"], ["academic.read"], A, ["finance.read"], ["parents.read"]]
CLASS = [["classes.read"], ["academic.read"], A]
POLICY = {
    "/ai-academic-predictions": [["academic.read"]],
    "/ai-attendance-predictions": [A],
    "/ai-financial-predictions": [["finance.read"], ["parents.read"]],
    "/ai-parent-sentiment": [["parents.read"], ["notification.read"]],
    "/ai-operational-optimization": [["classes.read"], ["students.read"], ["users.read"]],
    "/insights-report": SCHOOL,
    "/ai-homework-analysis": [["homework.read"], ["academic.read"]],
    "/ai-daily-reports-analysis": [["daily_reports.read"]],
    "/student-performance/{student_id}": [["students.read", "parent.view_children"]],
    "/attendance-analysis": [A],
    "/payment-forecast": [["finance.read"]],
    "/canteen-analysis": [["canteen.read"]],
    "/students-overview": [["students.read"], ["academic.read"], A],
    "/parents-overview": [["parents.read"], ["finance.read"], A, ["notification.read"], ["announcements.read"]],
    "/parent-analysis/{parent_id}": [["parents.read"], ["finance.read"], A],
    "/parent-satisfaction": [["parents.read"], ["notification.read"], ["announcements.read"]],
    "/teacher-performance/{teacher_id}": [["users.read"], ["academic.read"], A],
    "/academic-performance": [["academic.read"]],
    "/communication-analysis": [["notification.read"]],
    "/inventory-analysis": [["inventory.read"]],
    "/staff-analysis": [["staff.read"], ["users.read"]],
    "/library-analysis": [["library.read"]],
    "/payroll-analysis": [["payroll.read"]],
    "/health-analysis": [["health.read"]],
    "/transport-analysis": [["bus.read"]],
    "/tutoring-analysis": [["tutoring.read"]],
    "/surveys-analysis": [["surveys.read"]],
    "/guidance-analysis": [["guidance.read"]],
    "/clubs-analysis": [["clubs.read"]],
    "/card-analysis": [["canteen.read"]],
    "/class-analysis/{class_id}": CLASS,
    "/classes-overview": CLASS,
    "/student-performance-trends": [["academic.read"]],
    "/organization-health": SCHOOL,
    "/executive-summary": [*SCHOOL, ["users.read"]],
    "/comparative-analysis": [["report.read"], ["academic.read"], A],
    "/resource-utilization": [["report.read"], ["classes.read"], ["students.read"], ["users.read"]],
    "/staff-productivity": [["report.read"], ["classes.read"], ["users.read"]],
    "/risk-management": [*SCHOOL, ["classes.read"], ["students.read"]],
    "/operational-metrics": [["report.read"], A, ["finance.read"]],
}


def allowed(tenant, path):
    return path in POLICY and all(tenant.has_any_permission(group) for group in POLICY[path])


class AnalysisPermission:
    def __init__(self, path):
        if path not in POLICY:
            raise ValueError("Missing analytics permission policy")
        self.path = path

    async def __call__(self, tenant: TenantContext = Depends(get_tenant_context)) -> TenantContext:
        if not allowed(tenant, self.path):
            raise ForbiddenException("Bu analiz için ilgili alanların okuma yetkileri gerekli")
        return tenant
