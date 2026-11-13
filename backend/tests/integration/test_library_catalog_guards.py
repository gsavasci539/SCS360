"""Book edits must not manufacture copies or erase loan history."""
from uuid import uuid4
from datetime import UTC, datetime, timedelta
import pytest
from sqlalchemy import event, select, func
from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.core.security import create_access_token
from app.infrastructure.models.models import LibraryBook, NotificationJob, Payment, Permission, Role, Student, User, UserRole


async def headers(sessions, org, write=True, student_write=False):
    async with sessions() as db:
        codes=['library.read']+(['library.write'] if write else [])+(['student.write'] if student_write else [])
        existing={p.code:p for p in (await db.execute(select(Permission))).scalars()}
        role=Role(name='Catalog acceptance',slug='catalog_'+uuid4().hex,organization_id=org,
            permissions=[existing.get(c) or Permission(code=c,name=c,module='library') for c in codes])
        actor=User(email=f'{uuid4().hex}@example.com',password_hash='unused-test-password',first_name='Catalog',last_name='Actor',organization_id=org,roles=[role])
        db.add(actor);await db.commit()
        return {'Authorization':'Bearer '+create_access_token(actor.id)}


async def book(client,auth):
    response=await client.post('/api/library/books',headers=auth,json={'title':'Guarded catalog','author':'Recorded author','category':'Acceptance','total_copies':2})
    assert response.status_code==200,response.text
    return response.json()['data']['id']


async def borrow(client,auth,key,student):
    response=await client.post('/api/library/loans/borrow',headers=auth,json={'book_id':key,'student_id':str(student),'student_name':'ignored','student_number':'','class_name':'','duration_days':14})
    assert response.status_code==200,response.text
    return response.json()['data']['id']


async def test_edit_preserves_loan_stock_and_rejects_stale_snapshot(materials_client):
    client,sessions,data=materials_client;auth=await headers(sessions,data['org'].id)
    key=await book(client,auth);await borrow(client,auth,key,data['children'][0].id)
    original=(await client.get(f'/api/library/books/{key}',headers=auth)).json()['data']
    assert original['available_copies']==1 and original['organization_id']==str(data['org'].id)
    response=await client.put(f'/api/library/books/{key}',headers=auth,json={'total_copies':3,'expected_updated_at':original['updated_at']})
    assert response.status_code==200,response.text
    saved=response.json()['data'];assert saved['total_copies']==3 and saved['available_copies']==2
    assert (await client.put(f'/api/library/books/{key}',headers=auth,json={'available_copies':99})).status_code==409
    assert (await client.put(f'/api/library/books/{key}',headers=auth,json={'title':'Stale overwrite','expected_updated_at':original['updated_at']})).status_code==409
    fresh=(await client.get(f'/api/library/books/{key}',headers=auth)).json()['data']
    assert fresh['title']=='Guarded catalog' and fresh['available_copies']==2


async def test_active_copies_and_returned_loan_history_cannot_be_deleted(materials_client):
    client,sessions,data=materials_client;auth=await headers(sessions,data['org'].id);key=await book(client,auth)
    loans=[await borrow(client,auth,key,data['children'][0].id) for _ in range(2)]
    assert (await client.put(f'/api/library/books/{key}',headers=auth,json={'total_copies':1})).status_code==409
    assert (await client.delete(f'/api/library/books/{key}',headers=auth)).status_code==409
    for loan in loans:assert (await client.put(f'/api/library/loans/{loan}/return',headers=auth)).status_code==200
    assert (await client.delete(f'/api/library/books/{key}',headers=auth)).status_code==409
    assert (await client.get(f'/api/library/books/{key}',headers=auth)).json()['data']['available_copies']==2
    async with sessions() as db:
        for model in (Payment,NotificationJob):assert (await db.execute(select(func.count()).select_from(model))).scalar_one()==0


async def test_readonly_and_foreign_scopes_cannot_edit_or_delete(materials_client):
    client,sessions,data=materials_client;auth=await headers(sessions,data['org'].id);key=await book(client,auth)
    reader=await headers(sessions,data['org'].id,False);foreign=await headers(sessions,data['stranger'].organization_id)
    for method in ('put','delete'):
        kwargs={'json':{'title':'Forbidden'}} if method=='put' else {}
        assert (await getattr(client,method)(f'/api/library/books/{key}',headers=reader,**kwargs)).status_code==403
        assert (await getattr(client,method)(f'/api/library/books/{key}',headers=foreign,**kwargs)).status_code==404
    assert (await client.get(f'/api/library/books/{key}',headers=foreign)).status_code==404
    assert (await client.delete(f'/api/library/books/{key}',headers=auth)).status_code==200
    assert (await client.get(f'/api/library/books/{key}',headers=auth)).status_code==404


