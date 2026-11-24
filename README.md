# GENCHI Intake & Funnel Tracker

FastAPI + SQLite service that records customer requests and tracks each one through
enquiry, qualified, booked, completed, paid, so conversion can be measured by stage and by source.

## Modules

- `tracker/intake.py` creates, lists and fetches requests.
- `tracker/funnel.py` moves a request forward one stage at a time and reports counts and conversion rates, overall and per source.
- `tracker/db.py` holds the SQLite schema and the stage list.

## Run

    pip install -r requirements.txt
    uvicorn tracker.main:app --reload

Interactive docs at http://127.0.0.1:8000/docs. Set `GENCHI_DB` to change the database path.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | /requests | create a request (starts at enquiry) |
| GET | /requests | list, filter by `source` and `stage` |
| GET | /requests/{id} | fetch one |
| POST | /requests/{id}/stage | move forward to a later stage |
| GET | /funnel | counts and conversion rates, optional `source` |
| GET | /funnel/by-source | the same, grouped by source |

## Test

    pytest

Stage names are working assumptions and need checking against Toraru's actual request process.
No real customer data should be loaded until the fields are reviewed with the team.
