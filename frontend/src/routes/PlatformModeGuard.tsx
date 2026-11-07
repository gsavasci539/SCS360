import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuthStore } from "../stores/auth";
import { usePlatformWorkspace } from "../stores/platformWorkspace";

export function PlatformModeGuard() {
  const user = useAuthStore((state) => state.user), workspace = usePlatformWorkspace((state) => state.workspace);
  const { pathname } = useLocation();
  const control = pathname === "/platform" || pathname.startsWith("/platform/");
  if (user?.is_super_admin && !control && workspace?.operatorId !== user.id) return <Navigate to="/platform" replace />;
  return <Outlet />;
}
