import { getAnalysis } from "../../lib/analysis";
import { reportClientError } from "../../lib/diagnostics";
import { ArrowLeft, Save, Upload, TrendingUp, Search } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { Link, useNavigate, useParams } from "react-router-dom";
import { DataTable } from "../../components/DataTable";
import { useToast } from "../../components/Toast";
import {
  AddButton,
  ConfirmDialog,
  ErrorState,
  Field,
  LoadingState,
  PageHeader,
} from "../../components/ui";
import { ExcelImport } from "../../components/ExcelImport";
import { resources } from "../../config/resources";
import { api, apiMessage } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";
import { useWorkspaceUser } from "../../lib/workspaceUser";
import { ResourceChoice } from "./ResourceChoice";
import type {
  ApiResponse,
  DataRecord,
  FieldConfig,
  Paginated,
  SelectOption,
} from "../../types/api";

function normalize<T>(
  data: T[] | Paginated<T> | undefined
): Paginated<T> {
  if (Array.isArray(data)) {
    return {
      items: data,
      total: data.length,
      page: 1,
      page_size: data.length || 20,
      total_pages: 1,
    };
  }

  return (
    data || {
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      total_pages: 0,
    }
  );
}

export function ResourceListPage({
  resourceKey,
}: {
  resourceKey: string;
}) {
  const config =
    resources[resourceKey];

  const basePath = config.listPath || config.detailPath || `/${resourceKey}`;

  const [rows, setRows] =
    useState<DataRecord[]>([]);

  const [page, setPage] =
    useState(1);

  const [total, setTotal] =
    useState(0);

  const [totalPages, setTotalPages] =
    useState(1);

  const [search, setSearch] =
    useState("");

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  const [deleting, setDeleting] =
    useState<DataRecord | null>(null);

  const [importOpen, setImportOpen] =
    useState(false);

  const [aiAnalysis, setAiAnalysis] =
    useState<any>(null);

  const can = useAuthStore(
    (state) => state.can
  );

  const { showToast } =
    useToast();
  const listRequest = useRef<AbortController | null>(null);

  // =========================================================
  // LISTE VERİLERİNİ YÜKLE
  // =========================================================
  const load = useCallback(
    async () => {
      listRequest.current?.abort();
      const controller = new AbortController();
      listRequest.current = controller;
      setLoading(true);
      setError("");

      try {
        

        

        const response =
          await api.get<
            ApiResponse<
              | DataRecord[]
              | Paginated<DataRecord>
            >
          >(
            config.endpoint,
            {
              params: {
                page,
                page_size: 20,
                skip:
                  (page - 1) * 20,
                limit: 20,
                search:
                  search ||
                  undefined,
              },
              signal: controller.signal,
            }
          );

        

        

        if (controller.signal.aborted) return;
        const result =
          normalize(
            response.data?.data
          );

        const finalRows = result.items;

        setRows(
          finalRows
        );

        setTotal(
          result.total
        );

        setTotalPages(
          result.total_pages ||
            1
        );
      } catch (err) {
        if (controller.signal.aborted) return;
        reportClientError(
          "DEBUG: List API error:",
          err
        );

        setError(
          apiMessage(err)
        );

        setRows([]);
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    },
    [
      config.endpoint,
      page,
      search,
      resourceKey,
    ]
  );

  // =========================================================
  // AI ANALYSIS
  // =========================================================
  const loadAiAnalysis =
    useCallback(
      async () => {
        if (
          resourceKey ===
          "parents"
        ) {
          try {
            const response =
              await getAnalysis<any>(
                "/ai/parents-overview"
              );

            if (
              response.data
                .success
            ) {
              setAiAnalysis(
                response.data
                  .data
              );
            }
          } catch (err) {
            reportClientError(
              "Failed to load AI analysis:",
              err
            );
          }
        }

        if (
          resourceKey ===
          "classes"
        ) {
          try {
            const response =
              await getAnalysis<any>(
                "/ai/classes-overview"
              );

            

            if (
              response.data
                .success
            ) {
              setAiAnalysis(
                response.data
                  .data
              );
            }
          } catch (err) {
            reportClientError(
              "Failed to load AI analysis:",
              err
            );
          }
        }
      },
      [resourceKey]
    );

  // =========================================================
  // EFFECTS
  // =========================================================
  useEffect(() => {
    const timer =
      window.setTimeout(
        load,
        search ? 320 : 0
      );

    return () => {
      window.clearTimeout(timer);
      listRequest.current?.abort();
    };
  }, [
    load,
    search,
  ]);

  useEffect(() => {
    setPage(1);
    setSearch("");
    setDeleting(null);
    setAiAnalysis(null);
  }, [resourceKey]);

  useEffect(() => {
    loadAiAnalysis();
  }, [
    loadAiAnalysis,
  ]);

  // =========================================================
  // DELETE
  // =========================================================
  async function confirmDelete() {
    if (!deleting) return;

    try {
      await api.delete(
        `${config.endpoint}/${deleting.id}`
      );

      showToast(
        `${config.singular} kaldırıldı`,
        "Kayıt güvenli biçimde pasife alındı."
      );

      setDeleting(null);

      await load();
    } catch (err) {
      showToast(
        "İşlem tamamlanamadı",
        apiMessage(err),
        "error"
      );
    }
  }

  const write = Boolean(config.permissionWrite) &&
    can(
      config.permissionWrite
    );

  // =========================================================
  // IMPORT CONFIGURATION
  // =========================================================
  const importConfig =
    useMemo(() => {
      if (
        resourceKey ===
        "students"
      ) {
        return {
          endpoint:
            "/import/students",
          title:
            "Öğrenci İçe Aktarma",
          description:
            "Excel dosyasından öğrenci bilgilerini toplu olarak içe aktarın.",
          templateColumns: [
            {
              key: "first_name",
              label: "Ad",
              required: true,
            },
            {
              key: "last_name",
              label: "Soyad",
              required: true,
            },
            {
              key: "student_number",
              label: "Öğrenci No",
              required: false,
            },
            {
              key: "date_of_birth",
              label: "Doğum Tarihi",
              required: false,
            },
            {
              key: "gender",
              label: "Cinsiyet",
              required: false,
            },
            {
              key: "address",
              label: "Adres",
              required: false,
            },
            {
              key: "phone",
              label: "Telefon",
              required: false,
            },
            {
              key: "email",
              label: "E-posta",
              required: false,
            },
          ],
        };
      }

      if (
        resourceKey ===
        "staff"
      ) {
        return {
          endpoint:
            "/import/staff",
          title:
            "Personel İçe Aktarma",
          description:
            "Excel dosyasından personel bilgilerini toplu olarak içe aktarın.",
          templateColumns: [
            {
              key: "first_name",
              label: "Ad",
              required: true,
            },
            {
              key: "last_name",
              label: "Soyad",
              required: true,
            },
            {
              key: "email",
              label: "E-posta",
              required: true,
            },
            {
              key: "phone",
              label: "Telefon",
              required: false,
            },
            {
              key: "position",
              label: "Ünvan",
              required: false,
            },
            {
              key: "department",
              label: "Departman",
              required: false,
            },
          ],
        };
      }

      if (
        resourceKey ===
        "parents"
      ) {
        return {
          endpoint:
            "/import/parents",
          title:
            "Veli İçe Aktarma",
          description:
            "Excel dosyasından veli bilgilerini toplu olarak içe aktarın.",
          templateColumns: [
            {
              key: "first_name",
              label: "Ad",
              required: true,
            },
            {
              key: "last_name",
              label: "Soyad",
              required: true,
            },
            {
              key: "relationship",
              label: "Yakınlık",
              required: true,
            },
            {
              key: "phone",
              label: "Telefon",
              required: true,
            },
            {
              key: "email",
              label: "E-posta",
              required: false,
            },
            {
              key: "address",
              label: "Adres",
              required: false,
            },
          ],
        };
      }

      if (
        resourceKey ===
        "classes"
      ) {
        return {
          endpoint:
            "/import/classes",
          title:
            "Sınıf İçe Aktarma",
          description:
            "Excel dosyasından sınıf bilgilerini toplu olarak içe aktarın.",
          templateColumns: [
            {
              key: "name",
              label: "Sınıf Adı",
              required: true,
            },
            {
              key: "code",
              label: "Sınıf Kodu",
              required: true,
            },
            {
              key: "capacity",
              label: "Kapasite",
              required: true,
            },
            {
              key: "academic_year",
              label: "Akademik Yıl",
              required: false,
            },
          ],
        };
      }

      if (
        resourceKey ===
        "organizations"
      ) {
        return {
          endpoint:
            "/import/organizations",
          title:
            "Kurum İçe Aktarma",
          description:
            "Excel dosyasından kurum bilgilerini toplu olarak içe aktarın.",
          templateColumns: [
            {
              key: "name",
              label: "Kurum Adı",
              required: true,
            },
            {
              key: "legal_name",
              label: "Ticari Unvan",
              required: false,
            },
            {
              key: "tax_number",
              label: "Vergi Numarası",
              required: false,
            },
            {
              key: "phone",
              label: "Telefon",
              required: false,
            },
            {
              key: "email",
              label: "E-posta",
              required: false,
            },
            {
              key: "city",
              label: "Şehir",
              required: false,
            },
            {
              key: "address",
              label: "Adres",
              required: false,
            },
          ],
        };
      }

      if (
        resourceKey ===
        "branches"
      ) {
        return {
          endpoint:
            "/import/branches",
          title:
            "Şube İçe Aktarma",
          description:
            "Excel dosyasından şube bilgilerini toplu olarak içe aktarın.",
          templateColumns: [
            {
              key: "name",
              label: "Şube Adı",
              required: true,
            },
            {
              key: "code",
              label: "Şube Kodu",
              required: true,
            },
            {
              key: "capacity",
              label: "Kapasite",
              required: true,
            },
            {
              key: "phone",
              label: "Telefon",
              required: false,
            },
            {
              key: "email",
              label: "E-posta",
              required: false,
            },
            {
              key: "city",
              label: "Şehir",
              required: false,
            },
            {
              key: "address",
              label: "Adres",
              required: false,
            },
          ],
        };
      }

      if (
        resourceKey ===
        "debts"
      ) {
        return {
          endpoint:
            "/import/debts",
          title:
            "Borç İçe Aktarma",
          description:
            "Excel dosyasından borç bilgilerini toplu olarak içe aktarın.",
          templateColumns: [
            {
              key: "student_number",
              label: "Öğrenci No",
              required: true,
            },
            {
              key: "debt_type",
              label: "Borç Türü",
              required: true,
            },
            {
              key: "amount",
              label: "Tutar",
              required: true,
            },
            {
              key: "due_date",
              label: "Vade Tarihi",
              required: true,
            },
            {
              key: "academic_year",
              label: "Akademik Yıl",
              required: false,
            },
            {
              key: "description",
              label: "Açıklama",
              required: false,
            },
          ],
        };
      }

      return null;
    }, [resourceKey]);

  // =========================================================
  // SINIF TABLOSU KOLONLARI
  // =========================================================
  // Eğer resources.ts öğretmen kolonunda farklı bir field
  // kullanıyorsa, sınıf sayfasında bunu teacher_name'e bağla.
  const tableColumns =
    resourceKey === "classes"
      ? (config.columns as any[]).map((column) => {
          const key = String(
            column.key ??
              column.field ??
              column.accessor ??
              column.accessorKey ??
              ""
          ).toLocaleLowerCase("tr-TR");

          const label = String(
            column.label ??
              column.title ??
              column.header ??
              ""
          ).toLocaleLowerCase("tr-TR");

          const isTeacherColumn =
            key.includes("teacher") ||
            key.includes("öğretmen") ||
            key.includes("ogretmen") ||
            label.includes("öğretmen") ||
            label.includes("ogretmen");

          if (!isTeacherColumn) {
            return column;
          }

          return {
            ...column,
            key: "teacher_name",
            field: "teacher_name",
            accessor: "teacher_name",
            accessorKey: "teacher_name",
          };
        })
      : config.columns;

  // =========================================================
  // RENDER
  // =========================================================
  return (
    <>
      <PageHeader
        eyebrow="Kayıt yönetimi"
        title={config.title}
        description={
          config.description
        }
      >
        {write && resourceKey !== "organizations" && (
          <>
            <AddButton
              to={`${basePath}/new`}
              label={`${config.singular} ekle`}
            />

            {importConfig && (
              <button
                className="btn btn-secondary"
                onClick={() =>
                  setImportOpen(
                    true
                  )
                }
              >
                <Upload size={16} />
                Excel İçe Aktar
              </button>
            )}
          </>
        )}
      </PageHeader>

      {/* =====================================================
          AI VELİ ANALİZİ
      ====================================================== */}
      {aiAnalysis &&
        resourceKey ===
          "parents" && (
          <div
            className="card"
            style={{
              marginBottom: 18,
            }}
          >
            <div className="card-head">
              <div>
                <h2>
                  AI Veli Analizi
                </h2>
                <p>
                  Veli katılımı ve
                  memnuniyeti
                </p>
              </div>

              <TrendingUp
                size={20}
                color="#176b5b"
              />
            </div>

            <div className="card-pad">
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns:
                    "repeat(4, 1fr)",
                  gap: 16,
                  marginBottom: 16,
                }}
              >
                <div
                  style={{
                    padding: 16,
                    borderRadius: 11,
                    background:
                      "#f8faf8",
                  }}
                >
                  <div
                    style={{
                      fontSize: 12,
                      color:
                        "#6e7b7d",
                      marginBottom: 4,
                    }}
                  >
                    Toplam Veli
                  </div>

                  <div
                    style={{
                      fontSize: 24,
                      fontWeight: 800,
                      color:
                        "#1b2b2e",
                    }}
                  >
                    {
                      aiAnalysis.total_parents
                    }
                  </div>
                </div>

                <div
                  style={{
                    padding: 16,
                    borderRadius: 11,
                    background:
                      "#f8faf8",
                  }}
                >
                  <div
                    style={{
                      fontSize: 12,
                      color:
                        "#6e7b7d",
                      marginBottom: 4,
                    }}
                  >
                    Aktif Veli
                  </div>

                  <div
                    style={{
                      fontSize: 24,
                      fontWeight: 800,
                      color:
                        "#1b2b2e",
                    }}
                  >
                    {
                      aiAnalysis.active_parents
                    }
                  </div>
                </div>

                <div
                  style={{
                    padding: 16,
                    borderRadius: 11,
                    background:
                      aiAnalysis.communication_rate >=
                      70
                        ? "#dcfce7"
                        : "#fee2e2",
                  }}
                >
                  <div
                    style={{
                      fontSize: 12,
                      color:
                        "#6e7b7d",
                      marginBottom: 4,
                    }}
                  >
                    İletişim Oranı
                  </div>

                  <div
                    style={{
                      fontSize: 24,
                      fontWeight: 800,
                      color:
                        "#1b2b2e",
                    }}
                  >
                    {
                      aiAnalysis.communication_rate
                    }
                    %
                  </div>
                </div>

                <div
                  style={{
                    padding: 16,
                    borderRadius: 11,
                    background:
                      aiAnalysis.payment_compliance >=
                      70
                        ? "#dcfce7"
                        : "#fee2e2",
                  }}
                >
                  <div
                    style={{
                      fontSize: 12,
                      color:
                        "#6e7b7d",
                      marginBottom: 4,
                    }}
                  >
                    Ödeme Uyumu
                  </div>

                  <div
                    style={{
                      fontSize: 24,
                      fontWeight: 800,
                      color:
                        "#1b2b2e",
                    }}
                  >
                    {
                      aiAnalysis.payment_compliance
                    }
                    %
                  </div>
                </div>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns:
                    "repeat(2, 1fr)",
                  gap: 16,
                  marginBottom: 16,
                }}
              >
                <div
                  style={{
                    padding: 16,
                    borderRadius: 11,
                    background:
                      "#f8faf8",
                  }}
                >
                  <div
                    style={{
                      fontSize: 12,
                      color:
                        "#6e7b7d",
                      marginBottom: 4,
                    }}
                  >
                    Devamsızlık Oranı
                  </div>

                  <div
                    style={{
                      fontSize: 24,
                      fontWeight: 800,
                      color:
                        "#1b2b2e",
                    }}
                  >
                    {
                      aiAnalysis.attendance_rate
                    }
                    %
                  </div>
                </div>

                <div
                  style={{
                    padding: 16,
                    borderRadius: 11,
                    background:
                      aiAnalysis.engagement_score >=
                      70
                        ? "#dcfce7"
                        : "#fee2e2",
                  }}
                >
                  <div
                    style={{
                      fontSize: 12,
                      color:
                        "#6e7b7d",
                      marginBottom: 4,
                    }}
                  >
                    Katılım Puanı
                  </div>

                  <div
                    style={{
                      fontSize: 24,
                      fontWeight: 800,
                      color:
                        "#1b2b2e",
                    }}
                  >
                    {
                      aiAnalysis.engagement_score
                    }
                    /100
                  </div>
                </div>
              </div>

              {aiAnalysis.recommendations &&
                aiAnalysis
                  .recommendations
                  .length > 0 && (
                  <div
                    style={{
                      padding: 16,
                      borderRadius: 11,
                      background:
                        "#f0f9ff",
                      borderLeft:
                        "4px solid #0ea5e9",
                    }}
                  >
                    <div
                      style={{
                        fontSize: 14,
                        fontWeight: 700,
                        color:
                          "#0c4a6e",
                        marginBottom: 12,
                      }}
                    >
                      Öneriler
                    </div>

                    <ul
                      style={{
                        margin: 0,
                        paddingLeft: 20,
                        color:
                          "#334155",
                      }}
                    >
                      {aiAnalysis.recommendations.map(
                        (
                          rec: string,
                          idx: number
                        ) => (
                          <li
                            key={idx}
                            style={{
                              marginBottom: 6,
                            }}
                          >
                            {rec}
                          </li>
                        )
                      )}
                    </ul>
                  </div>
                )}
            </div>
          </div>
        )}

      {/* =====================================================
          AI SINIF ANALİZİ
      ====================================================== */}
      {aiAnalysis &&
        resourceKey ===
          "classes" && (
          <div
            className="card"
            style={{
              marginBottom: 18,
            }}
          >
            <div className="card-head">
              <div>
                <h2>
                  AI Sınıf Analizi
                </h2>

                <p>
                  Sınıf performansı ve
                  doluluk
                </p>
              </div>

              <TrendingUp
                size={20}
                color="#176b5b"
              />
            </div>

            <div className="card-pad">
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns:
                    "repeat(4, 1fr)",
                  gap: 16,
                  marginBottom: 16,
                }}
              >
                <div
                  style={{
                    padding: 16,
                    borderRadius: 11,
                    background:
                      "#f8faf8",
                  }}
                >
                  <div
                    style={{
                      fontSize: 12,
                      color:
                        "#6e7b7d",
                      marginBottom: 4,
                    }}
                  >
                    Toplam Sınıf
                  </div>

                  <div
                    style={{
                      fontSize: 24,
                      fontWeight: 800,
                      color:
                        "#1b2b2e",
                    }}
                  >
                    {
                      aiAnalysis.total_classes
                    }
                  </div>
                </div>

                <div
                  style={{
                    padding: 16,
                    borderRadius: 11,
                    background:
                      "#f8faf8",
                  }}
                >
                  <div
                    style={{
                      fontSize: 12,
                      color:
                        "#6e7b7d",
                      marginBottom: 4,
                    }}
                  >
                    Toplam Öğrenci
                  </div>

                  <div
                    style={{
                      fontSize: 24,
                      fontWeight: 800,
                      color:
                        "#1b2b2e",
                    }}
                  >
                    {
                      aiAnalysis.total_students
                    }
                  </div>
                </div>

                <div
                  style={{
                    padding: 16,
                    borderRadius: 11,
                    background:
                      aiAnalysis.occupancy_rate >=
                      70
                        ? "#dcfce7"
                        : aiAnalysis.occupancy_rate >=
                          50
                        ? "#fef9c3"
                        : "#fee2e2",
                  }}
                >
                  <div
                    style={{
                      fontSize: 12,
                      color:
                        "#6e7b7d",
                      marginBottom: 4,
                    }}
                  >
                    Doluluk Oranı
                  </div>

                  <div
                    style={{
                      fontSize: 24,
                      fontWeight: 800,
                      color:
                        "#1b2b2e",
                    }}
                  >
                    {
                      aiAnalysis.occupancy_rate
                    }
                    %
                  </div>
                </div>

                <div
                  style={{
                    padding: 16,
                    borderRadius: 11,
                    background:
                      "#f8faf8",
                  }}
                >
                  <div
                    style={{
                      fontSize: 12,
                      color:
                        "#6e7b7d",
                      marginBottom: 4,
                    }}
                  >
                    Ortalama Sınıf Boyutu
                  </div>

                  <div
                    style={{
                      fontSize: 24,
                      fontWeight: 800,
                      color:
                        "#1b2b2e",
                    }}
                  >
                    {
                      aiAnalysis.avg_class_size
                    }
                  </div>
                </div>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns:
                    "repeat(2, 1fr)",
                  gap: 16,
                  marginBottom: 16,
                }}
              >
                <div
                  style={{
                    padding: 16,
                    borderRadius: 11,
                    background:
                      aiAnalysis.overall_attendance_rate >=
                      85
                        ? "#dcfce7"
                        : aiAnalysis.overall_attendance_rate >=
                          70
                        ? "#fef9c3"
                        : "#fee2e2",
                  }}
                >
                  <div
                    style={{
                      fontSize: 12,
                      color:
                        "#6e7b7d",
                      marginBottom: 4,
                    }}
                  >
                    Genel Devamsızlık
                  </div>

                  <div
                    style={{
                      fontSize: 24,
                      fontWeight: 800,
                      color:
                        "#1b2b2e",
                    }}
                  >
                    {
                      aiAnalysis.overall_attendance_rate
                    }
                    %
                  </div>
                </div>

                <div
                  style={{
                    padding: 16,
                    borderRadius: 11,
                    background:
                      aiAnalysis.overall_avg_grade >=
                      80
                        ? "#dcfce7"
                        : aiAnalysis.overall_avg_grade >=
                          70
                        ? "#fef9c3"
                        : "#fee2e2",
                  }}
                >
                  <div
                    style={{
                      fontSize: 12,
                      color:
                        "#6e7b7d",
                      marginBottom: 4,
                    }}
                  >
                    Ortalama Not
                  </div>

                  <div
                    style={{
                      fontSize: 24,
                      fontWeight: 800,
                      color:
                        "#1b2b2e",
                    }}
                  >
                    {
                      aiAnalysis.overall_avg_grade
                    }
                  </div>
                </div>
              </div>

              {aiAnalysis.recommendations &&
                aiAnalysis
                  .recommendations
                  .length > 0 && (
                  <div
                    style={{
                      padding: 16,
                      borderRadius: 11,
                      background:
                        "#f0f9ff",
                      borderLeft:
                        "4px solid #0ea5e9",
                    }}
                  >
                    <div
                      style={{
                        fontSize: 14,
                        fontWeight: 700,
                        color:
                          "#0c4a6e",
                        marginBottom: 12,
                      }}
                    >
                      Öneriler
                    </div>

                    <ul
                      style={{
                        margin: 0,
                        paddingLeft: 20,
                        color:
                          "#334155",
                      }}
                    >
                      {aiAnalysis.recommendations.map(
                        (
                          rec: string,
                          idx: number
                        ) => (
                          <li
                            key={idx}
                            style={{
                              marginBottom: 6,
                            }}
                          >
                            {rec}
                          </li>
                        )
                      )}
                    </ul>
                  </div>
                )}
            </div>
          </div>
        )}

      {/* =====================================================
          ANA TABLO
      ====================================================== */}
      {loading ? (
        <div className="card">
          <LoadingState />
        </div>
      ) : error ? (
        <div className="card">
          <ErrorState
            message={error}
            retry={load}
          />
        </div>
      ) : (
        <>
          <div className="toolbar">
            <div className="search">
              <Search size={16} />

              <input
                type="text"
                placeholder="Ara..."
                value={search}
                onChange={(e) =>
                  setSearch(
                    e.target.value
                  )
                }
              />
            </div>
          </div>

          <DataTable
            columns={tableColumns}
            rows={rows}
            search={search}
            onSearch={(value) => {
              setSearch(value);
              setPage(1);
            }}
            page={page}
            totalPages={
              totalPages
            }
            total={total}
            onPage={setPage}
            detailBase={
              basePath
            }
            editBase={
              basePath
            }
            canEdit={write}
            onDelete={resourceKey === "organizations" ? undefined : (row) => setDeleting(row)}
          />

          {totalPages > 1 && (
            <div
              style={{
                display: "flex",
                justifyContent:
                  "center",
                gap: 8,
                marginTop: 16,
              }}
            >
              <button
                className="btn btn-secondary"
                disabled={
                  page === 1
                }
                onClick={() =>
                  setPage(
                    page - 1
                  )
                }
              >
                Önceki
              </button>

              <span
                style={{
                  padding: 8,
                }}
              >
                Sayfa {page} /{" "}
                {totalPages}
              </span>

              <button
                className="btn btn-secondary"
                disabled={
                  page ===
                  totalPages
                }
                onClick={() =>
                  setPage(
                    page + 1
                  )
                }
              >
                Sonraki
              </button>
            </div>
          )}
        </>
      )}

      {/* =====================================================
          DELETE
      ====================================================== */}
      {deleting && resourceKey !== "organizations" && (
        <ConfirmDialog
          open={true}
          title={`${config.singular} kaldırılsın mı?`}
          description="Bu işlem geri alınamaz."
          onConfirm={
            confirmDelete
          }
          onCancel={() =>
            setDeleting(null)
          }
        />
      )}

      {/* =====================================================
          EXCEL IMPORT
      ====================================================== */}
      {resourceKey !== "organizations" && importConfig &&
        importOpen && (
          <ExcelImport
            open={true}
            endpoint={
              importConfig.endpoint
            }
            title={
              importConfig.title
            }
            description={
              importConfig.description
            }
            templateColumns={
              importConfig.templateColumns
            }
            onClose={() =>
              setImportOpen(false)
            }
            onSuccess={load}
          />
        )}
    </>
  );
}

