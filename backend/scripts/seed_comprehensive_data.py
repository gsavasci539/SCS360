"""
Comprehensive Seed Data Script for SQLite Database
This script populates the database with complete data for AI Analytics
WARNING: Only run in development with SEED_DEMO_DATA=true
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
import uuid

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.core.database import engine, get_db
from app.infrastructure.models.models import (
    Organization, Branch, Role, Permission, RolePermission,
    User, UserRole, UserBranch, ClassRoom, Student, Parent,
    StudentParent, StudentFile, AttendanceRecord, Debt, Payment,
    Receipt, Announcement, NotificationJob,
    AuditLog, MessageTemplate, AppSetting, Grade, DebtStatus,
    AttendanceStatus, DebtType, PaymentMethod, ReceiptStatus,
    FileCategory, NotificationChannel, NotificationStatus,
    AnnouncementAudience, UserStatus, StudentStatus, GenderType,
    DailyDevelopmentReport
)


async def seed_grades(session):
    """Seed grades for academic performance analysis"""
    print("Seeding grades...")
    
    # Check if grades already exist
    existing_grades = await session.execute(select(Grade).limit(1))
    if existing_grades.scalar_one_or_none():
        print("Grades already exist, skipping...")
        return
    
    grades_data = [
        # Minikler A students
        {
            'id': 'ii0e8400-e29b-41d4-a716-446655440001',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'class_id': 'aa0e8400-e29b-41d4-a716-446655440001',
            'student_id': 'cc0e8400-e29b-41d4-a716-446655440001',
            'subject': 'Matematik',
            'grade_type': 'EXAM',
            'score': 85.0,
            'max_score': 100.0,
            'exam_date': datetime(2024, 9, 15),
            'term': '1',
            'academic_year': '2024-2025',
            'notes': 'İyi performans',
            'created_by': '990e8400-e29b-41d4-a716-446655440004',
            'updated_by': '990e8400-e29b-41d4-a716-446655440004'
        },
        {
            'id': 'ii0e8400-e29b-41d4-a716-446655440002',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'class_id': 'aa0e8400-e29b-41d4-a716-446655440001',
            'student_id': 'cc0e8400-e29b-41d4-a716-446655440001',
            'subject': 'Türkçe',
            'grade_type': 'EXAM',
            'score': 78.0,
            'max_score': 100.0,
            'exam_date': datetime(2024, 9, 20),
            'term': '1',
            'academic_year': '2024-2025',
            'created_by': '990e8400-e29b-41d4-a716-446655440004',
            'updated_by': '990e8400-e29b-41d4-a716-446655440004'
        },
        {
            'id': 'ii0e8400-e29b-41d4-a716-446655440003',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'class_id': 'aa0e8400-e29b-41d4-a716-446655440001',
            'student_id': 'cc0e8400-e29b-41d4-a716-446655440001',
            'subject': 'Fen Bilgisi',
            'grade_type': 'HOMEWORK',
            'score': 90.0,
            'max_score': 100.0,
            'exam_date': datetime(2024, 9, 25),
            'term': '1',
            'academic_year': '2024-2025',
            'created_by': '990e8400-e29b-41d4-a716-446655440004',
            'updated_by': '990e8400-e29b-41d4-a716-446655440004'
        },
        {
            'id': 'ii0e8400-e29b-41d4-a716-446655440004',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'class_id': 'aa0e8400-e29b-41d4-a716-446655440001',
            'student_id': 'cc0e8400-e29b-41d4-a716-446655440001',
            'subject': 'Sosyal Bilgiler',
            'grade_type': 'PROJECT',
            'score': 82.0,
            'max_score': 100.0,
            'exam_date': datetime(2024, 10, 1),
            'term': '1',
            'academic_year': '2024-2025',
            'notes': 'Proje çalışması',
            'created_by': '990e8400-e29b-41d4-a716-446655440004',
            'updated_by': '990e8400-e29b-41d4-a716-446655440004'
        },
        {
            'id': 'ii0e8400-e29b-41d4-a716-446655440005',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'class_id': 'aa0e8400-e29b-41d4-a716-446655440001',
            'student_id': 'cc0e8400-e29b-41d4-a716-446655440001',
            'subject': 'Matematik',
            'grade_type': 'EXAM',
            'score': 72.0,
            'max_score': 100.0,
            'exam_date': datetime(2024, 10, 10),
            'term': '2',
            'academic_year': '2024-2025',
            'notes': 'Düşüş var',
            'created_by': '990e8400-e29b-41d4-a716-446655440004',
            'updated_by': '990e8400-e29b-41d4-a716-446655440004'
        },
        # More grades for other students with varying performance
        {
            'id': 'ii0e8400-e29b-41d4-a716-446655440006',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'class_id': 'aa0e8400-e29b-41d4-a716-446655440001',
            'student_id': 'cc0e8400-e29b-41d4-a716-446655440002',
            'subject': 'Matematik',
            'grade_type': 'EXAM',
            'score': 92.0,
            'max_score': 100.0,
            'exam_date': datetime(2024, 9, 15),
            'term': '1',
            'academic_year': '2024-2025',
            'notes': 'Mükemmel',
            'created_by': '990e8400-e29b-41d4-a716-446655440004',
            'updated_by': '990e8400-e29b-41d4-a716-446655440004'
        },
        {
            'id': 'ii0e8400-e29b-41d4-a716-446655440007',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'class_id': 'aa0e8400-e29b-41d4-a716-446655440001',
            'student_id': 'cc0e8400-e29b-41d4-a716-446655440002',
            'subject': 'Türkçe',
            'grade_type': 'EXAM',
            'score': 88.0,
            'max_score': 100.0,
            'exam_date': datetime(2024, 9, 20),
            'term': '1',
            'academic_year': '2024-2025',
            'created_by': '990e8400-e29b-41d4-a716-446655440004',
            'updated_by': '990e8400-e29b-41d4-a716-446655440004'
        },
        {
            'id': 'ii0e8400-e29b-41d4-a716-446655440008',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'class_id': 'aa0e8400-e29b-41d4-a716-446655440001',
            'student_id': 'cc0e8400-e29b-41d4-a716-446655440002',
            'subject': 'Fen Bilgisi',
            'grade_type': 'HOMEWORK',
            'score': 95.0,
            'max_score': 100.0,
            'exam_date': datetime(2024, 9, 25),
            'term': '1',
            'academic_year': '2024-2025',
            'created_by': '990e8400-e29b-41d4-a716-446655440004',
            'updated_by': '990e8400-e29b-41d4-a716-446655440004'
        },
        # Risk students with lower grades
        {
            'id': 'ii0e8400-e29b-41d4-a716-446655440011',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'class_id': 'aa0e8400-e29b-41d4-a716-446655440001',
            'student_id': 'cc0e8400-e29b-41d4-a716-446655440003',
            'subject': 'Matematik',
            'grade_type': 'EXAM',
            'score': 65.0,
            'max_score': 100.0,
            'exam_date': datetime(2024, 9, 15),
            'term': '1',
            'academic_year': '2024-2025',
            'notes': 'Zayıf',
            'created_by': '990e8400-e29b-41d4-a716-446655440004',
            'updated_by': '990e8400-e29b-41d4-a716-446655440004'
        },
        {
            'id': 'ii0e8400-e29b-41d4-a716-446655440012',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'class_id': 'aa0e8400-e29b-41d4-a716-446655440001',
            'student_id': 'cc0e8400-e29b-41d4-a716-446655440003',
            'subject': 'Türkçe',
            'grade_type': 'EXAM',
            'score': 70.0,
            'max_score': 100.0,
            'exam_date': datetime(2024, 9, 20),
            'term': '1',
            'academic_year': '2024-2025',
            'created_by': '990e8400-e29b-41d4-a716-446655440004',
            'updated_by': '990e8400-e29b-41d4-a716-446655440004'
        },
        {
            'id': 'ii0e8400-e29b-41d4-a716-446655440013',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'class_id': 'aa0e8400-e29b-41d4-a716-446655440001',
            'student_id': 'cc0e8400-e29b-41d4-a716-446655440003',
            'subject': 'Fen Bilgisi',
            'grade_type': 'HOMEWORK',
            'score': 75.0,
            'max_score': 100.0,
            'exam_date': datetime(2024, 9, 25),
            'term': '1',
            'academic_year': '2024-2025',
            'created_by': '990e8400-e29b-41d4-a716-446655440004',
            'updated_by': '990e8400-e29b-41d4-a716-446655440004'
        },
        {
            'id': 'ii0e8400-e29b-41d4-a716-446655440014',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'class_id': 'aa0e8400-e29b-41d4-a716-446655440001',
            'student_id': 'cc0e8400-e29b-41d4-a716-446655440003',
            'subject': 'Sosyal Bilgiler',
            'grade_type': 'PROJECT',
            'score': 68.0,
            'max_score': 100.0,
            'exam_date': datetime(2024, 10, 1),
            'term': '1',
            'academic_year': '2024-2025',
            'notes': 'Geliştirilmeli',
            'created_by': '990e8400-e29b-41d4-a716-446655440004',
            'updated_by': '990e8400-e29b-41d4-a716-446655440004'
        },
        {
            'id': 'ii0e8400-e29b-41d4-a716-446655440015',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'class_id': 'aa0e8400-e29b-41d4-a716-446655440001',
            'student_id': 'cc0e8400-e29b-41d4-a716-446655440003',
            'subject': 'Matematik',
            'grade_type': 'EXAM',
            'score': 62.0,
            'max_score': 100.0,
            'exam_date': datetime(2024, 10, 10),
            'term': '2',
            'academic_year': '2024-2025',
            'notes': 'Düşüş devam ediyor',
            'created_by': '990e8400-e29b-41d4-a716-446655440004',
            'updated_by': '990e8400-e29b-41d4-a716-446655440004'
        },
        # Critical risk student
        {
            'id': 'ii0e8400-e29b-41d4-a716-446655440021',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'class_id': 'aa0e8400-e29b-41d4-a716-446655440001',
            'student_id': 'cc0e8400-e29b-41d4-a716-446655440005',
            'subject': 'Matematik',
            'grade_type': 'EXAM',
            'score': 55.0,
            'max_score': 100.0,
            'exam_date': datetime(2024, 9, 15),
            'term': '1',
            'academic_year': '2024-2025',
            'notes': 'Kritik',
            'created_by': '990e8400-e29b-41d4-a716-446655440004',
            'updated_by': '990e8400-e29b-41d4-a716-446655440004'
        },
        {
            'id': 'ii0e8400-e29b-41d4-a716-446655440022',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'class_id': 'aa0e8400-e29b-41d4-a716-446655440001',
            'student_id': 'cc0e8400-e29b-41d4-a716-446655440005',
            'subject': 'Türkçe',
            'grade_type': 'EXAM',
            'score': 60.0,
            'max_score': 100.0,
            'exam_date': datetime(2024, 9, 20),
            'term': '1',
            'academic_year': '2024-2025',
            'notes': 'Zayıf',
            'created_by': '990e8400-e29b-41d4-a716-446655440004',
            'updated_by': '990e8400-e29b-41d4-a716-446655440004'
        },
        {
            'id': 'ii0e8400-e29b-41d4-a716-446655440023',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'class_id': 'aa0e8400-e29b-41d4-a716-446655440001',
            'student_id': 'cc0e8400-e29b-41d4-a716-446655440005',
            'subject': 'Fen Bilgisi',
            'grade_type': 'HOMEWORK',
            'score': 65.0,
            'max_score': 100.0,
            'exam_date': datetime(2024, 9, 25),
            'term': '1',
            'academic_year': '2024-2025',
            'created_by': '990e8400-e29b-41d4-a716-446655440004',
            'updated_by': '990e8400-e29b-41d4-a716-446655440004'
        },
        {
            'id': 'ii0e8400-e29b-41d4-a716-446655440024',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'class_id': 'aa0e8400-e29b-41d4-a716-446655440001',
            'student_id': 'cc0e8400-e29b-41d4-a716-446655440005',
            'subject': 'Sosyal Bilgiler',
            'grade_type': 'PROJECT',
            'score': 58.0,
            'max_score': 100.0,
            'exam_date': datetime(2024, 10, 1),
            'term': '1',
            'academic_year': '2024-2025',
            'notes': 'Yardım gerekli',
            'created_by': '990e8400-e29b-41d4-a716-446655440004',
            'updated_by': '990e8400-e29b-41d4-a716-446655440004'
        },
        {
            'id': 'ii0e8400-e29b-41d4-a716-446655440025',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'class_id': 'aa0e8400-e29b-41d4-a716-446655440001',
            'student_id': 'cc0e8400-e29b-41d4-a716-446655440005',
            'subject': 'Matematik',
            'grade_type': 'EXAM',
            'score': 52.0,
            'max_score': 100.0,
            'exam_date': datetime(2024, 10, 10),
            'term': '2',
            'academic_year': '2024-2025',
            'notes': 'Acil destek',
            'created_by': '990e8400-e29b-41d4-a716-446655440004',
            'updated_by': '990e8400-e29b-41d4-a716-446655440004'
        },
        # More students with good performance
        {
            'id': 'ii0e8400-e29b-41d4-a716-446655440026',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'class_id': 'aa0e8400-e29b-41d4-a716-446655440001',
            'student_id': 'cc0e8400-e29b-41d4-a716-446655440006',
            'subject': 'Matematik',
            'grade_type': 'EXAM',
            'score': 95.0,
            'max_score': 100.0,
            'exam_date': datetime(2024, 9, 15),
            'term': '1',
            'academic_year': '2024-2025',
            'notes': 'Mükemmel',
            'created_by': '990e8400-e29b-41d4-a716-446655440004',
            'updated_by': '990e8400-e29b-41d4-a716-446655440004'
        },
        {
            'id': 'ii0e8400-e29b-41d4-a716-446655440027',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'class_id': 'aa0e8400-e29b-41d4-a716-446655440001',
            'student_id': 'cc0e8400-e29b-41d4-a716-446655440006',
            'subject': 'Türkçe',
            'grade_type': 'EXAM',
            'score': 92.0,
            'max_score': 100.0,
            'exam_date': datetime(2024, 9, 20),
            'term': '1',
            'academic_year': '2024-2025',
            'created_by': '990e8400-e29b-41d4-a716-446655440004',
            'updated_by': '990e8400-e29b-41d4-a716-446655440004'
        },
    ]
    
    for grade_data in grades_data:
        grade = Grade(**grade_data)
        session.add(grade)
    
    await session.commit()
    print(f"Seeded {len(grades_data)} grades")


async def seed_attendance_records(session):
    """Seed comprehensive attendance records for pattern analysis"""
    print("Seeding attendance records...")
    
    # Check if attendance records already exist
    existing_attendance = await session.execute(select(AttendanceRecord).limit(1))
    if existing_attendance.scalar_one_or_none():
        print("Attendance records already exist, skipping...")
        return
    
    attendance_data = []
    
    # Generate 30 days of attendance data for multiple students
    students = [
        'cc0e8400-e29b-41d4-a716-446655440001',  # Ahmet - mostly present
        'cc0e8400-e29b-41d4-a716-446655440002',  # Elif - excellent attendance
        'cc0e8400-e29b-41d4-a716-446655440003',  # Mustafa - some absences
        'cc0e8400-e29b-41d4-a716-446655440005',  # Emre - critical attendance issues
        'cc0e8400-e29b-41d4-a716-446655440006',  # Selin - perfect attendance
        'cc0e8400-e29b-41d4-a716-446655440007',  # Kaan - good attendance
        'cc0e8400-e29b-41d4-a716-446655440008',  # Defne - good attendance
    ]
    
    attendance_patterns = {
        'cc0e8400-e29b-41d4-a716-446655440001': ['PRESENT', 'PRESENT', 'PRESENT', 'ABSENT', 'PRESENT'],  # 80% present
        'cc0e8400-e29b-41d4-a716-446655440002': ['PRESENT', 'PRESENT', 'PRESENT', 'PRESENT', 'PRESENT'],  # 100% present
        'cc0e8400-e29b-41d4-a716-446655440003': ['LATE', 'PRESENT', 'ABSENT', 'PRESENT', 'PRESENT'],  # 60% present
        'cc0e8400-e29b-41d4-a716-446655440005': ['ABSENT', 'PRESENT', 'ABSENT', 'LATE', 'PRESENT'],  # 40% present
        'cc0e8400-e29b-41d4-a716-446655440006': ['PRESENT', 'PRESENT', 'PRESENT', 'PRESENT', 'PRESENT'],  # 100% present
        'cc0e8400-e29b-41d4-a716-446655440007': ['PRESENT', 'PRESENT', 'PRESENT', 'PRESENT', 'PRESENT'],  # 100% present
        'cc0e8400-e29b-41d4-a716-446655440008': ['PRESENT', 'PRESENT', 'PRESENT', 'PRESENT', 'PRESENT'],  # 100% present
    }
    
    record_id = 1000
    start_date = datetime(2024, 9, 2)
    
    for week in range(6):  # 6 weeks
        for day in range(5):  # 5 days per week
            current_date = start_date + timedelta(days=week*7 + day)
            
            for student_id in students:
                pattern = attendance_patterns[student_id]
                status = pattern[day % len(pattern)]
                
                notes = None
                if status == 'ABSENT':
                    if student_id == 'cc0e8400-e29b-41d4-a716-446655440001':
                        notes = 'Hastalık'
                    elif student_id == 'cc0e8400-e29b-41d4-a716-446655440003':
                        notes = 'Raporlu'
                    elif student_id == 'cc0e8400-e29b-41d4-a716-446655440005':
                        notes = 'Mazeretsiz'
                elif status == 'LATE':
                    notes = 'Trafik'
                
                attendance_data.append({
                    'id': f'hh1e8400-e29b-41d4-a716-44665544{record_id:06d}',
                    'organization_id': '550e8400-e29b-41d4-a716-446655440000',
                    'branch_id': '660e8400-e29b-41d4-a716-446655440001',
                    'class_id': 'aa0e8400-e29b-41d4-a716-446655440001',
                    'student_id': student_id,
                    'attendance_date': current_date,
                    'status': AttendanceStatus.PRESENT if status == 'PRESENT' else 
                              AttendanceStatus.ABSENT if status == 'ABSENT' else
                              AttendanceStatus.LATE,
                    'notes': notes,
                    'recorded_by': '990e8400-e29b-41d4-a716-446655440004',
                    'created_by': '990e8400-e29b-41d4-a716-446655440004',
                    'updated_by': '990e8400-e29b-41d4-a716-446655440004'
                })
                record_id += 1
    
    for att_data in attendance_data:
        attendance = AttendanceRecord(**att_data)
        session.add(attendance)
    
    await session.commit()
    print(f"Seeded {len(attendance_data)} attendance records")


async def seed_additional_debts(session):
    """Seed additional debt data for financial analysis"""
    print("Seeding additional debts...")
    
    # Check if we already have debts with jj0e8400 prefix
    existing_debts = await session.execute(select(Debt).where(Debt.id.like('jj0e8400%')))
    existing_debt_list = list(existing_debts.scalars().all())
    if existing_debt_list:
        print(f"Found {len(existing_debt_list)} existing debts with jj0e8400 prefix, skipping...")
        return
    
    debts_data = [
        {
            'id': 'jj0e8400-e29b-41d4-a716-446655440007',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'student_id': 'cc0e8400-e29b-41d4-a716-446655440006',
            'debt_type': DebtType.EDUCATION,
            'description': 'Ekim 2024 Eğitim Ücreti',
            'amount': Decimal('5000.00'),
            'paid_amount': Decimal('5000.00'),
            'status': DebtStatus.PAID,
            'due_date': datetime(2024, 10, 30),
            'created_by': '550e8400-e29b-41d4-a716-446655440000',
            'updated_by': '550e8400-e29b-41d4-a716-446655440000'
        },
        {
            'id': 'jj0e8400-e29b-41d4-a716-446655440008',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'student_id': 'cc0e8400-e29b-41d4-a716-446655440007',
            'debt_type': DebtType.EDUCATION,
            'description': 'Ekim 2024 Eğitim Ücreti',
            'amount': Decimal('5000.00'),
            'paid_amount': Decimal('3000.00'),
            'status': DebtStatus.PARTIALLY_PAID,
            'due_date': datetime(2024, 10, 30),
            'created_by': '550e8400-e29b-41d4-a716-446655440000',
            'updated_by': '550e8400-e29b-41d4-a716-446655440000'
        },
        {
            'id': 'jj0e8400-e29b-41d4-a716-446655440009',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'student_id': 'cc0e8400-e29b-41d4-a716-446655440008',
            'debt_type': DebtType.FOOD,
            'description': 'Ekim 2024 Yemek Ücreti',
            'amount': Decimal('800.00'),
            'paid_amount': Decimal('0.00'),
            'status': DebtStatus.UNPAID,
            'due_date': datetime(2024, 10, 30),
            'created_by': '550e8400-e29b-41d4-a716-446655440000',
            'updated_by': '550e8400-e29b-41d4-a716-446655440000'
        },
        {
            'id': 'jj0e8400-e29b-41d4-a716-446655440010',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'student_id': 'cc0e8400-e29b-41d4-a716-446655440009',
            'debt_type': DebtType.SERVICE,
            'description': 'Ekim 2024 Servis Ücreti',
            'amount': Decimal('1200.00'),
            'paid_amount': Decimal('600.00'),
            'status': DebtStatus.PARTIALLY_PAID,
            'due_date': datetime(2024, 10, 30),
            'created_by': '550e8400-e29b-41d4-a716-446655440000',
            'updated_by': '550e8400-e29b-41d4-a716-446655440000'
        },
        {
            'id': 'jj0e8400-e29b-41d4-a716-446655440011',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'student_id': 'cc0e8400-e29b-41d4-a716-446655440010',
            'debt_type': DebtType.EDUCATION,
            'description': 'Ekim 2024 Eğitim Ücreti',
            'amount': Decimal('5000.00'),
            'paid_amount': Decimal('0.00'),
            'status': DebtStatus.UNPAID,
            'due_date': datetime(2024, 10, 30),
            'created_by': '550e8400-e29b-41d4-a716-446655440000',
            'updated_by': '550e8400-e29b-41d4-a716-446655440000'
        },
        {
            'id': 'jj0e8400-e29b-41d4-a716-446655440012',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'student_id': 'cc0e8400-e29b-41d4-a716-446655440011',
            'debt_type': DebtType.STATIONERY,
            'description': 'Ekim 2024 Kırtasiye',
            'amount': Decimal('500.00'),
            'paid_amount': Decimal('500.00'),
            'status': DebtStatus.PAID,
            'due_date': datetime(2024, 10, 30),
            'created_by': '550e8400-e29b-41d4-a716-446655440000',
            'updated_by': '550e8400-e29b-41d4-a716-446655440000'
        },
        {
            'id': 'jj0e8400-e29b-41d4-a716-446655440013',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'student_id': 'cc0e8400-e29b-41d4-a716-446655440012',
            'debt_type': DebtType.ACTIVITY,
            'description': 'Ekim 2024 Etkinlik',
            'amount': Decimal('300.00'),
            'paid_amount': Decimal('0.00'),
            'status': DebtStatus.UNPAID,
            'due_date': datetime(2024, 10, 30),
            'created_by': '550e8400-e29b-41d4-a716-446655440000',
            'updated_by': '550e8400-e29b-41d4-a716-446655440000'
        },
        {
            'id': 'jj0e8400-e29b-41d4-a716-446655440014',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'student_id': 'cc0e8400-e29b-41d4-a716-446655440013',
            'debt_type': DebtType.EDUCATION,
            'description': 'Ekim 2024 Eğitim Ücreti',
            'amount': Decimal('5000.00'),
            'paid_amount': Decimal('2500.00'),
            'status': DebtStatus.PARTIALLY_PAID,
            'due_date': datetime(2024, 10, 30),
            'created_by': '550e8400-e29b-41d4-a716-446655440000',
            'updated_by': '550e8400-e29b-41d4-a716-446655440000'
        },
        {
            'id': 'jj0e8400-e29b-41d4-a716-446655440015',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'student_id': 'cc0e8400-e29b-41d4-a716-446655440014',
            'debt_type': DebtType.FOOD,
            'description': 'Ekim 2024 Yemek Ücreti',
            'amount': Decimal('800.00'),
            'paid_amount': Decimal('800.00'),
            'status': DebtStatus.PAID,
            'due_date': datetime(2024, 10, 30),
            'created_by': '550e8400-e29b-41d4-a716-446655440000',
            'updated_by': '550e8400-e29b-41d4-a716-446655440000'
        },
        {
            'id': 'jj0e8400-e29b-41d4-a716-446655440016',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'student_id': 'cc0e8400-e29b-41d4-a716-446655440015',
            'debt_type': DebtType.SERVICE,
            'description': 'Ekim 2024 Servis Ücreti',
            'amount': Decimal('1200.00'),
            'paid_amount': Decimal('0.00'),
            'status': DebtStatus.OVERDUE,
            'due_date': datetime(2024, 10, 15),
            'created_by': '550e8400-e29b-41d4-a716-446655440000',
            'updated_by': '550e8400-e29b-41d4-a716-446655440000'
        },
    ]
    
    for debt_data in debts_data:
        debt = Debt(**debt_data)
        session.add(debt)
        await session.commit()  # Commit each individually to avoid bulk insert issues
    
    print(f"Seeded {len(debts_data)} additional debts")


async def seed_notification_jobs(session):
    """Seed notification jobs for parent sentiment analysis"""
    print("Seeding notification jobs...")
    
    # Check if we already have notification jobs with mm0e8400 prefix
    existing_notifications = await session.execute(select(NotificationJob).where(NotificationJob.id.like('mm0e8400%')))
    existing_notification_list = list(existing_notifications.scalars().all())
    if existing_notification_list:
        print(f"Found {len(existing_notification_list)} existing notification jobs with mm0e8400 prefix, skipping...")
        return
    
    notifications_data = [
        {
            'id': 'mm0e8400-e29b-41d4-a716-446655440001',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'channel': NotificationChannel.EMAIL,
            'subject': 'Eylül Ayı Raporu',
            'body': 'Sayın velimiz, çocuğunuzun eylül ayı performans raporu ektedir.',
            'status': NotificationStatus.SENT,
            'scheduled_at': datetime(2024, 9, 30, 10, 0),
            'processed_at': datetime(2024, 9, 30, 10, 5),
            'retry_count': 0,
            'max_retries': 3
        },
        {
            'id': 'mm0e8400-e29b-41d4-a716-446655440002',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'channel': NotificationChannel.SMS,
            'subject': 'Ödeme Hatırlatma',
            'body': 'Sayın velimiz, ödeme hatırlatmasıdır.',
            'status': NotificationStatus.SENT,
            'scheduled_at': datetime(2024, 9, 25, 9, 0),
            'processed_at': datetime(2024, 9, 25, 9, 2),
            'retry_count': 0,
            'max_retries': 3
        },
        {
            'id': 'mm0e8400-e29b-41d4-a716-446655440003',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'channel': NotificationChannel.WHATSAPP,
            'subject': 'Duyuru',
            'body': 'Okulumuzda yeni etkinlik başlıyor.',
            'status': NotificationStatus.SENT,
            'scheduled_at': datetime(2024, 9, 20, 14, 0),
            'processed_at': datetime(2024, 9, 20, 14, 5),
            'retry_count': 0,
            'max_retries': 3
        },
        {
            'id': 'mm0e8400-e29b-41d4-a716-446655440004',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'channel': NotificationChannel.EMAIL,
            'subject': 'Devamsızlık Uyarısı',
            'body': 'Çocuğunuzun devamsızlık durumu hakkında bilgilendirme.',
            'status': NotificationStatus.SENT,
            'scheduled_at': datetime(2024, 9, 15, 11, 0),
            'processed_at': datetime(2024, 9, 15, 11, 3),
            'retry_count': 0,
            'max_retries': 3
        },
        {
            'id': 'mm0e8400-e29b-41d4-a716-446655440005',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'channel': NotificationChannel.SMS,
            'subject': 'Etkinlik Daveti',
            'body': 'Okulumuz etkinliğine davetlisiniz.',
            'status': NotificationStatus.SENT,
            'scheduled_at': datetime(2024, 9, 10, 16, 0),
            'processed_at': datetime(2024, 9, 10, 16, 2),
            'retry_count': 0,
            'max_retries': 3
        },
        {
            'id': 'mm0e8400-e29b-41d4-a716-446655440006',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'channel': NotificationChannel.EMAIL,
            'subject': 'Haftalık Bülten',
            'body': 'Haftalık okul bülteni.',
            'status': NotificationStatus.SENT,
            'scheduled_at': datetime(2024, 9, 5, 8, 0),
            'processed_at': datetime(2024, 9, 5, 8, 5),
            'retry_count': 0,
            'max_retries': 3
        },
        {
            'id': 'mm0e8400-e29b-41d4-a716-446655440007',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'channel': NotificationChannel.WHATSAPP,
            'subject': 'Özel Ders Bilgisi',
            'body': 'Çocuğunuz için özel ders programı.',
            'status': NotificationStatus.SENT,
            'scheduled_at': datetime(2024, 10, 5, 10, 0),
            'processed_at': datetime(2024, 10, 5, 10, 3),
            'retry_count': 0,
            'max_retries': 3
        },
        {
            'id': 'mm0e8400-e29b-41d4-a716-446655440008',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'channel': NotificationChannel.SMS,
            'subject': 'Veli Toplantısı',
            'body': 'Veli toplantısı daveti.',
            'status': NotificationStatus.SENT,
            'scheduled_at': datetime(2024, 10, 8, 9, 0),
            'processed_at': datetime(2024, 10, 8, 9, 2),
            'retry_count': 0,
            'max_retries': 3
        },
        {
            'id': 'mm0e8400-e29b-41d4-a716-446655440009',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'channel': NotificationChannel.EMAIL,
            'subject': 'Akademik İlerleme',
            'body': 'Çocuğunuzun akademik ilerlemesi.',
            'status': NotificationStatus.SENT,
            'scheduled_at': datetime(2024, 10, 10, 12, 0),
            'processed_at': datetime(2024, 10, 10, 12, 5),
            'retry_count': 0,
            'max_retries': 3
        },
        {
            'id': 'mm0e8400-e29b-41d4-a716-446655440010',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'channel': NotificationChannel.WHATSAPP,
            'subject': 'Ödeme Onayı',
            'body': 'Ödemeniz onaylandı.',
            'status': NotificationStatus.SENT,
            'scheduled_at': datetime(2024, 10, 12, 15, 0),
            'processed_at': datetime(2024, 10, 12, 15, 3),
            'retry_count': 0,
            'max_retries': 3
        },
    ]
    
    for notif_data in notifications_data:
        notification = NotificationJob(**notif_data)
        session.add(notification)
        await session.commit()  # Commit each individually to avoid bulk insert issues
    
    print(f"Seeded {len(notifications_data)} notification jobs")


async def seed_announcements(session):
    """Seed announcements for the system"""
    print("Seeding announcements...")
    
    from app.infrastructure.models.models import AnnouncementStatus
    
    # Check if we already have announcements with nn0e8400 prefix
    existing_announcements = await session.execute(select(Announcement).where(Announcement.id.like('nn0e8400%')))
    existing_announcement_list = list(existing_announcements.scalars().all())
    if existing_announcement_list:
        print(f"Found {len(existing_announcement_list)} existing announcements with nn0e8400 prefix, skipping...")
        return
    
    announcements_data = [
        {
            'id': 'nn0e8400-e29b-41d4-a716-446655440001',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'class_id': None,
            'student_id': None,
            'title': 'Eylül Ayı Veli Toplantısı',
            'content': 'Eylül ayı veli toplantısı 25 Eylül Salı günü saat 14:00\'te okulumuzda yapılacaktır. Tüm velilerimiz davetlidir.',
            'audience': AnnouncementAudience.ALL_PARENTS,
            'channels': ['EMAIL', 'SMS', 'WHATSAPP'],
            'status': AnnouncementStatus.SENT,
            'sent_at': datetime(2024, 9, 1, 10, 5),
            'created_by': '990e8400-e29b-41d4-a716-446655440001'
        },
        {
            'id': 'nn0e8400-e29b-41d4-a716-446655440002',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'class_id': 'aa0e8400-e29b-41d4-a716-446655440001',
            'student_id': None,
            'title': 'Minikler A Sınıfı Etkinliği',
            'content': 'Minikler A sınıfı için resim etkinliği 10 Ekim Perşembe günü yapılacaktır.',
            'audience': AnnouncementAudience.CLASS_PARENTS,
            'channels': ['EMAIL', 'WHATSAPP'],
            'status': AnnouncementStatus.SENT,
            'sent_at': datetime(2024, 9, 15, 9, 5),
            'created_by': '990e8400-e29b-41d4-a716-446655440004'
        },
        {
            'id': 'nn0e8400-e29b-41d4-a716-446655440003',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': None,
            'class_id': None,
            'student_id': None,
            'title': 'Okul Kapanış Tarihi',
            'content': '2024-2025 eğitim yılı kapanış tarihi 20 Haziran 2025 olarak belirlenmiştir.',
            'audience': AnnouncementAudience.ALL_PARENTS,
            'channels': ['EMAIL', 'SMS'],
            'status': AnnouncementStatus.SENT,
            'sent_at': datetime(2024, 9, 20, 11, 5),
            'created_by': '990e8400-e29b-41d4-a716-446655440001'
        },
        {
            'id': 'nn0e8400-e29b-41d4-a716-446655440004',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'class_id': None,
            'student_id': None,
            'title': 'Yemek Menüsü Güncellemesi',
            'content': 'Ekim ayı yemek menüsü güncellenmiştir. Detaylar için okul web sitesini ziyaret ediniz.',
            'audience': AnnouncementAudience.BRANCH_PARENTS,
            'channels': ['EMAIL'],
            'status': AnnouncementStatus.SENT,
            'sent_at': datetime(2024, 9, 25, 8, 5),
            'created_by': '990e8400-e29b-41d4-a716-446655440003'
        },
        {
            'id': 'nn0e8400-e29b-41d4-a716-446655440005',
            'organization_id': '550e8400-e29b-41d4-a716-446655440000',
            'branch_id': '660e8400-e29b-41d4-a716-446655440001',
            'class_id': 'aa0e8400-e29b-41d4-a716-446655440002',
            'student_id': None,
            'title': 'Minikler B Sınıfı Gezisi',
            'content': 'Minikler B sınıfı için müze gezisi 15 Ekim Salı günü planlanmıştır.',
            'audience': AnnouncementAudience.CLASS_PARENTS,
            'channels': ['EMAIL', 'SMS', 'WHATSAPP'],
            'status': AnnouncementStatus.SENT,
            'sent_at': datetime(2024, 10, 1, 10, 5),
            'created_by': '990e8400-e29b-41d4-a716-446655440004'
        },
    ]
    
    for announcement_data in announcements_data:
        announcement = Announcement(**announcement_data)
        session.add(announcement)
        await session.commit()  # Commit each individually to avoid bulk insert issues
    
    print(f"Seeded {len(announcements_data)} announcements")


async def seed_daily_reports(session):
    """Seed daily development reports for wellness analysis"""
    print("Seeding daily development reports...")
    
    # Get first class and students
    class_result = await session.execute(
        select(ClassRoom).limit(1)
    )
    first_class = class_result.scalar_one_or_none()
    
    if not first_class:
        print("No class found, skipping daily reports seeding")
        return
    
    student_result = await session.execute(
        select(Student).where(Student.class_id == first_class.id).limit(10)
    )
    students = student_result.scalars().all()
    
    if not students:
        print("No students found, skipping daily reports seeding")
        return
    
    # Generate daily reports for last 7 days
    daily_reports_data = []
    report_counter = 1
    
    for day_offset in range(7):
        report_date = datetime.now() - timedelta(days=day_offset)
        
        for student in students:
            mood_options = ['HAPPY', 'CALM', 'UNSETTLED', 'TIRED']
            sleep_options = ['SLEPT_WELL', 'SHORT', 'NO_SLEEP']
            meal_options = ['ALL', 'HALF', 'NONE']
            
            daily_reports_data.append({
                'id': uuid.uuid4(),  # Generate proper UUID
                'student_id': student.id,
                'class_id': first_class.id,
                'date': report_date.date(),
                'mood': mood_options[report_counter % 4],
                'sleep_status': sleep_options[report_counter % 3],
                'meal_status': meal_options[report_counter % 3],
                'activities': ['resim', 'oyun', 'müzik'] if report_counter % 2 == 0 else ['oyun', 'okuma'],
                'teacher_notes': f'Günlük gelişim raporu {report_counter}'
            })
            report_counter += 1
    
    for report_data in daily_reports_data:
        report = DailyDevelopmentReport(**report_data)
        session.add(report)
        await session.commit()  # Commit each individually
    
    print(f"Seeded {len(daily_reports_data)} daily development reports")


async def main():
    """Main seed function"""
    # Check if running in production
    seed_demo_data = os.getenv("SEED_DEMO_DATA", "false").lower() == "true"
    app_env = os.getenv("APP_ENV", "production").lower()
    
    if not seed_demo_data and app_env == "production":
        print("ERROR: Cannot seed comprehensive data in production. Set SEED_DEMO_DATA=true to override.")
        return
    
    print("Starting comprehensive data seeding...")
    
    from app.core.database import AsyncSessionLocal
    
    async with AsyncSessionLocal() as session:
        try:
            # Each seed function now handles its own existence checks
            await seed_grades(session)
            await seed_attendance_records(session)
            await seed_additional_debts(session)
            await seed_notification_jobs(session)
            await seed_announcements(session)
            await seed_daily_reports(session)
            
            print("Comprehensive data seeding completed successfully!")
            
        except Exception as e:
            print(f"Error during seeding: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()


if __name__ == "__main__":
    asyncio.run(main())
