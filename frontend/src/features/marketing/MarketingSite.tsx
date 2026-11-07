import { ArrowDownRight, ArrowRight, ArrowUpRight, BookOpen, Building2, CalendarDays, Check, CheckCheck, ChevronRight, GraduationCap, HeartPulse, Layers3, LockKeyhole, MessageSquare, ShieldCheck, Users, WalletCards } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { Brand } from "../../components/Brand";
import { ErrorState, LoadingState } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { getHomePath } from "../../lib/home";
import { packagePrice } from "../../lib/subscription";
import { useAuthStore } from "../../stores/auth";
import type { DataRecord } from "../../types/api";
import { ProductTour } from "./ProductTour";
import { CampusVisual } from "./CampusVisual";
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
  const { pathname, hash } = useLocation();
  useEffect(() => { const previous = document.title; document.title = `${title} | SCS360`; return () => { document.title = previous; }; }, [title]);
  useEffect(() => {
    let frame = 0, disposed = false, activeHash = hash;
    function scrollToAnchor(rawHash: string) {
      activeHash = rawHash;
      cancelAnimationFrame(frame);
      if (!rawHash || rawHash === "#") return;
      let id: string;
      try { id = decodeURIComponent(rawHash.slice(1)); } catch { return; }
      frame = requestAnimationFrame(() => {
        if (disposed) return;
        const target = document.getElementById(id);
        target?.scrollIntoView?.({ block: "start", behavior: "instant" });
        if (id === "public-main") target?.focus({ preventScroll: true });
      });
    }
    // Native fragment navigation can precede the lazy route's first render.
    // Scroll after this page has mounted, and on same-page native anchors too.
    if (!hash) frame = requestAnimationFrame(() => { if (!disposed) window.scrollTo({ top: 0, left: 0, behavior: "instant" }); });
    else scrollToAnchor(hash);
    const changed = () => scrollToAnchor(window.location.hash);
    window.addEventListener("hashchange", changed);
    // A catalog response can change the height above FAQ/footer bookmarks.
    // Observe only initial loading, then disconnect before normal interactions.
    const main = document.getElementById("public-main");
    const observer = new MutationObserver(() => {
      if (!main?.querySelector('[aria-busy="true"]')) { scrollToAnchor(activeHash); observer.disconnect(); }
    });
    if (main?.querySelector('[aria-busy="true"]')) observer.observe(main, { subtree: true, attributes: true, attributeFilter: ["aria-busy"] });
    return () => { disposed = true; cancelAnimationFrame(frame); observer.disconnect(); window.removeEventListener("hashchange", changed); };
  }, [pathname, hash]);
  return <div className="marketing"><a className="marketing-skip" href="#public-main">İçeriğe geç</a>
    <div className="marketing-header-shell"><header className="marketing-header"><Link className="marketing-brand-link" to="/" aria-label="SCS360 ana sayfa"><Brand subtitle="Okul ve kurum yönetimi" /></Link>
      <nav aria-label="Site menüsü"><a href="/#cozumler">Çözümler</a><a href="/#nasil-calisir">Nasıl çalışır?</a><a href="/#guven">Erişim ve üyelik</a><Link to="/hakkimizda" aria-current={pathname === "/hakkimizda" ? "page" : undefined}>Hakkımızda</Link><Link to="/fiyatlandirma" aria-current={pathname === "/fiyatlandirma" ? "page" : undefined}>Fiyatlandırma</Link></nav>
      <Link className="marketing-login" to={user ? getHomePath(user) : "/login"}>{user ? "Panelime git" : "Giriş yap"}<ArrowUpRight size={16} /></Link>
    </header></div>
    <main id="public-main" tabIndex={-1}>{children}</main>
    <footer className="marketing-footer"><div className="marketing-footer-top"><div><Brand subtitle="Eğitimin etrafında, birlikte." /><p>Okulunuzun her günü için<br />birbirine bağlı çalışma alanları.</p></div><div className="marketing-footer-nav"><nav aria-label="Ürün bağlantıları"><strong>Keşfedin</strong><Link to="/hakkimizda">Hakkımızda</Link><a href="/#cozumler">Çözümler</a><a href="/#urun">Ürün turu</a><a href="/#guven">Erişim ve üyelik</a></nav><nav aria-label="Üyelik bağlantıları"><strong>Birlikte başlayın</strong><Link to="/fiyatlandirma">Paketler ve fiyatlar</Link><a href="/#sorular">Sık sorulan sorular</a><Link to="/login">Kurum girişi</Link></nav></div></div><div className="marketing-footer-bottom"><small>© {new Date().getFullYear()} SCS360</small><span>Okulunuzu yönetmeye alan açın.</span><a href="#public-main" aria-label="Sayfanın başına dön">Yukarı dön <ArrowUpRight size={15} /></a></div></footer>
  </div>;
}

