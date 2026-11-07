import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "../stores/auth";

export function SubscriptionGuard() {
  const user = useAuthStore((state) => state.user);
  return !user?.is_super_admin && user?.organization_access?.restricted
    ? <Navigate to="/subscription" replace /> : <Outlet />;
}
