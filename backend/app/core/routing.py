"""Register one handler per HTTP method/path, preserving runtime precedence.

Historically multiple modules registered the same URL. Starlette selected the
first handler while OpenAPI described the last one, breaking generated clients.
Keep the first registration consistently in routing and documentation.
"""
from copy import copy
from hashlib import sha256
import re

from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute


class RouterRegistry:
    def __init__(self, app: FastAPI):
        self.app = app
        self.router = APIRouter()
        self.app.include_router(self.router)
        self.registered: set[tuple[str, str]] = set()
        self.shadowed: list[dict] = []
        self.operation_ids: set[str] = set()

    def include(self, router: APIRouter) -> None:
        filtered = copy(router)
        filtered.routes = []
        for route in router.routes:
            if not isinstance(route, APIRoute):
                filtered.routes.append(route)
                continue
            shape = re.sub(r"\{[^}]+\}", "{}", route.path)
            methods = set()
            for method in route.methods:
                key = (method, shape)
                if key in self.registered:
                    self.shadowed.append({"method": method, "path": route.path, "handler": route.name})
                else:
                    self.registered.add(key)
                    methods.add(method)
            if methods:
                registered_route = copy(route)
                registered_route.methods = methods
                operation_id = route.operation_id or route.unique_id
                if operation_id in self.operation_ids:
                    suffix = sha256(f"{sorted(methods)}:{route.path}".encode()).hexdigest()[:8]
                    operation_id = f"{operation_id}_{suffix}"
                    registered_route.operation_id = operation_id
                    registered_route.unique_id = operation_id
                self.operation_ids.add(operation_id)
                filtered.routes.append(registered_route)
        self.router.routes.extend(filtered.routes)
        # A static action/list URL (e.g. /notifications/unread-count) must
        # never be parsed as the UUID of an earlier /notifications/{id} route.
        self.router.routes.sort(key=lambda route: getattr(route, "path", "").count("{"))
