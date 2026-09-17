import { Plus, Search, Pencil, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader, Badge, LoadingState, ErrorState } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import type { ApiResponse, Paginated } from "../../types/api";

interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string | null;
  status: string;
  organization_id: string | null;
  roles: Array<{ id: string; name: string; slug: string }>;
}

export function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    loadUsers();
  }, [page, search]);

  const loadUsers = async () => {
    setLoading(true);
    try {
      const response = await api.get<ApiResponse<Paginated<User>>>(
        `/users?page=${page}&page_size=20${search ? `&search=${search}` : ""}`
      );
      setUsers(response.data.data.items || []);
      setTotal(response.data.data.total || 0);
    } catch (err) {
      setError(apiMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (userId: string) => {
    if (!confirm("Bu kullanıcıyı silmek istediğinize emin misiniz?")) return;
    
    try {
      await api.delete(`/users/${userId}`);
      setUsers(users.filter(u => u.id !== userId));
    } catch (err) {
      setError(apiMessage(err));
    }
  };

  if (loading) return <div className="card"><LoadingState label="Kullanıcılar yükleniyor" /></div>;
  if (error) return <div className="card"><ErrorState message={error} /></div>;

  return (
    <>
      <PageHeader
        eyebrow="Kullanıcı Yönetimi"
        title="Kullanıcılar"
        description="Sistem kullanıcılarını görüntüleyin ve yönetin."
      >
        <Link className="btn btn-primary" to="/users/new">
          <Plus size={16} />Yeni Kullanıcı
        </Link>
      </PageHeader>

      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <h2>Kullanıcı Listesi</h2>
          <span className="badge badge-green">{String(total)}</span>
        </div>
        <div className="card-pad">
          <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
            <input
              type="text"
              placeholder="İsim, soyisim veya e-posta ile ara..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{
                flex: 1,
                padding: "8px 12px",
                border: "1px solid #d1d5db",
                borderRadius: 4
              }}
            />
            <button className="btn btn-secondary" onClick={() => loadUsers()}>
              <Search size={16} />
            </button>
          </div>

          {users.length === 0 ? (
            <p style={{ color: "#5e6c6d" }}>Henüz kullanıcı yok</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Ad Soyad</th>
                  <th>E-posta</th>
                  <th>Telefon</th>
                  <th>Durum</th>
                  <th>Roller</th>
                  <th>İşlemler</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td>{user.first_name} {user.last_name}</td>
                    <td>{user.email}</td>
                    <td>{user.phone || "-"}</td>
                    <td><Badge value={user.status} /></td>
                    <td>
                      {user.roles.length > 0 ? (
                        <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                          {user.roles.map((role) => (
                            <span key={role.id} className="badge badge-blue">
                              {role.name}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span style={{ color: "#9ca3af" }}>-</span>
                      )}
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: 4 }}>
                        <Link
                          className="btn btn-secondary"
                          style={{ padding: "4px 8px", fontSize: 12 }}
                          to={`/users/${user.id}`}
                        >
                          <Pencil size={14} />
                        </Link>
                        <button
                          className="btn btn-danger"
                          style={{ padding: "4px 8px", fontSize: 12 }}
                          onClick={() => handleDelete(user.id)}
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {total > 20 && (
            <div style={{ display: "flex", gap: 8, marginTop: 16, justifyContent: "center" }}>
              <button
                className="btn btn-secondary"
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                Önceki
              </button>
              <span style={{ display: "flex", alignItems: "center" }}>
                Sayfa {page}
              </span>
              <button
                className="btn btn-secondary"
                onClick={() => setPage(p => p + 1)}
                disabled={page * 20 >= total}
              >
                Sonraki
              </button>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
