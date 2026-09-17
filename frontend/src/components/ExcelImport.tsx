import { Upload, FileSpreadsheet, X } from "lucide-react";
import { useState } from "react";
import { Modal } from "./ui";
import { useToast } from "./Toast";
import { api, apiMessage } from "../lib/api";

interface ExcelImportProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  endpoint: string;
  title: string;
  description: string;
  templateColumns: { key: string; label: string; required?: boolean }[];
}

export function ExcelImport({ open, onClose, onSuccess, endpoint, title, description, templateColumns }: ExcelImportProps) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const { showToast } = useToast();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      const validTypes = [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel"
      ];
      if (!validTypes.includes(selectedFile.type) && !selectedFile.name.endsWith(".xlsx") && !selectedFile.name.endsWith(".xls")) {
        showToast("Geçersiz dosya", "Lütfen Excel dosyası (.xlsx veya .xls) yükleyin.", "error");
        return;
      }
      setFile(selectedFile);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);

      await api.post(endpoint, formData, {
        headers: {
          "Content-Type": "multipart/form-data"
        }
      });

      showToast("İçe aktarma başarılı", "Veriler başarıyla içe aktarıldı.");
      onClose();
      onSuccess();
    } catch (e) {
      showToast("İçe aktarma başarısız", apiMessage(e), "error");
    } finally {
      setUploading(false);
    }
  };

  const downloadTemplate = () => {
    const headers = templateColumns.map(col => col.label).join(",");
    const content = headers;
    const blob = new Blob([content], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `${title.replace(/\s+/g, "_").toLowerCase()}_template.csv`;
    link.click();
  };

  return (
    <Modal
      open={open}
      title={title}
      description={description}
      onClose={onClose}
      actions={
        <>
          <button className="btn btn-secondary" onClick={onClose} disabled={uploading}>
            Vazgeç
          </button>
          <button
            className="btn btn-secondary"
            onClick={downloadTemplate}
            disabled={uploading}
          >
            <FileSpreadsheet size={16} />Şablon İndir
          </button>
          <button
            className="btn btn-primary"
            onClick={handleUpload}
            disabled={!file || uploading}
          >
            <Upload size={16} />
            {uploading ? "Yükleniyor..." : "İçe Aktar"}
          </button>
        </>
      }
    >
      <div style={{ padding: "20px 0" }}>
        {!file ? (
          <div
            style={{
              border: "2px dashed var(--line)",
              borderRadius: 12,
              padding: "40px",
              textAlign: "center",
              cursor: "pointer",
              transition: "all 0.2s"
            }}
            onClick={() => document.getElementById("excel-upload")?.click()}
            onMouseEnter={(e) => e.currentTarget.style.borderColor = "var(--brand)"}
            onMouseLeave={(e) => e.currentTarget.style.borderColor = "var(--line)"}
          >
            <Upload size={32} style={{ color: "var(--muted)", marginBottom: 12 }} />
            <p style={{ color: "var(--muted)", marginBottom: 8 }}>
              Excel dosyasını buraya sürükleyin veya tıklayın
            </p>
            <small style={{ color: "var(--muted)" }}>
              .xlsx veya .xls formatında dosya yükleyin
            </small>
            <input
              id="excel-upload"
              type="file"
              accept=".xlsx,.xls"
              onChange={handleFileChange}
              style={{ display: "none" }}
            />
          </div>
        ) : (
          <div
            style={{
              border: "1px solid var(--line)",
              borderRadius: 12,
              padding: "16px",
              display: "flex",
              alignItems: "center",
              gap: 12
            }}
          >
            <div
              style={{
                display: "grid",
                placeItems: "center",
                width: 40,
                height: 40,
                borderRadius: 8,
                background: "#e9f3ef",
                color: "var(--brand)"
              }}
            >
              <FileSpreadsheet size={20} />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <strong style={{ display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {file.name}
              </strong>
              <small style={{ color: "var(--muted)" }}>
                {(file.size / 1024).toFixed(1)} KB
              </small>
            </div>
            <button
              className="btn btn-ghost btn-icon"
              onClick={() => setFile(null)}
              disabled={uploading}
            >
              <X size={16} />
            </button>
          </div>
        )}

        <div style={{ marginTop: 20 }}>
          <h4 style={{ fontSize: 13, fontWeight: 700, marginBottom: 12 }}>Gerekli Sütunlar:</h4>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {templateColumns.map((col) => (
              <span
                key={col.key}
                style={{
                  padding: "4px 10px",
                  background: col.required ? "#fee2e2" : "#f3f4f6",
                  borderRadius: 6,
                  fontSize: 12,
                  color: col.required ? "#dc2626" : "var(--muted)"
                }}
              >
                {col.label}
                {col.required && " *"}
              </span>
            ))}
          </div>
        </div>
      </div>
    </Modal>
  );
}
