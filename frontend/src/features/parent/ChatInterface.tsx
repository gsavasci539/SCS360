import { ArrowLeft, Paperclip, Send } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";
import { api, apiMessage, unwrap } from "../../lib/api";
import { downloadFile } from "../../lib/download";
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
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [message, setMessage] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [historyError, setHistoryError] = useState("");
  const [actionError, setActionError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState<PendingMessage | null>(null);
  const [missingReceipt, setMissingReceipt] = useState(false);
  const session = useRef<AbortController | null>(null);
  const historyRequest = useRef<Promise<void> | null>(null);
  const sending = useRef(false);
  const history = useRef<HTMLDivElement>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const followMessages = useRef(true);
  const lastId = messages.at(-1)?.id;
  const params = useMemo(() => (parentId || branchId ? {
    ...(parentId ? { parent_id: parentId } : {}),
    ...(branchId ? { branch_id: branchId } : {}),
  } : undefined),
    [parentId, branchId]);

  const refresh = useCallback(async (signal: AbortSignal) => {
    try {
      const rows = unwrap(await api.get<ApiResponse<ChatMessage[]>>(endpoint, {
        params, signal,
      }));
      if (signal.aborted) return;
      setMessages(rows);
      setHistoryError("");
    } catch (error) {
      if (!signal.aborted) setHistoryError(apiMessage(error));
    } finally {
      if (!signal.aborted) setLoading(false);
    }
  }, [endpoint, params]);

  useEffect(() => {
    const controller = new AbortController();
    session.current = controller;
    const poll = () => {
      if (historyRequest.current || sending.current) return;
      const request = refresh(controller.signal);
      historyRequest.current = request;
      void request.finally(() => {
        if (historyRequest.current === request) historyRequest.current = null;
      });
    };
    poll();
    const timer = window.setInterval(poll, 5000);
    return () => {
      controller.abort();
      historyRequest.current = null;
      window.clearInterval(timer);
    };
  }, [refresh]);

  useEffect(() => {
    if (history.current && followMessages.current) history.current.scrollTop = history.current.scrollHeight;
  }, [lastId]);

  async function verify(draft: PendingMessage, signal: AbortSignal) {
    const receipt = unwrap(await api.get<ApiResponse<ChatMessage>>(`${endpoint}/sent/${draft.id}`, { params, signal }));
    const name = draft.file?.name.replace(/\\/g, "/").split("/").at(-1)?.trim() ?? null;
    if (receipt.id !== draft.id || !receipt.is_current_user || receipt.content !== draft.content ||
        (receipt.attachment_name ?? null) !== name ||
        (draft.file && !/^[a-f0-9]{64}$/.test(receipt.attachment_sha256 ?? ""))) {
      throw new Error("Sunucudaki mesaj bilgileri gönderimle eşleşmiyor.");
    }
    return receipt;
  }

  async function submit(draft: PendingMessage, send: boolean) {
    const signal = session.current?.signal;
    if (!canSend || !signal || signal.aborted || sending.current) return;
    sending.current = true;
    setBusy(true);
    setPending(draft);
    setMissingReceipt(false);
    setActionError("");
    let posting = send;
    try {
      if (send) {
        if (draft.file) {
          const form = new FormData();
          form.set("file", draft.file);
          form.set("message", draft.content);
          form.set("request_id", draft.id);
          await api.post(`${endpoint}/send-file`, form, { params, signal });
        } else {
          await api.post(endpoint, { message: draft.content, request_id: draft.id }, { params, signal });
        }
      }
      posting = false;
      const receipt = await verify(draft, signal);
      await historyRequest.current;
      if (signal.aborted) return;
      followMessages.current = true;
      setMessages((rows) => rows.some((row) => row.id === receipt.id) ? rows : [...rows, receipt]);
      setPending(null);
      setMessage("");
      setFile(null);
      if (fileInput.current) fileInput.current.value = "";
    } catch (error) {
      if (!signal.aborted) {
        const status = (error as { response?: { status?: number } } | null)?.response?.status;
        if (posting && (status === 413 || status === 422)) setPending(null);
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
    try {
      await downloadFile(`${endpoint}/attachments/${encodeURIComponent(row.id)}`, row.attachment_name, { params, signal });
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
        {messages.map((row) => (
          <article key={row.id} className={row.is_current_user ? "student-chat-own" : ""}>
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
      {canSend ? <form onSubmit={sendMessage} className="student-chat-form">
        <textarea aria-label="Sohbet mesajı" rows={2} maxLength={10000} value={message}
          disabled={!!pending} placeholder="Mesajınızı yazın…" onChange={(event) => setMessage(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
              event.preventDefault();
              event.currentTarget.form?.requestSubmit();
            }
          }} />
        {file && <div className="student-chat-file">{file.name}</div>}
        <input ref={fileInput} type="file" aria-label="Sohbet dosyası" accept=".pdf,.png,.jpg,.jpeg" hidden
          disabled={!!pending} onChange={(event) => {
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
              <button type="button" className="btn btn-secondary" onClick={() => fileInput.current?.click()}>
                <Paperclip size={18} aria-hidden="true" /> Dosya ekle
              </button>
              {file && <button type="button" className="btn btn-secondary" onClick={() => {
                setFile(null);
                if (fileInput.current) fileInput.current.value = "";
              }}>Eki kaldır</button>}
              <button type="submit" className="btn btn-primary" disabled={!message.trim() && !file}>
                <Send size={18} aria-hidden="true" /> Gönder
              </button>
            </>
          )}
        </div>
      </form> : <p className="student-chat-status">Bu hesapla gönderim yapılamaz.</p>}
    </section>
  );
}
