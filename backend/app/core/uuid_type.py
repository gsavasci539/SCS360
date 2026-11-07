"""UUID values use one format for new writes and accept legacy SQLite keys."""
import uuid

from sqlalchemy import String, TypeDecorator, literal
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql import Select, operators
from sqlalchemy.sql.elements import BinaryExpression, BindParameter
from sqlalchemy.sql.functions import FunctionElement


class uuid_key(FunctionElement):
    type = String()
    inherit_cache = True


@compiles(uuid_key)
def _native_uuid_key(element, compiler, **kw):
    return compiler.process(list(element.clauses)[0], **kw)


@compiles(uuid_key, "sqlite")
def _sqlite_uuid_key(element, compiler, **kw):
    return "replace(CAST(" + compiler.process(list(element.clauses)[0], **kw) + " AS VARCHAR), '-', '')"


class CustomUUID(TypeDecorator):
    impl = String(36)
    cache_ok = True

    class comparator_factory(TypeDecorator.Comparator):
        def in_(self, other):
            if isinstance(other, Select) and len(other.selected_columns) == 1:
                return uuid_key(self.expr).in_(other.with_only_columns(uuid_key(list(other.selected_columns)[0])))
            if isinstance(other, (list, set, tuple)):
                return uuid_key(self.expr).in_([uuid_key(literal(value, type_=CustomUUID())) for value in other])
            return super().in_(other)

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(PG_UUID(as_uuid=True) if dialect.name == "postgresql" else String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        try:
            return str(uuid.UUID(str(value)))
        except (ValueError, TypeError):
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None or isinstance(value, uuid.UUID):
            return value
        try:
            return uuid.UUID(str(value))
        except (ValueError, TypeError, AttributeError):
            return None


class _UUIDKeyString(TypeDecorator):
    impl = String(32)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return str(value).replace("-", "") if value is not None else None


@compiles(BinaryExpression, "sqlite")
def _legacy_uuid_comparison(element, compiler, **kw):
    # Rendering changes only SQLite SQL; ordinary equality remains available
    # to SQLAlchemy's relationship/foreign-key inspection.
    if isinstance(element.left.type, CustomUUID):
        if element.operator == operators.eq:
            return compiler.visit_binary(uuid_key(element.left) == uuid_key(element.right), **kw)
        if element.operator in (operators.in_op, operators.not_in_op) and isinstance(element.right, BindParameter):
            parameter = element.right._clone()
            parameter.type = _UUIDKeyString()
            return compiler.visit_binary(BinaryExpression(uuid_key(element.left), parameter, element.operator), **kw)
    return compiler.visit_binary(element, **kw)

