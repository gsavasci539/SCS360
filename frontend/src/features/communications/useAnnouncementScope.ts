import { useAuthStore } from "../../stores/auth";
import { usePlatformWorkspace } from "../../stores/platformWorkspace";

export function useAnnouncementScope() {
  const account = useAuthStore((state) => state.user);
  const session = useAuthStore((state) => state.sessionVersion);
  const workspace = usePlatformWorkspace((state) => state.workspace);
  const institution = account?.is_super_admin
    ? workspace?.operatorId === account.id ? workspace.id : null
    : account?.organization_id;
  const canRead = useAuthStore((state) => state.can("announcement.read"));
  const canWrite = useAuthStore((state) => state.can("announcement.write"));
  const active = Boolean(account && (!account.is_super_admin || institution));
  return { active, canRead, canWrite, key: JSON.stringify([session, account?.id, institution, account?.branch_ids, canRead, canWrite]) };
}
