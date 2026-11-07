import json
from pathlib import Path

from app.core.analysis_access import AnalysisPermission, POLICY
from app.main import app


def test_each_registered_analytics_route_has_its_feature_policy_and_frontend_export_matches():
    def registered(router):
        for route in router.routes:
            if hasattr(route, "original_router"):
                yield from registered(route.original_router)
            else:
                yield route
    routes = [route for route in registered(app) if getattr(route, "path", "").startswith("/api/ai/")]
    assert len(routes) == len(POLICY)
    for route in routes:
        expected = route.path.removeprefix("/api/ai")
        assert any(isinstance(dependency.call, AnalysisPermission) and dependency.call.path == expected for dependency in route.dependant.dependencies), route.path
    exported = Path(__file__).resolve().parents[3] / "frontend/src/config/analysisPermissions.json"
    assert json.loads(exported.read_text(encoding="utf-8")) == {"/ai" + path: groups for path, groups in POLICY.items()}
