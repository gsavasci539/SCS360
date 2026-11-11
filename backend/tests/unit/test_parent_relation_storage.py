import pytest
from sqlalchemy import Enum
from sqlalchemy.dialects import postgresql, sqlite

from app.infrastructure.models.models import ParentRelationStorageEnum, ParentRelationType


def test_legacy_relation_read_aliases_keep_the_original_enum_and_ddl_contract():
    stored = ParentRelationStorageEnum(ParentRelationType)
    original = Enum(ParentRelationType)
    for dialect in (sqlite.dialect(), postgresql.dialect()):
        assert stored.compile(dialect=dialect) == original.compile(dialect=dialect)
    assert stored.enums == original.enums == ["MOTHER", "FATHER", "GUARDIAN", "OTHER"]
    process = stored.dialect_impl(sqlite.dialect()).result_processor(sqlite.dialect(), None)
    assert process("ANNE") is ParentRelationType.MOTHER
    assert process("BABA") is ParentRelationType.FATHER
    assert process("FATHER") is ParentRelationType.FATHER
    assert process(None) is None
    with pytest.raises(LookupError):
        process("UNKNOWN_RELATION")