// ===========================================================
// FORM
// ===========================================================

type FormValues = Record<
  string,
  string | number | boolean
>;

function getDefaults(
  fields: FieldConfig[],
  organizationId?: string | null
) {
  return fields.reduce<FormValues>(
    (acc, field) => {
      if (
        field.name ===
          "organization_id"
      ) {
        acc[field.name] =
          field.defaultValue ??
          (organizationId ||
            "");
      } else {
        acc[field.name] =
          field.defaultValue ??
          (field.type ===
          "checkbox"
            ? false
            : "");
      }

      return acc;
    },
    {}
  );
}

export function ResourceFormPage({
  resourceKey,
}: {
  resourceKey: string;
}) {
  const config =
    resources[resourceKey];

  const { id } =
    useParams();

  const editing =
    Boolean(id);

  const navigate =
    useNavigate();

  const {
    showToast,
  } = useToast();

  const user = useWorkspaceUser();
  const can = useAuthStore((state) => state.can);

  const basePath = config.listPath || config.detailPath || `/${resourceKey}`;

  const [loading, setLoading] =
    useState(editing);
  const [optionsLoading, setOptionsLoading] = useState(true);

  const [
    serverError,
    setServerError,
  ] = useState("");

  const [options, setOptions] =
    useState<
      Record<
        string,
        SelectOption[]
      >
    >({});

  const defaults =
    useMemo(
      () =>
        getDefaults(
          config.fields,
          user?.organization_id
        ),
      [
        config.fields,
        user?.organization_id,
      ]
    );

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    control,
    formState: {
      errors,
      isSubmitting,
    },
  } =
    useForm<FormValues>({
      defaultValues:
        defaults,
    });

  const selectedOrganization = useWatch({ control, name: "organization_id" });
  const selectedBranch = useWatch({ control, name: "branch_id" });
  const previousStudentScope = useRef<{ organization: unknown; branch: unknown } | null>(null);
  useEffect(() => {
    if (resourceKey !== "students" || loading) return;
    const previous = previousStudentScope.current;
    if (previous && previous.organization !== selectedOrganization) {
      setValue("branch_id", "");
      setValue("class_id", "");
    } else if (previous && previous.branch !== selectedBranch) {
      setValue("class_id", "");
    }
    previousStudentScope.current = { organization: selectedOrganization, branch: selectedBranch };
  }, [resourceKey, loading, selectedOrganization, selectedBranch, setValue]);

  // =========================================================
  // OPTIONS
  // =========================================================
  useEffect(() => {
    const controller = new AbortController();
    setOptionsLoading(true);
    const sources = [
      ...new Set(
        config.fields.filter((field) => !field.searchable && !(id && field.hideOnEdit))
          .map(
            (field) =>
              field.optionSource
          )
          .filter(Boolean)
      ),
    ] as string[];

    Promise.all(
      sources.map(
        async (source) => {
          try {
            const response =
              await api.get<
                ApiResponse<
                  | DataRecord[]
                  | Paginated<DataRecord>
                >
              >(
                source,
                {
                  params: {
                    page_size: 100,
                    limit: 100,
                  },
                  signal: controller.signal,
                }
              );

            return [
              source,
              normalize(
                response.data.data
              ).items,
            ] as const;
          } catch (reason) {
            if (!controller.signal.aborted) setServerError(apiMessage(reason));
            return [
              source,
              [],
            ] as const;
          }
        }
      )
    ).then(
      (entries) => {
        if (controller.signal.aborted) return;
        const mapped: Record<
          string,
          SelectOption[]
        > = {};

        for (const [
          source,
          items,
        ] of entries) {
          mapped[source] =
            items.map(
              (item) => ({
                value:
                  item.id
                    ? String(
                        item.id
                      )
                    : "",
                label: [
                  item.name,
                  item.first_name,
                  item.last_name,
                ]
                  .filter(
                    Boolean
                  )
                  .join(" "),
              })
            );
        }

        setOptions(
          mapped
        );
      }
    ).finally(() => { if (!controller.signal.aborted) setOptionsLoading(false); });
    return () => controller.abort();
  }, [
    config.fields,
    id,
  ]);

  // =========================================================
  // LOAD EDIT RECORD
  // =========================================================
  useEffect(() => {
    const controller = new AbortController();
    setServerError("");
    previousStudentScope.current = null;
    if (!id) { reset(defaults); setLoading(false); return; }
    setLoading(true);

    api
      .get<
        ApiResponse<DataRecord>
      >(
        `${config.endpoint}/${id}${resourceKey === "students" ? "/form" : ""}`, { signal: controller.signal }
      )
      .then((response) => {
        if (controller.signal.aborted) return;
        const record =
          response.data.data;

        const values = {
          ...defaults,
        };

        for (const field of config.fields) {
          const value =
            record?.[
              field.name
            ];

          if (
            value !==
              undefined &&
            value !== null
          ) {
            values[
              field.name
            ] =
              field.type ===
              "date"
                ? String(
                    value
                  ).slice(
                    0,
                    10
                  )
                : (value as
                    | string
                    | number
                    | boolean);
          }
        }

        reset(values);
      })
      .catch((error) => {
        if (controller.signal.aborted) return;
        setServerError(
          apiMessage(error)
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(
          false
        );
      });
    return () => controller.abort();
  }, [
    config.endpoint,
    config.fields,
    defaults,
    id,
    reset,
    resourceKey,
  ]);

  // =========================================================
  // SUBMIT
  // =========================================================
  const submit =
    async (
      values: FormValues
    ) => {
      setServerError("");

      const payload: Record<string, unknown> =
        Object.fromEntries(
          Object.entries(
            values
          ).filter(
            ([
              key,
              value,
            ]) => {
              if (
                (
                  key ===
                    "organization_id" ||
                  key ===
                    "branch_id" ||
                  key ===
                    "class_id"
                ) &&
                (!value ||
                  value === "")
              ) {
                return false;
              }

              return (
                value !== ""
              );
            }
          )
        );

      if (editing && resourceKey === "parents") {
        for (const name of ["phone", "sms_phone", "whatsapp_phone", "email", "address"]) {
          if (values[name] === "") payload[name] = null;
        }
      }
      if (editing && ["organizations", "branches"].includes(resourceKey)) {
        for (const name of ["legal_name", "tax_number", "tax_office", "code", "phone", "email", "city", "address"]) {
          if (values[name] === "") payload[name] = null;
        }
      }
      if (editing && resourceKey === "students") {
        for (const name of ["address", "notes", "class_id", "gender", "date_of_birth"]) {
          if (values[name] === "") payload[name] = null;
        }
      }
      if (editing && resourceKey === "classes" && values.teacher_id === "") payload.teacher_id = null;

      for (const field of config.fields) {
        if (editing && field.hideOnEdit) { delete payload[field.name]; continue; }
        if (
          field.type ===
            "number" &&
          payload[
            field.name
          ] !== undefined
        ) {
          payload[
            field.name
          ] = Number(
            payload[
              field.name
            ]
          );
        }
      }

      try {
        const response = editing
          ? await api.put<ApiResponse<DataRecord>>(`${config.endpoint}/${id}`, payload)
          : await api.post<ApiResponse<DataRecord>>(config.endpoint, payload);

        showToast(
          `${config.singular} ${
            editing
              ? "güncellendi"
              : "oluşturuldu"
          }`,
          "Değişiklikler başarıyla kaydedildi."
        );

        const savedId = response.data?.data?.id || id;
        navigate(resourceKey === "students" && !can("students.read") && savedId
          ? `/students/${savedId}/edit` : basePath);
      } catch (error) {
        setServerError(
          apiMessage(error)
        );
      }
    };

  if (!editing && resourceKey === "organizations") {
    return <div className="card card-pad"><p>Yeni kurum hesaplarını ana yönetici SaaS yönetiminden açar.</p><Link className="btn btn-secondary" to={basePath}>Kurum bilgilerine dön</Link></div>;
  }

  if (loading || optionsLoading) {
    return (
      <div className="card">
        <LoadingState label="Kayıt açılıyor" />
      </div>
    );
  }

  return (
    <>
      <PageHeader
        eyebrow={
          editing
            ? "Kayıt düzenleme"
            : "Yeni kayıt"
        }
        title={`${config.singular} ${
          editing
            ? "düzenle"
            : "ekle"
        }`}
        description={`Zorunlu alanları doldurarak ${config.singular.toLocaleLowerCase(
          "tr-TR"
        )} kaydını tamamlayın.`}
      >
        <Link
          className="btn btn-secondary"
          to={basePath}
        >
          <ArrowLeft
            size={16}
          />
          Listeye dön
        </Link>
      </PageHeader>

      <form
        className="card form-card"
        onSubmit={handleSubmit(
          submit
        )}
        noValidate
      >
        <div className="form-section">
          <h2>
            Temel bilgiler
          </h2>

          <p>
            Bu bilgiler kurum
            içindeki ilgili
            ekranlarda
            kullanılır.
          </p>

          <div className="form-grid">
            {config.fields
              .filter(
                (field) =>
                  !(
                    editing &&
                    field.hideOnEdit
                  )
              )
              .map(
                (field) => field.searchable ? (
                  <ResourceChoice key={field.name} field={field} control={control}
                    organizationId={selectedOrganization ? String(selectedOrganization) : undefined}
                    branchId={selectedBranch ? String(selectedBranch) : undefined}
                    studentId={resourceKey === "students" ? id : undefined} />
                ) : (
                  <DynamicField
                    key={
                      field.name
                    }
                    field={
                      field
                    }
                    options={
                      field.options ||
                      (field.optionSource
                        ? options[
                            field
                              .optionSource
                          ]
                        : []) ||
                      []
                    }
                    register={
                      register
                    }
                    error={
                      errors[
                        field.name
                      ]?.message as
                        | string
                        | undefined
                    }
                    editing={
                      editing
                    }
                  />
                )
              )}
          </div>
        </div>

        {serverError && (
          <div
            className="field-error"
            role="alert"
            style={{
              marginTop: 18,
              padding: 12,
              borderRadius: 10,
              background:
                "#fff0ef",
            }}
          >
            {
              serverError
            }
          </div>
        )}

        <div className="form-actions">
          <Link
            className="btn btn-secondary"
            to={basePath}
          >
            Vazgeç
          </Link>

          <button
            className="btn btn-primary"
            disabled={
              isSubmitting
            }
          >
            <Save size={16} />

            {isSubmitting
              ? "Kaydediliyor…"
              : "Kaydet"}
          </button>
        </div>
      </form>
    </>
  );
}

