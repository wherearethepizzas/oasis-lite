from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.services.utils import execute_query

router = APIRouter()

@router.get("/{user_id}")
def get_user(user_id: str, db = Depends(get_db)):
    rows = execute_query(
        db,
        query="""
            SELECT *
            FROM users
            WHERE user_id = :user_id
        """,
        params={"user_id":user_id}
    )

    user = rows[0] if rows else None

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user