"""Portable embedding column type.

On PostgreSQL it is a real pgvector ``vector(dim)`` column (with the ``<=>`` cosine
operator and index support). On other dialects (SQLite used in offline tests) it falls
back to JSON storing a list[float], so scoring can be computed in Python deterministically.
"""
from __future__ import annotations

from sqlalchemy.types import JSON, TypeDecorator


class Embedding(TypeDecorator):
    impl = JSON
    cache_ok = True

    def __init__(self, dim: int) -> None:
        self.dim = dim
        super().__init__()

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from pgvector.sqlalchemy import Vector

            return dialect.type_descriptor(Vector(self.dim))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return list(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return list(value)
