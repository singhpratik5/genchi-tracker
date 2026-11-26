import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from .db import STAGES, get_db
from .funnel import summarise

router = APIRouter(prefix="/export", tags=["export"])

FORMULA_PREFIXES = ("=", "+", "-", "@")


def safe(value):
    if isinstance(value, str) and value.startswith(FORMULA_PREFIXES):
        return "'" + value
    return value


def to_csv(header, rows):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    writer.writerows([safe(v) for v in row] for row in rows)
    return Response(buf.getvalue(), media_type="text/csv")


@router.get("/requests.csv")
def export_requests(db=Depends(get_db)):
    rows = db.execute(
        "SELECT id, created_at, country, source, use_case, stage FROM requests ORDER BY id"
    ).fetchall()
    return to_csv(["id", "created_at", "country", "source", "use_case", "stage"], rows)


@router.get("/funnel.csv")
def export_funnel(db=Depends(get_db)):
    sources = [r["source"] for r in db.execute("SELECT DISTINCT source FROM requests ORDER BY source")]
    rows = []
    for label, source in [("all", None)] + [(s, s) for s in sources]:
        data = summarise(db, source)
        rows.append([label, *(data["counts"][s] for s in STAGES), data["overall"]])
    return to_csv(["source", *STAGES, "overall_rate"], rows)
