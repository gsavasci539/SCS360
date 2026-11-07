import re
from pathlib import Path

from app.main import app


API_CALL_PATTERN = re.compile(r"api\.(get|post|put|patch|delete)\s*(?:<[^()]*>)?\s*\(\s*([`\"'])(.*?)\2", re.S)


def _openapi_path_regex(path: str) -> re.Pattern[str]:
    parts = []
    for part in path.split("/"):
        if part.startswith("{") and part.endswith("}"):
            parts.append("[^/]+")
        else:
            parts.append(re.escape(part))
    return re.compile("^" + "/".join(parts) + "$")


def _frontend_api_calls():
    frontend_root = Path(__file__).resolve().parents[3] / "frontend" / "src"
    for extension in ("*.ts", "*.tsx"):
        for source_file in frontend_root.rglob(extension):
            relative = source_file.relative_to(frontend_root)
            if {"test", "__tests__"}.intersection(relative.parts) or ".test." in source_file.name:
                continue
            text = source_file.read_text(encoding="utf-8")
            for match in API_CALL_PATTERN.finditer(text):
                method, _, raw_path = match.groups()
                if not raw_path.startswith("/"):
                    continue
                # These interpolations select among a fixed set of registered
                # static report endpoints, rather than a path parameter.
                if raw_path == "/reports/${tab}":
                    for report in ("monthly-payments", "debts", "overdue-debts", "attendance", "class-occupancy", "branch-performance"):
                        yield source_file, method, raw_path, f"/api/reports/{report}"
                    continue
                if raw_path == "/reports/export/${format}":
                    for format in ("csv", "excel"):
                        yield source_file, method, raw_path, f"/api/reports/export/{format}"
                    continue
                if raw_path == "/guidance/${kind}":
                    for resource in ("sessions", "incidents", "notes"):
                        yield source_file, method, raw_path, f"/api/guidance/{resource}"
                    continue
                if raw_path == "/payroll/${kind}":
                    for resource in ("records", "timesheets", "additional-hours"):
                        yield source_file, method, raw_path, f"/api/payroll/{resource}"
                    continue
                if raw_path == "/tutoring/${kind}":
                    for resource in ("sessions", "requests", "availability"):
                        yield source_file, method, raw_path, f"/api/tutoring/{resource}"
                    continue
                normalized_path = re.sub(r"\$\{[^}]+\}", "value", raw_path).split("?")[0]
                yield source_file, method, raw_path, f"/api{normalized_path}"


def test_frontend_api_contract_is_registered():
    paths = app.openapi()["paths"]

    assert "/api/{path}" not in paths
    expected = {
        "/api/students": {"get", "post"},
        "/api/parents": {"get", "post"},
        "/api/classes/{class_id}/assign-students": {"post"},
        "/api/reports/attendance": {"get"},
        "/api/reports/overdue-debts/remind": {"post"},
        "/api/announcements/{announcement_id}/results": {"get"},
        "/api/announcements/{announcement_id}/retry": {"post"},
        "/api/notifications/templates/{template_id}": {"get", "put"},
    }
    for path, methods in expected.items():
        assert path in paths
        assert methods.issubset(paths[path])


def test_mobile_openapi_operation_ids_are_unique():
    ids = [operation["operationId"] for methods in app.openapi()["paths"].values()
           for operation in methods.values() if isinstance(operation, dict) and "operationId" in operation]
    assert len(ids) == len(set(ids))


def test_static_notification_template_route_precedes_dynamic_job_route():
    route_paths = list(app.openapi()["paths"])

    assert route_paths.index("/api/notifications/templates") < route_paths.index(
        "/api/notifications/{job_id}"
    )


def test_frontend_api_calls_are_registered_in_openapi():
    compiled_paths = [
        (path, _openapi_path_regex(path), set(operations.keys()))
        for path, operations in app.openapi()["paths"].items()
    ]
    missing = []

    for source_file, method, raw_path, normalized_path in _frontend_api_calls():
        matches = [
            operations
            for _, path_regex, operations in compiled_paths
            if path_regex.match(normalized_path)
        ]
        if not any(method in operations for operations in matches):
            missing.append(f"{source_file.name}: {method.upper()} {raw_path}")

    assert not missing, "\n".join(missing)
