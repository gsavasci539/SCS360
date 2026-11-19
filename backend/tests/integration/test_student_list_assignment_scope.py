from test_material_files import headers, materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401

from app.infrastructure.models.models import (
    Branch,
    ClassTeacher,
    Role,
    Student,
    StudentTeacherAssignment,
    UserBranch,
    UserRole,
)


async def test_student_list_uses_relationship_scope_and_preserves_owner_access(materials_client):  # noqa: F811
    client, sessions, data = materials_client
    teacher, branch, org = data["teacher"], data["branch"], data["org"]
    async with sessions() as db:
        other_branch = Branch(name="Second campus", organization_id=org.id)
        db.add_all([other_branch, UserBranch(user_id=teacher.id, branch_id=branch.id),
            ClassTeacher(class_id=data["classroom"].id, user_id=teacher.id)])
        await db.flush()

        def student(name, campus, classroom=None):
            return Student(first_name=name, last_name="Test", organization_id=org.id,
                branch_id=campus.id, class_id=classroom.id if classroom else None)

        directly_assigned = student("Direct", branch, data["other_class"])
        assigned_without_class = student("No class", branch)
        unassigned_to_teacher = student("Another learner", branch, data["other_class"])
        outside_branch = student("Another campus", other_branch)
        db.add_all([directly_assigned, assigned_without_class, unassigned_to_teacher, outside_branch])
        await db.flush()
        db.add_all([StudentTeacherAssignment(student_id=row.id, teacher_id=teacher.id, subject_name="Matematik")
            for row in (directly_assigned, assigned_without_class, outside_branch)])
        await db.commit()

    async def listed_ids(**params):
        response = await client.get("/api/students", headers=headers(teacher), params=params)
        assert response.status_code == 200, response.text
        payload = response.json()["data"]
        assert payload["total"] == len(payload["items"])
        return {item["id"] for item in payload["items"]}

    assigned_ids = {str(row.id) for row in (*data["children"], directly_assigned, assigned_without_class)}
    assert await listed_ids() == assigned_ids
    assert await listed_ids(class_id=str(data["other_class"].id)) == {str(directly_assigned.id)}
    assert await listed_ids(unassigned="true") == {str(assigned_without_class.id)}
    assert await listed_ids(branch_id=str(other_branch.id)) == set()

    async with sessions() as db:
        owner = Role(name="Owner", slug="owner", organization_id=org.id)
        db.add(owner)
        await db.flush()
        db.add(UserRole(user_id=teacher.id, role_id=owner.id))
        await db.commit()

    assert await listed_ids() == assigned_ids | {str(unassigned_to_teacher.id), str(outside_branch.id)}
    assert await listed_ids(branch_id=str(other_branch.id)) == {str(outside_branch.id)}
