from fastapi import FastAPI

from .export import router as export_router
from .funnel import router as funnel_router
from .intake import router as intake_router

app = FastAPI(title="GENCHI Intake & Funnel Tracker")
app.include_router(intake_router)
app.include_router(funnel_router)
app.include_router(export_router)
