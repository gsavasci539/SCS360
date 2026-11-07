import { create } from "zustand";

const key = "scs360-platform-workspace";
export const WORKSPACE_OPERATOR = Symbol("scs360-workspace-operator");
export interface PlatformWorkspace { id: string; name: string; operatorId: string }
function initial(): PlatformWorkspace | null {
  try { const value = JSON.parse(sessionStorage.getItem(key) || "null");
    return value && ["id", "name", "operatorId"].every((field) => typeof value[field] === "string" && value[field]) ? value : null;
  } catch { return null; }
}
export const usePlatformWorkspace = create<{ workspace: PlatformWorkspace | null; select: (value: PlatformWorkspace | null) => void }>((set) => ({
  workspace: initial(),
  select: (workspace) => { try { if (workspace) sessionStorage.setItem(key, JSON.stringify(workspace)); else sessionStorage.removeItem(key); } catch { /* In-memory mode remains available. */ } set({ workspace }); },
}));

export function isWorkspaceRequest(path: string) {
  return !/^(?:[a-z]+:)?\/\//i.test(path) && !/^\/?(?:api\/)?(?:auth|platform|subscription|public)(?:\/|$|\?)/.test(path);
}
