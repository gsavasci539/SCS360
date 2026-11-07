"""Add teacher_id column to classes table"""

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from alembic import op
    import sqlalchemy as sa

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('classes')]
    
    # SQLite doesn't support adding foreign keys directly, so we use batch mode
    if 'teacher_id' not in columns:
        with op.batch_alter_table('classes') as batch_op:
            batch_op.add_column(sa.Column('teacher_id', sa.String(36), nullable=True))
            batch_op.create_foreign_key('fk_classes_teacher_id', 'users', ['teacher_id'], ['id'])


def downgrade() -> None:
    from alembic import op

    with op.batch_alter_table('classes') as batch_op:
        batch_op.drop_constraint('fk_classes_teacher_id', type_='foreignkey')
        batch_op.drop_column('teacher_id')
