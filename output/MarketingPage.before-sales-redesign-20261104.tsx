import { ArrowUpRight, Check, ChevronRight, Building2, CalendarDays, GraduationCap, ShieldCheck, Users, WalletCards } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { Brand } from "../../components/Brand";
import { ErrorState, LoadingState } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { getHomePath } from "../../lib/home";
import { packagePrice } from "../../lib/subscription";
import { useAuthStore } from "../../stores/auth";
import type { DataRecord } from "../../types/api";
import "./marketing.css";

export function usePublicPlans() {
  const [plans, setPlans] = useState<DataRecord[]>([]), [loading, setLoading] = useState(true), [error, setError] = useState(""), [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true);
    api.get("/public/plans", { signal: controller.signal }).then((response) => {
      if (!controller.signal.aborted) { setPlans(response.data.data || []); setError(""); }
    }).catch((reason) => { if (!controller.signal.aborted) setError(apiMessage(reason)); }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [revision]);
  return { plans, loading, error, retry: () => setRevision((value) => value + 1) };
}

export function PublicLayout({ title, children }: { title: string; children: ReactNode }) {
  const user = useAuthStore((state) => state.user);
  useEffect(() => { const previous = document.title; document.title = `${title} | SCS360`; return () => { document.title = previous; }; }, [title]);
  return <div className="marketing"><a className="marketing-skip" href="#public-main">İçeriğe geç</a>
    <header className="marketing-header"><Link to="/" aria-label="SCS360 ana sayfa"><Brand subtitle="Eğitim yönetimi" /></Link>
      <nav aria-label="Site menüsü"><a href="/#cozumler">Çözümler</a><a href="/#nasil-calisir">Nasıl çalışır?</a><Link to="/fiyatlandirma">Fiyatlandırma</Link></nav>
      <Link className="marketing-login" to={user ? getHomePath(user) : "/login"}>{user ? "Panelime git" : "Giriş yap"}<ArrowUpRight size={16} /></Link>
    </header>
    <main id="public-main">{children}</main>
    <footer className="marketing-footer"><div><Brand subtitle="Her güne daha net bir bakış" /><p>Okulunuzun süreçleri, ekibinizin ortak çalışma alanı.</p></div><nav aria-label="Alt menü"><a href="/#cozumler">Çözümler</a><Link to="/fiyatlandirma">Paketler ve fiyatlar</Link><a href="/#sorular">Sık sorulan sorular</a><Link to="/login">Kurum girişi</Link></nav><small>© {new Date().getFullYear()} SCS360</small></footer>
  </div>;
}

function ProductIllustration() {
  return <div className="marketing-product" role="img" aria-label="Örnek çalışma alanı: günlük plan, yoklama ve kurum süreçleri">
    <div className="marketing-product-bar"><span className="marketing-dots"><i /><i /><i /></span><span>Örnek çalışma alanı</span><ShieldCheck size={16} /></div>
    <div className="marketing-product-body"><div className="marketing-product-nav"><GraduationCap size={27} /><CalendarDays /><Users /><WalletCards /></div>
      <div className="marketing-product-content"><span className="marketing-kicker">ORTAK ÇALIŞMA ALANI</span><h2>Güne birlikte başlayın.</h2><p>Ekibinize bir bakış, gününüze net bir plan.</p>
        <div className="marketing-demo-calendar">{["Pzt", "Sal", "Çar", "Per", "Cum"].map((day, index) => <div key={day} className={index === 2 ? "selected" : ""}><span>{day}</span><strong>{index + 2}</strong></div>)}</div>
        <div className="marketing-demo-task"><span><CalendarDays size={19} /></span><div><strong>Günlük plan</strong><small>Sınıf ve etkinlik akışını inceleyin</small></div><ChevronRight size={17} /></div>
        <div className="marketing-demo-task"><span><Users size={19} /></span><div><strong>Yoklama</strong><small>Sınıfınızın katılımını kaydedin</small></div><ChevronRight size={17} /></div>
        <div className="marketing-demo-note"><Check size={17} /><span>Doğru bilgi, doğru yetkiye sahip kişide.</span></div>
      </div></div>
  </div>;
}

