import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../../lib/api";
import { CheckCircle, XCircle, Loader2 } from "lucide-react";

export function PaymentPage() {
  const { debtId, amount } = useParams<{ debtId: string; amount: string }>();
  const [checkoutContent, setCheckoutContent] = useState<string>("");
  const [status, setStatus] = useState<"loading" | "pending" | "success" | "failed">("loading");
  const [message, setMessage] = useState<string>("");

  useEffect(() => {
    if (!debtId || !amount) {
      setStatus("failed");
      setMessage("Geçersiz ödeme bilgileri");
      return;
    }

    // Initialize payment
    api.post("/payments/iyzico/initialize", {
      debt_id: debtId,
      amount: parseFloat(amount),
      currency: "TRY",
      payment_channel: "WEB",
      basket_items: []
    }, { timeout: 30000 })
      .then(response => {
        if (response.data.data.checkout_form_content) {
          setCheckoutContent(response.data.data.checkout_form_content);
          setStatus("pending");
          
          // Execute the iyzico script
          const scriptContent = response.data.data.checkout_form_content;
          const scriptMatch = scriptContent.match(/<script[^>]*>([\s\S]*?)<\/script>/);
          if (scriptMatch) {
            const scriptCode = scriptMatch[1];
            try {
              // Create a function from the script code and execute it
              const scriptFunction = new Function(scriptCode);
              scriptFunction();
            } catch (err) {
              console.error('Error executing iyzico script:', err);
            }
          }
          
          // Start polling for payment status
          const pollInterval = setInterval(async () => {
            try {
              // Get the student_id from the debt first
              const debtResponse = await api.get(`/debts/${debtId}`);
              const studentId = debtResponse.data.data.student_id;
              
              if (studentId) {
                const response = await api.get(`/parent/child/${studentId}/financial-invoices`);
                const invoices = response.data.data.invoices;
                const paidDebt = invoices.find((inv: any) => 
                  inv.debt_id === debtId && inv.status === 'PAID'
                );
                
                if (paidDebt) {
                  setStatus("success");
                  setMessage("Ödeme başarıyla tamamlandı");
                  clearInterval(pollInterval);
                }
              }
            } catch {
              console.error('Error polling payment status');
            }
          }, 3000);
          
          // Stop polling after 5 minutes
          const timeout = setTimeout(() => {
            clearInterval(pollInterval);
            if (status === "pending") {
              setStatus("failed");
              setMessage("Ödeme işlemi zaman aşımına uğradı");
            }
          }, 300000);
          
          return () => {
            clearInterval(pollInterval);
            clearTimeout(timeout);
          };
        }
      })
      .catch(() => {
        setStatus("failed");
        setMessage("Ödeme başlatılamadı");
      });
  }, [debtId, amount]);

  if (status === "loading") {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        padding: '20px',
        background: '#f5f5f5'
      }}>
        <Loader2 size={48} style={{ color: '#2196f3', marginBottom: 16 }} />
        <h2 style={{ margin: 0, fontSize: '20px', color: '#333' }}>
          Ödeme Başlatılıyor...
        </h2>
        <p style={{ margin: '16px 0 0 0', color: '#666', fontSize: '16px' }}>
          Lütfen bekleyin
        </p>
      </div>
    );
  }

  if (status === "pending") {
    return (
      <div style={{ minHeight: '100vh', background: '#f5f5f5', padding: '20px' }}>
        <div style={{
          maxWidth: 600,
          margin: '0 auto',
          background: 'white',
          borderRadius: 12,
          padding: 24,
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
        }}>
          <div style={{ marginBottom: 20, textAlign: 'center' }}>
            <h1 style={{ margin: 0, fontSize: '24px', color: '#333' }}>
              Ödeme İşlemi
            </h1>
            <p style={{ margin: '8px 0 0 0', color: '#666', fontSize: '16px' }}>
              Ödeme Tutarı: ₺{amount ? parseFloat(amount).toLocaleString('tr-TR') : '0'}
            </p>
          </div>
          <div 
            style={{ minHeight: '400px' }}
            dangerouslySetInnerHTML={{ __html: checkoutContent }} 
          />
        </div>
      </div>
    );
  }

  if (status === "success") {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        padding: '20px',
        background: '#f5f5f5'
      }}>
        <CheckCircle size={64} style={{ color: '#4caf50', marginBottom: 16 }} />
        <h1 style={{ margin: 0, fontSize: '28px', color: '#2e7d32' }}>
          Ödeme Başarılı
        </h1>
        <p style={{ margin: '16px 0 0 0', color: '#666', fontSize: '18px', textAlign: 'center' }}>
          {message}
        </p>
        <button
          onClick={() => window.close()}
          style={{
            marginTop: 24,
            padding: '12px 32px',
            background: '#4caf50',
            color: 'white',
            border: 'none',
            borderRadius: 8,
            fontSize: '16px',
            cursor: 'pointer'
          }}
        >
          Pencereyi Kapat
        </button>
      </div>
    );
  }

  if (status === "failed") {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        padding: '20px',
        background: '#f5f5f5'
      }}>
        <XCircle size={64} style={{ color: '#f44336', marginBottom: 16 }} />
        <h1 style={{ margin: 0, fontSize: '28px', color: '#c62828' }}>
          Ödeme Başarısız
        </h1>
        <p style={{ margin: '16px 0 0 0', color: '#666', fontSize: '18px', textAlign: 'center' }}>
          {message}
        </p>
        <button
          onClick={() => window.close()}
          style={{
            marginTop: 24,
            padding: '12px 32px',
            background: '#f44336',
            color: 'white',
            border: 'none',
            borderRadius: 8,
            fontSize: '16px',
            cursor: 'pointer'
          }}
        >
          Pencereyi Kapat
        </button>
      </div>
    );
  }

  return null;
}
