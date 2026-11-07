-- SCS360 Seed Data
-- Password hash for Admin123* will be set by seed_demo_data.py

INSERT OR IGNORE INTO permissions (id, code, name, module) VALUES
    ('f0000000-0000-4000-8000-000000000001', 'org.read', 'Kurum Görüntüle', 'organizations'),
    ('f0000000-0000-4000-8000-000000000002', 'org.write', 'Kurum Yönet', 'organizations'),
    ('f0000000-0000-4000-8000-000000000003', 'branch.read', 'Şube Görüntüle', 'branches'),
    ('f0000000-0000-4000-8000-000000000004', 'branch.write', 'Şube Yönet', 'branches'),
    ('f0000000-0000-4000-8000-000000000005', 'user.read', 'Kullanıcı Görüntüle', 'users'),
    ('f0000000-0000-4000-8000-000000000006', 'user.write', 'Kullanıcı Yönet', 'users'),
    ('f0000000-0000-4000-8000-000000000007', 'student.read', 'Öğrenci Görüntüle', 'students'),
    ('f0000000-0000-4000-8000-000000000008', 'student.write', 'Öğrenci Yönet', 'students'),
    ('f0000000-0000-4000-8000-000000000009', 'class.read', 'Sınıf Görüntüle', 'classes'),
    ('f0000000-0000-4000-8000-00000000000a', 'class.write', 'Sınıf Yönet', 'classes'),
    ('f0000000-0000-4000-8000-00000000000b', 'attendance.read', 'Devamsızlık Görüntüle', 'attendance'),
    ('f0000000-0000-4000-8000-00000000000c', 'attendance.write', 'Devamsızlık Yönet', 'attendance'),
    ('f0000000-0000-4000-8000-00000000000d', 'finance.read', 'Finans Görüntüle', 'finance'),
    ('f0000000-0000-4000-8000-00000000000e', 'finance.write', 'Finans Yönet', 'finance'),
    ('f0000000-0000-4000-8000-00000000000f', 'receipt.read', 'Makbuz Görüntüle', 'receipts'),
    ('f0000000-0000-4000-8000-000000000010', 'receipt.write', 'Makbuz Oluştur', 'receipts'),
    ('f0000000-0000-4000-8000-000000000011', 'announcement.read', 'Duyuru Görüntüle', 'announcements'),
    ('f0000000-0000-4000-8000-000000000012', 'announcement.write', 'Duyuru Yönet', 'announcements'),
    ('f0000000-0000-4000-8000-000000000013', 'notification.read', 'Bildirim Görüntüle', 'notifications'),
    ('f0000000-0000-4000-8000-000000000014', 'notification.write', 'Bildirim Gönder', 'notifications'),
    ('f0000000-0000-4000-8000-000000000015', 'report.read', 'Rapor Görüntüle', 'reports'),
    ('f0000000-0000-4000-8000-000000000016', 'settings.read', 'Ayar Görüntüle', 'settings'),
    ('f0000000-0000-4000-8000-000000000017', 'settings.write', 'Ayar Yönet', 'settings'),
    ('f0000000-0000-4000-8000-000000000018', 'dashboard.read', 'Dashboard Görüntüle', 'dashboard'),
    ('f0000000-0000-4000-8000-000000000019', 'canteen.read', 'Kantin Görüntüle', 'canteen'),
    ('f0000000-0000-4000-8000-00000000001a', 'canteen.write', 'Kantin Yönet', 'canteen'),
    ('f0000000-0000-4000-8000-00000000001b', 'parent.view_children', 'Çocukları Görüntüle', 'parent'),
    ('f0000000-0000-4000-8000-00000000001c', 'parent.view_attendance', 'Devamsızlık Görüntüle', 'parent'),
    ('f0000000-0000-4000-8000-00000000001d', 'parent.view_finances', 'Ödemeler Görüntüle', 'parent'),
    ('f0000000-0000-4000-8000-00000000001e', 'health.read', 'Sağlık Görüntüle', 'health'),
    ('f0000000-0000-4000-8000-00000000001f', 'health.write', 'Sağlık Yönet', 'health'),
    ('f0000000-0000-4000-8000-000000000020', 'parent.medicine_request', 'İlaç Talebi Oluştur', 'parent');

