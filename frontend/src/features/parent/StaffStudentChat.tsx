import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { api, apiMessage, unwrap } from "../../lib/api";
import { hasPermission, useAuthStore } from "../../stores/auth";
import { usePlatformWorkspace } from "../../stores/platformWorkspace";
import type { ApiResponse, Paginated } from "../../types/api";
import { ChatInterface } from "./ChatInterface";
import "./StaffStudentChat.css";

interface Contact {
  student_id: string;
  student_name: string;
  parent_id: string;
  parent_name: string;
  branch_id: string;
  class_name: string | null;
}

interface Branch { id: string; name: string }

interface ContactResult {
  key: string;
  data?: Paginated<Contact>;
  error?: string;
}

type Area = "/teacher" | "/admin";

export function StaffStudentChat({ area }: { area: Area }) {
  const user = useAuthStore((state) => state.user);
  const session = useAuthStore((state) => state.sessionVersion);
  const workspace = usePlatformWorkspace((state) => state.workspace);
  const institution = user?.is_super_admin ? (workspace?.operatorId === user.id ? workspace.id : null) : user?.organization_id;
  if (user?.is_super_admin && !institution) return <p>Sohbetleri açmak için bir kurum seçin.</p>;
  if (!hasPermission(user, "messaging.read") || !hasPermission(user, "students.read")) {
    return <p>Öğrenci sohbetlerini görüntüleme yetkiniz yok.</p>;
  }
  return <ChatDirectory key={JSON.stringify([session, user?.id, institution, area])} area={area}
    canSend={hasPermission(user, "messaging.send")} />;
}

function ChatDirectory({ area, canSend }: { area: Area; canSend: boolean }) {
  const [branch, setBranch] = useState("");
  const [branches, setBranches] = useState<Branch[]>([]);
  const [branchError, setBranchError] = useState("");
  const [input, setInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [result, setResult] = useState<ContactResult | null>(null);
  const [selected, setSelected] = useState<Contact | null>(null);
  const [attempt, setAttempt] = useState(0);
  const queryKey = JSON.stringify([branch, search, page, attempt]);
  const current = result?.key === queryKey ? result : null;

  useEffect(() => {
    const controller = new AbortController();
    api.get<ApiResponse<Branch[]>>(`${area}/chat-branches`, { signal: controller.signal })
      .then((response) => { if (!controller.signal.aborted) setBranches(unwrap(response)); })
      .catch((error) => { if (!controller.signal.aborted) setBranchError(apiMessage(error)); });
    return () => controller.abort();
  }, [area]);

  useEffect(() => {
    const controller = new AbortController();
    api.get<ApiResponse<Paginated<Contact>>>(`${area}/chat-contacts`, {
      params: { branch_id: branch || undefined, search, page },
      signal: controller.signal,
    }).then((response) => {
      if (controller.signal.aborted) return;
      const data = unwrap(response);
      if (data.page !== page || data.items.some((row) =>
        !row.student_id || !row.parent_id || !row.branch_id || (branch && row.branch_id !== branch))) {
        throw new Error("Öğrenci listesi seçili şubeyle eşleşmiyor.");
      }
      setResult({ key: queryKey, data });
    }).catch((error) => {
      if (!controller.signal.aborted) setResult({ key: queryKey, error: apiMessage(error) });
    });
    return () => controller.abort();
  }, [area, branch, search, page, queryKey]);

  function submitSearch(event: FormEvent) {
    event.preventDefault();
    setSelected(null);
    setPage(1);
    setSearch(input.trim());
  }

  return (
    <section className="staff-student-chat">
      <form className="staff-chat-filters" onSubmit={submitSearch}>
        <label>
          Şube
          <select className="filter-select" value={branch} onChange={(event) => {
            setSelected(null);
            setBranch(event.target.value);
            setPage(1);
          }}>
            <option value="">Tüm yetkili şubeler</option>
            {branches.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}
          </select>
        </label>
        <label>
          Öğrenci, veli veya sınıf ara
          <input type="search" value={input} maxLength={120} onChange={(event) => setInput(event.target.value)} />
        </label>
        <button className="btn btn-secondary" type="submit">Ara</button>
      </form>
      {branchError && <p role="alert">Şubeler yüklenemedi. {branchError}</p>}
      {selected ? (
        <ChatInterface apiBase={area} studentId={selected.student_id} parentId={selected.parent_id}
          branchId={selected.branch_id} subjectName={selected.student_name} teacherName={selected.parent_name}
          canSend={canSend} onBack={() => setSelected(null)} />
      ) : (
        <>
          {!current && <p role="status">Öğrenci ve veli listesi yükleniyor…</p>}
          {current?.error && <div role="alert">
            <p>{current.error}</p>
            <button type="button" className="btn btn-secondary" onClick={() => setAttempt((n) => n + 1)}>Yeniden dene</button>
          </div>}
          {current?.data?.items.length === 0 && <p>Eşleşen öğrenci ve bağlı veli hesabı bulunamadı.</p>}
          {!!current?.data?.items.length && (
            <ul className="staff-chat-contacts">
              {current.data.items.map((row) => <li key={`${row.student_id}/${row.parent_id}`}>
                <button type="button" onClick={() => setSelected(row)}>
                  <strong>{row.student_name}</strong>
                  <span>{row.parent_name}</span>
                  {row.class_name && <small>{row.class_name}</small>}
                </button>
              </li>)}
            </ul>
          )}
          {current?.data && current.data.total_pages > 1 && (
            <nav className="staff-chat-pages" aria-label="Öğrenci ve veli sayfaları">
              <button type="button" className="btn btn-secondary" disabled={page <= 1} onClick={() => setPage((n) => n - 1)}>Önceki</button>
              <span>{page} / {current.data.total_pages}</span>
              <button type="button" className="btn btn-secondary" disabled={page >= current.data.total_pages}
                onClick={() => setPage((n) => n + 1)}>Sonraki</button>
            </nav>
          )}
        </>
      )}
    </section>
  );
}
