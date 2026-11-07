"""Enforce parent account and teacher-class relationship lookup keys.

The unique parent account link prevents one login from gaining access through
multiple parent records.  Class-teacher and legacy homeroom-teacher indexes
keep relationship scoped authorization queries efficient.
"""

from alembic import op
import sqlalchemy as sa


revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    indexes = {index["name"] for index in inspector.get_indexes("parents")}
    if "ix_parents_user_id" not in indexes:
        op.create_index("ix_parents_user_id", "parents", ["user_id"], unique=True)

    class_teacher_indexes = {index["name"] for index in inspector.get_indexes("class_teachers")}
    if "ix_class_teachers_user_id" not in class_teacher_indexes:
        op.create_index("ix_class_teachers_user_id", "class_teachers", ["user_id"])

    class_indexes = {index["name"] for index in inspector.get_indexes("classes")}
    if "ix_classes_teacher_id" not in class_indexes:
        op.create_index("ix_classes_teacher_id", "classes", ["teacher_id"])


def downgrade() -> None:
    op.drop_index("ix_classes_teacher_id", table_name="classes")
    op.drop_index("ix_class_teachers_user_id", table_name="class_teachers")
    op.drop_index("ix_parents_user_id", table_name="parents")
