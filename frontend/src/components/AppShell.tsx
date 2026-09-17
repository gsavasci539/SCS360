import { Bell, Building2, ChevronDown, ChevronRight, LogOut, Menu, PanelLeftClose, School, Search, ShieldCheck, GraduationCap, MessageSquareQuote, Bus, WalletCards, ChartNoAxesCombined, Settings } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { navigation, type NavigationSection } from "../config/navigation";
import { api } from "../lib/api";
import { initials } from "../lib/format";
import { useAuthStore } from "../stores/auth";
import { useToast } from "./Toast";

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
  const visibleNavigation = useMemo(() => {
    // Check if user has admin-level permissions (not just canteen.write)
    const isAdmin = can("users.write") || can("org.read") || can("branch.read");
    
    // If user is canteen staff (has canteen.write but not admin permissions), only show Operasyon section
    if (can("canteen.write") && !isAdmin) {
      return navigation
        .filter(section => section.label === "Operasyon")
        .map(section => ({
          ...section,
          items: section.items.filter((item) => can(item.permission))
        }))
        .filter(section => section.items.length > 0);
    }
    
    // Normal permission-based filtering for admin and other users
    return navigation.map(section => ({
      ...section,
      items: section.items.filter((item) => can(item.permission))
    })).filter(section => section.items.length > 0);
  }, [can]);
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
      <div className="brand"><div className="brand-mark"><School size={23} /></div><div><div className="brand-title">Okul360</div><div className="brand-subtitle">Yönetim Merkezi</div></div></div>
      <div className="branch-pill"><Building2 size={18} /><div><span>Aktif çalışma alanı</span><strong>{user?.is_super_admin ? "Tüm kurumlar" : "Kurum paneli"}</strong></div></div>
      <nav className="nav-list" aria-label="Ana menü">
        {visibleNavigation.map((section) => {
          const isOpen = openSection === section.label;
          const toggleSection = () => setOpenSection(isOpen ? null : section.label);
          return (
            <div key={section.label}>
              <button
                className="nav-section"
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
      <div className="sidebar-footer"><strong>Okul360 v1.0</strong><br />Veriye dayalı, güvenli eğitim yönetimi.</div>
    </aside>
    <div className="workspace">
      <header className="topbar">
        <div className="topbar-left"><button className="topbar-button menu-button" onClick={() => setSidebarOpen(true)} aria-label="Menüyü aç"><Menu size={19} /></button><div className="breadcrumb">Okul360 <span> / </span> <strong>{current?.label || "Yönetim"}</strong></div></div>
        <div className="topbar-actions">{can("students.read") && <button className="topbar-button" aria-label="Öğrenci aramasına git" onClick={() => navigate("/students")}><Search size={17} /></button>}{can("notification.read") && <button className="topbar-button" aria-label="Bildirimler" onClick={() => navigate("/notifications")}><Bell size={17} /></button>}<div ref={profileRef} className="user-menu" style={{ position: "relative" }}><div className="avatar" aria-hidden="true">{initials(user?.first_name, user?.last_name)}</div><button className="btn btn-ghost" style={{ padding: 0 }} onClick={() => setProfileOpen((value) => !value)} aria-label="Kullanıcı menüsü" aria-expanded={profileOpen} aria-haspopup="menu"><div className="user-copy"><strong>{user?.first_name} {user?.last_name}</strong><small>{user?.roles[0]?.name || "Kullanıcı"}</small></div><ChevronDown size={14} /></button>
          {profileOpen && <div className="card" role="menu" style={{ position: "absolute", right: 0, top: 49, width: 210, padding: 8, boxShadow: "var(--shadow)" }}>{can("settings.read") && <button role="menuitem" className="btn btn-ghost" style={{ width: "100%", justifyContent: "flex-start" }} onClick={() => { setProfileOpen(false); navigate("/settings"); }}><PanelLeftClose size={15} />Hesap ayarları</button>}<button role="menuitem" className="btn btn-ghost" style={{ width: "100%", justifyContent: "flex-start", color: "#a84141" }} onClick={logout}><LogOut size={15} />Çıkış yap</button></div>}
        </div></div>
      </header>
      <main className="main"><Outlet /></main>
    </div>
  </div>;
}
