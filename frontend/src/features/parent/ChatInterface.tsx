import { ArrowLeft, Paperclip, Send } from "lucide-react";
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";
import { api, apiMessage, unwrap } from "../../lib/api";
import { downloadFile } from "../../lib/download";
import { fileSha256 } from "../../lib/fileIntegrity";
import { newRequestId } from "../../lib/requestId";
import { useAuthStore } from "../../stores/auth";
import { usePlatformWorkspace } from "../../stores/platformWorkspace";
import type { ApiResponse } from "../../types/api";
import "./ChatInterface.css";

interface ChatMessage {
  id: string;
  content: string;
  is_read: boolean;
  sent_at: string;
  is_current_user: boolean;
  attachment_name?: string | null;
  attachment_sha256?: string | null;
}

interface ChatInterfaceProps {
  studentId: string;
  teacherId?: string;
  parentId?: string;
  branchId?: string;
  subjectName?: string;
  canSend?: boolean;
  teacherName: string;
  onBack: () => void;
  apiBase?: string;
}

interface PendingMessage {
  id: string;
  content: string;
  file: File | null;
  sha256?: string;
}

const PAGE_SIZE = 50;

interface HistoryWindow {
  rows: ChatMessage[];
  hasOlder: boolean;
}

export function ChatInterface({ studentId, teacherId, parentId, branchId, canSend = true, apiBase = "/parent", ...props }: ChatInterfaceProps) {
  const session = useAuthStore((state) => state.sessionVersion);
  const workspace = usePlatformWorkspace((state) => state.workspace?.id);
  const endpoint = teacherId ? `${apiBase}/child/${studentId}/chat/${teacherId}` : `${apiBase}/chat/${studentId}`;
  return <StudentChat key={JSON.stringify([session, workspace, endpoint, parentId, branchId, canSend])}
    endpoint={endpoint} parentId={parentId} branchId={branchId} canSend={canSend} {...props} />;
}

