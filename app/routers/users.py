from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import MessageResponse, PromotionImpressionResponse, UserResponse
from app.services.utils import execute_query

router = APIRouter()

@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: str, db: Session = Depends(get_db)):
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
    
    return dict(user)

@router.get("/{user_id}/promotion-history", response_model=list[PromotionImpressionResponse] | MessageResponse)
def get_user_promotion_history(user_id, db: Session = Depends(get_db)):
    rows = execute_query(
        db,
        query="""
            SELECT * 
            FROM promotion_impressions pi
            WHERE pi.user_id = :user_id
        """,
        params={"user_id": user_id}
    )

    if not rows:
        return {"message": f"User {user_id} does not have a promotion history."}
    else:
        return [dict(row) for row in rows]
