from app.main import app


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


def test_static_notification_template_route_precedes_dynamic_job_route():
    route_paths = list(app.openapi()["paths"])

    assert route_paths.index("/api/notifications/templates") < route_paths.index(
        "/api/notifications/{job_id}"
    )
