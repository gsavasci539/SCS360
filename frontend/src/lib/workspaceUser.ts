import { useMemo } from "react";
import { useAuthStore } from "../stores/auth";
import { usePlatformWorkspace, WORKSPACE_OPERATOR } from "../stores/platformWorkspace";

/** Business forms use the chosen school; authentication keeps the real account. */
export function useWorkspaceUser() {
  const principal = useAuthStore((state) => state.user), workspace = usePlatformWorkspace((state) => state.workspace);
  return useMemo(() => principal?.is_super_admin && workspace?.operatorId === principal.id
    ? { ...principal, organization_id: workspace.id, is_super_admin: false, [WORKSPACE_OPERATOR]: true }
    : principal, [principal, workspace]);
}
