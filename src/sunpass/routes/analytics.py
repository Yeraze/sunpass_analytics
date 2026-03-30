from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from sunpass.db.queries import (
    get_spending_by_day_of_week,
    get_spending_by_month,
    get_spending_by_plaza,
    get_spending_by_transponder,
    get_spending_by_vehicle,
)

router = APIRouter()
templates = Jinja2Templates(directory="src/sunpass/templates")


@router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    return templates.TemplateResponse(
        "analytics.html",
        {"request": request, "active_page": "analytics"},
    )


@router.get("/api/analytics/by-plaza")
async def api_by_plaza(start_date: str | None = None, end_date: str | None = None):
    data = await get_spending_by_plaza(start_date, end_date)
    return JSONResponse({
        "labels": [r["plaza_name"] or "Unknown" for r in data],
        "values": [r["total"] for r in data],
        "counts": [r["count"] for r in data],
    })


@router.get("/api/analytics/by-vehicle")
async def api_by_vehicle(start_date: str | None = None, end_date: str | None = None):
    data = await get_spending_by_vehicle(start_date, end_date)
    labels = []
    for r in data:
        if r.get("license_plate"):
            labels.append(f"{r['license_plate']} ({r.get('make', '')} {r.get('model', '')})")
        else:
            labels.append(r["vehicle_id"] or "Unknown")
    return JSONResponse({
        "labels": labels,
        "values": [r["total"] for r in data],
        "counts": [r["count"] for r in data],
    })


@router.get("/api/analytics/by-transponder")
async def api_by_transponder(start_date: str | None = None, end_date: str | None = None):
    data = await get_spending_by_transponder(start_date, end_date)
    return JSONResponse({
        "labels": [r["transponder_id"] or "Unknown" for r in data],
        "values": [r["total"] for r in data],
        "counts": [r["count"] for r in data],
    })


@router.get("/api/analytics/by-month")
async def api_by_month(start_date: str | None = None, end_date: str | None = None):
    data = await get_spending_by_month(start_date, end_date)
    return JSONResponse({
        "labels": [r["month"] for r in data],
        "values": [r["total"] for r in data],
        "counts": [r["count"] for r in data],
    })


@router.get("/api/analytics/by-day-of-week")
async def api_by_day_of_week(start_date: str | None = None, end_date: str | None = None):
    data = await get_spending_by_day_of_week(start_date, end_date)
    return JSONResponse({
        "labels": [r["day"] for r in data],
        "values": [r["total"] for r in data],
        "counts": [r["count"] for r in data],
    })