function StudentChat({ endpoint, parentId, branchId, subjectName, teacherName, canSend, onBack }: {
  endpoint: string;
  parentId?: string;
  branchId?: string;
  subjectName?: string;
  teacherName: string;
  canSend: boolean;
  onBack: () => void;
}) {
  const [historyWindow, setHistoryWindow] = useState<HistoryWindow>({ rows: [], hasOlder: false });
  const messages = historyWindow.rows;
  const [message, setMessage] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [historyError, setHistoryError] = useState("");
  const [actionError, setActionError] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState<PendingMessage | null>(null);
  const [missingReceipt, setMissingReceipt] = useState(false);
  const session = useRef<AbortController | null>(null);
  const historyRequest = useRef<Promise<void> | null>(null);
  const olderPending = useRef(false);
  const sending = useRef(false);
  const history = useRef<HTMLDivElement>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const followMessages = useRef(true);
  const scrollAnchor = useRef<{ height: number; top: number } | null>(null);
  const lastId = messages.at(-1)?.id;
  const params = useMemo(() => (parentId || branchId ? {
    ...(parentId ? { parent_id: parentId } : {}),
    ...(branchId ? { branch_id: branchId } : {}),
  } : undefined),
    [parentId, branchId]);

  const refresh = useCallback(async (signal: AbortSignal, before?: string) => {
    try {
      const rows = unwrap(await api.get<ApiResponse<ChatMessage[]>>(endpoint, {
        params: { ...params, limit: PAGE_SIZE, ...(before ? { before_id: before } : {}) }, signal,
      }));
      if (signal.aborted) return;
      if (before && rows.length && history.current) {
        scrollAnchor.current = { height: history.current.scrollHeight, top: history.current.scrollTop };
        followMessages.current = false;
      }
      setHistoryWindow((current) => {
        const hasOlder = rows.length === PAGE_SIZE;
        if (before) {
          if (current.rows[0]?.id !== before) return current;
          const ids = new Set(current.rows.map((row) => row.id));
          return { rows: [...rows.filter((row) => !ids.has(row.id)), ...current.rows], hasOlder };
        }
        // Keep loaded older pages only when the newest response overlaps the window.
        const first = current.rows.findIndex((row) => row.id === rows[0]?.id);
        return first > 0 ? { rows: [...current.rows.slice(0, first), ...rows], hasOlder: current.hasOlder }
          : { rows, hasOlder: first === 0 ? current.hasOlder || hasOlder : hasOlder };
      });
      setHistoryError("");
    } catch (error) {
      if (!signal.aborted) setHistoryError(apiMessage(error));
    } finally {
      if (!signal.aborted) setLoading(false);
    }
  }, [endpoint, params]);

  const trackHistory = useCallback((signal: AbortSignal, before?: string) => {
    const request = refresh(signal, before);
    historyRequest.current = request;
    return request.finally(() => {
      if (historyRequest.current === request) historyRequest.current = null;
    });
  }, [refresh]);

  useEffect(() => {
    const controller = new AbortController();
    session.current = controller;
    const poll = () => {
      if (historyRequest.current || sending.current || olderPending.current) return;
      void trackHistory(controller.signal);
    };
    poll();
    const timer = window.setInterval(poll, 5000);
    return () => {
      controller.abort();
      historyRequest.current = null;
      window.clearInterval(timer);
    };
  }, [trackHistory]);

  async function loadOlder() {
    const signal = session.current?.signal;
    if (!signal || signal.aborted || sending.current || olderPending.current) return;
    olderPending.current = true;
    setLoadingOlder(true);
    try {
      await historyRequest.current;
      const first = history.current?.querySelector<HTMLElement>("article[data-message-id]")?.dataset.messageId;
      if (!signal.aborted && first && !sending.current) await trackHistory(signal, first);
    } finally {
      olderPending.current = false;
      if (!signal.aborted) setLoadingOlder(false);
    }
  }

  useLayoutEffect(() => {
    if (scrollAnchor.current && history.current) {
      const { height, top } = scrollAnchor.current;
      history.current.scrollTop = top + history.current.scrollHeight - height;
      scrollAnchor.current = null;
    }
  }, [messages]);

  useEffect(() => {
    if (history.current && followMessages.current) history.current.scrollTop = history.current.scrollHeight;
  }, [lastId]);

  async function verify(draft: PendingMessage, signal: AbortSignal) {
    const receipt = unwrap(await api.get<ApiResponse<ChatMessage>>(`${endpoint}/sent/${draft.id}`, { params, signal }));
    const name = draft.file?.name.replace(/\\/g, "/").split("/").at(-1)?.trim() ?? null;
    if (receipt.id !== draft.id || !receipt.is_current_user || receipt.content !== draft.content ||
        (receipt.attachment_name ?? null) !== name || (receipt.attachment_sha256 ?? null) !== (draft.sha256 ?? null)) {
      throw new Error("Sunucudaki mesaj bilgileri gönderimle eşleşmiyor.");
    }
    return receipt;
  }

  async function submit(draft: PendingMessage, send: boolean) {
    const signal = session.current?.signal;
    if (!canSend || !signal || signal.aborted || sending.current) return;
    sending.current = true;
    setBusy(true);
    setMissingReceipt(false);
    setActionError("");
    let preparing = true;
    let posting = send;
    try {
      const prepared = draft.file && !draft.sha256
        ? { ...draft, sha256: await fileSha256(draft.file, signal) }
        : draft;
      if (signal.aborted) return;
      preparing = false;
      setPending(prepared);
      if (send) {
        if (prepared.file) {
          const form = new FormData();
          form.set("file", prepared.file);
          form.set("message", prepared.content);
          form.set("request_id", prepared.id);
          await api.post(`${endpoint}/send-file`, form, { params, signal });
        } else {
          await api.post(endpoint, { message: prepared.content, request_id: prepared.id }, { params, signal });
        }
      }
      posting = false;
      const receipt = await verify(prepared, signal);
      await historyRequest.current;
      if (signal.aborted) return;
      followMessages.current = true;
      setHistoryWindow((current) => current.rows.some((row) => row.id === receipt.id) ? current
        : { ...current, rows: [...current.rows, receipt] });
      setPending(null);
      setMessage("");
      setFile(null);
      if (fileInput.current) fileInput.current.value = "";
    } catch (error) {
      if (!signal.aborted) {
        const status = (error as { response?: { status?: number } } | null)?.response?.status;
        if (preparing || (posting && (status === 413 || status === 422))) setPending(null);
        else if (!posting && status === 404) setMissingReceipt(true);
        setActionError(apiMessage(error));
      }
    } finally {
      sending.current = false;
      if (!signal.aborted) setBusy(false);
    }
  }

  function sendMessage(event: FormEvent) {
    event.preventDefault();
    if (!pending && (message.trim() || file)) {
      void submit({ id: newRequestId(), content: message.trim(), file }, true);
    }
  }

  async function download(row: ChatMessage) {
    if (!row.attachment_name || !row.attachment_sha256) return;
    const signal = session.current?.signal;
    setActionError("");
    try {
      await downloadFile(`${endpoint}/attachments/${encodeURIComponent(row.id)}`, row.attachment_name, {
        params, signal, expectedSha256: row.attachment_sha256,
      });
    } catch (error) {
      if (!signal?.aborted) setActionError(apiMessage(error));
    }
  }

  return (
    <section className="student-chat">
      <header>
        <button type="button" aria-label="Sohbeti kapat" className="btn btn-ghost"
          onClick={onBack}><ArrowLeft size={20} /></button>
        <div>
          <h3>{subjectName || teacherName}</h3>
          {subjectName && <p>{teacherName}</p>}
        </div>
      </header>
      <div className="student-chat-history" ref={history} onScroll={(event) => {
        const list = event.currentTarget;
        followMessages.current = list.scrollHeight - list.scrollTop - list.clientHeight < 56;
      }}>
        {historyError && <p role="alert">{historyError}</p>}
        {loading ? <p>Mesajlar yükleniyor…</p> : !messages.length && !historyError && <p>Henüz mesaj yok.</p>}
        {historyWindow.hasOlder && <button type="button" className="btn btn-secondary" disabled={loadingOlder || busy}
          onClick={() => void loadOlder()}>{loadingOlder ? "Yükleniyor…" : "Daha eski mesajları göster"}</button>}
        {messages.map((row) => (
          <article key={row.id} data-message-id={row.id} className={row.is_current_user ? "student-chat-own" : ""}>
            {row.content && <div>{row.content}</div>}
            {row.attachment_name && row.attachment_sha256 &&
              <button type="button" onClick={() => void download(row)} className="student-chat-link">
                <Paperclip size={16} aria-hidden="true" /> {row.attachment_name}
              </button>}
            <time dateTime={row.sent_at}>{new Date(row.sent_at).toLocaleTimeString("tr-TR", {
              hour: "2-digit", minute: "2-digit",
            })}{row.is_current_user && row.is_read && " ✓"}</time>
          </article>
        ))}
      </div>
      {actionError && <p className="student-chat-status" role="alert">{actionError}</p>}
      {canSend ? <form onSubmit={sendMessage} className="student-chat-form" aria-busy={busy}>
        <textarea aria-label="Sohbet mesajı" rows={2} maxLength={10000} value={message}
          disabled={busy || !!pending} placeholder="Mesajınızı yazın…" onChange={(event) => setMessage(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
              event.preventDefault();
              event.currentTarget.form?.requestSubmit();
            }
          }} />
        {file && <div className="student-chat-file">{file.name}</div>}
        <input ref={fileInput} type="file" aria-label="Sohbet dosyası" accept=".pdf,.png,.jpg,.jpeg" hidden
          disabled={busy || !!pending} onChange={(event) => {
            setFile(event.target.files?.[0] ?? null);
            setActionError("");
          }} />
        <div className="student-chat-actions">
          {pending ? (
            <>
              <button type="button" className="btn btn-secondary" disabled={busy}
                onClick={() => void submit(pending, false)}>Gönderimi kontrol et</button>
              {missingReceipt && <button type="button" className="btn btn-primary" disabled={busy}
                onClick={() => void submit(pending, true)}>Yeniden dene</button>}
            </>
          ) : (
            <>
              <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => fileInput.current?.click()}>
                <Paperclip size={18} aria-hidden="true" /> Dosya ekle
              </button>
              {file && <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => {
                setFile(null);
                if (fileInput.current) fileInput.current.value = "";
              }}>Eki kaldır</button>}
              <button type="submit" className="btn btn-primary" disabled={busy || (!message.trim() && !file)}>
                <Send size={18} aria-hidden="true" /> Gönder
              </button>
            </>
          )}
        </div>
      </form> : <p className="student-chat-status">Bu hesapla gönderim yapılamaz.</p>}
    </section>
  );
}
