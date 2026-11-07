"""Add user_id field to parents table"""

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from alembic import op
    import sqlalchemy as sa
    if "user_id" in {column["name"] for column in sa.inspect(op.get_bind()).get_columns("parents")}:
        return
    from alembic import op
    import sqlalchemy as sa

    # Use batch mode for SQLite compatibility
    with op.batch_alter_table('parents') as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.String(36), nullable=True))
        batch_op.create_foreign_key('fk_parents_user_id', 'users', ['user_id'], ['id'])


def downgrade() -> None:
    from alembic import op

    with op.batch_alter_table('parents') as batch_op:
        batch_op.drop_constraint('fk_parents_user_id', type_='foreignkey')
        batch_op.drop_column('user_id')
