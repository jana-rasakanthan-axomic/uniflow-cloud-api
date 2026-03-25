"""Shared test configuration.

Patches PostgreSQL-specific column types (JSONB, INET) to be SQLite-compatible
so models can be tested against in-memory SQLite databases.
"""

from sqlalchemy import JSON, Text
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

# Teach SQLite how to compile JSONB -> JSON and INET -> TEXT
SQLiteTypeCompiler.visit_JSONB = lambda self, type_, **kw: self.visit_JSON(type_, **kw)
SQLiteTypeCompiler.visit_INET = lambda self, type_, **kw: "TEXT"