export function PublicPricing({ standalone = false }: { standalone?: boolean }) {
  const { plans, loading, error, retry } = usePublicPlans(); const [months, setMonths] = useState(1); const user = useAuthStore((state) => state.user);
  const visible = plans.filter((plan) => Number(plan.period_months) === months);
  return <section className="marketing-section marketing-pricing" id="paketler" aria-label="Üyelik paketleri"><div className="marketing-section-heading"><span className="marketing-kicker">KURUMUNUZA UYGUN ALAN</span>{standalone ? <h1>İhtiyacınıza göre bir paket.</h1> : <h2>İhtiyacınıza göre bir paket.</h2>}<p>Şube, öğrenci ve kullanıcı sınırlarını birlikte görün. Paketinizin fiyatını ve dönemini seçerek başlayın.</p></div>
    <div className="marketing-period" aria-label="Paket dönemi"><button aria-pressed={months === 1} onClick={() => setMonths(1)}>Aylık</button><button aria-pressed={months === 12} onClick={() => setMonths(12)}>Yıllık</button></div>
    {loading ? <LoadingState label="Güncel paketler yükleniyor" /> : error ? <ErrorState message={error} retry={retry} /> : !plans.length ? <div className="marketing-empty"><Building2 size={28} /><h3>Paketler hazırlanıyor.</h3><p>Güncel satış paketleri tanımlandığında fiyat ve sınırlar burada görünecek.</p><Link to="/login">Mevcut kurum hesabınıza giriş yapın <ArrowUpRight size={16} /></Link></div> : !visible.length ? <p className="marketing-empty">Bu dönem için satışa açık paket bulunmuyor. Diğer dönemdeki paketleri inceleyebilirsiniz.</p> : <div className="marketing-plan-grid">{visible.map((plan) => <article className="marketing-plan" key={plan.id}><span className="marketing-kicker">{Number(plan.period_months) === 12 ? "YILLIK" : "AYLIK"} ÜYELİK</span><h3>{String(plan.name)}</h3><div className="marketing-price">{packagePrice(plan.price, plan.currency)}<span> / {Number(plan.period_months) === 12 ? "yıl" : "ay"}</span></div>
      <ul><li><Check size={17} />{Number(plan.branch_limit).toLocaleString("tr-TR")} şube</li><li><Check size={17} />{Number(plan.student_limit).toLocaleString("tr-TR")} öğrenci</li><li><Check size={17} />{Number(plan.user_limit).toLocaleString("tr-TR")} kullanıcı hesabı</li><li><ShieldCheck size={17} />Rollere göre kurum erişimi</li></ul>
      <Link className="marketing-primary" to={user ? user.is_super_admin ? "/platform" : `/subscription?paket=${plan.id}` : `/kayit?paket=${plan.id}`}>{user ? "Üyeliği yönet" : "Paketi seç"}<ArrowUpRight size={18} /></Link>
    </article>)}</div>}
    <p className="marketing-price-note">Gösterilen tutar seçtiğiniz üyelik döneminin paket fiyatıdır. Kurum erişimi, üyelik ödemeniz doğrulandığında açılır.</p>
  </section>;
}

const questions = [
  ["SCS360 kimler için?", "Okullar ve eğitim kurumları için ortak bir çalışma alanı sunar. Kurum sahibi, yöneticiler, öğretmenler ve veliler kendi yetkilerine göre işlem yapar."],
  ["Üyeliği nasıl başlatırım?", "Satışa açık paketlerden birini seçin, kurum ve sahip hesabını oluşturun. Üyelik ekranındaki ödeme talebini tamamlayın; ödeme doğrulandığında kurum çalışma alanınız açılır."],
  ["Şube ve kullanıcı sınırları nasıl işler?", "Paket sınırları kurumunuzun toplam şube, öğrenci ve kullanıcı sayısı için geçerlidir. Yeni kayıt sınırına ulaştığınızda mevcut kayıtlarınız korunur; daha geniş bir paket seçebilirsiniz."],
  ["Üyelik süresi biterse ne olur?", "Süre bitiminde ekibiniz ödeme uyarısı görür. On günlük ek sürenin ardından üyelik yenilenene kadar çalışma alanı kapanır; kurum sahibi üyelik ve ödeme ekranına erişmeye devam eder."],
  ["Telefondan kullanabilir miyim?", "SCS360 web arayüzü mobil ekranlara uyum sağlar. Öğretmen ve veli alanlarına tarayıcınız üzerinden ulaşabilirsiniz."],
];

