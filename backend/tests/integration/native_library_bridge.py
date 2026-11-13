"""Opt-in native catalog/borrow/return acceptance against a fresh temporary DB."""
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
from app.infrastructure.models.models import Branch, LibraryBook, LibraryLoan, NotificationJob, Payment, Permission, Role, User


async def test_native_library_real_api(materials_client):  # noqa: F811
    client, sessions, data = materials_client
    async with sessions() as db:
        existing = {p.code:p for p in (await db.execute(select(Permission))).scalars()}
        permissions = {code:existing.get(code) or Permission(code=code,name=code,module=code.split('.')[0]) for code in ['library.read','library.write','student.read','students.read']}
        writer_role = Role(name='Library operator',slug='native_library_operator',organization_id=data['org'].id,permissions=list(permissions.values()))
        reader_role = Role(name='Library reader',slug='native_library_reader',organization_id=data['org'].id,permissions=[permissions['library.read']])
        branch = await db.get(Branch,data['branch'].id)
        writer = User(email='native-library@example.com',password_hash=hash_password('Synthetic-pass-2026!'),first_name='Library',last_name='Operator',organization_id=data['org'].id,roles=[writer_role],branches=[branch])
        reader = User(email='native-library-reader@example.com',password_hash=hash_password('Synthetic-pass-2026!'),first_name='Library',last_name='Reader',organization_id=data['org'].id,roles=[reader_role],branches=[branch])
        db.add_all([writer,reader]);await db.commit()
    loop=asyncio.get_running_loop();events=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        def forward(self):
            content=self.rfile.read(int(self.headers.get('Content-Length','0')))
            headers={k:v for k,v in self.headers.items() if k.lower() not in ('host','connection','content-length')}
            response=asyncio.run_coroutine_threadsafe(client.request(self.command,self.path,headers=headers,content=content),loop).result(timeout=60)
            events.append({'method':self.command,'path':self.path,'status':response.status_code})
            if response.status_code>=400:print('Library bridge rejected',self.command,self.path,response.status_code,response.text[:350],flush=True)
            self.send_response(response.status_code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(response.content)));self.send_header('Connection','close');self.end_headers();self.wfile.write(response.content)
        do_GET=forward
        do_POST=forward
        do_PUT=forward
        do_DELETE=forward
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    root=Path(__file__).resolve().parents[3]
    env=os.environ.copy();env.update({'NATIVE_TEST_API_URL':f'http://127.0.0.1:{server.server_port}/api/','NATIVE_TEST_STUDENT':str(data['children'][0].id),'NATIVE_TEST_FOREIGN_STUDENT':str(data['stranger'].id)})
    command=['cmd.exe','/d','/c',env['NATIVE_GRADLE_EXECUTABLE'],'--no-daemon','--no-configuration-cache','--offline','--max-workers','1','--no-parallel','-PnativeBackendAcceptance=true',':app:testDebugUnitTest','--tests','com.example.NativeLibraryBackendAcceptance','-g',env['NATIVE_GRADLE_HOME'],'--project-cache-dir',env['NATIVE_GRADLE_PROJECT_CACHE']]
    try:
        with Path(env['NATIVE_ACCEPTANCE_LOG']).open('wb') as stream:
            process=await asyncio.create_subprocess_exec(*command,cwd=root/'mobile-android',env=env,stdout=stream,stderr=stream)
            assert await asyncio.wait_for(process.wait(),timeout=1500)==0,Path(env['NATIVE_ACCEPTANCE_LOG']).read_text(encoding='utf-8',errors='replace')[-5000:]
        assert any(e['method']=='POST' and e['path']=='/api/library/loans/borrow' and e['status']==403 for e in events)
        assert any(e['method']=='POST' and e['path']=='/api/library/loans/borrow' and e['status'] in (403,404) for e in events)
        assert any(e['method']=='PUT' and e['path'].endswith('/return') and e['status']==409 for e in events)
        async with sessions() as db:
            book=(await db.execute(select(LibraryBook).where(LibraryBook.title=='Native edited catalog'))).scalar_one()
            assert book.total_copies==book.available_copies==2 and book.barcode=='NATIVE-ACCEPTANCE' and book.publisher=='Acceptance Press' and book.location=='A-2'
            loans=(await db.execute(select(LibraryLoan).where(LibraryLoan.book_id==book.id))).scalars().all()
            assert len(loans)==1 and loans[0].student_id==data['children'][0].id and loans[0].return_date is not None
            assert (await db.execute(select(LibraryBook.id).where(LibraryBook.title=='Native removable catalog'))).first() is None
            for model in (Payment,NotificationJob):assert (await db.execute(select(func.count()).select_from(model))).scalar_one()==0
        Path(env['NATIVE_ACCEPTANCE_REPORT']).write_text(json.dumps({'real_api':True,'temporary_database':'sqlite','actual_native_login':True,'canonical_catalog_create_list':True,'detail_and_edit_persisted':True,'stale_edit_conflict':True,'delete_without_history_persisted':True,'delete_with_loan_history_conflict':True,'real_student_options':True,'borrow_and_put_return_persisted':True,'stock_restored':2,'loan_rows':1,'foreign_student_rejected':True,'reader_write_forbidden':True,'duplicate_return_conflict':True,'payment_rows':0,'notification_jobs':0,'real_message_delivery':0,'requests':events},indent=2),encoding='utf-8')
    finally:
        await asyncio.to_thread(server.shutdown);server.server_close();thread.join(timeout=5)
