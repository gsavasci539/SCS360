"""Add daily_development_reports and chat_messages tables according to OKUL360 documentation"""

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create daily_development_reports table
    from alembic import op
    import sqlalchemy as sa

    op.create_table(
        'daily_development_reports',
        sa.Column('id', sa.String(36), nullable=False),  # String for SQLite UUID compatibility
        sa.Column('student_id', sa.String(36), nullable=False),
        sa.Column('class_id', sa.String(36), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('meal_status', sa.String(30), nullable=True),
        sa.Column('sleep_status', sa.String(30), nullable=True),
        sa.Column('mood', sa.String(50), nullable=True),
        sa.Column('activities', sa.JSON(), nullable=True),
        sa.Column('teacher_notes', sa.Text(), nullable=True),
        sa.Column('recorded_by', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_daily_reports_student_id', 'daily_development_reports', ['student_id'])
    op.create_index('idx_daily_reports_class_id', 'daily_development_reports', ['class_id'])
    op.create_index('idx_daily_reports_date', 'daily_development_reports', ['date'])

    # Create chat_messages table
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.String(36), nullable=False),  # String for SQLite UUID compatibility
        sa.Column('sender_id', sa.String(36), nullable=False),
        sa.Column('receiver_id', sa.String(36), nullable=False),
        sa.Column('class_id', sa.String(36), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('attachment_url', sa.String(500), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('sent_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_chat_messages_sender_id', 'chat_messages', ['sender_id'])
    op.create_index('idx_chat_messages_receiver_id', 'chat_messages', ['receiver_id'])
    op.create_index('idx_chat_messages_class_id', 'chat_messages', ['class_id'])
    op.create_index('idx_chat_messages_sent_at', 'chat_messages', ['sent_at'])


def downgrade() -> None:
    from alembic import op

    op.drop_index('idx_chat_messages_sent_at', table_name='chat_messages')
    op.drop_index('idx_chat_messages_class_id', table_name='chat_messages')
    op.drop_index('idx_chat_messages_receiver_id', table_name='chat_messages')
    op.drop_index('idx_chat_messages_sender_id', table_name='chat_messages')
    op.drop_table('chat_messages')

    op.drop_index('idx_daily_reports_date', table_name='daily_development_reports')
    op.drop_index('idx_daily_reports_class_id', table_name='daily_development_reports')
    op.drop_index('idx_daily_reports_student_id', table_name='daily_development_reports')
    op.drop_table('daily_development_reports')