export function MarketingPage({ pricing = false }: { pricing?: boolean }) {
  return <PublicLayout title={pricing ? "Paketler ve fiyatlandırma" : "Okulunuzun ortak çalışma alanı"}>
    {!pricing && <>
      <section className="marketing-hero"><div className="marketing-hero-copy"><span className="marketing-kicker"><span className="marketing-dot" /> OKULUNUZUN ORTAK ÇALIŞMA ALANI</span><h1>Eğitimde bütün resmi <em>görün.</em></h1><p>Şubelerden sınıflara, yoklamadan veli iletişimine. SCS360 ile okulunuzun günlük akışını tek bir yerde yönetin.</p><div className="marketing-hero-actions"><Link className="marketing-primary" to="/fiyatlandirma">Paketleri keşfedin<ArrowUpRight size={18} /></Link><a className="marketing-secondary" href="#cozumler">SCS360'ı tanıyın<ChevronRight size={17} /></a></div><div className="marketing-proof"><span><ShieldCheck size={17} />Rollere göre erişim</span><span><Building2 size={17} />Şubeler birlikte</span><span><Users size={17} />Ekibinizle aynı sayfada</span></div></div><ProductIllustration /></section>
      <section className="marketing-intro" id="cozumler"><span className="marketing-kicker">DAHA AZ DAĞINIKLIK, DAHA NET BİR AKIŞ</span><h2>Herkesin işi farklı.<br />Çalışma alanınız ortak.</h2><p>Bilginin farklı dosyalarda kaybolmasını önleyin. Kurumunuzun eğitim, operasyon ve finans süreçlerini birbirine bağlayın.</p></section>
      <section className="marketing-solutions" aria-label="SCS360 çözümleri">
        <article><div className="marketing-solution-number">01 / KURUM</div><Building2 size={29} /><h3>Her şubeye<br />birlikte bakın.</h3><p>Şubelerinizi, öğrenci kayıtlarını ve kullanıcı erişimlerini kurumunuzun paket sınırları içinde yönetin.</p><ul><li>Kurum ve şube kayıtları</li><li>Öğrenci ve veli ilişkileri</li><li>Kullanıcı, rol ve yetki yönetimi</li></ul></article>
        <article><div className="marketing-solution-number">02 / EĞİTİM</div><GraduationCap size={29} /><h3>Günün akışında<br />ekibinizle buluşun.</h3><p>Öğretmenlerin çalışma alanından veli portalına, okulunuzun eğitim bilgileri ilgili kişilere ulaşsın.</p><ul><li>Yoklama ve günlük raporlar</li><li>Ödev ve ders materyalleri</li><li>Veli iletişimi ve duyurular</li></ul></article>
        <article><div className="marketing-solution-number">03 / OPERASYON</div><WalletCards size={29} /><h3>Kayıtlarınızı<br />bir arada tutun.</h3><p>Finans ve kurum operasyonlarını aynı sistemden takip edin; ekipleriniz kendi yetki alanlarında çalışsın.</p><ul><li>Borç, ödeme ve makbuz takibi</li><li>Revir, teslim ve güvenlik kayıtları</li><li>Envanter, anket ve onay süreçleri</li></ul></article>
      </section>
      <section className="marketing-how" id="nasil-calisir"><div><span className="marketing-kicker">İLK ADIMDAN GÜNLÜK KULLANIMA</span><h2>Kurumunuza alan açın.</h2><p>Paketinizi seçin. Kurum sahibi hesabınızla üyeliğinizi yönetin. Ödemeniz doğrulandığında ekibinizi davet etmeden önce hesap ve erişimlerini kendiniz oluşturun.</p></div><ol><li><span>1</span><div><h3>Paketinizi seçin</h3><p>Şube, öğrenci ve kullanıcı ihtiyacınızı karşılayan dönemi ve paketi inceleyin.</p></div></li><li><span>2</span><div><h3>Kurum hesabınızı oluşturun</h3><p>Kurum sahibi hesabıyla üyelik ve ödeme adımlarını tamamlayın.</p></div></li><li><span>3</span><div><h3>Ekibinizle başlayın</h3><p>Kullanıcıları, öğrencileri ve velileri oluşturup rol ve şube erişimlerini atayın.</p></div></li></ol></section>
    </>}
    <PublicPricing standalone={pricing} />
    <section className="marketing-faq marketing-section" id="sorular"><div><span className="marketing-kicker">AKLINIZDAKİLER</span><h2>Sık sorulan sorular.</h2><p>Üyelik ve kurum kullanımı hakkında.</p></div><div>{questions.map(([question, answer]) => <details key={question}><summary>{question}<span>+</span></summary><p>{answer}</p></details>)}</div></section>
    <section className="marketing-final"><div><span className="marketing-kicker">BİR SONRAKİ OKUL GÜNÜNE HAZIR MISINIZ?</span><h2>Okulunuz için<br />daha net bir başlangıç.</h2></div><Link className="marketing-primary" to={pricing ? "/login" : "/fiyatlandirma"}>{pricing ? "Kurum hesabına giriş" : "Paketleri incele"}<ArrowUpRight size={18} /></Link></section>
  </PublicLayout>;
}
