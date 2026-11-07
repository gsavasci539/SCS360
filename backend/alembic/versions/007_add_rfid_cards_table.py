"""add rfid cards table

Revision ID: 007
Revises: 006
Create Date: 2026-08-29

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade():
    # Create rfid_cards table (SQLite doesn't support ENUM, use CHECK constraints)
    # Check if table already exists before creating
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'rfid_cards' not in inspector.get_table_names():
        op.create_table(
            'rfid_cards',
            sa.Column('id', sa.String(), primary_key=True),  # SQLite uses String for UUID
            sa.Column('organization_id', sa.String(), nullable=True),
            sa.Column('branch_id', sa.String(), nullable=True),
            sa.Column('card_number', sa.String(50), nullable=False),
            sa.Column('card_type', sa.String(20), nullable=False),  # STUDENT or STAFF
            sa.Column('holder_id', sa.String(100), nullable=False),
            sa.Column('holder_name', sa.String(255), nullable=False),
            sa.Column('status', sa.String(20), server_default='ACTIVE'),  # ACTIVE, INACTIVE, BLOCKED
            sa.Column('issue_date', sa.Date(), nullable=True),
            sa.Column('expiry_date', sa.Date(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.UniqueConstraint('card_number', 'organization_id', name='uq_rfid_cards_card_number_org')
        )


def downgrade():
    op.drop_table('rfid_cards')
