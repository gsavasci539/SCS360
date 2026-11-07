import { GraduationCap } from "lucide-react";

export function CampusVisual({ about = false }: { about?: boolean }) {
  return <figure className={`marketing-campus${about ? " marketing-campus-about" : ""}`}>
    <picture><source srcSet="/images/scs360-education-campus-v1.webp" type="image/webp" /><img src="/images/scs360-education-campus-v1.png" width={1536} height={1024}
      alt="Öğrencilerin, öğretmenlerin ve ailelerin bir araya geldiği eğitim kampüsü illüstrasyonu"
      loading="eager" decoding="async" fetchPriority={about ? "auto" : "high"} /></picture>
    <figcaption><span><GraduationCap size={21} /><strong>Eğitimin etrafında,<br />birlikte.</strong></span><small>Temsili eğitim kampüsü illüstrasyonu.</small></figcaption>
  </figure>;
}
