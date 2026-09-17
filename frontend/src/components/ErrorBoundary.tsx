import { Component, type ErrorInfo, type ReactNode } from "react";

export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(error: Error, info: ErrorInfo) { console.error("UI error", error, info); }
  render() {
    if (this.state.failed) return <div className="error-page">
      <div><div className="error-code">!</div><h1>Bir şeyler yolunda gitmedi</h1><p>Bu ekran beklenmeyen bir sorunla karşılaştı. Sayfayı yenileyerek güvenli biçimde devam edebilirsiniz.</p><button className="btn btn-primary" onClick={() => window.location.reload()}>Sayfayı yenile</button></div>
    </div>;
    return this.props.children;
  }
}
