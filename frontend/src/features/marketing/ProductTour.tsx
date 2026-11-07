import { useState, type KeyboardEvent } from "react";
import { BookOpen, Building2, CalendarDays, Check, ChevronRight, GraduationCap, ReceiptText, ShieldCheck, Users, WalletCards } from "lucide-react";
import { BrandMark } from "../../components/Brand";

const areas = [
  { id: "kurum", label: "Kurum", icon: Building2, title: "Bütün şubeler. Ortak bir düzen.", description: "Kurum, şube ve ekip erişimlerini birlikte yönetin." },
  { id: "egitim", label: "Eğitim", icon: GraduationCap, title: "Her okul gününe net bir akış.", description: "Sınıftaki bilgi, ilgili öğretmen ve veliyle buluşsun." },
  { id: "finans", label: "Finans", icon: WalletCards, title: "Kayıttan makbuza, izlenebilir.", description: "Borç ve tahsilat geçmişinizi aynı alanda takip edin." },
];

export function ProductTour() {
  const [active, setActive] = useState(0);
  const area = areas[active];
  function changeWithKeyboard(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    let next: number;
    if (event.key === "ArrowRight") next = (index + 1) % areas.length;
    else if (event.key === "ArrowLeft") next = (index + areas.length - 1) % areas.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = areas.length - 1;
    else return;
    event.preventDefault(); setActive(next); document.getElementById(`product-tab-${areas[next].id}`)?.focus();
  }
  return <div className="marketing-product-stage" id="urun">
    <div className="marketing-orbit marketing-orbit-one" aria-hidden="true" /><div className="marketing-orbit marketing-orbit-two" aria-hidden="true" />
    <section className="marketing-product" aria-label="SCS360 ürün turu">
      <div className="marketing-product-bar"><span><BrandMark size={24} /><strong>SCS360</strong><span className="marketing-demo-label">Ürün turu</span></span><span className="marketing-window-dots" aria-hidden="true"><i /><i /><i /></span></div>
      <div className="marketing-product-tabs" role="tablist" aria-label="Ürün alanları">
        {areas.map((item, index) => <button type="button" key={item.id} id={`product-tab-${item.id}`} role="tab" aria-selected={index === active}
          aria-controls={`product-panel-${item.id}`} tabIndex={index === active ? 0 : -1} onClick={() => setActive(index)} onKeyDown={(event) => changeWithKeyboard(event, index)}><item.icon size={16} />{item.label}</button>)}
      </div>
      <div className="marketing-product-body" role="tabpanel" id={`product-panel-${area.id}`} aria-labelledby={`product-tab-${area.id}`} tabIndex={0}>
        <div className="marketing-product-topline"><span className="marketing-kicker">ÖRNEK ÇALIŞMA ALANI</span><span className="marketing-demo-status"><i />Birbirine bağlı</span></div>
        <h2>{area.title}</h2><p>{area.description}</p>
        {active === 0 && <div className="marketing-demo-organization">
          <div className="marketing-demo-root"><Building2 size={20} /><div><strong>Örnek Eğitim Kurumu</strong><small>Kurum çalışma alanı</small></div><ShieldCheck size={17} /></div>
          <div className="marketing-demo-branches"><div><span><GraduationCap size={18} /></span><strong>Merkez Şube</strong><small>Öğrenci ve sınıflar</small></div><div><span><GraduationCap size={18} /></span><strong>İkinci Şube</strong><small>Öğrenci ve sınıflar</small></div></div>
          <div className="marketing-demo-roles"><span>Ekibinizin erişimi</span><div><span>Yönetici</span><span>Öğretmen</span><span>Veli</span></div></div>
        </div>}
        {active === 1 && <div className="marketing-demo-school">
          <div className="marketing-demo-day"><CalendarDays size={18} /><strong>Bir okul gününden</strong><span>Temsili akış</span></div>
          {[{ icon: Users, time: "09:00", title: "Sınıf yoklaması", note: "Katılım bilgisi kayıt altında" }, { icon: BookOpen, time: "11:00", title: "Ödev ve materyaller", note: "Öğretmenden öğrencinin alanına" }, { icon: Check, time: "16:00", title: "Günlük rapor", note: "Veli portalında ilgili çocuğun bilgisi" }].map((item) => <div className="marketing-demo-timeline" key={item.title}><time>{item.time}</time><span><item.icon size={17} /></span><div><strong>{item.title}</strong><small>{item.note}</small></div></div>)}
        </div>}
        {active === 2 && <div className="marketing-demo-finance">
          <div className="marketing-demo-payment"><span><WalletCards size={23} /></span><div><strong>Borç ve tahsilat takibi</strong><small>Öğrenciye bağlı kayıt geçmişi</small></div></div>
          <ol><li><span>01</span><strong>Borç kaydı</strong><Check size={16} /></li><li><span>02</span><strong>Tahsilat</strong><Check size={16} /></li><li><span>03</span><strong>Makbuz</strong><ReceiptText size={16} /></li></ol>
          <div className="marketing-demo-finance-note"><ShieldCheck size={17} /><span>İşlemler, tanımlanan finans yetkilerine göre açılır.</span></div>
        </div>}
      </div>
      <div className="marketing-product-caption"><span>Temsili arayüz ve örnek içerik.</span><span>Alanları keşfedin <ChevronRight size={12} /></span></div>
    </section>
    <div className="marketing-product-stamp"><ShieldCheck size={20} /><div><strong>İlgili bilgi, ilgili kişide.</strong><span>Roller ve şube erişimleriyle.</span></div></div>
  </div>;
}
