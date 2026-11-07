import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import hash_password
from app.infrastructure.models.models import (
    Student, Grade, AttendanceRecord, Debt, Payment, Parent, User, ClassRoom, ClassTeacher, Branch
)

async def add_test_data():
    async for db in get_db():
        organization_id = 1
        
        # Mevcut verileri kontrol et
        student_result = await db.execute(select(Student).where(Student.organization_id == organization_id))
        students = student_result.scalars().all()
        
        class_result = await db.execute(select(ClassRoom).where(ClassRoom.organization_id == organization_id))
        classrooms = class_result.scalars().all()
        
        user_result = await db.execute(select(User).where(User.organization_id == organization_id))
        users = user_result.scalars().all()
        
        parent_result = await db.execute(select(Parent).where(Parent.organization_id == organization_id))
        parents = parent_result.scalars().all()
        
        print(f"Mevcut veriler:")
        print(f"  Ogrenci: {len(students)}")
        print(f"  Sinif: {len(classrooms)}")
        print(f"  Personel: {len(users)}")
        print(f"  Veli: {len(parents)}")
        
        # Eğer öğrenci yoksa, temel verileri oluştur
        if len(students) == 0:
            print("\nTemel veriler yok, olusturuluyor...")
            
            # 0. Branch oluştur
            try:
                branch = Branch(
                    organization_id=organization_id,
                    name="Ana Kampüs",
                    code="MAIN"
                )
                db.add(branch)
                await db.commit()
                await db.refresh(branch)
                print(f"  - Branch olusturuldu: {branch.name}")
            except Exception as e:
                print(f"  - Branch olusturma hatasi: {e}")
                await db.rollback()
                branch = None
            
            # 0.5. Super Admin kullanıcı oluştur
            try:
                super_admin = User(
                    organization_id=organization_id,
                    email="superadmin@scs360.com",
                    password_hash=hash_password("SuperAdmin123!"),
                    first_name="Super",
                    last_name="Admin",
                    phone="5550000000",
                    position="Super Administrator",
                    department="IT",
                    status="ACTIVE",
                    is_super_admin=True
                )
                db.add(super_admin)
                await db.commit()
                await db.refresh(super_admin)
                print(f"  - Super Admin olusturuldu: {super_admin.first_name} {super_admin.last_name}")
                print(f"    Email: {super_admin.email}")
                print(f"    Password: SuperAdmin123!")
            except Exception as e:
                print(f"  - Super Admin olusturma hatasi: {e}")
                await db.rollback()
                super_admin = None
            
            # 1. Sınıf oluştur
            try:
                classroom = ClassRoom(
                    organization_id=organization_id,
                    branch_id=branch.id if branch else None,
                    name="10-A",
                    code="10A",
                    capacity=30,
                    academic_year="2024-2025",
                    is_active=True
                )
                db.add(classroom)
                await db.commit()
                await db.refresh(classroom)
                print(f"  - Sinif olusturuldu: {classroom.name}")
            except Exception as e:
                print(f"  - Sinif olusturma hatasi: {e}")
                await db.rollback()
                classroom = None
            
            # 2. Personel oluştur
            try:
                teacher = User(
                    organization_id=organization_id,
                    email="ahmet.veli@scs360.com",
                    password_hash=hash_password("Teacher123!"),
                    first_name="Ahmet",
                    last_name="Veli",
                    phone="5551234567",
                    position="Ogretmen",
                    department="Matematik",
                    status="ACTIVE"
                )
                db.add(teacher)
                await db.commit()
                await db.refresh(teacher)
                print(f"  - Personel olusturuldu: {teacher.first_name} {teacher.last_name}")
            except Exception as e:
                print(f"  - Personel olusturma hatasi: {e}")
                await db.rollback()
                teacher = None
            
            # 3. Sınıf öğretmen ataması
            if classroom and teacher:
                try:
                    class_teacher = ClassTeacher(
                        organization_id=organization_id,
                        class_id=classroom.id,
                        user_id=teacher.id
                    )
                    db.add(class_teacher)
                    await db.commit()
                    print(f"  - Sinif ogretmen atamasi yapildi")
                except Exception as e:
                    print(f"  - Sinif ogretmen atama hatasi: {e}")
            
            # 4. Öğrenciler oluştur
            first_names = ["Ali", "Ayse", "Mehmet", "Fatma", "Mustafa", "Zeynep", "Can", "Elif", "Emre", "Selin"]
            last_names = ["Yilmaz", "Demir", "Kaya", "Celik", "Aydin", "Oz", "Yildiz", "Koc", "Arslan", "Polat"]
            
            for i in range(10):
                try:
                    student = Student(
                        organization_id=organization_id,
                        branch_id=branch.id if branch else None,
                        class_id=classroom.id if classroom else None,
                        student_number=f"2024{i+1:03d}",
                        first_name=first_names[i],
                        last_name=last_names[i],
                        gender="MALE" if i % 2 == 0 else "FEMALE",
                        birth_date=datetime.now() - timedelta(days=15*365 + i*100),
                        enrollment_date=datetime.now() - timedelta(days=30),
                        status="ACTIVE"
                    )
                    db.add(student)
                    await db.flush()
                except Exception as e:
                    print(f"  - Ogrenci {i+1} olusturma hatasi: {e}")
            
            await db.commit()
            print(f"  - 10 ogrenci olusturuldu")
            
            # 5. Veliler oluştur
            for i in range(10):
                try:
                    parent = Parent(
                        organization_id=organization_id,
                        first_name=first_names[i],
                        last_name=last_names[i],
                        relation_type="FATHER" if i % 2 == 0 else "MOTHER",
                        phone=f"555{10000000 + i}",
                        email=f"{first_names[i].lower()}.{last_names[i].lower()}@email.com",
                        receive_notifications=True
                    )
                    db.add(parent)
                    await db.flush()
                except Exception as e:
                    print(f"  - Veli {i+1} olusturma hatasi: {e}")
            
            await db.commit()
            print(f"  - 10 veli olusturuldu")
            
            # Verileri yeniden yükle
            student_result = await db.execute(select(Student).where(Student.organization_id == organization_id))
            students = student_result.scalars().all()
            
            parent_result = await db.execute(select(Parent).where(Parent.organization_id == organization_id))
            parents = parent_result.scalars().all()
        
        # 2. Öğrenci notları ekle
        grade_types = ["Vize", "Final", "Odev", "Quiz"]
        subjects = ["Matematik", "Turkce", "Fen", "Sosyal"]
        
        for student in students[:10]:
            for subject in subjects:
                for i in range(5):
                    score = 50 + (i * 8) + (hash(f"{student.id}{subject}{i}") % 30)
                    grade = Grade(
                        student_id=student.id,
                        organization_id=organization_id,
                        grade_type=f"{subject} {grade_types[i % 4]}",
                        score=Decimal(str(score)),
                        created_at=datetime.now() - timedelta(days=i * 10)
                    )
                    db.add(grade)
        
        await db.commit()
        print(f"+ {len(students[:10]) * 5 * 4} not eklendi")
        
        # 3. Devamsızlık kayıtları ekle (son 30 gün)
        for student in students[:15]:
            for day in range(30):
                date = datetime.now() - timedelta(days=day)
                
                if date.weekday() >= 5:
                    status_prob = 0.3
                else:
                    status_prob = 0.1
                
                import random
                if random.random() < status_prob:
                    status = "ABSENT"
                elif random.random() < 0.15:
                    status = "EXCUSED"
                else:
                    status = "PRESENT"
                
                attendance = AttendanceRecord(
                    student_id=student.id,
                    organization_id=organization_id,
                    attendance_date=date.date(),
                    status=status
                )
                db.add(attendance)
        
        await db.commit()
        print(f"+ {len(students[:15]) * 30} devamsizlik kaydi eklendi")
        
        # 4. Borçlar ekle
        for student in students[:20]:
            amount = Decimal(str(5000 + (hash(str(student.id)) % 10000)))
            debt = Debt(
                student_id=student.id,
                organization_id=organization_id,
                amount=amount,
                paid_amount=Decimal("0"),
                due_date=datetime.now() + timedelta(days=30 + (hash(str(student.id)) % 60)),
                status="UNPAID"
            )
            db.add(debt)
        
        await db.commit()
        print(f"+ {len(students[:20])} borc eklendi")
        
        # 5. Ödemeler ekle (son 6 ay)
        for i in range(30):
            payment = Payment(
                organization_id=organization_id,
                amount=Decimal(str(10000 + (i * 500))),
                created_at=datetime.now() - timedelta(days=i * 6)
            )
            db.add(payment)
        
        await db.commit()
        print(f"+ 30 odeme kaydi eklendi")
        
        # 6. Bazı borçları kısmen ödenmiş yap
        for student in students[:10]:
            debt_result = await db.execute(
                select(Debt).where(Debt.student_id == student.id).limit(1)
            )
            debt = debt_result.scalar_one_or_none()
            if debt:
                debt.paid_amount = debt.amount * Decimal("0.6")
                debt.status = "PARTIAL"
        
        await db.commit()
        print(f"+ {len(students[:10])} borc kismen odenmis olarak guncellendi")
        
        # 7. Veliler için bildirim tercihleri
        for parent in parents[:15]:
            parent.receive_notifications = True
        
        await db.commit()
        print(f"+ {len(parents[:15])} veli bildirim tercihleri guncellendi")
        
        print("\nTest verileri basariyla eklendi!")
        print("\nOzet:")
        print(f"- {len(students[:10]) * 5 * 4} ogrenci notu")
        print(f"- {len(students[:15]) * 30} devamsizlik kaydi")
        print(f"- {len(students[:20])} borc")
        print(f"- 30 odeme kaydi")
        print(f"- {len(parents[:15])} aktif veli")
        
        break

if __name__ == "__main__":
    asyncio.run(add_test_data())
