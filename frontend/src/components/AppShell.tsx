import { Bell, Building2, ChevronDown, ChevronRight, LogOut, Menu, PanelLeftClose, Search, ShieldCheck, GraduationCap, MessageSquareQuote, Bus, WalletCards, ChartNoAxesCombined, Settings } from "lucide-react";
import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { navigation } from "../config/navigation";
import { api } from "../lib/api";
import { initials } from "../lib/format";
import { useAuthStore } from "../stores/auth";
import { useToast } from "./Toast";
import { Chatbot } from "./Chatbot";
import { Brand } from "./Brand";
import { LoadingState } from "./ui";
import { usePlatformWorkspace } from "../stores/platformWorkspace";

export function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [openSection, setOpenSection] = useState<string | null>(null);
  const profileRef = useRef<HTMLDivElement>(null);
  const user = useAuthStore((state) => state.user);
  const can = useAuthStore((state) => state.can);
  const refreshToken = useAuthStore((state) => state.refreshToken);
  const clearSession = useAuthStore((state) => state.clearSession);
  const location = useLocation();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const workspace = usePlatformWorkspace((state) => state.workspace);
  const activeWorkspace = user?.is_super_admin && workspace?.operatorId === user.id ? workspace : null;
  const platformView = Boolean(user?.is_super_admin && (!activeWorkspace || location.pathname.startsWith("/platform")));
  const visibleNavigation = useMemo(() => {
    if (platformView) return [{ label: "SaaS Yönetimi", items: [
      { label: "Kurumlar ve Üyelikler", path: "/platform", icon: Building2, permission: "super_admin" },
    ] }];
    const isParent = user?.roles?.some(role => role.slug === "parent");
    // Default canteen accounts receive students.read for the card picker.
    // Keep that focused menu, while honoring additional roles and permissions.
    const canteenOnly = !user?.is_super_admin && user?.roles.length === 1 && user.roles[0].slug === "canteen_staff"
      && user.permissions.every((permission) => permission.startsWith("canteen.")
        || ["students.read", "student.read", "surveys.respond"].includes(permission));
    return navigation
      .filter(section => (!section.parentOnly || isParent) && (!canteenOnly || section.label === "Operasyon"))
      .map(section => ({
        ...section,
        items: section.items.filter((item) => (can(item.permission) || item.alternativePermissions?.some((permission) => can(permission))) && (!activeWorkspace || !["/platform", "/subscription"].includes(item.path)) && (!activeWorkspace || item.permission !== "super_admin"))
      }))
      .filter(section => section.items.length > 0);
  }, [can, user, platformView, activeWorkspace]);
  const current = useMemo(() => {
    // First try to find exact match
    for (const section of visibleNavigation) {
      const item = section.items.find((item) => location.pathname === item.path);
      if (item) return item;
    }
    
    // Then try to find subpath match (excluding dashboard)
    for (const section of visibleNavigation) {
      const item = section.items.find((item) => {
        if (item.path === "/dashboard") return false;
        return location.pathname.startsWith(item.path + "/");
      });
      if (item) return item;
    }
    
    return null;
  }, [visibleNavigation, location.pathname]);

  useEffect(() => {
    if (!profileOpen) return;
    const close = (event: MouseEvent | KeyboardEvent) => {
      if (event instanceof KeyboardEvent && event.key !== "Escape") return;
      if (event instanceof MouseEvent && profileRef.current?.contains(event.target as Node)) return;
      setProfileOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => { document.removeEventListener("mousedown", close); document.removeEventListener("keydown", close); };
  }, [profileOpen]);

  async function logout() {
    try { if (refreshToken) await api.post("/auth/logout", { refresh_token: refreshToken }); } catch { /* local logout must still work */ }
    clearSession(); showToast("Oturum kapatıldı", "Güvenli biçimde çıkış yaptınız."); navigate("/login", { replace: true });
  }

  const sectionIcons: Record<string, any> = {
    "Yönetim": ShieldCheck,
    "Eğitim": GraduationCap,
    "İletişim": MessageSquareQuote,
    "Operasyon": Bus,
    "Finans": WalletCards,
    "Analiz": ChartNoAxesCombined,
    "Sistem": Settings
  };

  return <div className="app">
    {sidebarOpen && <button className="overlay" aria-label="Menüyü kapat" onClick={() => setSidebarOpen(false)} />}
    <aside className={`sidebar${sidebarOpen ? " open" : ""}`}>
      <Brand subtitle={platformView ? "Platform Yönetimi" : "Yönetim Merkezi"} />
      <div className="branch-pill"><Building2 size={18} /><div><span>Aktif çalışma alanı</span><strong>{platformView ? "SaaS yönetimi" : activeWorkspace?.name || "Kurum paneli"}</strong></div></div>
      <nav className="nav-list" aria-label="Ana menü">
        {visibleNavigation.map((section) => {
          const isOpen = openSection === section.label;
          const toggleSection = () => setOpenSection(isOpen ? null : section.label);
          return (
            <div key={section.label}>
              <button
                className="nav-section"
                aria-expanded={isOpen}
                onClick={toggleSection}
                style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%", padding: "10px 12px", background: "none", border: "none", cursor: "pointer", color: "#5e6c6d", fontSize: "13px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px", borderRadius: "6px", transition: "background 0.2s" }}
                onMouseEnter={(e) => e.currentTarget.style.background = "rgba(0,0,0,0.04)"}
                onMouseLeave={(e) => e.currentTarget.style.background = "none"}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  {(() => {
                    const SectionIcon = sectionIcons[section.label] || ShieldCheck;
                    return <SectionIcon size={16} style={{ color: "#7a8888" }} />;
                  })()}
                  {section.label}
                </div>
                <ChevronRight size={14} style={{ transition: "transform 0.2s", transform: isOpen ? "rotate(90deg)" : "rotate(0deg)" }} />
              </button>
              {isOpen && (
                <div style={{ paddingLeft: 8, marginTop: "4px" }}>
                  {section.items.map((item) => {
                    const Icon = item.icon;
                    return (
                      <NavLink
                        key={item.path}
                        to={item.path}
                        onClick={() => setSidebarOpen(false)}
                        className={({ isActive }) => `nav-item${isActive || (item.path !== "/dashboard" && location.pathname.startsWith(item.path)) ? " active" : ""}`}
                        style={{ display: "flex", alignItems: "center", gap: "10px", padding: "8px 12px", borderRadius: "6px", transition: "all 0.2s" }}
                      >
                        <Icon size={16} style={{ color: "inherit" }} />
                        <span>{item.label}</span>
                      </NavLink>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </nav>
      <div className="sidebar-footer"><strong>SCS360 v1.0</strong><br />Veriye dayalı, güvenli eğitim yönetimi.</div>
    </aside>
    <div className="workspace">
      <header className="topbar">
        <div className="topbar-left"><button className="topbar-button menu-button" onClick={() => setSidebarOpen(true)} aria-label="Menüyü aç"><Menu size={19} /></button><div className="breadcrumb">SCS360 <span> / </span> <strong>{current?.label || "Yönetim"}</strong></div></div>
        <div className="topbar-actions">{!platformView && can("students.read") && <button className="topbar-button" aria-label="Öğrenci aramasına git" onClick={() => navigate("/students")}><Search size={17} /></button>}{!platformView && can("notification.read") && <button className="topbar-button" aria-label="Bildirimler" onClick={() => navigate("/notifications")}><Bell size={17} /></button>}<div ref={profileRef} className="user-menu" style={{ position: "relative" }}><div className="avatar" aria-hidden="true">{initials(user?.first_name, user?.last_name)}</div><button className="btn btn-ghost" style={{ padding: 0 }} onClick={() => setProfileOpen((value) => !value)} aria-label="Kullanıcı menüsü" aria-expanded={profileOpen} aria-haspopup="menu"><div className="user-copy"><strong>{user?.first_name} {user?.last_name}</strong><small>{user?.roles[0]?.name || "Kullanıcı"}</small></div><ChevronDown size={14} /></button>
          {profileOpen && <div className="card" role="menu" style={{ position: "absolute", right: 0, top: 49, width: 210, padding: 8, boxShadow: "var(--shadow)" }}>{!platformView && can("settings.read") && <button role="menuitem" className="btn btn-ghost" style={{ width: "100%", justifyContent: "flex-start" }} onClick={() => { setProfileOpen(false); navigate("/settings"); }}><PanelLeftClose size={15} />Hesap ayarları</button>}<button role="menuitem" className="btn btn-ghost" style={{ width: "100%", justifyContent: "flex-start", color: "#a84141" }} onClick={logout}><LogOut size={15} />Çıkış yap</button></div>}
        </div></div>
      </header>
      <main className="main">{activeWorkspace && !platformView && <section className="card card-pad" aria-label="Seçilen kurum çalışma alanı" style={{ marginBottom: 18, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}><strong>{activeWorkspace.name}</strong><button className="btn btn-secondary" onClick={() => { usePlatformWorkspace.getState().select(null); navigate("/platform"); }}>Platform yönetimine dön</button></section>}{!user?.is_super_admin && user?.organization_access?.status === "GRACE" && <section className="card card-pad" role="alert" style={{ marginBottom: 18 }}><p>{user.organization_access.warning}</p><Link className="btn btn-primary" to="/subscription">Üyelik ve ödeme</Link></section>}<Suspense key={activeWorkspace?.id || "platform"} fallback={<LoadingState label="Sayfa yükleniyor" />}><Outlet /></Suspense></main>
    </div>
    {!platformView && <Chatbot />}
  </div>;
}
