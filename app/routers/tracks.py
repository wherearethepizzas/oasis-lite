from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.utils import execute_query

router=APIRouter()

@router.get("/{track_id}")
def get_track(track_id: str, db: Session = Depends(get_db)):
    rows = execute_query(
        db,
        query="""
            SELECT 
                t.track_name, 
                t.genre, 
                t.release_year, 
                a.artist_name
            FROM tracks t 
            JOIN track_artists ta ON ta.track_id = t.track_id
            JOIN artists a ON a.artist_id = ta.artist_id
            WHERE t.track_id = :track_id
            """,
        params={"track_id":track_id}
    )
   
    track = rows[0] if rows else None

    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")
    
    return track