export function PublicPricing({ standalone = false }: { standalone?: boolean }) {
  const { plans, loading, error, retry } = usePublicPlans(); const [months, setMonths] = useState(1); const user = useAuthStore((state) => state.user);
  const visible = plans.filter((plan) => Number(plan.period_months) === months);
  return <section className={`marketing-section marketing-pricing${standalone ? " marketing-pricing-standalone" : ""}`} id="paketler" aria-label="Üyelik paketleri" aria-busy={loading}>
    <div className="marketing-section-heading"><span className="marketing-kicker">OKULUNUZLA BÜYÜYEN BİR ALAN</span>{standalone ? <h1>İhtiyacınıza göre bir paket.</h1> : <h2>İhtiyacınıza göre bir paket.</h2>}<p>İhtiyacınız olan şube, öğrenci ve kullanıcı kapasitesini seçin.<br className="marketing-desktop-break" /> Döneminizi, fiyatınızı ve sınırlarınızı baştan görün.</p></div>
    <div className="marketing-period" aria-label="Paket dönemi"><button type="button" aria-pressed={months === 1} onClick={() => setMonths(1)}>Aylık</button><button type="button" aria-pressed={months === 12} onClick={() => setMonths(12)}>Yıllık</button></div>
    {loading ? <LoadingState label="Güncel paketler yükleniyor" /> : error ? <ErrorState message={error} retry={retry} /> : !plans.length ? <div className="marketing-empty"><span className="marketing-empty-icon"><Building2 size={27} /></span><h3>Paketler hazırlanıyor.</h3><p>Güncel satış paketleri tanımlandığında fiyatları ve kapasite sınırlarını burada görebileceksiniz.</p><Link to="/login">Mevcut kurum hesabınıza giriş yapın <ArrowUpRight size={16} /></Link></div> : !visible.length ? <div className="marketing-empty"><CalendarDays size={26} /><p>Bu dönem için satışa açık paket bulunmuyor. Diğer dönemdeki paketleri inceleyebilirsiniz.</p><button className="marketing-text-button" onClick={() => setMonths(months === 1 ? 12 : 1)}>Diğer dönemi göster <ArrowRight size={16} /></button></div> : <div className="marketing-plan-grid">{visible.map((plan) => <article className="marketing-plan" key={plan.id}><div className="marketing-plan-heading"><span className="marketing-kicker">{Number(plan.period_months) === 12 ? "YILLIK" : "AYLIK"} ÜYELİK</span><Building2 size={23} /></div><h3>{String(plan.name)}</h3><div className="marketing-price">{packagePrice(plan.price, plan.currency)}<span> / {Number(plan.period_months) === 12 ? "yıl" : "ay"}</span></div><p className="marketing-plan-caption">Kurumunuzun toplam kapasitesi</p>
      <ul><li><Check size={17} /><strong>{Number(plan.branch_limit).toLocaleString("tr-TR")} şube</strong></li><li><Check size={17} /><strong>{Number(plan.student_limit).toLocaleString("tr-TR")} öğrenci</strong></li><li><Check size={17} /><strong>{Number(plan.user_limit).toLocaleString("tr-TR")} kullanıcı hesabı</strong></li></ul>
      <Link className="marketing-primary" to={user ? user.is_super_admin ? "/platform" : `/subscription?paket=${plan.id}` : `/kayit?paket=${plan.id}`}>{user ? "Üyeliği yönet" : "Paketi seç"}<ArrowUpRight size={18} /></Link><span className="marketing-plan-access"><ShieldCheck size={15} />Rollere göre kurum erişimi</span>
    </article>)}</div>}
    <p className="marketing-price-note"><ShieldCheck size={15} />Gösterilen tutar seçtiğiniz dönemin paket fiyatıdır. Kurum erişimi, üyelik ödemeniz doğrulandığında açılır.</p>
  </section>;
}