INSERT OR IGNORE INTO roles (id, name, slug, description, is_system, organization_id) VALUES
    ('a0000000-0000-4000-8000-000000000001', 'Super Admin', 'super_admin', 'Tüm sistem yetkileri', TRUE, NULL),
    ('a0000000-0000-4000-8000-000000000002', 'Kurum Admini', 'org_admin', 'Kurum yöneticisi', TRUE, NULL),
    ('a0000000-0000-4000-8000-000000000003', 'Şube Yetkilisi', 'branch_manager', 'Şube yöneticisi', TRUE, NULL),
    ('a0000000-0000-4000-8000-000000000004', 'Öğretmen', 'teacher', 'Sınıf öğretmeni', TRUE, NULL),
    ('a0000000-0000-4000-8000-000000000005', 'Muhasebe', 'accountant', 'Finans sorumlusu', TRUE, NULL),
    ('a0000000-0000-4000-8000-000000000006', 'Personel', 'staff', 'Genel personel', TRUE, NULL),
    ('a0000000-0000-4000-8000-000000000007', 'Kantin Personeli', 'canteen_staff', 'Kantin yöneticisi', TRUE, NULL),
    ('a0000000-0000-4000-8000-000000000008', 'Veli', 'parent', 'Veli', TRUE, NULL),
    ('a0000000-0000-4000-8000-000000000009', 'Yönetici', 'manager', 'Yönetici', TRUE, NULL),
    ('a0000000-0000-4000-8000-00000000000a', 'İdareci', 'administrator', 'İdareci', TRUE, NULL),
    ('a0000000-0000-4000-8000-00000000000b', 'Kurum Sahibi', 'owner', 'Kurum Sahibi', TRUE, NULL);

INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
SELECT 'a0000000-0000-4000-8000-000000000001', id FROM permissions;

INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
SELECT 'a0000000-0000-4000-8000-000000000002', id FROM permissions
WHERE code NOT IN ('org.write');

INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
SELECT 'a0000000-0000-4000-8000-000000000003', id FROM permissions
WHERE module IN ('branches', 'students', 'classes', 'attendance', 'announcements', 'reports', 'dashboard', 'health') AND code LIKE '%.read'
   OR (module = 'branches' AND code = 'branch.write')
   OR (module = 'students' AND code = 'student.write')
   OR (module = 'classes' AND code = 'class.write')
   OR (module = 'attendance' AND code = 'attendance.write')
   OR (module = 'health' AND code = 'health.write');

INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
SELECT 'a0000000-0000-4000-8000-000000000004', id FROM permissions
WHERE code IN ('student.read', 'class.read', 'attendance.read', 'attendance.write', 'dashboard.read', 'health.read');

INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
SELECT 'a0000000-0000-4000-8000-000000000005', id FROM permissions
WHERE module IN ('finance', 'receipts', 'reports', 'dashboard', 'students') AND code LIKE '%.read'
   OR code IN ('finance.write', 'receipt.write');

INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
SELECT 'a0000000-0000-4000-8000-000000000007', id FROM permissions
WHERE module = 'canteen';

-- Veli - Parent focused permissions
INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
SELECT 'a0000000-0000-4000-8000-000000000008', id FROM permissions
WHERE code IN ('student.read', 'attendance.read', 'finance.read', 'receipt.read', 'announcement.read', 'dashboard.read', 'parent.view_children', 'parent.view_attendance', 'parent.view_finances', 'health.read', 'parent.medicine_request');

-- Yönetici - Manager with broad organizational access
INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
SELECT 'a0000000-0000-4000-8000-000000000009', id FROM permissions
WHERE code IN ('branch.read', 'branch.write', 'user.read', 'user.write', 'student.read', 'student.write', 'class.read', 'class.write', 'attendance.read', 'attendance.write', 'finance.read', 'finance.write', 'receipt.read', 'receipt.write', 'announcement.read', 'announcement.write', 'report.read', 'dashboard.read');

