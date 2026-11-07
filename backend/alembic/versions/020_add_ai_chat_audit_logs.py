"""Add ai_chat_audit_logs table for LLM fine-tuning and analytics"""

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from alembic import op
    import sqlalchemy as sa

    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Create ai_chat_audit_logs table
    if 'ai_chat_audit_logs' not in inspector.get_table_names():
        op.create_table(
            'ai_chat_audit_logs',
            sa.Column('id', sa.String(36), nullable=False),
            sa.Column('session_id', sa.String(100), nullable=False),
            sa.Column('user_id', sa.String(36), nullable=False),
            sa.Column('organization_id', sa.String(36), nullable=False),
            sa.Column('user_query', sa.Text(), nullable=False),
            sa.Column('ai_response', sa.Text(), nullable=False),
            sa.Column('detected_intent', sa.String(50), nullable=True),
            sa.Column('topic_category', sa.String(100), nullable=True),
            sa.Column('sentiment', sa.String(20), nullable=False, server_default='NEUTRAL'),
            sa.Column('quality_rating', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('feedback_status', sa.String(20), nullable=False, server_default='NEEDS_REVIEW'),
            sa.Column('corrected_response', sa.Text(), nullable=True),
            sa.Column('token_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('latency_ms', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('is_fine_tuning_ready', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('meta_data', sa.JSON(), nullable=True),
            sa.Column('created_by', sa.String(36), nullable=True),
            sa.Column('updated_by', sa.String(36), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL')
        )
        op.create_index('idx_audit_logs_session', 'ai_chat_audit_logs', ['session_id'])
        op.create_index('idx_audit_logs_user', 'ai_chat_audit_logs', ['user_id'])
        op.create_index('idx_audit_logs_organization', 'ai_chat_audit_logs', ['organization_id'])
        op.create_index('idx_audit_logs_intent', 'ai_chat_audit_logs', ['detected_intent'])
        op.create_index('idx_audit_logs_topic', 'ai_chat_audit_logs', ['topic_category'])
        op.create_index('idx_audit_logs_feedback', 'ai_chat_audit_logs', ['feedback_status'])
        op.create_index('idx_audit_logs_finetuning', 'ai_chat_audit_logs', ['is_fine_tuning_ready'])


def downgrade() -> None:
    from alembic import op

    # Drop indexes
    op.drop_index('idx_audit_logs_finetuning', table_name='ai_chat_audit_logs')
    op.drop_index('idx_audit_logs_feedback', table_name='ai_chat_audit_logs')
    op.drop_index('idx_audit_logs_topic', table_name='ai_chat_audit_logs')
    op.drop_index('idx_audit_logs_intent', table_name='ai_chat_audit_logs')
    op.drop_index('idx_audit_logs_organization', table_name='ai_chat_audit_logs')
    op.drop_index('idx_audit_logs_user', table_name='ai_chat_audit_logs')
    op.drop_index('idx_audit_logs_session', table_name='ai_chat_audit_logs')

    # Drop table
    op.drop_table('ai_chat_audit_logs')
