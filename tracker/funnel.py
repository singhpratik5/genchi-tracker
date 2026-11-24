from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .db import STAGES, get_db, now
from .intake import fetch_request

router = APIRouter(tags=["funnel"])


class StageIn(BaseModel):
    stage: str


def rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else None


def summarise(db, source=None):
    where, args = ("WHERE r.source = ?", [source]) if source else ("", [])
    rows = db.execute(
        "SELECT e.stage AS stage, COUNT(DISTINCT e.request_id) AS n "
        "FROM stage_events e JOIN requests r ON r.id = e.request_id "
        f"{where} GROUP BY e.stage",
        args,
    ).fetchall()
    counts = {s: 0 for s in STAGES}
    counts.update({r["stage"]: r["n"] for r in rows})
    steps = [
        {"from": a, "to": b, "rate": rate(counts[b], counts[a])}
        for a, b in zip(STAGES, STAGES[1:])
    ]
    return {
        "counts": counts,
        "steps": steps,
        "overall": rate(counts[STAGES[-1]], counts[STAGES[0]]),
    }


@router.post("/requests/{request_id}/stage")
def advance_stage(request_id: int, body: StageIn, db=Depends(get_db)):
    if body.stage not in STAGES:
        raise HTTPException(422, f"stage must be one of {STAGES}")
    current = fetch_request(db, request_id)["stage"]
    if STAGES.index(body.stage) <= STAGES.index(current):
        raise HTTPException(409, f"request is already at '{current}'")
    db.execute("UPDATE requests SET stage = ? WHERE id = ?", (body.stage, request_id))
    db.execute(
        "INSERT INTO stage_events (request_id, stage, at) VALUES (?, ?, ?)",
        (request_id, body.stage, now()),
    )
    db.commit()
    return fetch_request(db, request_id)


@router.get("/funnel")
def funnel(source: str | None = None, db=Depends(get_db)):
    return summarise(db, source)


@router.get("/funnel/by-source")
def funnel_by_source(db=Depends(get_db)):
    sources = [r["source"] for r in db.execute("SELECT DISTINCT source FROM requests ORDER BY source")]
    return {s: summarise(db, s) for s in sources}