-- İdareci - Administrator with administrative access
INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
SELECT 'a0000000-0000-4000-8000-00000000000a', id FROM permissions
WHERE code NOT IN ('org.write', 'settings.write');

-- Kurum Sahibi - Organization owner with full access
INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
SELECT 'a0000000-0000-4000-8000-00000000000b', id FROM permissions
WHERE code NOT IN ('org.write', 'settings.write');

INSERT OR IGNORE INTO organizations (id, name, legal_name, phone, email, city, country, is_active)
VALUES ('b0000000-0000-4000-8000-000000000001', 'Demo Eğitim Kurumu', 'Demo Eğitim Kurumu A.Ş.', '02121234567', 'info@demoegitim.com', 'İstanbul', 'Türkiye', TRUE);

INSERT OR IGNORE INTO branches (id, organization_id, name, code, city, capacity, is_active) VALUES
    ('c0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000001', 'Merkez Şube', 'MRK', 'İstanbul', 150, TRUE),
    ('c0000000-0000-4000-8000-000000000002', 'b0000000-0000-4000-8000-000000000001', 'Kadıköy Şube', 'KDK', 'İstanbul', 100, TRUE),
    ('c0000000-0000-4000-8000-000000000003', 'b0000000-0000-4000-8000-000000000001', 'Beşiktaş Şube', 'BTK', 'İstanbul', 80, TRUE);

INSERT OR IGNORE INTO classes (id, organization_id, branch_id, name, code, capacity, academic_year, is_active) VALUES
    ('d0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000001', 'c0000000-0000-4000-8000-000000000001', 'Minikler A', 'MA', 20, '2025-2026', TRUE),
    ('d0000000-0000-4000-8000-000000000002', 'b0000000-0000-4000-8000-000000000001', 'c0000000-0000-4000-8000-000000000001', 'Minikler B', 'MB', 20, '2025-2026', TRUE),
    ('d0000000-0000-4000-8000-000000000003', 'b0000000-0000-4000-8000-000000000001', 'c0000000-0000-4000-8000-000000000002', 'Etüt 1', 'E1', 15, '2025-2026', TRUE),
    ('d0000000-0000-4000-8000-000000000004', 'b0000000-0000-4000-8000-000000000001', 'c0000000-0000-4000-8000-000000000003', 'Etüt 2', 'E2', 15, '2025-2026', TRUE);

-- Admin user placeholder - password set by seed script
INSERT OR IGNORE INTO users (id, organization_id, email, password_hash, first_name, last_name, status, is_super_admin)
VALUES (
    'e0000000-0000-4000-8000-000000000001',
    NULL,
    'admin@demo.com',
    '$2b$12$placeholder_will_be_updated_by_seed_script',
    'Sistem',
    'Yöneticisi',
    'ACTIVE',
    TRUE
);

INSERT OR IGNORE INTO user_roles (user_id, role_id) VALUES
    ('e0000000-0000-4000-8000-000000000001', 'a0000000-0000-4000-8000-000000000001');

