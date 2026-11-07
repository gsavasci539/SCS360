"""Add chat_conversations and student_teacher_assignments tables for chatbot teacher integration"""

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from alembic import op
    import sqlalchemy as sa

    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Add conversation_id to chat_messages table
    if 'chat_messages' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('chat_messages')]
        if 'conversation_id' not in columns:
            op.add_column('chat_messages', sa.Column('conversation_id', sa.String(36), nullable=True))
            op.create_index('idx_chat_messages_conversation_id', 'chat_messages', ['conversation_id'])
        
        # Add sender_role if not exists
        if 'sender_role' not in columns:
            op.add_column('chat_messages', sa.Column('sender_role', sa.String(20), nullable=True))
        
        # Add recipient_id if not exists (keep receiver_id for backward compatibility)
        if 'recipient_id' not in columns:
            op.add_column('chat_messages', sa.Column('recipient_id', sa.String(36), nullable=True))
            # Copy data from receiver_id to recipient_id
            conn.execute(sa.text("UPDATE chat_messages SET recipient_id = receiver_id"))

    # Create student_teacher_assignments table
    if 'student_teacher_assignments' not in inspector.get_table_names():
        op.create_table(
            'student_teacher_assignments',
            sa.Column('id', sa.String(36), nullable=False),
            sa.Column('student_id', sa.String(36), nullable=False),
            sa.Column('teacher_id', sa.String(36), nullable=False),
            sa.Column('subject_name', sa.String(100), nullable=False),
            sa.Column('is_primary_adviser', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('office_hours', sa.String(50), nullable=True),
            sa.Column('academic_year', sa.String(20), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['teacher_id'], ['users.id'], ondelete='CASCADE')
        )
        op.create_index('idx_student_teacher_student', 'student_teacher_assignments', ['student_id'])
        op.create_index('idx_student_teacher_teacher', 'student_teacher_assignments', ['teacher_id'])
        # Note: Unique constraint handled in model, not in migration for SQLite compatibility

    # Create chat_conversations table
    if 'chat_conversations' not in inspector.get_table_names():
        op.create_table(
            'chat_conversations',
            sa.Column('id', sa.String(36), nullable=False),
            sa.Column('student_id', sa.String(36), nullable=False),
            sa.Column('parent_id', sa.String(36), nullable=False),
            sa.Column('teacher_id', sa.String(36), nullable=False),
            sa.Column('subject_context', sa.String(150), nullable=False),
            sa.Column('last_message', sa.Text(), nullable=True),
            sa.Column('last_message_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('parent_unread_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('teacher_unread_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('created_via', sa.String(30), nullable=False, server_default='CHATBOT'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['parent_id'], ['users.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['teacher_id'], ['users.id'], ondelete='CASCADE')
        )
        op.create_index('idx_conversations_parent', 'chat_conversations', ['parent_id'])
        op.create_index('idx_conversations_teacher', 'chat_conversations', ['teacher_id'])
        op.create_index('idx_conversations_student', 'chat_conversations', ['student_id'])


def downgrade() -> None:
    from alembic import op

    # Drop chat_conversations table
    op.drop_index('idx_conversations_student', table_name='chat_conversations')
    op.drop_index('idx_conversations_teacher', table_name='chat_conversations')
    op.drop_index('idx_conversations_parent', table_name='chat_conversations')
    op.drop_table('chat_conversations')

    # Drop student_teacher_assignments table
    op.drop_constraint('uq_student_teacher_subject', 'student_teacher_assignments', type_='unique')
    op.drop_index('idx_student_teacher_teacher', table_name='student_teacher_assignments')
    op.drop_index('idx_student_teacher_student', table_name='student_teacher_assignments')
    op.drop_table('student_teacher_assignments')

    # Remove columns from chat_messages
    op.drop_index('idx_chat_messages_conversation_id', table_name='chat_messages')
    op.drop_column('chat_messages', 'conversation_id')
    op.drop_column('chat_messages', 'sender_role')
    # Note: We're not reverting the recipient_id change as it's complex
