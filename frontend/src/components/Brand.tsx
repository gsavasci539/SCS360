export function BrandMark({ size = 42 }: { size?: number }) {
  return <img className="brand-mark" src={`${import.meta.env.BASE_URL}scs360-mark.svg?v=2`} alt="SCS360 logosu" width={size} height={size} style={{ width: size, height: size }} />;
}

export function Brand({ subtitle, className = "brand" }: { subtitle: string; className?: string }) {
  return <div className={className}>
    <BrandMark />
    <div>
      <div className="brand-title">SCS360</div>
      <div className="brand-subtitle">{subtitle}</div>
    </div>
  </div>;
}

export function ReceiptBrand() {
  return <div className="receipt-brand"><BrandMark size={32} /><span>SCS360</span></div>;
}
