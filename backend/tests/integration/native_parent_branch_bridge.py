"""Opt-in native branch-limited contact creation acceptance; disposable DB only."""
import asyncio
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from sqlalchemy import func, select
from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.core.security import hash_password
from app.infrastructure.models.models import Branch, NotificationJob, Parent, Payment, Permission, Role, Student, StudentParent, User, UserRole


async def test_native_branch_contact_real_api(materials_client):  # noqa: F811
    client, sessions, data = materials_client
    async with sessions() as db:
        existing = {p.code: p for p in (await db.execute(select(Permission))).scalars()}
        codes = ['parents.read', 'parents.write', 'student.read', 'student.write', 'students.read', 'students.write']
        permissions = [existing.get(code) or Permission(code=code, name=code, module=code.split('.')[0]) for code in codes]
        role = Role(name='Branch contact manager', slug='branch_contact_manager', organization_id=data['org'].id, permissions=permissions)
        branch = await db.get(Branch, data['branch'].id)
        manager = User(email='native-branch@example.com', password_hash=hash_password('Synthetic-pass-2026!'), first_name='Branch', last_name='Manager', organization_id=data['org'].id, roles=[role], branches=[branch])
        db.add(manager)
        await db.flush()
        teacher = await db.get(User, data['teacher'].id)
        teacher.email = 'native-class-teacher@example.com'; teacher.password_hash = hash_password('Synthetic-pass-2026!')
        db.add(UserRole(user_id=teacher.id, role_id=role.id))
        other_class_student = Student(first_name='OtherClass', last_name='Student', organization_id=data['org'].id, branch_id=branch.id, class_id=data['other_class'].id)
        db.add(other_class_student)
        db.add_all([Parent(organization_id=data['org'].id, first_name=f'BranchSeed{n:03}', last_name='Contact') for n in range(101)])
        await db.commit()
    loop = asyncio.get_running_loop(); events = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass
        def forward(self):
            content = self.rfile.read(int(self.headers.get('Content-Length', '0')))
            headers = {k: v for k, v in self.headers.items() if k.lower() not in ('host', 'connection', 'content-length')}
            response = asyncio.run_coroutine_threadsafe(client.request(self.command, self.path, headers=headers, content=content), loop).result(timeout=60)
            events.append({'method': self.command, 'path': self.path, 'status': response.status_code})
            if response.status_code >= 400:
                print('Native branch rejected', self.command, self.path, response.status_code, response.text[:350], flush=True)
            self.send_response(response.status_code); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(response.content))); self.send_header('Connection', 'close'); self.end_headers(); self.wfile.write(response.content)
        do_GET = forward
        do_POST = forward
        do_PUT = forward
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler); thread = Thread(target=server.serve_forever, daemon=True); thread.start()
    root = Path(__file__).resolve().parents[3]
    env = os.environ.copy(); env.update({'NATIVE_TEST_API_URL': f'http://127.0.0.1:{server.server_port}/api/', 'NATIVE_TEST_ORGANIZATION': str(data['org'].id), 'NATIVE_TEST_BRANCH': str(data['branch'].id), 'NATIVE_TEST_STUDENT': str(data['children'][0].id), 'NATIVE_TEST_FOREIGN_STUDENT': str(data['stranger'].id), 'NATIVE_TEST_OTHER_CLASS_STUDENT': str(other_class_student.id)})
    command = ['cmd.exe', '/d', '/c', env['NATIVE_GRADLE_EXECUTABLE'], '--no-daemon', '--no-configuration-cache', '--offline', '--max-workers', '1', '--no-parallel', '-PnativeBackendAcceptance=true', ':app:testDebugUnitTest', '--tests', 'com.example.NativeParentBranchBackendAcceptance', '-g', env['NATIVE_GRADLE_HOME'], '--project-cache-dir', env['NATIVE_GRADLE_PROJECT_CACHE']]
    try:
        with Path(env['NATIVE_ACCEPTANCE_LOG']).open('wb') as stream:
            process = await asyncio.create_subprocess_exec(*command, cwd=root/'mobile-android', env=env, stdout=stream, stderr=stream)
            assert await asyncio.wait_for(process.wait(), timeout=1500) == 0, Path(env['NATIVE_ACCEPTANCE_LOG']).read_text(encoding='utf-8', errors='replace')[-5000:]
        assert sum(row['method'] == 'POST' and row['path'] == '/api/parents' for row in events) == 0
        assert sum(row['method'] == 'POST' and row['path'] == f"/api/students/{data['children'][0].id}/parents" and row['status'] == 200 for row in events) == 2
        assert any(row['path'] == f"/api/students/{data['stranger'].id}/parents" and row['status'] in (403, 404) for row in events)
        assert any(row['path'] == f"/api/students/{other_class_student.id}/parents" and row['status'] in (403, 404) for row in events)
        async with sessions() as db:
            created = (await db.execute(select(Parent).where(Parent.first_name == 'BranchCreated'))).scalar_one()
            assert created.phone == '05320000002' and created.organization_id == data['org'].id
            assert (await db.execute(select(func.count()).select_from(StudentParent).where(StudentParent.parent_id == created.id, StudentParent.student_id == data['children'][0].id))).scalar_one() == 1
            assert (await db.execute(select(func.count()).select_from(Parent).where(Parent.first_name == 'ForeignRejected'))).scalar_one() == 0
            teacher_created = (await db.execute(select(Parent).where(Parent.first_name == 'TeacherCreated'))).scalar_one()
            assert (await db.execute(select(func.count()).select_from(StudentParent).where(StudentParent.parent_id == teacher_created.id, StudentParent.student_id == data['children'][0].id))).scalar_one() == 1
            assert (await db.execute(select(func.count()).select_from(Parent).where(Parent.first_name == 'OtherClassRejected'))).scalar_one() == 0
            for model in (Payment, NotificationJob):
                assert (await db.execute(select(func.count()).select_from(model))).scalar_one() == 0
        Path(env['NATIVE_ACCEPTANCE_REPORT']).write_text(json.dumps({'real_api': True, 'temporary_database': 'sqlite', 'actual_native_login': True, 'branch_limited_custom_role': True, 'teacher_class_scoped': True, 'actual_student_options_scoped': True, 'other_class_rejected': True, 'unlinked_contacts_hidden': 101, 'atomic_contact_and_student_link': True, 'reload_edit_visible': True, 'foreign_student_rejected': True, 'payment_rows': 0, 'notification_jobs': 0, 'requests': events}, indent=2), encoding='utf-8')
    finally:
        await asyncio.to_thread(server.shutdown); server.server_close(); thread.join(timeout=5)
