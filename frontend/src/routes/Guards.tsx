import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuthStore } from "../stores/auth";

export function ProtectedRoute() {
  const token = useAuthStore((state) => state.accessToken); const hydrated = useAuthStore((state) => state.hydrated); const location = useLocation();
  if (!hydrated) return <div className="state" style={{ minHeight: "100vh" }}><div className="spinner" /></div>;
  return token ? <Outlet /> : <Navigate to="/login" replace state={{ from: location.pathname }} />;
}

export function PermissionRoute({ permission }: { permission?: string }) {
  const can = useAuthStore((state) => state.can);
  return can(permission) ? <Outlet /> : <Navigate to="/forbidden" replace />;
}