const questions = [
  ["SCS360 kimler için?", "Okullar ve eğitim kurumları için ortak bir çalışma alanı sunar. Kurum sahibi, yöneticiler, öğretmenler ve veliler kendilerine tanımlanan yetkilerle işlem yapar."],
  ["Üyeliği nasıl başlatırım?", "Satışa açık paketlerden birini seçin, kurum ve sahip hesabını oluşturun. Üyelik ekranındaki ödeme talebini tamamlayın; ödeme doğrulandığında kurum çalışma alanınız açılır."],
  ["Şube ve kullanıcı sınırları nasıl işler?", "Paket sınırları kurumunuzun toplam şube, öğrenci ve giriş kullanıcı sayısı için geçerlidir. Sınıra ulaştığınızda yeni kayıt eklenmez; mevcut kayıtlarınız korunur. Daha geniş bir paket için üyeliğinizi yönetebilirsiniz."],
  ["Öğretmenler ve veliler aynı bilgileri mi görür?", "Her kullanıcı kendi rolüne ve atanmış erişimine göre çalışır. Veli alanında bağlı olduğu çocuğun bilgileri görünür. Kurum sahibi, kullanıcıların rol ve şube erişimlerini panelinden yönetir."],
  ["Üyelik süresi biterse ne olur?", "Süre bitiminde ekibiniz ödeme uyarısı görür. On günlük ek sürenin ardından üyelik yenilenene kadar çalışma alanı kapanır; kurum sahibi üyelik ve ödeme ekranına erişmeye devam eder."],
  ["Telefondan kullanabilir miyim?", "SCS360 web arayüzü mobil ekranlara uyum sağlar. Öğretmen ve veli alanlarına telefonunuzun tarayıcısından ulaşabilirsiniz."],
];

function Solutions() {
  return <section className="marketing-section marketing-solutions" id="cozumler" aria-label="SCS360 çözümleri">
    <div className="marketing-split-heading"><div><span className="marketing-kicker">BİRBİRİNE BAĞLI SÜREÇLER</span><h2>Okulun merkezinde eğitim.<br /><em>Etrafında SCS360.</em></h2></div><p>Sınıftan kurum yönetimine uzanan bilgiler aynı çalışma alanında buluşur. Ekibiniz kendi işine odaklanır; siz bütünü takip edersiniz.</p></div>
    <div className="marketing-solution-grid">
      <article className="marketing-solution marketing-solution-education"><span className="marketing-solution-number">01 / EĞİTİM</span><GraduationCap size={32} /><h3>Bir okul gününün<br />bütün parçaları.</h3><p>Yoklama, ödev, materyal ve karneler öğretmenlerin çalışma alanında; ilgili bilgiler velinin portalında.</p><div className="marketing-education-flow"><span><CalendarDays size={16} />Yoklama</span><span><BookOpen size={16} />Ödevler</span><span><CheckCheck size={16} />Karneler</span></div></article>
      <article className="marketing-solution marketing-solution-organization"><span className="marketing-solution-number">02 / KURUM YÖNETİMİ</span><Building2 size={30} /><h3>Şubeler ayrı.<br />Bakışınız bütün.</h3><p>Öğrenciler, veliler ve kullanıcılar kurumunuza bağlı kalır. Şube ve rol erişimleriyle ekibinize alan açın.</p><div className="marketing-mini-network" aria-hidden="true"><span>Okulunuz</span><div><i>Merkez</i><i>Şube</i><i>Ekip</i></div></div></article>
      <article className="marketing-solution marketing-solution-finance"><WalletCards size={27} /><span className="marketing-solution-number">03 / FİNANS</span><h3>Kayıttan tahsilata<br />finansal takip.</h3><p>Borç, ödeme ve makbuz geçmişini aynı yerden inceleyin. İşlemleri ekibinizin finans yetkileriyle yönetin.</p><span className="marketing-solution-line">Borç <ChevronRight size={14} />Tahsilat <ChevronRight size={14} />Makbuz</span></article>
      <article className="marketing-solution marketing-solution-communication"><MessageSquare size={27} /><span className="marketing-solution-number">04 / VELİ İLETİŞİMİ</span><h3>Okulla aile arasında<br />ortak bir alan.</h3><p>Duyurular, günlük raporlar, izin ve onaylar. Veli, bağlı olduğu çocuğun okul gününü kendi portalından takip eder.</p><span className="marketing-solution-line">Öğretmen <ChevronRight size={14} />Veli portalı</span></article>
      <article className="marketing-solution marketing-solution-operations"><HeartPulse size={27} /><span className="marketing-solution-number">05 / GÜNLÜK OPERASYON</span><h3>Günlük ayrıntılar<br />kayıt altında.</h3><p>Revirden öğrenci teslimine, envanterden servis kayıtlarına. Kurumun günlük süreçleri ilgili ekiplerin alanında.</p><span className="marketing-solution-line">Planlayın. Kaydedin. Takip edin.</span></article>
    </div>
  </section>;
}

