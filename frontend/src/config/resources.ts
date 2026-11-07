import type { ResourceConfig } from "../types/api";

const activeOptions = [{ label: "Aktif", value: "ACTIVE" }, { label: "Pasif", value: "PASSIVE" }];
const orgField = { name: "organization_id", label: "Kurum", type: "select" as const, optionSource: "/organizations", optionLabel: "name", required: true, hideOnEdit: true };
const branchField = { name: "branch_id", label: "Şube", type: "select" as const, optionSource: "/branches", optionLabel: "name", required: true };

export const resources: Record<string, ResourceConfig> = {
  organizations: {
    key: "organizations", title: "Kurumlar", singular: "Kurum", description: "Franchise ve eğitim kurumlarının kurumsal bilgilerini yönetin.", endpoint: "/organizations", permissionRead: "org.read", permissionWrite: "org.write",
    columns: [{ key: "name", label: "Kurum", type: "text", subKey: "legal_name" }, { key: "city", label: "Şehir" }, { key: "phone", label: "Telefon" }, { key: "email", label: "E-posta" }, { key: "is_active", label: "Durum", type: "status" }],
    fields: [{ name: "name", label: "Kurum adı", required: true }, { name: "legal_name", label: "Ticari unvan" }, { name: "tax_number", label: "Vergi numarası" }, { name: "tax_office", label: "Vergi dairesi" }, { name: "country", label: "Ülke", required: true, defaultValue: "Türkiye" }, { name: "phone", label: "Telefon" }, { name: "email", label: "E-posta", type: "email" }, { name: "city", label: "Şehir" }, { name: "address", label: "Adres", type: "textarea", full: true }], detailPath: "/organizations",
  },
  branches: {
    key: "branches", title: "Şubeler", singular: "Şube", description: "Şube kapasitesini, iletişim bilgilerini ve çalışma durumunu izleyin.", endpoint: "/branches", permissionRead: "branch.read", permissionWrite: "branch.write",
    columns: [{ key: "name", label: "Şube", subKey: "code" }, { key: "city", label: "Şehir" }, { key: "phone", label: "Telefon" }, { key: "capacity", label: "Kapasite", type: "capacity" }, { key: "is_active", label: "Durum", type: "status" }],
    fields: [orgField, { name: "name", label: "Şube adı", required: true }, { name: "code", label: "Şube kodu" }, { name: "capacity", label: "Kapasite", type: "number", min: 0, step: 1, defaultValue: 0, required: true }, { name: "phone", label: "Telefon" }, { name: "email", label: "E-posta", type: "email" }, { name: "city", label: "Şehir" }, { name: "address", label: "Adres", type: "textarea", full: true }, { name: "is_active", label: "Şube aktif", type: "checkbox", defaultValue: true }], detailPath: "/branches",
  },
  users: {
    key: "users", title: "Kullanıcılar", singular: "Kullanıcı", description: "Ekip üyelerinin hesaplarını, erişimini ve çalışma durumunu yönetin.", endpoint: "/users", permissionRead: "user.read", permissionWrite: "user.write",
    columns: [{ key: "first_name", label: "Kullanıcı", type: "person", subKey: "last_name" }, { key: "email", label: "E-posta" }, { key: "phone", label: "Telefon" }, { key: "roles", label: "Rol", type: "roles" }, { key: "status", label: "Durum", type: "status" }],
    fields: [{ name: "first_name", label: "Ad", required: true }, { name: "last_name", label: "Soyad", required: true }, { name: "email", label: "E-posta", type: "email", required: true }, { name: "phone", label: "Telefon" }, { ...orgField, required: false }, { name: "password", label: "Geçici şifre", type: "password", required: true, hideOnEdit: true }, { name: "status", label: "Durum", type: "select", options: [...activeOptions, { label: "Bloke", value: "BLOCKED" }] }], detailPath: "/users",
  },
  students: {
    key: "students", title: "Öğrenciler", singular: "Öğrenci", description: "Öğrenci kayıtlarını, sınıf ilişkilerini ve durumlarını tek listede yönetin.", endpoint: "/students", permissionRead: "students.read", permissionWrite: "students.write",
    columns: [{ key: "first_name", label: "Öğrenci", type: "person", subKey: "last_name" }, { key: "student_number", label: "Öğrenci no" }, { key: "date_of_birth", label: "Doğum tarihi", type: "date" }, { key: "enrollment_date", label: "Kayıt tarihi", type: "date" }, { key: "status", label: "Durum", type: "status" }],
    fields: [{ ...orgField, optionSource: "/students/organization-options", searchable: true }, { ...branchField, optionSource: "/students/branch-options", searchable: true }, { name: "class_id", label: "Sınıf", type: "select", optionSource: "/students/class-options", optionLabel: "name", searchable: true }, { name: "first_name", label: "Ad", required: true }, { name: "last_name", label: "Soyad", required: true }, { name: "date_of_birth", label: "Doğum tarihi", type: "date" }, { name: "gender", label: "Cinsiyet", type: "select", options: [{ label: "Kız", value: "FEMALE" }, { label: "Erkek", value: "MALE" }, { label: "Diğer", value: "OTHER" }] }, { name: "enrollment_date", label: "Kayıt tarihi", type: "date", required: true }, { name: "status", label: "Durum", type: "select", options: [{ label: "Aktif", value: "ACTIVE" }, { label: "Pasif", value: "PASSIVE" }, { label: "Mezun", value: "GRADUATED" }, { label: "Ayrıldı", value: "LEFT" }], defaultValue: "ACTIVE" }, { name: "address", label: "Adres", type: "textarea", full: true }, { name: "notes", label: "Notlar", type: "textarea", full: true }], detailPath: "/students",
  },
  parents: {
    key: "parents", title: "Veliler", singular: "Veli", description: "İletişim izinleriyle birlikte veli kayıtlarını güvenle yönetin.", endpoint: "/parents", permissionRead: "parents.read", permissionWrite: "parents.write",
    columns: [{ key: "first_name", label: "Veli", type: "person", subKey: "last_name" }, { key: "relation_type", label: "Yakınlık" }, { key: "phone", label: "Telefon" }, { key: "email", label: "E-posta" }, { key: "status", label: "Durum", type: "status" }],
    fields: [orgField, { name: "first_name", label: "Ad", required: true }, { name: "last_name", label: "Soyad", required: true }, { name: "relation_type", label: "Yakınlık", type: "select", options: [{ label: "Anne", value: "MOTHER" }, { label: "Baba", value: "FATHER" }, { label: "Vasi", value: "GUARDIAN" }, { label: "Diğer", value: "OTHER" }] }, { name: "phone", label: "Telefon" }, { name: "email", label: "E-posta", type: "email" }, { name: "address", label: "Adres", type: "textarea", full: true }, { name: "sms_phone", label: "SMS telefonu" }, { name: "whatsapp_phone", label: "WhatsApp telefonu" }, { name: "receive_notifications", label: "Bildirim almayı kabul ediyor", type: "checkbox", defaultValue: true }], detailPath: "/parents",
  },
  classes: {
    key: "classes", title: "Sınıflar", singular: "Sınıf", description: "Kontenjanı, öğretmenleri ve öğrenci dağılımını sınıf bazında izleyin.", endpoint: "/classes", permissionRead: "class.read", permissionWrite: "class.write",
    columns: [{ key: "name", label: "Sınıf", subKey: "code" }, { key: "academic_year", label: "Dönem" }, { key: "capacity", label: "Kapasite", type: "capacity" }, { key: "teacher_name", label: "Öğretmen" }, { key: "is_active", label: "Durum", type: "status" }],
    fields: [orgField, { ...branchField, hideOnEdit: true }, { name: "name", label: "Sınıf adı", required: true }, { name: "code", label: "Sınıf kodu", required: true }, { name: "capacity", label: "Kontenjan", type: "number", min: 1, step: 1, required: true }, { name: "academic_year", label: "Akademik yıl", placeholder: "2026-2027" }, { name: "teacher_id", label: "Öğretmen", type: "select", optionSource: "/classes/teacher-options", optionLabel: "name", searchable: true }, { name: "is_active", label: "Sınıf aktif", type: "checkbox", defaultValue: true }], detailPath: "/classes",
  },
  debts: {
    key: "debts", title: "Borçlar", singular: "Borç", description: "Öğrenci borçlarını, vadeleri ve kalan tutarları takip edin.", endpoint: "/debts", permissionRead: "finance.read", permissionWrite: "finance.write",
    columns: [{ key: "student_name", label: "Öğrenci", subKey: "student_id" }, { key: "parent_name", label: "Veli", subKey: "parent_phone" }, { key: "debt_type", label: "Borç türü" }, { key: "amount", label: "Tutar", type: "money" }, { key: "remaining_amount", label: "Kalan", type: "money" }, { key: "due_date", label: "Vade", type: "date" }, { key: "status", label: "Durum", type: "status" }],
    fields: [{ name: "student_id", label: "Öğrenci", type: "select", optionSource: "/debts/student-options", optionLabel: "name", required: true, searchable: true, hideOnEdit: true }, { name: "debt_type", label: "Borç türü", type: "select", required: true, hideOnEdit: true, options: [{ label: "Eğitim", value: "EDUCATION" }, { label: "Yemek", value: "FOOD" }, { label: "Servis", value: "SERVICE" }, { label: "Kırtasiye", value: "STATIONERY" }, { label: "Etkinlik", value: "ACTIVITY" }, { label: "Diğer", value: "OTHER" }] }, { name: "amount", label: "Tutar", type: "number", min: 0.01, required: true }, { name: "due_date", label: "Vade tarihi", type: "date", required: true }, { name: "description", label: "Açıklama", type: "textarea", full: true }], detailPath: "/finance/debts",
  },
  libraryBooks: {
    key: "libraryBooks", title: "Kütüphane", singular: "Kitap", description: "Kitap bilgileri ve stok durumu.",
    endpoint: "/library/books", permissionRead: "library.read", permissionWrite: "library.write", detailPath: "/library/books", listPath: "/library",
    columns: [{ key: "title", label: "Kitap" }, { key: "author", label: "Yazar" }, { key: "available_copies", label: "Mevcut kopya" }],
    fields: [{ name: "title", label: "Kitap adı", required: true }, { name: "author", label: "Yazar", required: true },
      { name: "category", label: "Kategori", required: true }, { name: "isbn", label: "ISBN" },
      { name: "total_copies", label: "Toplam kopya", type: "number", min: 1, defaultValue: 1, required: true }],
  },
  expenses: {
    key: "expenses", title: "Giderler", singular: "Gider", description: "Gider bilgileri.", endpoint: "/finance/expenses",
    permissionRead: "finance.read", permissionWrite: "finance.write", detailPath: "/finance/expenses",
    columns: [{ key: "description", label: "Açıklama" }, { key: "amount", label: "Tutar", type: "money" }],
    fields: [{ name: "description", label: "Açıklama", required: true }, { name: "category", label: "Kategori", required: true },
      { name: "amount", label: "Tutar", type: "number", min: 0.01, required: true },
      { name: "expense_date", label: "Tarih", type: "date" }, { name: "notes", label: "Notlar", type: "textarea" }],
  },
  notificationJobs: {
    key: "notificationJobs", title: "Bildirimler", singular: "Bildirim", description: "Gönderim durumu ve alıcılar.", endpoint: "/notifications",
    permissionRead: "notification.read", detailPath: "/notifications",
    columns: [{ key: "channel", label: "Kanal" }, { key: "status", label: "Durum" }], fields: [],
  },
  // Parent-specific resources
  myChildren: {
    key: "myChildren", title: "Çocuklarım", singular: "Çocuk", description: "Çocuklarınızın bilgilerini ve durumlarını görüntüleyin.", endpoint: "/students", permissionRead: "student.read", permissionWrite: undefined,
    columns: [{ key: "first_name", label: "Çocuk", type: "person", subKey: "last_name" }, { key: "student_number", label: "Öğrenci no" }, { key: "date_of_birth", label: "Doğum tarihi", type: "date" }, { key: "enrollment_date", label: "Kayıt tarihi", type: "date" }, { key: "status", label: "Durum", type: "status" }],
    fields: [], detailPath: "/students", parentOnly: true,
  },
  myChildrenDebts: {
    key: "myChildrenDebts", title: "Borçlarım", singular: "Borç", description: "Çocuklarınızın borçlarını ve ödemelerini görüntüleyin.", endpoint: "/debts", permissionRead: "finance.read", permissionWrite: undefined,
    columns: [{ key: "student_name", label: "Çocuk", subKey: "student_id" }, { key: "debt_type", label: "Borç türü" }, { key: "amount", label: "Tutar", type: "money" }, { key: "remaining_amount", label: "Kalan", type: "money" }, { key: "due_date", label: "Vade", type: "date" }, { key: "status", label: "Durum", type: "status" }],
    fields: [], detailPath: "/finance/debts", parentOnly: true,
  },
  myChildrenAttendance: {
    key: "myChildrenAttendance", title: "Devamsızlık", singular: "Devamsızlık", description: "Çocuklarınızın devamsızlık durumlarını görüntüleyin.", endpoint: "/attendance", permissionRead: "attendance.read", permissionWrite: undefined,
    columns: [{ key: "student_name", label: "Çocuk" }, { key: "attendance_date", label: "Tarih", type: "date" }, { key: "status", label: "Durum" }],
    fields: [], detailPath: "/attendance", parentOnly: true,
  },
};
