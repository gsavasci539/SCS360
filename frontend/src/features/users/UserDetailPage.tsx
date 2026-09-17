import { ArrowLeft, Pencil, Shield, Building2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ErrorState, LoadingState, PageHeader, Badge } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { textValue, toArray } from "../../lib/data";
import { shortDate, titleCase } from "../../lib/format";
import { useAuthStore } from "../../stores/auth";
import type { ApiResponse, DataRecord, Paginated } from "../../types/api";

export function UserDetailPage() {
  const { id } = useParams();
  const [user, setUser] = useState<DataRecord | null>(null);
  const [roles, setRoles] = useState<DataRecord[]>([]);
  const [branches, setBranches] = useState<DataRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const can = useAuthStore((state) => state.can);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError("");
      try {
        const [userRes, rolesRes, branchesRes] = await Promise.allSettled([
          api.get<ApiResponse<DataRecord>>(`/users/${id}`),
          api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>(`/users/${id}/roles`),
          api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>(`/users/${id}/branches`)
        ]);

        if (userRes.status === "fulfilled") {
          setUser(userRes.value.data.data);
        } else {
          throw new Error(apiMessage(userRes.reason));
        }

        if (rolesRes.status === "fulfilled") {
          setRoles(toArray(rolesRes.value.data.data));
        }

        if (branchesRes.status === "fulfilled") {
          setBranches(toArray(branchesRes.value.data.data));
        }
      } catch (err) {
        setError(apiMessage(err));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  if (loading) return <div className="card"><LoadingState label="Kullanıcı bilgileri yükleniyor" /></div>;
  if (error || !user) return <div className="card"><ErrorState message={error || "Kullanıcı bulunamadı."} /></div>;

  const displayName = [user.first_name, user.last_name].map((value) => textValue(value, "")).filter(Boolean).join(" ") || textValue(user.email);

  return (
    <>
      <PageHeader
        eyebrow="Kullanıcı profili"
        title={displayName}
        description="Kullanıcı bilgileri, roller ve şube atamaları."
      >
        <Link className="btn btn-secondary" to="/users">
          <ArrowLeft size={16} />Listeye dön
        </Link>
        {can("user.write") && (
          <Link className="btn btn-primary" to={`/users/${id}/edit`}>
            <Pencil size={16} />Düzenle
          </Link>
        )}
      </PageHeader>

      <div className="detail-grid">
        <div className="card">
          <div className="card-head">
            <div>
              <h2>Kişisel bilgiler</h2>
              <p>Kullanıcının temel bilgileri</p>
            </div>
          </div>
          <div className="card-pad detail-list">
            <div className="detail-item">
              <small>Ad</small>
              <strong>{titleCase(user.first_name)}</strong>
            </div>
            <div className="detail-item">
              <small>Soyad</small>
              <strong>{titleCase(user.last_name)}</strong>
            </div>
            <div className="detail-item">
              <small>E-posta</small>
              <strong>{String(user.email)}</strong>
            </div>
            <div className="detail-item">
              <small>Telefon</small>
              <strong>{user.phone ? String(user.phone) : "-"}</strong>
            </div>
            <div className="detail-item">
              <small>Durum</small>
              <strong><Badge value={user.status} /></strong>
            </div>
            {user.created_at && (
              <div className="detail-item">
                <small>Kayıt tarihi</small>
                <strong>{shortDate(user.created_at)}</strong>
              </div>
            )}
          </div>
        </div>

        <aside className="card card-pad">
          <h2 style={{ margin: "0 0 15px", font: "700 15px Manrope" }}>Hızlı bilgiler</h2>
          <div className="quick-list" style={{ padding: 0 }}>
            <div className="quick-item" style={{ cursor: "default" }}>
              <div className="quick-icon"><Shield size={16} /></div>
              <div className="quick-copy">
                <strong>{roles.length} rol</strong>
                <span>Atanmış roller</span>
              </div>
            </div>
            <div className="quick-item" style={{ cursor: "default" }}>
              <div className="quick-icon"><Building2 size={16} /></div>
              <div className="quick-copy">
                <strong>{branches.length} şube</strong>
                <span>Erişim izni</span>
              </div>
            </div>
          </div>
        </aside>
      </div>

      {roles.length > 0 && (
        <div className="card" style={{ marginTop: 18 }}>
          <div className="card-head">
            <div>
              <h2>Roller</h2>
              <p>Kullanıcıya atanan roller</p>
            </div>
          </div>
          <div className="card-pad">
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {roles.map((role) => (
                <span key={role.id} className="badge badge-neutral">
                  <Shield size={12} style={{ marginRight: 4 }} />
                  {String(role.name)}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {branches.length > 0 && (
        <div className="card" style={{ marginTop: 18 }}>
          <div className="card-head">
            <div>
              <h2>Şube erişimi</h2>
              <p>Kullanıcının erişebildiği şubeler</p>
            </div>
          </div>
          <div className="card-pad">
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {branches.map((branch) => (
                <div key={branch.id} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <Building2 size={14} style={{ color: "#7a8888" }} />
                  <span style={{ font: "600 14px Manrope" }}>{String(branch.name)}</span>
                  {branch.code && (
                    <span style={{ fontSize: 12, color: "#7a8888" }}>({String(branch.code)})</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
