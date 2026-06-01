from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Any


def execute_query(db: Session, query: str, params: dict[str, Any] | None = None):
    result = db.execute(text(query), params or {})
    return result.mappings().all()