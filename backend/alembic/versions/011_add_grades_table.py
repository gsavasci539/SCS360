"""Add grades table for student performance tracking"""

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from alembic import op
    import sqlalchemy as sa

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'grades' not in inspector.get_table_names():
        op.create_table(
            'grades',
            sa.Column('id', sa.String(36), nullable=False),
            sa.Column('organization_id', sa.String(36), nullable=False),
            sa.Column('branch_id', sa.String(36), nullable=False),
            sa.Column('class_id', sa.String(36), nullable=False),
            sa.Column('student_id', sa.String(36), nullable=False),
            sa.Column('teacher_id', sa.String(36), nullable=True),
            sa.Column('subject', sa.String(30), nullable=False),
            sa.Column('grade_type', sa.String(30), nullable=False),
            sa.Column('score', sa.Numeric(5, 2), nullable=False),
            sa.Column('max_score', sa.Numeric(5, 2), nullable=False, server_default='100'),
            sa.Column('exam_date', sa.Date(), nullable=False),
            sa.Column('term', sa.String(20), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_by', sa.String(36), nullable=True),
            sa.Column('updated_by', sa.String(36), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('student_id', 'subject', 'grade_type', 'exam_date')
        )
        op.create_index('idx_grades_student_id', 'grades', ['student_id'])
        op.create_index('idx_grades_class_id', 'grades', ['class_id'])
        op.create_index('idx_grades_subject', 'grades', ['subject'])
        op.create_index('idx_grades_exam_date', 'grades', ['exam_date'])


def downgrade() -> None:
    from alembic import op

    op.drop_index('idx_grades_exam_date', table_name='grades')
    op.drop_index('idx_grades_subject', table_name='grades')
    op.drop_index('idx_grades_class_id', table_name='grades')
    op.drop_index('idx_grades_student_id', table_name='grades')
    op.drop_table('grades')