async def test_catalog_list_is_tenant_scoped_and_web_pagination_is_honored(materials_client):
    client,sessions,data=materials_client;auth=await headers(sessions,data['org'].id)
    keys=[await book(client,auth) for _ in range(3)]
    async with sessions() as db:
        foreign=LibraryBook(organization_id=data['stranger'].organization_id,title='Foreign catalog secret',author='Foreign',
            category='Private',total_copies=1,available_copies=1)
        db.add(foreign);await db.commit()
    first=await client.get('/api/library/books?limit=2&offset=1',headers=auth)
    assert first.status_code==200,first.text
    page=first.json()['data']
    if isinstance(page,list):
        assert all(row['id'] in keys for row in page), 'catalog leaked another organization book before pagination checks'
    assert isinstance(page,dict) and page['total']==3 and page['page']==1 and page['page_size']==2
    assert len(page['items'])==2 and all(row['id'] in keys for row in page['items'])
    second=await client.get('/api/library/books?page=2&page_size=2&skip=2',headers=auth)
    assert second.status_code==200,second.text
    web=second.json()['data']
    assert web['total']==3 and web['page']==2 and web['page_size']==2 and len(web['items'])==1
    assert all(row['id'] in keys for row in web['items'])
    foreign_auth=await headers(sessions,data['stranger'].organization_id)
    all_books=await client.get('/api/library/books?limit=1000',headers=foreign_auth)
    assert all_books.status_code==200
    assert all(row['title']=='Foreign catalog secret' for row in all_books.json()['data']['items'])


async def test_null_required_fields_are_rejected_without_mutation(materials_client):
    client,sessions,data=materials_client;auth=await headers(sessions,data['org'].id);key=await book(client,auth)
    for field in ('title','author','total_copies','available_copies'):
        assert (await client.put(f'/api/library/books/{key}',headers=auth,json={field:None})).status_code==422
    saved=(await client.get(f'/api/library/books/{key}',headers=auth)).json()['data']
    assert saved['title']=='Guarded catalog' and saved['total_copies']==saved['available_copies']==2


async def test_teacher_inventory_guards_include_loans_outside_their_student_scope(materials_client):
    client,sessions,data=materials_client;auth=await headers(sessions,data['org'].id);key=await book(client,auth)
    async with sessions() as db:
        permissions=(await db.execute(select(Permission).where(Permission.code.in_(['library.read','library.write'])))).scalars().all()
        role=Role(name='Library permission',slug='library_permission',organization_id=data['org'].id,permissions=permissions)
        db.add(role);await db.flush();db.add(UserRole(user_id=data['teacher'].id,role_id=role.id))
        other=Student(first_name='Outside',last_name='Class',organization_id=data['org'].id,branch_id=data['branch'].id,class_id=data['other_class'].id)
        db.add(other);await db.commit();outside=other.id
    await borrow(client,auth,key,outside)
    teacher={'Authorization':'Bearer '+create_access_token(data['teacher'].id)}
    response=await client.put(f'/api/library/books/{key}',headers=teacher,json={'title':'Scoped metadata edit'})
    assert response.status_code==200,response.text
    assert response.json()['data']['available_copies']==1
    assert (await client.delete(f'/api/library/books/{key}',headers=teacher)).status_code==409


async def test_edit_rejects_version_change_between_load_and_atomic_write(materials_client):
    from uuid import UUID
    client,sessions,data=materials_client;auth=await headers(sessions,data['org'].id);key=await book(client,auth)
    engine=sessions.kw['bind'].sync_engine;fired=False
    def interleave(connection,cursor,statement,parameters,context,many):
        nonlocal fired
        if not fired and statement.lstrip().upper().startswith('SELECT') and 'CAST(library_books.updated_at' in statement:
            fired=True
            connection.execute(LibraryBook.__table__.update().where(LibraryBook.__table__.c.id==UUID(key)).values(
                title='Concurrent edit',updated_at=datetime.now(UTC)+timedelta(seconds=1)))
    event.listen(engine,'before_cursor_execute',interleave)
    try:
        response=await client.put(f'/api/library/books/{key}',headers=auth,json={'title':'Lost update'})
        assert fired and response.status_code==409,response.text
    finally:event.remove(engine,'before_cursor_execute',interleave)
