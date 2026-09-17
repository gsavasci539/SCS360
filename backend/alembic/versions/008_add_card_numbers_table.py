"""add card numbers table

Revision ID: 008
Revises: 007
Create Date: 2026-08-30

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    # Create card_numbers table (SQLite doesn't support ENUM, use CHECK constraints)
    op.create_table(
        'card_numbers',
        sa.Column('id', sa.String(), primary_key=True),  # SQLite uses String for UUID
        sa.Column('organization_id', sa.String(), nullable=True),
        sa.Column('branch_id', sa.String(), nullable=True),
        sa.Column('card_number', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), server_default='AVAILABLE'),  # AVAILABLE, ASSIGNED, DAMAGED, LOST
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('purchased_date', sa.Date(), nullable=True),
        sa.Column('supplier', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.UniqueConstraint('card_number', 'organization_id', name='uq_card_numbers_card_number_org')
    )


def downgrade():
    op.drop_table('card_numbers')
