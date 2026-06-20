# backend/app/models/context.py
"""Modelos del contexto de negocio (Sprint 9)."""
from pydantic import BaseModel


class GlossaryTerm(BaseModel):
    term: str
    definition: str = ""


class DatabaseContext(BaseModel):
    description: str = ""
    rules: list[str] = []
    glossary: list[GlossaryTerm] = []


class TableContext(BaseModel):
    business_name: str = ""
    description: str = ""
    tags: list[str] = []
    sensitive: bool = False
    sensitive_columns: str = ""
    restriction: str = ""


class TableContextEntry(TableContext):
    schema_name: str
    table_name: str
