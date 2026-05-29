from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_db

router = APIRouter()

@router.get("/health")
def check_health():
    return {"status": "ok"}

@router.get("/health/db")
def check_db(db:Session = Depends(get_db)):
    try:
        result = db.execute(text("SELECT 1")).scalar_one()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "error",
                "database": "unavailable"
            },
        )
    
    return {
        "status": "ok", 
        "database": "ok"
    }
    