-- Additional demo users - password set by seed script
INSERT OR IGNORE INTO users (id, organization_id, email, password_hash, first_name, last_name, status, is_super_admin)
VALUES
    ('e0000000-0000-4000-8000-000000000002', 'b0000000-0000-4000-8000-000000000001', 'kurumadmin@demo.com', '$2b$12$placeholder_will_be_updated_by_seed_script', 'Ahmet', 'Yılmaz', 'ACTIVE', FALSE),
    ('e0000000-0000-4000-8000-000000000003', 'b0000000-0000-4000-8000-000000000001', 'subeyetkili@demo.com', '$2b$12$placeholder_will_be_updated_by_seed_script', 'Ayşe', 'Demir', 'ACTIVE', FALSE),
    ('e0000000-0000-4000-8000-000000000004', 'b0000000-0000-4000-8000-000000000001', 'ogretmen@demo.com', '$2b$12$placeholder_will_be_updated_by_seed_script', 'Fatma', 'Kaya', 'ACTIVE', FALSE),
    ('e0000000-0000-4000-8000-000000000005', 'b0000000-0000-4000-8000-000000000001', 'muhasebe@demo.com', '$2b$12$placeholder_will_be_updated_by_seed_script', 'Mehmet', 'Özkan', 'ACTIVE', FALSE),
    ('e0000000-0000-4000-8000-000000000006', 'b0000000-0000-4000-8000-000000000001', 'personel@demo.com', '$2b$12$placeholder_will_be_updated_by_seed_script', 'Zeynep', 'Akar', 'ACTIVE', FALSE),
    ('e0000000-0000-4000-8000-000000000007', 'b0000000-0000-4000-8000-000000000001', 'veli@demo.com', '$2b$12$placeholder_will_be_updated_by_seed_script', 'Ali', 'Yılmaz', 'ACTIVE', FALSE),
    ('e0000000-0000-4000-8000-000000000008', 'b0000000-0000-4000-8000-000000000001', 'yonetici@demo.com', '$2b$12$placeholder_will_be_updated_by_seed_script', 'Murat', 'Şahin', 'ACTIVE', FALSE),
    ('e0000000-0000-4000-8000-000000000009', 'b0000000-0000-4000-8000-000000000001', 'idareci@demo.com', '$2b$12$placeholder_will_be_updated_by_seed_script', 'Selim', 'Kara', 'ACTIVE', FALSE),
    ('e0000000-0000-4000-8000-00000000000a', 'b0000000-0000-4000-8000-000000000001', 'kurumsahibi@demo.com', '$2b$12$placeholder_will_be_updated_by_seed_script', 'Hakan', 'Demirci', 'ACTIVE', FALSE);

INSERT OR IGNORE INTO user_roles (user_id, role_id) VALUES
    ('e0000000-0000-4000-8000-000000000002', 'a0000000-0000-4000-8000-000000000002'),
    ('e0000000-0000-4000-8000-000000000003', 'a0000000-0000-4000-8000-000000000003'),
    ('e0000000-0000-4000-8000-000000000004', 'a0000000-0000-4000-8000-000000000004'),
    ('e0000000-0000-4000-8000-000000000005', 'a0000000-0000-4000-8000-000000000005'),
    ('e0000000-0000-4000-8000-000000000006', 'a0000000-0000-4000-8000-000000000006'),
    ('e0000000-0000-4000-8000-000000000007', 'a0000000-0000-4000-8000-000000000008'),
    ('e0000000-0000-4000-8000-000000000008', 'a0000000-0000-4000-8000-000000000009'),
    ('e0000000-0000-4000-8000-000000000009', 'a0000000-0000-4000-8000-00000000000a'),
    ('e0000000-0000-4000-8000-00000000000a', 'a0000000-0000-4000-8000-00000000000b');

INSERT OR IGNORE INTO message_templates (id, organization_id, code, name, channel, subject, body_template, is_active) VALUES
    ('f0000000-0000-4000-8000-000000000019', NULL, 'payment_received', 'Ödeme Alındı', 'EMAIL', 'Ödeme Bildirimi', 'Sayın {{parent_name}}, {{student_name}} için {{amount}} TL ödeme alınmıştır. Makbuz No: {{receipt_number}}', TRUE),
    ('f0000000-0000-4000-8000-00000000001a', NULL, 'debt_reminder', 'Borç Hatırlatma', 'SMS', NULL, 'Sayın velimiz, {{student_name}} için {{amount}} TL borcunuzun vadesi {{due_date}}. {{organization_name}}', TRUE),
    ('f0000000-0000-4000-8000-00000000001b', NULL, 'announcement', 'Duyuru', 'WHATSAPP', NULL, '{{title}}: {{content}}', TRUE);

INSERT OR IGNORE INTO app_settings (id, organization_id, setting_key, setting_value, description) VALUES
    ('90000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000001', 'upload', '{"max_size_mb": 10, "allowed_types": ["pdf","jpg","jpeg","png","docx"]}', 'Dosya yükleme ayarları'),
    ('90000000-0000-4000-8000-000000000002', 'b0000000-0000-4000-8000-000000000001', 'receipt', '{"prefix": "RCP", "show_remaining_debt": true}', 'Makbuz ayarları');
