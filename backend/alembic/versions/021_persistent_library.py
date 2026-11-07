"""Persistent, organization-scoped library catalog and loans."""
from alembic import op
import sqlalchemy as sa

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if set(["library_books","library_loans"]).issubset(existing):
        return
    from app.infrastructure.models.models import CustomUUID
    op.create_table("library_books",
        sa.Column("id", CustomUUID(), primary_key=True),
        sa.Column("organization_id", CustomUUID(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("author", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100)), sa.Column("isbn", sa.String(32)),
        sa.Column("barcode", sa.String(100)),
        sa.Column("total_copies", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("available_copies", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("publisher", sa.String(255)), sa.Column("publication_year", sa.Integer()),
        sa.Column("description", sa.Text()), sa.Column("location", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table("library_loans",
        sa.Column("id", CustomUUID(), primary_key=True),
        sa.Column("book_id", CustomUUID(), sa.ForeignKey("library_books.id"), nullable=False),
        sa.Column("student_id", CustomUUID(), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("borrow_date", sa.Date(), nullable=False), sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("return_date", sa.Date()),
        sa.Column("loaned_by", CustomUUID(), sa.ForeignKey("users.id")),
        sa.Column("returned_by", CustomUUID(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade():
    op.drop_table("library_loans")
    op.drop_table("library_books")