function TrustAndSetup() {
  return <>
    <section className="marketing-trust" id="guven" aria-label="Erişim ve üyelik yaklaşımı"><div className="marketing-trust-inner"><div className="marketing-trust-copy"><span className="marketing-kicker">KURUMUNUZUN KONTROLÜ SİZDE</span><h2>Birlikte çalışın.<br /><em>Sınırları siz belirleyin.</em></h2><p>Ortak bir sistem, herkesin her şeyi görmesi anlamına gelmez. Kurumunuzun kullanıcılarını ve erişimlerini kendi panelinizden yönetirsiniz.</p><a className="marketing-light-link" href="#sorular">Merak ettiklerinizi inceleyin <ArrowUpRight size={17} /></a></div><div className="marketing-trust-points">
      <article><span><LockKeyhole size={23} /></span><div><h3>Rollere göre erişim</h3><p>Yönetici, öğretmen ve veli alanları tanımlanan izinlerle açılır. Veli bilgileri ilgili çocukla sınırlıdır.</p></div></article>
      <article><span><Layers3 size={23} /></span><div><h3>Kurum ve şube kapsamı</h3><p>Hesaplar kurumlarına bağlı çalışır. Personelin şube erişimini kurum sahibi yönetir.</p></div></article>
      <article><span><WalletCards size={23} /></span><div><h3>Görünür üyelik ve sınırlar</h3><p>Paket kapasitesi, üyelik dönemi ve ödeme talepleri panelinizde görünür. Kayıt sınırları kurum toplamına uygulanır.</p></div></article>
    </div></div></section>
    <section className="marketing-section marketing-how" id="nasil-calisir"><div className="marketing-split-heading"><div><span className="marketing-kicker">BAŞLAMAK İÇİN NET BİR YOL</span><h2>Okulunuz için<br />yeni bir çalışma düzeni.</h2></div><p>Paket seçiminizden ekibinizin ilk gününe kadar, sıradaki adımınız bellidir.</p></div><ol>
      <li><span className="marketing-step-number">01</span><div><h3>İhtiyacınızı seçin.</h3><p>Şube, öğrenci ve kullanıcı kapasitenizi karşılayan paketi ve üyelik dönemini inceleyin.</p><Link to="/fiyatlandirma">Paketleri karşılaştırın <ArrowUpRight size={16} /></Link></div></li>
      <li><span className="marketing-step-number">02</span><div><h3>Kurum hesabınızı açın.</h3><p>Kurum sahibi hesabınızı oluşturun. Üyelik ekranındaki ödeme adımlarını tamamlayın.</p><span className="marketing-step-caption">Çalışma alanı ödeme doğrulanınca açılır.</span></div></li>
      <li><span className="marketing-step-number">03</span><div><h3>Ekibinizle başlayın.</h3><p>Şubeleri, öğrencileri ve kullanıcıları ekleyin. Öğretmen ve veli hesaplarının erişimlerini tanımlayın.</p><span className="marketing-step-caption">Her kullanıcı kendi çalışma alanına ulaşır.</span></div></li>
    </ol></section>
  </>;
}

