import { ArrowRight, ArrowUpRight, Building2, Check, GraduationCap, Layers3, LockKeyhole, Users } from "lucide-react";
import { Link } from "react-router-dom";
import { CampusVisual } from "./CampusVisual";
import { PublicLayout } from "./MarketingSite";

const roles = [
  { name: "Kurum sahibi", icon: Building2, copy: "Kurumunun üyeliğini, şubelerini ve kullanıcı erişimlerini yönetir." },
  { name: "Yönetici", icon: Layers3, copy: "Tanımlanan rol ve şube erişimiyle okulun günlük süreçlerini takip eder." },
  { name: "Öğretmen", icon: GraduationCap, copy: "Yetkili olduğu öğrencilerin yoklama, ödev ve eğitim kayıtlarıyla çalışır." },
  { name: "Veli", icon: Users, copy: "Bağlı olduğu çocuğun ilgili bilgilerine kendi portalından ulaşır." },
];

export function AboutPage() {
  return <PublicLayout title="Hakkımızda">
    <section className="marketing-about-hero marketing-section"><div><span className="marketing-kicker">HAKKIMIZDA / SCS360</span><h1>Eğitimin etrafında<br /><em>birlikte.</em></h1><p className="marketing-about-lead">Bir okul günü, birbirine bağlı pek çok insanın emeğiyle şekillenir.</p><p>SCS360; kurum sahiplerini, yöneticileri, öğretmenleri ve velileri ortak bir dijital çalışma alanında buluşturan okul ve kurum yönetim platformudur.</p><p>Amacımız, eğitimle ilgili günlük kayıtların ve işlemlerin ilgili kişilerin çalışma alanında bir araya gelmesine yardımcı olmaktır.</p><a className="marketing-secondary" href="#yaklasim">Yaklaşımımızı keşfedin <ArrowRight size={18} /></a></div><CampusVisual about /></section>
    <section className="marketing-about-purpose" id="yaklasim"><div className="marketing-section"><span className="marketing-kicker">BİRLİKTE ÇALIŞMAYI KOLAYLAŞTIRMAK İÇİN</span><h2>Her okul gününü<br /><em>birbirine bağlamak.</em></h2><div><p>Bir öğrenci kaydı, sınıf yoklaması, veliye sunulan bir karne veya tahsilat makbuzu. Her biri okul yaşamının bir parçası.</p><p>SCS360 bu süreçleri kurum, şube ve kullanıcı ilişkileri içinde ele alır. Ekipler kendi yetkileriyle çalışırken, bilgi aynı sistemin içinde takip edilir.</p></div></div></section>
    <section className="marketing-section marketing-about-principles" aria-label="Ürüne yaklaşımımız"><div className="marketing-split-heading"><div><span className="marketing-kicker">ÜRÜNÜN TEMELİNDE</span><h2>Ortak bir alan.<br /><em>Net bir yaklaşım.</em></h2></div><p>Birlikte çalışmanın, erişimin ve üyeliğin sınırlarını görünür kılan bir çalışma düzeni.</p></div><div className="marketing-about-principle-grid">
      <article><span>01</span><LockKeyhole size={25} /><h3>İlgili bilgi, ilgili kişide.</h3><p>Kullanıcılar, kendilerine tanımlanan rol ve erişimlerle çalışır. Ortak bir sistemde bulunmak, herkese aynı yetkiyi vermez.</p></article>
      <article><span>02</span><Layers3 size={25} /><h3>Kurumun bütünü bir arada.</h3><p>Şubeler, kullanıcılar, öğrenci ve veli ilişkileri kurumun yapısı içinde yönetilir. Yetkiler bu kapsama göre uygulanır.</p></article>
      <article><span>03</span><Check size={25} /><h3>Üyelikte görünür sınırlar.</h3><p>Paketin şube, öğrenci ve kullanıcı kapasitesi baştan görünür. Kurum sahibi üyelik dönemini ve ödeme taleplerini panelinden takip eder.</p></article>
    </div></section>
    <section className="marketing-about-people"><div className="marketing-section"><div className="marketing-split-heading"><div><span className="marketing-kicker">HERKES KENDİ ALANINDA</span><h2>Aynı okulun<br /><em>farklı bakışları.</em></h2></div><p>Günlük akışta herkesin sorumluluğu farklıdır. SCS360, bu farklı rolleri birbirine bağlı çalışma alanlarında bir araya getirir.</p></div><div className="marketing-about-role-grid">{roles.map((role) => <article key={role.name}><role.icon size={25} /><h3>{role.name}</h3><p>{role.copy}</p></article>)}</div></div></section>
    <section className="marketing-section marketing-about-discover"><div><span className="marketing-kicker">YAKINDAN TANIYIN</span><h2>SCS360 okulunuzda<br />nasıl yer alabilir?</h2><p>Çözümleri ve temsili ürün turunu inceleyin. Ardından kurumunuzun kapasitesine uygun gerçek paketleri karşılaştırın.</p></div><div><Link to="/#urun" className="marketing-about-discover-link"><span><strong>Ürün turunu keşfedin</strong><small>Kurum, eğitim ve finans alanları.</small></span><ArrowUpRight size={21} /></Link><Link to="/fiyatlandirma" className="marketing-about-discover-link"><span><strong>Paketleri inceleyin</strong><small>Şube, öğrenci, kullanıcı ve dönem seçimi.</small></span><ArrowUpRight size={21} /></Link></div></section>
    <section className="marketing-final"><div className="marketing-final-orbit" aria-hidden="true" /><div><span className="marketing-kicker">OKULUNUZ İÇİN ORTAK BİR ALAN</span><h2>Bir sonraki okul gününe<br /><em>birlikte başlayalım.</em></h2><p>Kurumunuza uygun paketi seçin, çalışma alanınızı oluşturun.</p></div><Link className="marketing-primary" to="/fiyatlandirma">Size uygun paketi bulun <ArrowUpRight size={18} /></Link></section>
  </PublicLayout>;
}
