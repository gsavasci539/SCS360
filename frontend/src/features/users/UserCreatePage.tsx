import { ArrowLeft, Save } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { PageHeader, LoadingState } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";

export function UserCreatePage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    first_name: "",
    last_name: "",
    phone: "",
    organization_id: ""
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      await api.post("/users", formData);
      navigate("/users");
    } catch (err) {
      setError(apiMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <PageHeader
        eyebrow="Kullanıcı Yönetimi"
        title="Yeni Kullanıcı"
        description="Sisteme yeni kullanıcı ekleyin."
      >
        <Link className="btn btn-secondary" to="/users">
          <ArrowLeft size={16} />Listeye dön
        </Link>
      </PageHeader>

      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <h2>Kullanıcı Bilgileri</h2>
        </div>
        <div className="card-pad">
          {error && (
            <div style={{
              padding: 12,
              backgroundColor: "#fef2f2",
              border: "1px solid #fecaca",
              borderRadius: 6,
              marginBottom: 16,
              color: "#dc2626"
            }}>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div>
                <label style={{ fontSize: 12, color: "#6b7280", marginBottom: 4, display: "block" }}>
                  E-posta *
                </label>
                <input
                  type="email"
                  required
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    border: "1px solid #d1d5db",
                    borderRadius: 4
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, color: "#6b7280", marginBottom: 4, display: "block" }}>
                  Şifre *
                </label>
                <input
                  type="password"
                  required
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    border: "1px solid #d1d5db",
                    borderRadius: 4
                  }}
                />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                <div>
                  <label style={{ fontSize: 12, color: "#6b7280", marginBottom: 4, display: "block" }}>
                    Ad *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.first_name}
                    onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                    style={{
                      width: "100%",
                      padding: "8px 12px",
                      border: "1px solid #d1d5db",
                      borderRadius: 4
                    }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: 12, color: "#6b7280", marginBottom: 4, display: "block" }}>
                    Soyad *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.last_name}
                    onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                    style={{
                      width: "100%",
                      padding: "8px 12px",
                      border: "1px solid #d1d5db",
                      borderRadius: 4
                    }}
                  />
                </div>
              </div>

              <div>
                <label style={{ fontSize: 12, color: "#6b7280", marginBottom: 4, display: "block" }}>
                  Telefon
                </label>
                <input
                  type="tel"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    border: "1px solid #d1d5db",
                    borderRadius: 4
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, color: "#6b7280", marginBottom: 4, display: "block" }}>
                  Organizasyon ID (Opsiyonel)
                </label>
                <input
                  type="text"
                  value={formData.organization_id}
                  onChange={(e) => setFormData({ ...formData, organization_id: e.target.value })}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    border: "1px solid #d1d5db",
                    borderRadius: 4
                  }}
                />
              </div>

              <div style={{ display: "flex", gap: 8, marginTop: 8, justifyContent: "flex-end" }}>
                <Link className="btn btn-secondary" to="/users">
                  İptal
                </Link>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={loading}
                >
                  {loading ? <LoadingState label="Kaydediliyor..." /> : <><Save size={16} />Kaydet</>}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </>
  );
}
