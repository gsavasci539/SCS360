-- School Management System - Seed Data
-- This file contains demo data for testing and initial setup

-- ============================================
-- ORGANIZATION
-- ============================================

INSERT INTO organizations (id, name, tax_number, tax_office, address, phone, email, is_active, created_by, updated_by)
VALUES (
    '550e8400-e29b-41d4-a716-446655440000',
    'Demo Eğitim Kurumu',
    '1234567890',
    'Kadıköy Vergi Dairesi',
    'Caferağa Mah. Moda Cad. No:123 Kadıköy/İstanbul',
    '+902123456789',
    'info@demoegitim.com',
    true,
    '550e8400-e29b-41d4-a716-446655440000',
    '550e8400-e29b-41d4-a716-446655440000'
);

-- ============================================
-- BRANCHES
-- ============================================

INSERT INTO branches (id, organization_id, name, code, address, phone, email, capacity, is_active, created_by, updated_by)
VALUES 
    ('660e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440000', 'Merkez Şube', 'MERKEZ', 'Caferağa Mah. Moda Cad. No:123 Kadıköy/İstanbul', '+902123456789', 'merkez@demoegitim.com', 200, true, '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
    ('660e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440000', 'Kadıköy Şube', 'KADIKOY', 'Caferağa Mah. Özgürlük Cad. No:45 Kadıköy/İstanbul', '+902123456790', 'kadikoy@demoegitim.com', 150, true, '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
    ('660e8400-e29b-41d4-a716-446655440003', '550e8400-e29b-41d4-a716-446655440000', 'Beşiktaş Şube', 'BESIKTAS', 'Sinanpaşa Mah. Ortabahçe Cad. No:78 Beşiktaş/İstanbul', '+902123456791', 'besiktas@demoegitim.com', 120, true, '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000');

-- ============================================
-- PERMISSIONS
-- ============================================

INSERT INTO permissions (id, name, description, module) VALUES
-- Auth
('770e8400-e29b-41d4-a716-446655440001', 'auth.login', 'Login to system', 'auth'),
('770e8400-e29b-41d4-a716-446655440002', 'auth.logout', 'Logout from system', 'auth'),
('770e8400-e29b-41d4-a716-446655440003', 'auth.reset_password', 'Reset password', 'auth'),

-- Organizations
('770e8400-e29b-41d4-a716-446655440004', 'organizations.view', 'View organizations', 'organizations'),
('770e8400-e29b-41d4-a716-446655440005', 'organizations.create', 'Create organizations', 'organizations'),
('770e8400-e29b-41d4-a716-446655440006', 'organizations.edit', 'Edit organizations', 'organizations'),
('770e8400-e29b-41d4-a716-446655440007', 'organizations.delete', 'Delete organizations', 'organizations'),

-- Branches
('770e8400-e29b-41d4-a716-446655440008', 'branches.view', 'View branches', 'branches'),
('770e8400-e29b-41d4-a716-446655440009', 'branches.create', 'Create branches', 'branches'),
('770e8400-e29b-41d4-a716-446655440010', 'branches.edit', 'Edit branches', 'branches'),
('770e8400-e29b-41d4-a716-446655440011', 'branches.delete', 'Delete branches', 'branches'),

-- Users
('770e8400-e29b-41d4-a716-446655440012', 'users.view', 'View users', 'users'),
('770e8400-e29b-41d4-a716-446655440013', 'users.create', 'Create users', 'users'),
('770e8400-e29b-41d4-a716-446655440014', 'users.edit', 'Edit users', 'users'),
('770e8400-e29b-41d4-a716-446655440015', 'users.delete', 'Delete users', 'users'),
('770e8400-e29b-41d4-a716-446655440016', 'users.assign_roles', 'Assign roles to users', 'users'),

-- Students
('770e8400-e29b-41d4-a716-446655440017', 'students.view', 'View students', 'students'),
('770e8400-e29b-41d4-a716-446655440018', 'students.create', 'Create students', 'students'),
('770e8400-e29b-41d4-a716-446655440019', 'students.edit', 'Edit students', 'students'),
('770e8400-e29b-41d4-a716-446655440020', 'students.delete', 'Delete students', 'students'),
('770e8400-e29b-41d4-a716-446655440021', 'students.view_all', 'View all students (all branches)', 'students'),

-- Classes
('770e8400-e29b-41d4-a716-446655440022', 'classes.view', 'View classes', 'classes'),
('770e8400-e29b-41d4-a716-446655440023', 'classes.create', 'Create classes', 'classes'),
('770e8400-e29b-41d4-a716-446655440024', 'classes.edit', 'Edit classes', 'classes'),
('770e8400-e29b-41d4-a716-446655440025', 'classes.delete', 'Delete classes', 'classes'),
('770e8400-e29b-41d4-a716-446655440026', 'classes.assign_students', 'Assign students to classes', 'classes'),

-- Attendance
('770e8400-e29b-41d4-a716-446655440027', 'attendance.view', 'View attendance', 'attendance'),
('770e8400-e29b-41d4-a716-446655440028', 'attendance.create', 'Create attendance records', 'attendance'),
('770e8400-e29b-41d4-a716-446655440029', 'attendance.edit', 'Edit attendance records', 'attendance'),
('770e8400-e29b-41d4-a716-446655440030', 'attendance.delete', 'Delete attendance records', 'attendance'),
('770e8400-e29b-41d4-a716-446655440031', 'attendance.take_own_class', 'Take attendance for own class only', 'attendance'),

-- Finance - Debts
('770e8400-e29b-41d4-a716-446655440032', 'debts.view', 'View debts', 'finance'),
('770e8400-e29b-41d4-a716-446655440033', 'debts.create', 'Create debts', 'finance'),
('770e8400-e29b-41d4-a716-446655440034', 'debts.edit', 'Edit debts', 'finance'),
('770e8400-e29b-41d4-a716-446655440035', 'debts.delete', 'Delete debts', 'finance'),

-- Finance - Payments
('770e8400-e29b-41d4-a716-446655440036', 'payments.view', 'View payments', 'finance'),
('770e8400-e29b-41d4-a716-446655440037', 'payments.create', 'Create payments', 'finance'),
('770e8400-e29b-41d4-a716-446655440038', 'payments.cancel', 'Cancel payments', 'finance'),

-- Receipts
('770e8400-e29b-41d4-a716-446655440039', 'receipts.view', 'View receipts', 'finance'),
('770e8400-e29b-41d4-a716-446655440040', 'receipts.download', 'Download receipt PDF', 'finance'),
('770e8400-e29b-41d4-a716-446655440041', 'receipts.print', 'Print receipt', 'finance'),

-- Announcements
('770e8400-e29b-41d4-a716-446655440042', 'announcements.view', 'View announcements', 'announcements'),
('770e8400-e29b-41d4-a716-446655440043', 'announcements.create', 'Create announcements', 'announcements'),
('770e8400-e29b-41d4-a716-446655440044', 'announcements.edit', 'Edit announcements', 'announcements'),
('770e8400-e29b-41d4-a716-446655440045', 'announcements.delete', 'Delete announcements', 'announcements'),
('770e8400-e29b-41d4-a716-446655440046', 'announcements.send', 'Send announcements', 'announcements'),

-- Notifications
('770e8400-e29b-41d4-a716-446655440047', 'notifications.view', 'View notifications', 'notifications'),
('770e8400-e29b-41d4-a716-446655440048', 'notifications.send', 'Send notifications', 'notifications'),
('770e8400-e29b-41d4-a716-446655440049', 'notifications.retry', 'Retry failed notifications', 'notifications'),
('770e8400-e29b-41d4-a716-446655440050', 'notifications.manage_templates', 'Manage notification templates', 'notifications'),

-- Reports
('770e8400-e29b-41d4-a716-446655440051', 'reports.view', 'View reports', 'reports'),
('770e8400-e29b-41d4-a716-446655440052', 'reports.export', 'Export reports', 'reports'),
('770e8400-e29b-41d4-a716-446655440053', 'reports.finance', 'View finance reports', 'reports'),
('770e8400-e29b-41d4-a716-446655440054', 'reports.attendance', 'View attendance reports', 'reports'),

-- Settings
('770e8400-e29b-41d4-a716-446655440055', 'settings.view', 'View settings', 'settings'),
('770e8400-e29b-41d4-a716-446655440056', 'settings.edit', 'Edit settings', 'settings'),
('770e8400-e29b-41d4-a716-446655440057', 'settings.manage_integrations', 'Manage integrations', 'settings'),
('770e8400-e29b-41d4-a716-446655440058', 'settings.manage_roles', 'Manage roles', 'settings');

-- ============================================
-- ROLES
-- ============================================

INSERT INTO roles (id, organization_id, name, description, is_system) VALUES
('880e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440000', 'Super Admin', 'Full system access', true),
('880e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440000', 'Kurum Admini', 'Organization administrator', true),
('880e8400-e29b-41d4-a716-446655440003', '550e8400-e29b-41d4-a716-446655440000', 'Şube Yetkilisi', 'Branch administrator', true),
('880e8400-e29b-41d4-a716-446655440004', '550e8400-e29b-41d4-a716-446655440000', 'Öğretmen', 'Teacher with class access', true),
('880e8400-e29b-41d4-a716-446655440005', '550e8400-e29b-41d4-a716-446655440000', 'Muhasebe', 'Finance and accounting', true),
('880e8400-e29b-41d4-a716-446655440006', '550e8400-e29b-41d4-a716-446655440000', 'Personel', 'Staff with limited access', true);

-- ============================================
-- ROLE PERMISSIONS
-- ============================================

-- Super Admin - All permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT '880e8400-e29b-41d4-a716-446655440001', id FROM permissions;

-- Kurum Admini - Most permissions except system-level
INSERT INTO role_permissions (role_id, permission_id)
SELECT '880e8400-e29b-41d4-a716-446655440002', id FROM permissions 
WHERE name NOT IN ('organizations.create', 'organizations.delete', 'organizations.edit', 'settings.manage_roles');

-- Şube Yetkilisi - Branch-level permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT '880e8400-e29b-41d4-a716-446655440003', id FROM permissions 
WHERE name IN (
    'auth.login', 'auth.logout', 'auth.reset_password',
    'branches.view', 'branches.edit',
    'users.view', 'users.create', 'users.edit',
    'students.view', 'students.create', 'students.edit',
    'classes.view', 'classes.create', 'classes.edit', 'classes.assign_students',
    'attendance.view', 'attendance.create', 'attendance.edit',
    'debts.view', 'debts.create', 'debts.edit',
    'payments.view', 'payments.create',
    'receipts.view', 'receipts.download', 'receipts.print',
    'announcements.view', 'announcements.create', 'announcements.send',
    'notifications.view',
    'reports.view', 'reports.export', 'reports.finance', 'reports.attendance'
);

-- Öğretmen - Class and student focused
INSERT INTO role_permissions (role_id, permission_id)
SELECT '880e8400-e29b-41d4-a716-446655440004', id FROM permissions 
WHERE name IN (
    'auth.login', 'auth.logout', 'auth.reset_password',
    'students.view',
    'classes.view',
    'attendance.view', 'attendance.create', 'attendance.edit', 'attendance.take_own_class',
    'announcements.view'
);

-- Muhasebe - Finance focused
INSERT INTO role_permissions (role_id, permission_id)
SELECT '880e8400-e29b-41d4-a716-446655440005', id FROM permissions 
WHERE name IN (
    'auth.login', 'auth.logout', 'auth.reset_password',
    'students.view',
    'debts.view', 'debts.create', 'debts.edit',
    'payments.view', 'payments.create', 'payments.cancel',
    'receipts.view', 'receipts.download', 'receipts.print',
    'reports.view', 'reports.export', 'reports.finance'
);

-- Personel - Limited access
INSERT INTO role_permissions (role_id, permission_id)
SELECT '880e8400-e29b-41d4-a716-446655440006', id FROM permissions 
WHERE name IN (
    'auth.login', 'auth.logout', 'auth.reset_password',
    'students.view',
    'attendance.view',
    'announcements.view'
);

-- ============================================
-- USERS
-- ============================================

-- Password hash for 'Admin123*' (bcrypt)
INSERT INTO users (id, organization_id, email, password_hash, first_name, last_name, phone, status, created_by, updated_by)
VALUES (
    '990e8400-e29b-41d4-a716-446655440001',
    '550e8400-e29b-41d4-a716-446655440000',
    'admin@demo.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYkX5qX1qWu',
    'Sistem',
    'Yöneticisi',
    '+902123456789',
    'ACTIVE',
    '550e8400-e29b-41d4-a716-446655440000',
    '550e8400-e29b-41d4-a716-446655440000'
);

-- Additional demo users
INSERT INTO users (id, organization_id, email, password_hash, first_name, last_name, phone, status, created_by, updated_by)
VALUES 
('990e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440000', 'kurumadmin@demo.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYkX5qX1qWu', 'Ahmet', 'Yılmaz', '+902123456780', 'ACTIVE', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('990e8400-e29b-41d4-a716-446655440003', '550e8400-e29b-41d4-a716-446655440000', 'subeyetkili@demo.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYkX5qX1qWu', 'Ayşe', 'Demir', '+902123456781', 'ACTIVE', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('990e8400-e29b-41d4-a716-446655440004', '550e8400-e29b-41d4-a716-446655440000', 'ogretmen@demo.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYkX5qX1qWu', 'Fatma', 'Kaya', '+902123456782', 'ACTIVE', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('990e8400-e29b-41d4-a716-446655440005', '550e8400-e29b-41d4-a716-446655440000', 'muhasebe@demo.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYkX5qX1qWu', 'Mehmet', 'Özkan', '+902123456783', 'ACTIVE', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('990e8400-e29b-41d4-a716-446655440006', '550e8400-e29b-41d4-a716-446655440000', 'personel@demo.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYkX5qX1qWu', 'Zeynep', 'Akar', '+902123456784', 'ACTIVE', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000');

-- ============================================
-- USER ROLES
-- ============================================

INSERT INTO user_roles (user_id, role_id, branch_id) VALUES
('990e8400-e29b-41d4-a716-446655440001', '880e8400-e29b-41d4-a716-446655440001', NULL), -- Super Admin
('990e8400-e29b-41d4-a716-446655440002', '880e8400-e29b-41d4-a716-446655440003', NULL), -- Kurum Admini
('990e8400-e29b-41d4-a716-446655440003', '880e8400-e29b-41d4-a716-446655440003', '660e8400-e29b-41d4-a716-446655440001'), -- Şube Yetkilisi - Merkez
('990e8400-e29b-41d4-a716-446655440004', '880e8400-e29b-41d4-a716-446655440004', '660e8400-e29b-41d4-a716-446655440001'), -- Öğretmen - Merkez
('990e8400-e29b-41d4-a716-446655440005', '880e8400-e29b-41d4-a716-446655440005', NULL), -- Muhasebe
('990e8400-e29b-41d4-a716-446655440006', '880e8400-e29b-41d4-a716-446655440006', '660e8400-e29b-41d4-a716-446655440001'); -- Personel - Merkez

-- ============================================
-- USER BRANCHES
-- ============================================

INSERT INTO user_branches (user_id, branch_id, is_primary) VALUES
('990e8400-e29b-41d4-a716-446655440003', '660e8400-e29b-41d4-a716-446655440001', true),
('990e8400-e29b-41d4-a716-446655440003', '660e8400-e29b-41d4-a716-446655440002', false),
('990e8400-e29b-41d4-a716-446655440004', '660e8400-e29b-41d4-a716-446655440001', true),
('990e8400-e29b-41d4-a716-446655440006', '660e8400-e29b-41d4-a716-446655440001', true);

-- ============================================
-- CLASSES
-- ============================================

INSERT INTO classes (id, organization_id, branch_id, name, code, capacity, teacher_id, academic_year, is_active, created_by, updated_by)
VALUES 
('aa0e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'Minikler A', 'MINIK-A', 20, '990e8400-e29b-41d4-a716-446655440004', '2024-2025', true, '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('aa0e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'Minikler B', 'MINIK-B', 20, '990e8400-e29b-41d4-a716-446655440004', '2024-2025', true, '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('aa0e8400-e29b-41d4-a716-446655440003', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'Etüt 1', 'ETUT-1', 15, '990e8400-e29b-41d4-a716-446655440004', '2024-2025', true, '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('aa0e8400-e29b-41d4-a716-446655440004', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440002', 'Anaokulu A', 'ANA-A', 25, '990e8400-e29b-41d4-a716-446655440004', '2024-2025', true, '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('aa0e8400-e29b-41d4-a716-446655440005', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440003', 'Kurs 1', 'KURS-1', 10, '990e8400-e29b-41d4-a716-446655440004', '2024-2025', true, '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000');

-- ============================================
-- PARENTS
-- ============================================

INSERT INTO parents (id, organization_id, first_name, last_name, relationship, phone, whatsapp_number, sms_number, email, address, receive_email_notifications, receive_sms_notifications, receive_whatsapp_notifications, created_by, updated_by)
VALUES 
('bb0e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440000', 'Ali', 'Yılmaz', 'Baba', '+905321234567', '+905321234567', '+905321234567', 'ali.yilmaz@example.com', 'Kadıköy/İstanbul', true, true, true, '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('bb0e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440000', 'Ayşe', 'Yılmaz', 'Anne', '+905321234568', '+905321234568', '+905321234568', 'ayse.yilmaz@example.com', 'Kadıköy/İstanbul', true, true, true, '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('bb0e8400-e29b-41d4-a716-446655440003', '550e8400-e29b-41d4-a716-446655440000', 'Mehmet', 'Demir', 'Baba', '+905321234569', '+905321234569', '+905321234569', 'mehmet.demir@example.com', 'Beşiktaş/İstanbul', true, false, true, '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('bb0e8400-e29b-41d4-a716-446655440004', '550e8400-e29b-41d4-a716-446655440000', 'Fatma', 'Demir', 'Anne', '+905321234570', '+905321234570', '+905321234570', 'fatma.demir@example.com', 'Beşiktaş/İstanbul', true, true, false, '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('bb0e8400-e29b-41d4-a716-446655440005', '550e8400-e29b-41d4-a716-446655440000', 'Hasan', 'Kaya', 'Baba', '+905321234571', '+905321234571', '+905321234571', 'hasan.kaya@example.com', 'Kadıköy/İstanbul', true, true, true, '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('bb0e8400-e29b-41d4-a716-446655440006', '550e8400-e29b-41d4-a716-446655440000', 'Zeynep', 'Kaya', 'Anne', '+905321234572', '+905321234572', '+905321234572', 'zeynep.kaya@example.com', 'Kadıköy/İstanbul', true, true, true, '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000');

-- ============================================
-- STUDENTS (25 students)
-- ============================================

INSERT INTO students (id, organization_id, branch_id, class_id, first_name, last_name, date_of_birth, gender, status, enrollment_date, created_by, updated_by) VALUES
('cc0e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'aa0e8400-e29b-41d4-a716-446655440001', 'Ahmet', 'Yılmaz', '2019-05-15', 'MALE', 'ACTIVE', '2024-09-01', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('cc0e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'aa0e8400-e29b-41d4-a716-446655440001', 'Elif', 'Demir', '2019-08-20', 'FEMALE', 'ACTIVE', '2024-09-01', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('cc0e8400-e29b-41d4-a716-446655440003', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'aa0e8400-e29b-41d4-a716-446655440001', 'Mustafa', 'Kaya', '2019-03-10', 'MALE', 'ACTIVE', '2024-09-01', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('cc0e8400-e29b-41d4-a716-446655440004', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'aa0e8400-e29b-41d4-a716-446655440001', 'Zeynep', 'Özkan', '2019-07-25', 'FEMALE', 'ACTIVE', '2024-09-01', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('cc0e8400-e29b-41d4-a716-446655440005', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'aa0e8400-e29b-41d4-a716-446655440001', 'Emre', 'Akar', '2019-11-05', 'MALE', 'ACTIVE', '2024-09-01', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('cc0e8400-e29b-41d4-a716-446655440006', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'aa0e8400-e29b-41d4-a716-446655440001', 'Selin', 'Çelik', '2019-01-30', 'FEMALE', 'ACTIVE', '2024-09-01', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('cc0e8400-e29b-41d4-a716-446655440007', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'aa0e8400-e29b-41d4-a716-446655440001', 'Kaan', 'Yıldız', '2019-09-12', 'MALE', 'ACTIVE', '2024-09-01', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('cc0e8400-e29b-41d4-a716-446655440008', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'aa0e8400-e29b-41d4-a716-446655440001', 'Defne', 'Arslan', '2019-04-18', 'FEMALE', 'ACTIVE', '2024-09-01', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('cc0e8400-e29b-41d4-a716-446655440009', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'aa0e8400-e29b-41d4-a716-446655440001', 'Yusuf', 'Doğan', '2019-06-22', 'MALE', 'ACTIVE', '2024-09-01', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('cc0e8400-e29b-41d4-a716-446655440010', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'aa0e8400-e29b-41d4-a716-446655440001', 'Leyla', 'Şahin', '2019-02-14', 'FEMALE', 'ACTIVE', '2024-09-01', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('cc0e8400-e29b-41d4-a716-446655440011', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'aa0e8400-e29b-41d4-a716-446655440002', 'Burak', 'Koç', '2019-10-08', 'MALE', 'ACTIVE', '2024-09-01', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('cc0e8400-e29b-41d4-a716-446655440012', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'aa0e8400-e29b-41d4-a716-446655440002', 'Ceren', 'Öztürk', '2019-12-03', 'FEMALE', 'ACTIVE', '2024-09-01', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('cc0e8400-e29b-41d4-a716-446655440013', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'aa0e8400-e29b-41d4-a716-446655440002', 'Mert', 'Aydan', '2019-05-28', 'MALE', 'ACTIVE', '2024-09-01', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('cc0e8400-e29b-41d4-a716-446655440014', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'aa0e8400-e29b-41d4-a716-446655440002', 'İpek', 'Yılmaz', '2019-08-15', 'FEMALE', 'ACTIVE', '2024-09-01', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('cc0e8400-e29b-41d4-a716-446655440015', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'aa0e8400-e29b-41d4-a716-446655440002', 'Ozan', 'Erdoğan', '2019-03-22', 'MALE', 'ACTIVE', '2024-09-01', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('cc0e8400-e29b-41d4-a716-446655440016', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'aa0e8400-e29b-41d4-a716-446655440002', 'Ece', 'Kurt', '2019-07-09', 'FEMALE', 'ACTIVE', '2024-09-01', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('cc0e8400-e29b-41d4-a716-446655440017', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'aa0e8400-e29b-41d4-a716-446655440002', 'Aras', 'Bulut', '2019-11-19', 'MALE', 'ACTIVE', '2024-09-01', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('cc0e8400-e29b-41d4-a716-446655440018', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'aa0e8400-e29b-41d4-a716-446655440002', 'Sude', 'Polat', '2019-01-25', 'FEMALE', 'ACTIVE', '2024-09-01', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('cc0e8400-e29b-41d4-a716-446655440019', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'aa0e8400-e29b-41d4-a716-446655440003', 'Kerem', 'Yalçın', '2019-09-05', 'MALE', 'ACTIVE', '2024-09-01', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('cc0e8400-e29b-41d4-a716-446655440020', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'aa0e8400-e29b-41d4-a716-446655440003', 'Melisa', 'Kara', '2019-04-30', 'FEMALE', 'ACTIVE', '2024-09-01', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('cc0e8400-e29b-41d4-a716-446655440021', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'aa0e8400-e29b-41d4-a716-446655440003', 'Eren', 'Çetin', '2019-06-15', 'MALE', 'ACTIVE', '2024-09-01', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('cc0e8400-e29b-41d4-a716-446655440022', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'aa0e8400-e29b-41d4-a716-446655440003', 'Berra', 'Taş', '2019-02-20', 'FEMALE', 'ACTIVE', '2024-09-01', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('cc0e8400-e29b-41d4-a716-446655440023', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'aa0e8400-e29b-41d4-a716-446655440003', 'Baran', 'Aksoy', '2019-10-12', 'MALE', 'ACTIVE', '2024-09-01', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('cc0e8400-e29b-41d4-a716-446655440024', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'aa0e8400-e29b-41d4-a716-446655440003', 'Simay', 'Yavuz', '2019-12-08', 'FEMALE', 'ACTIVE', '2024-09-01', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('cc0e8400-e29b-41d4-a716-446655440025', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'aa0e8400-e29b-41d4-a716-446655440003', 'Rüzgar', 'Kılıç', '2019-05-18', 'MALE', 'ACTIVE', '2024-09-01', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000');

-- ============================================
-- STUDENT PARENTS (Many-to-Many)
-- ============================================

INSERT INTO student_parents (student_id, parent_id, is_primary, is_emergency_contact) VALUES
('cc0e8400-e29b-41d4-a716-446655440001', 'bb0e8400-e29b-41d4-a716-446655440001', true, true),
('cc0e8400-e29b-41d4-a716-446655440001', 'bb0e8400-e29b-41d4-a716-446655440002', false, false),
('cc0e8400-e29b-41d4-a716-446655440002', 'bb0e8400-e29b-41d4-a716-446655440003', true, true),
('cc0e8400-e29b-41d4-a716-446655440002', 'bb0e8400-e29b-41d4-a716-446655440004', false, false),
('cc0e8400-e29b-41d4-a716-446655440003', 'bb0e8400-e29b-41d4-a716-446655440005', true, true),
('cc0e8400-e29b-41d4-a716-446655440003', 'bb0e8400-e29b-41d4-a716-446655440006', false, false),
('cc0e8400-e29b-41d4-a716-446655440004', 'bb0e8400-e29b-41d4-a716-446655440001', true, true),
('cc0e8400-e29b-41d4-a716-446655440005', 'bb0e8400-e29b-41d4-a716-446655440003', true, true),
('cc0e8400-e29b-41d4-a716-446655440006', 'bb0e8400-e29b-41d4-a716-446655440005', true, true),
('cc0e8400-e29b-41d4-a716-446655440007', 'bb0e8400-e29b-41d4-a716-446655440001', true, true),
('cc0e8400-e29b-41d4-a716-446655440008', 'bb0e8400-e29b-41d4-a716-446655440003', true, true),
('cc0e8400-e29b-41d4-a716-446655440009', 'bb0e8400-e29b-41d4-a716-446655440005', true, true),
('cc0e8400-e29b-41d4-a716-446655440010', 'bb0e8400-e29b-41d4-a716-446655440001', true, true),
('cc0e8400-e29b-41d4-a716-446655440011', 'bb0e8400-e29b-41d4-a716-446655440003', true, true),
('cc0e8400-e29b-41d4-a716-446655440012', 'bb0e8400-e29b-41d4-a716-446655440005', true, true),
('cc0e8400-e29b-41d4-a716-446655440013', 'bb0e8400-e29b-41d4-a716-446655440001', true, true),
('cc0e8400-e29b-41d4-a716-446655440014', 'bb0e8400-e29b-41d4-a716-446655440003', true, true),
('cc0e8400-e29b-41d4-a716-446655440015', 'bb0e8400-e29b-41d4-a716-446655440005', true, true),
('cc0e8400-e29b-41d4-a716-446655440016', 'bb0e8400-e29b-41d4-a716-446655440001', true, true),
('cc0e8400-e29b-41d4-a716-446655440017', 'bb0e8400-e29b-41d4-a716-446655440003', true, true),
('cc0e8400-e29b-41d4-a716-446655440018', 'bb0e8400-e29b-41d4-a716-446655440005', true, true),
('cc0e8400-e29b-41d4-a716-446655440019', 'bb0e8400-e29b-41d4-a716-446655440001', true, true),
('cc0e8400-e29b-41d4-a716-446655440020', 'bb0e8400-e29b-41d4-a716-446655440003', true, true),
('cc0e8400-e29b-41d4-a716-446655440021', 'bb0e8400-e29b-41d4-a716-446655440005', true, true),
('cc0e8400-e29b-41d4-a716-446655440022', 'bb0e8400-e29b-41d4-a716-446655440001', true, true),
('cc0e8400-e29b-41d4-a716-446655440023', 'bb0e8400-e29b-41d4-a716-446655440003', true, true),
('cc0e8400-e29b-41d4-a716-446655440024', 'bb0e8400-e29b-41d4-a716-446655440005', true, true),
('cc0e8400-e29b-41d4-a716-446655440025', 'bb0e8400-e29b-41d4-a716-446655440001', true, true);

-- ============================================
-- DEBTS (Sample debts for some students)
-- ============================================

INSERT INTO debts (id, organization_id, branch_id, student_id, debt_type, description, amount, paid_amount, status, due_date, academic_year, created_by, updated_by) VALUES
('dd0e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'cc0e8400-e29b-41d4-a716-446655440001', 'EDUCATION', 'Eylül 2024 Eğitim Ücreti', 5000.00, 0.00, 'UNPAID', '2024-09-30', '2024-2025', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('dd0e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'cc0e8400-e29b-41d4-a716-446655440002', 'EDUCATION', 'Eylül 2024 Eğitim Ücreti', 5000.00, 2500.00, 'PARTIALLY_PAID', '2024-09-30', '2024-2025', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('dd0e8400-e29b-41d4-a716-446655440003', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'cc0e8400-e29b-41d4-a716-446655440003', 'FOOD', 'Eylül 2024 Yemek Ücreti', 800.00, 800.00, 'PAID', '2024-09-30', '2024-2025', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('dd0e8400-e29b-41d4-a716-446655440004', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'cc0e8400-e29b-41d4-a716-446655440004', 'SERVICE', 'Eylül 2024 Servis Ücreti', 1200.00, 0.00, 'OVERDUE', '2024-09-15', '2024-2025', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('dd0e8400-e29b-41d4-a716-446655440005', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'cc0e8400-e29b-41d4-a716-446655440005', 'EDUCATION', 'Eylül 2024 Eğitim Ücreti', 5000.00, 5000.00, 'PAID', '2024-09-30', '2024-2025', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000'),
('dd0e8400-e29b-41d4-a716-446655440006', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'cc0e8400-e29b-41d4-a716-446655440006', 'STATIONERY', 'Kırtasiye Ücreti', 500.00, 0.00, 'UNPAID', '2024-10-15', '2024-2025', '550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000');

-- ============================================
-- PAYMENTS (Sample payments)
-- ============================================

INSERT INTO payments (id, organization_id, branch_id, student_id, debt_id, amount, payment_method, payment_date, notes, created_by, updated_by) VALUES
('ee0e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'cc0e8400-e29b-41d4-a716-446655440002', 'dd0e8400-e29b-41d4-a716-446655440002', 2500.00, 'CASH', '2024-09-15', 'Kısmi ödeme', '990e8400-e29b-41d4-a716-446655440005', '990e8400-e29b-41d4-a716-446655440005'),
('ee0e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'cc0e8400-e29b-41d4-a716-446655440003', 'dd0e8400-e29b-41d4-a716-446655440003', 800.00, 'BANK_TRANSFER', '2024-09-10', 'Tam ödeme', '990e8400-e29b-41d4-a716-446655440005', '990e8400-e29b-41d4-a716-446655440005'),
('ee0e8400-e29b-41d4-a716-446655440003', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'cc0e8400-e29b-41d4-a716-446655440005', 'dd0e8400-e29b-41d4-a716-446655440005', 5000.00, 'CREDIT_CARD', '2024-09-05', 'Tam ödeme', '990e8400-e29b-41d4-a716-446655440005', '990e8400-e29b-41d4-a716-446655440005');

-- ============================================
-- RECEIPTS (Sample receipts)
-- ============================================

INSERT INTO receipts (id, organization_id, branch_id, payment_id, receipt_number, status, created_by, updated_by) VALUES
('ff0e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'ee0e8400-e29b-41d4-a716-446655440001', 'RCP-20240915-000001', 'ACTIVE', '990e8400-e29b-41d4-a716-446655440005', '990e8400-e29b-41d4-a716-446655440005'),
('ff0e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'ee0e8400-e29b-41d4-a716-446655440002', 'RCP-20240910-000001', 'ACTIVE', '990e8400-e29b-41d4-a716-446655440005', '990e8400-e29b-41d4-a716-446655440005'),
('ff0e8400-e29b-41d4-a716-446655440003', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'ee0e8400-e29b-41d4-a716-446655440003', 'RCP-20240905-000001', 'ACTIVE', '990e8400-e29b-41d4-a716-446655440005', '990e8400-e29b-41d4-a716-446655440005');

-- ============================================
-- ATTENDANCE RECORDS (Sample attendance)
-- ============================================

INSERT INTO attendance_records (id, organization_id, branch_id, class_id, student_id, attendance_date, status, recorded_by, created_by, updated_by) VALUES
('gg0e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'aa0e8400-e29b-41d4-a716-446655440001', 'cc0e8400-e29b-41d4-a716-446655440001', CURRENT_DATE, 'PRESENT', '990e8400-e29b-41d4-a716-446655440004', '990e8400-e29b-41d4-a716-446655440004', '990e8400-e29b-41d4-a716-446655440004'),
('gg0e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'aa0e8400-e29b-41d4-a716-446655440001', 'cc0e8400-e29b-41d4-a716-446655440002', CURRENT_DATE, 'PRESENT', '990e8400-e29b-41d4-a716-446655440004', '990e8400-e29b-41d4-a716-446655440004', '990e8400-e29b-41d4-a716-446655440004'),
('gg0e8400-e29b-41d4-a716-446655440003', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'aa0e8400-e29b-41d4-a716-446655440001', 'cc0e8400-e29b-41d4-a716-446655440003', CURRENT_DATE, 'ABSENT', '990e8400-e29b-41d4-a716-446655440004', '990e8400-e29b-41d4-a716-446655440004', '990e8400-e29b-41d4-a716-446655440004'),
('gg0e8400-e29b-41d4-a716-446655440004', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'aa0e8400-e29b-41d4-a716-446655440001', 'cc0e8400-e29b-41d4-a716-446655440004', CURRENT_DATE, 'PRESENT', '990e8400-e29b-41d4-a716-446655440004', '990e8400-e29b-41d4-a716-446655440004', '990e8400-e29b-41d4-a716-446655440004'),
('gg0e8400-e29b-41d4-a716-446655440005', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'aa0e8400-e29b-41d4-a716-446655440001', 'cc0e8400-e29b-41d4-a716-446655440005', CURRENT_DATE, 'LATE', '990e8400-e29b-41d4-a716-446655440004', '990e8400-e29b-41d4-a716-446655440004', '990e8400-e29b-41d4-a716-446655440004'),
('gg0e8400-e29b-41d4-a716-446655440006', '550e8400-e29b-41d4-a716-446655440000', '660e8400-e29b-41d4-a716-446655440001', 'aa0e8400-e29b-41d4-a716-446655440001', 'cc0e8400-e29b-41d4-a716-446655440006', CURRENT_DATE, 'EXCUSED', '990e8400-e29b-41d4-a716-446655440004', '990e8400-e29b-41d4-a716-446655440004', '990e8400-e29b-41d4-a716-446655440004');

-- ============================================
-- APP SETTINGS
-- ============================================

INSERT INTO app_settings (id, organization_id, key, value, description) VALUES
('hh0e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440000', 'school_name', 'Demo Eğitim Kurumu', 'Kurum adı'),
('hh0e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440000', 'default_currency', 'TRY', 'Varsayılan para birimi'),
('hh0e8400-e29b-41d4-a716-446655440003', '550e8400-e29b-41d4-a716-446655440000', 'academic_year', '2024-2025', 'Mevcut akademik yıl'),
('hh0e8400-e29b-41d4-a716-446655440004', '550e8400-e29b-41d4-a716-446655440000', 'max_upload_size_mb', '10', 'Maksimum dosya yükleme boyutu (MB)'),
('hh0e8400-e29b-41d4-a716-446655440005', '550e8400-e29b-41d4-a716-446655440000', 'allowed_file_types', 'pdf,jpg,jpeg,png,docx', 'İzin verilen dosya tipleri');

-- ============================================
-- END OF SEED DATA
-- ============================================
