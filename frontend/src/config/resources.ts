import type { ResourceConfig } from "../types/api";

const activeOptions = [{ label: "Aktif", value: "ACTIVE" }, { label: "Pasif", value: "PASSIVE" }];
const orgField = { name: "organization_id", label: "Kurum", type: "select" as const, optionSource: "/organizations", optionLabel: "name", required: true };
const branchField = { name: "branch_id", label: "Şube", type: "select" as const, optionSource: "/branches", optionLabel: "name", required: true };

export const resources: Record<string, ResourceConfig> = {
  organizations: {
    key: "organizations", title: "Kurumlar", singular: "Kurum", description: "Franchise ve eğitim kurumlarının kurumsal bilgilerini yönetin.", endpoint: "/organizations", permissionRead: "org.read", permissionWrite: "org.write",
    columns: [{ key: "name", label: "Kurum", type: "text", subKey: "legal_name" }, { key: "city", label: "Şehir" }, { key: "phone", label: "Telefon" }, { key: "email", label: "E-posta" }, { key: "is_active", label: "Durum", type: "status" }],
    fields: [{ name: "name", label: "Kurum adı", required: true }, { name: "legal_name", label: "Ticari unvan" }, { name: "tax_number", label: "Vergi numarası" }, { name: "phone", label: "Telefon" }, { name: "email", label: "E-posta", type: "email" }, { name: "city", label: "Şehir" }, { name: "address", label: "Adres", type: "textarea", full: true }], detailPath: "/organizations",
  },
  branches: {
    key: "branches", title: "Şubeler", singular: "Şube", description: "Şube kapasitesini, iletişim bilgilerini ve çalışma durumunu izleyin.", endpoint: "/branches", permissionRead: "branch.read", permissionWrite: "branch.write",
    columns: [{ key: "name", label: "Şube", subKey: "code" }, { key: "city", label: "Şehir" }, { key: "phone", label: "Telefon" }, { key: "capacity", label: "Kapasite", type: "capacity" }, { key: "is_active", label: "Durum", type: "status" }],
    fields: [orgField, { name: "name", label: "Şube adı", required: true }, { name: "code", label: "Şube kodu", required: true }, { name: "capacity", label: "Kapasite", type: "number", min: 1 }, { name: "phone", label: "Telefon" }, { name: "email", label: "E-posta", type: "email" }, { name: "city", label: "Şehir" }, { name: "address", label: "Adres", type: "textarea", full: true }], detailPath: "/branches",
  },
  users: {
    key: "users", title: "Kullanıcılar", singular: "Kullanıcı", description: "Ekip üyelerinin hesaplarını, erişimini ve çalışma durumunu yönetin.", endpoint: "/users", permissionRead: "user.read", permissionWrite: "user.write",
    columns: [{ key: "first_name", label: "Kullanıcı", type: "person", subKey: "last_name" }, { key: "email", label: "E-posta" }, { key: "phone", label: "Telefon" }, { key: "roles", label: "Rol", type: "roles" }, { key: "status", label: "Durum", type: "status" }],
    fields: [{ name: "first_name", label: "Ad", required: true }, { name: "last_name", label: "Soyad", required: true }, { name: "email", label: "E-posta", type: "email", required: true }, { name: "phone", label: "Telefon" }, { ...orgField, required: false }, { name: "password", label: "Geçici şifre", type: "password", required: true, hideOnEdit: true }, { name: "status", label: "Durum", type: "select", options: [...activeOptions, { label: "Bloke", value: "BLOCKED" }] }], detailPath: "/users",
  },
  students: {
    key: "students", title: "Öğrenciler", singular: "Öğrenci", description: "Öğrenci kayıtlarını, sınıf ilişkilerini ve durumlarını tek listede yönetin.", endpoint: "/students", permissionRead: "students.read", permissionWrite: "students.write",
    columns: [{ key: "first_name", label: "Öğrenci", type: "person", subKey: "last_name" }, { key: "student_number", label: "Öğrenci no" }, { key: "date_of_birth", label: "Doğum tarihi", type: "date" }, { key: "enrollment_date", label: "Kayıt tarihi", type: "date" }, { key: "status", label: "Durum", type: "status" }],
    fields: [orgField, branchField, { name: "class_id", label: "Sınıf", type: "select", optionSource: "/classes", optionLabel: "name" }, { name: "first_name", label: "Ad", required: true }, { name: "last_name", label: "Soyad", required: true }, { name: "date_of_birth", label: "Doğum tarihi", type: "date" }, { name: "gender", label: "Cinsiyet", type: "select", options: [{ label: "Kız", value: "FEMALE" }, { label: "Erkek", value: "MALE" }, { label: "Diğer", value: "OTHER" }] }, { name: "enrollment_date", label: "Kayıt tarihi", type: "date", required: true }, { name: "status", label: "Durum", type: "select", options: [{ label: "Aktif", value: "ACTIVE" }, { label: "Pasif", value: "PASSIVE" }, { label: "Mezun", value: "GRADUATED" }, { label: "Ayrıldı", value: "LEFT" }], defaultValue: "ACTIVE" }, { name: "address", label: "Adres", type: "textarea", full: true }, { name: "notes", label: "Notlar", type: "textarea", full: true }], detailPath: "/students",
  },
  parents: {
    key: "parents", title: "Veliler", singular: "Veli", description: "İletişim izinleriyle birlikte veli kayıtlarını güvenle yönetin.", endpoint: "/parents", permissionRead: "student.read", permissionWrite: "student.write",
    columns: [{ key: "first_name", label: "Veli", type: "person", subKey: "last_name" }, { key: "relationship", label: "Yakınlık" }, { key: "phone", label: "Telefon" }, { key: "email", label: "E-posta" }, { key: "status", label: "Durum", type: "status" }],
    fields: [orgField, { name: "first_name", label: "Ad", required: true }, { name: "last_name", label: "Soyad", required: true }, { name: "relationship", label: "Yakınlık", type: "select", options: [{ label: "Anne", value: "MOTHER" }, { label: "Baba", value: "FATHER" }, { label: "Vasi", value: "GUARDIAN" }, { label: "Diğer", value: "OTHER" }] }, { name: "phone", label: "Telefon", required: true }, { name: "email", label: "E-posta", type: "email" }, { name: "address", label: "Adres", type: "textarea", full: true }, { name: "notification_email", label: "E-posta bildirimi", type: "checkbox", defaultValue: true }, { name: "notification_sms", label: "SMS bildirimi", type: "checkbox" }, { name: "notification_whatsapp", label: "WhatsApp bildirimi", type: "checkbox" }], detailPath: "/parents",
  },
  classes: {
    key: "classes", title: "Sınıflar", singular: "Sınıf", description: "Kontenjanı, öğretmenleri ve öğrenci dağılımını sınıf bazında izleyin.", endpoint: "/classes", permissionRead: "class.read", permissionWrite: "class.write",
    columns: [{ key: "name", label: "Sınıf", subKey: "code" }, { key: "academic_year", label: "Dönem" }, { key: "capacity", label: "Kapasite", type: "capacity" }, { key: "teacher_name", label: "Öğretmen" }, { key: "status", label: "Durum", type: "status" }],
    fields: [orgField, branchField, { name: "name", label: "Sınıf adı", required: true }, { name: "code", label: "Sınıf kodu", required: true }, { name: "capacity", label: "Kontenjan", type: "number", min: 1, required: true }, { name: "academic_year", label: "Akademik yıl", placeholder: "2026-2027" }, { name: "teacher_id", label: "Öğretmen", type: "select", optionSource: "/users", optionLabel: "first_name" }, { name: "status", label: "Durum", type: "select", options: activeOptions, defaultValue: "ACTIVE" }], detailPath: "/classes",
  },
  debts: {
    key: "debts", title: "Borçlar", singular: "Borç", description: "Öğrenci borçlarını, vadeleri ve kalan tutarları takip edin.", endpoint: "/debts", permissionRead: "finance.read", permissionWrite: "finance.write",
    columns: [{ key: "student_name", label: "Öğrenci", subKey: "student_id" }, { key: "debt_type", label: "Borç türü" }, { key: "amount", label: "Tutar", type: "money" }, { key: "remaining_amount", label: "Kalan", type: "money" }, { key: "due_date", label: "Vade", type: "date" }, { key: "status", label: "Durum", type: "status" }],
    fields: [orgField, branchField, { name: "student_id", label: "Öğrenci", type: "select", optionSource: "/students", optionLabel: "first_name", required: true }, { name: "debt_type", label: "Borç türü", type: "select", required: true, options: [{ label: "Eğitim", value: "EDUCATION" }, { label: "Yemek", value: "FOOD" }, { label: "Servis", value: "SERVICE" }, { label: "Kırtasiye", value: "STATIONERY" }, { label: "Etkinlik", value: "ACTIVITY" }, { label: "Diğer", value: "OTHER" }] }, { name: "amount", label: "Tutar", type: "number", min: 1, required: true }, { name: "due_date", label: "Vade tarihi", type: "date", required: true }, { name: "academic_year", label: "Akademik yıl" }, { name: "description", label: "Açıklama", type: "textarea", full: true }], detailPath: "/finance/debts",
  },
};