// ===========================================================
// DYNAMIC FIELD
// ===========================================================

function DynamicField({
  field,
  options,
  register,
  error,
  editing,
}: {
  field: FieldConfig;
  options: SelectOption[];
  register: ReturnType<
    typeof useForm<FormValues>
  >["register"];
  error?: string;
  editing: boolean;
}) {
  const rules = {
    required:
      field.required &&
      !(
        editing &&
        field.hideOnEdit
      )
        ? `${field.label} zorunludur.`
        : false,

    min: field.min !== undefined
      ? {
          value:
            field.min,
          message: `En az ${field.min} olmalıdır.`,
        }
      : undefined,
  };

  if (
    field.type ===
    "checkbox"
  ) {
    return (
      <Field
        label={
          field.label
        }
        error={error}
        full={
          field.full
        }
      >
          <input
            type="checkbox"
            aria-label={field.label}
            {...register(
              field.name,
              rules
            )}
          />
      </Field>
    );
  }

  if (
    field.type ===
    "textarea"
  ) {
    return (
      <Field
        label={
          field.label
        }
        error={error}
        required={
          field.required
        }
        full={
          field.full
        }
      >
        <textarea
          placeholder={
            field.placeholder
          }
          {...register(
            field.name,
            rules
          )}
        />
      </Field>
    );
  }

  if (
    field.type ===
    "select"
  ) {
    return (
      <Field
        label={
          field.label
        }
        error={error}
        required={
          field.required
        }
        full={
          field.full
        }
      >
        <select
          {...register(
            field.name,
            rules
          )}
        >
          <option value="">
            Seçiniz
          </option>

          {options.map(
            (option) => (
              <option
                key={
                  option.value
                }
                value={
                  option.value
                }
              >
                {
                  option.label
                }
              </option>
            )
          )}
        </select>
      </Field>
    );
  }

  return (
    <Field
      label={
        field.label
      }
      error={error}
      required={
        field.required
      }
      full={
        field.full
      }
    >
      <input
        type={
          field.type ||
          "text"
        }
        placeholder={
          field.placeholder
        }
        step={
          field.type ===
          "number"
            ? (field.step ?? "0.01")
            : undefined
        }
        {...register(
          field.name,
          rules
        )}
      />
    </Field>
  );
}
