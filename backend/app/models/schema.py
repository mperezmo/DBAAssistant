# backend/app/models/schema.py
"""Modelos Pydantic para el análisis de metadata/esquema (Sprint 4)."""
from pydantic import BaseModel


class DatabaseOverview(BaseModel):
    server: str
    database: str
    table_count: int
    total_size_kb: int


class TableSummary(BaseModel):
    schema_name: str
    table_name: str
    row_count: int
    size_kb: int
    column_count: int
    index_count: int


class ColumnInfo(BaseModel):
    name: str
    data_type: str
    max_length: int
    is_nullable: bool
    is_primary_key: bool


class IndexInfo(BaseModel):
    name: str | None
    type_desc: str
    is_unique: bool
    is_primary_key: bool


class ForeignKeyInfo(BaseModel):
    name: str
    ref_schema: str
    ref_table: str


class TableDetail(BaseModel):
    schema_name: str
    table_name: str
    columns: list[ColumnInfo]
    indexes: list[IndexInfo]
    foreign_keys: list[ForeignKeyInfo]
