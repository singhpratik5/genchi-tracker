from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .db import STAGES, get_db, now

EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

router = APIRouter(prefix="/requests", tags=["intake"])


class RequestIn(BaseModel):
    name: str = Field(min_length=1)
    email: str = Field(pattern=EMAIL)
    country: str | None = None
    source: str = Field(default="direct", min_length=1)
    use_case: str = Field(min_length=1)
    details: str | None = None


def fetch_request(db, request_id):
    row = db.execute("SELECT * FROM requests WHERE id = ?", (request_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "request not found")
    return dict(row)


@router.post("", status_code=201)
def create_request(body: RequestIn, db=Depends(get_db)):
    ts = now()
    cur = db.execute(
        "INSERT INTO requests (created_at, name, email, country, source, use_case, details, stage) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (ts, body.name, body.email, body.country, body.source, body.use_case, body.details, STAGES[0]),
    )
    db.execute(
        "INSERT INTO stage_events (request_id, stage, at) VALUES (?, ?, ?)",
        (cur.lastrowid, STAGES[0], ts),
    )
    db.commit()
    return fetch_request(db, cur.lastrowid)


@router.get("")
def list_requests(source: str | None = None, stage: str | None = None, db=Depends(get_db)):
    clauses, args = [], []
    if source:
        clauses.append("source = ?")
        args.append(source)
    if stage:
        clauses.append("stage = ?")
        args.append(stage)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = db.execute(f"SELECT * FROM requests {where} ORDER BY id", args).fetchall()
    return [dict(r) for r in rows]


@router.get("/{request_id}")
def get_request(request_id: int, db=Depends(get_db)):
    return fetch_request(db, request_id)
