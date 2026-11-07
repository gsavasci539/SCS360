import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuthStore, hasPermission } from "../stores/auth";
import { useWorkspaceUser } from "../lib/workspaceUser";

export function ProtectedRoute() {
  const token = useAuthStore((state) => state.accessToken); const hydrated = useAuthStore((state) => state.hydrated); const location = useLocation();
  if (!hydrated) return <div className="state" style={{ minHeight: "100vh" }}><div className="spinner" /></div>;
  return token ? <Outlet /> : <Navigate to="/login" replace state={{ from: location.pathname }} />;
}

export function PermissionRoute({ permission, alternativePermissions = [] }: { permission?: string; alternativePermissions?: string[] }) {
  const principal = useAuthStore((state) => state.user), user = useWorkspaceUser(), location = useLocation();
  const account = location.pathname === "/platform" || location.pathname.startsWith("/platform/") ? principal : user;
  const allowed = hasPermission(account, permission) || alternativePermissions.some((code) => hasPermission(account, code));
  return allowed ? <Outlet /> : <Navigate to="/forbidden" replace />;
}
