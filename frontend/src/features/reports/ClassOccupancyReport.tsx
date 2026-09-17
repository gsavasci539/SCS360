import { Building2, Download, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { ErrorState, LoadingState, PageHeader, StatCard } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { toArray } from "../../lib/data";
import { downloadCsv } from "../../lib/export";
import type { ApiResponse, Paginated } from "../../types/api";

interface ClassOccupancyData {
  id: string;
  class_name: string;
  class_code: string;
  branch_name: string;
  capacity: number;
  student_count: number;
  occupancy_rate: number;
  academic_year: string;
}

export function ClassOccupancyReport() {
  const [branchId, setBranchId] = useState("");
  const [academicYear, setAcademicYear] = useState("2026-2027");
  const [branches, setBranches] = useState<Array<{ id: string; name: string }>>([]);
  const [data, setData] = useState<ClassOccupancyData[]>([]);
  const [summary, setSummary] = useState({ totalClasses: 0, totalStudents: 0, totalCapacity: 0, avgOccupancy: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [branchesRes, dataRes] = await Promise.allSettled([
        api.get<ApiResponse<Array<{ id: string; name: string }> | Paginated<{ id: string; name: string }>>>("/branches", { params: { limit: 100, page_size: 100 } }),
        api.get<ApiResponse<ClassOccupancyData[] | Paginated<ClassOccupancyData>>>("/reports/class-occupancy", {
          params: {
            branch_id: branchId || undefined,
            academic_year: academicYear
          }
        })
      ]);

      if (branchesRes.status === "fulfilled") {
        setBranches(toArray(branchesRes.value.data.data));
      }

      if (dataRes.status === "fulfilled") {
        const reportData = toArray(dataRes.value.data.data);
        setData(reportData);
        const totalClasses = reportData.length;
        const totalStudents = reportData.reduce((sum, item) => sum + Number(item.student_count), 0);
        const totalCapacity = reportData.reduce((sum, item) => sum + Number(item.capacity), 0);
        const avgOccupancy = totalCapacity > 0 ? Math.round((totalStudents / totalCapacity) * 100) : 0;
        setSummary({ totalClasses, totalStudents, totalCapacity, avgOccupancy });
      } else {
        throw new Error(apiMessage(dataRes.reason));
      }
    } catch (err) {
      setError(apiMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [branchId, academicYear]);

  return (
    <>
      <PageHeader
        eyebrow="Sınıf raporları"
        title="Sınıf Doluluk Raporu"
        description="Sınıf kapasiteleri ve doluluk oranları."
      >
        <button className="btn btn-secondary" onClick={() => downloadCsv("sinif-doluluk-raporu", data)} disabled={!data.length}>
          <Download size={16} />Dışa aktar
        </button>
      </PageHeader>

      <div className="card">
        <div className="toolbar">
          <select
            className="filter-select"
            value={branchId}
            onChange={(e) => setBranchId(e.target.value)}
          >
            <option value="">Tüm şubeler</option>
            {branches.map((branch) => (
              <option key={branch.id} value={branch.id}>
                {branch.name}
              </option>
            ))}
          </select>
          <select
            className="filter-select"
            value={academicYear}
            onChange={(e) => setAcademicYear(e.target.value)}
          >
            <option value="2025-2026">2025-2026</option>
            <option value="2026-2027">2026-2027</option>
            <option value="2027-2028">2027-2028</option>
          </select>
        </div>

        {loading ? (
          <LoadingState />
        ) : error ? (
          <ErrorState message={error} retry={load} />
        ) : (
          <>
            <div className="grid stats-grid" style={{ marginBottom: 18 }}>
              <StatCard icon={<Building2 size={19} />} label="Toplam sınıf" value={summary.totalClasses} color="blue" />
              <StatCard icon={<Users size={19} />} label="Toplam öğrenci" value={summary.totalStudents} color="green" />
              <StatCard icon={<Users size={19} />} label="Toplam kapasite" value={summary.totalCapacity} color="orange" />
              <StatCard icon={<Users size={19} />} label="Ortalama doluluk" value={`${summary.avgOccupancy}%`} color="green" />
            </div>

            {data.length === 0 ? (
              <div style={{ textAlign: "center", padding: "40px 20px", color: "#7a8888" }}>
                <Users size={48} style={{ color: "#d1d9d6", margin: "0 auto 16px" }} />
                <h3 style={{ font: "600 16px Manrope", marginBottom: 8 }}>Sınıf kaydı yok</h3>
                <p>Seçili kriterlere uygun sınıf kaydı bulunmuyor.</p>
              </div>
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Sınıf</th>
                      <th>Kod</th>
                      <th>Şube</th>
                      <th>Kapasite</th>
                      <th>Öğrenci</th>
                      <th>Doluluk</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.map((item) => (
                      <tr key={item.id}>
                        <td>{item.class_name}</td>
                        <td>{item.class_code}</td>
                        <td>{item.branch_name}</td>
                        <td>{item.capacity}</td>
                        <td>{item.student_count}</td>
                        <td>
                          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <div style={{ flex: 1, height: 6, background: "#e7ece8", borderRadius: 3, overflow: "hidden" }}>
                              <div
                                style={{
                                  height: "100%",
                                  width: `${item.occupancy_rate}%`,
                                  background: item.occupancy_rate >= 90 ? "#b14545" : item.occupancy_rate >= 70 ? "#ad7020" : "#2d8f78"
                                }}
                              />
                            </div>
                            <span style={{ fontSize: 12, minWidth: 35 }}>{item.occupancy_rate}%</span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </>
  );
}