export function MarketingPage({ pricing = false }: { pricing?: boolean }) {
  return <PublicLayout title={pricing ? "Paketler ve fiyatlandırma" : "Okulunuzun ortak çalışma alanı"}>
    {!pricing && <>
      <section className="marketing-hero"><div className="marketing-hero-copy"><span className="marketing-hero-badge"><span />OKUL VE KURUM YÖNETİMİ, BİR ARADA</span><h1>Eğitimde <br />bütün resmi <br /><em>görün.</em></h1><p>Okulunuzun her günü, tek bir yerde. Öğrencilerden şubelere, öğretmenlerden velilere; SCS360 ile ekibinizin işini birbirine bağlayın.</p><div className="marketing-hero-actions"><Link className="marketing-primary" to="/fiyatlandirma">Paketleri keşfedin<ArrowUpRight size={18} /></Link><a className="marketing-secondary" href="#urun">Ürün turunu keşfedin<ArrowDownRight size={18} /></a></div><div className="marketing-proof"><span><Check size={15} />Rollere göre erişim</span><span><Check size={15} />Çok şubeli yönetim</span><span><Check size={15} />Mobil uyumlu web</span></div></div><CampusVisual /></section>
      <section className="marketing-connect-strip" aria-label="Ortak çalışma alanları"><div><span className="marketing-kicker">AYNI OKUL GÜNÜ.<br />ORTAK BİR BAKIŞ.</span></div><span><Building2 size={21} />Kurum yönetimi</span><i aria-hidden="true" /><span><GraduationCap size={22} />Öğretmen</span><i aria-hidden="true" /><span><Users size={21} />Veli</span><p>Herkes kendi alanında.<br /><strong>Bilgi aynı sistemde.</strong></p></section>
      <section className="marketing-section marketing-product-story"><div><span className="marketing-kicker">BİLGİDEN GÜNLÜK AKIŞA</span><h2>Her süreç için<br /><em>doğru çalışma alanı.</em></h2><p>Kurum, eğitim ve finans alanları arasındaki bağlantıyı keşfedin. Temsili turdaki sekmelerle SCS360 yaklaşımını yakından inceleyin.</p><ul><li><Check size={16} />Kurum ve şubeler birlikte.</li><li><Check size={16} />Öğretmen ve veli kendi alanında.</li><li><Check size={16} />Kayıtlar ilgili süreçle bağlantılı.</li></ul><Link className="marketing-secondary" to="/hakkimizda">SCS360'ı tanıyın <ArrowUpRight size={17} /></Link></div><ProductTour /></section>
      <Solutions /><TrustAndSetup />
    </>}
    <PublicPricing standalone={pricing} />
    <section className="marketing-faq marketing-section" id="sorular"><div><span className="marketing-kicker">AKLINIZDA SORU KALMASIN</span><h2>Birlikte başlamadan<br />önce.</h2><p>Üyelik, erişim ve günlük kullanım hakkında merak ettikleriniz.</p></div><div>{questions.map(([question, answer]) => <details key={question}><summary>{question}<span>+</span></summary><p>{answer}</p></details>)}</div></section>
    <section className="marketing-final"><div className="marketing-final-orbit" aria-hidden="true" /><div><span className="marketing-kicker">OKULUNUZUN BİR SONRAKİ ADIMI</span><h2>Daha net bir okul günü.<br /><em>Birlikte başlayalım.</em></h2><p>Kurumunuza uygun kapasiteyi seçin, çalışma alanınızı oluşturun.</p></div>{pricing ? <a className="marketing-primary" href="#paketler">Paketleri yeniden incele<ArrowUpRight size={18} /></a> : <Link className="marketing-primary" to="/fiyatlandirma">Size uygun paketi bulun<ArrowUpRight size={18} /></Link>}</section>
  </PublicLayout>;
}
