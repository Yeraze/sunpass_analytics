from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from sunpass.db.queries import (
    get_spending_by_day_of_week,
    get_spending_by_month,
    get_spending_by_plaza,
    get_spending_by_transponder,
    get_spending_by_vehicle,
)
from sunpass.routes import templates

router = APIRouter()


@router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    return templates.TemplateResponse(
        request, "analytics.html",
        {"active_page": "analytics"},
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
        name = r.get("friendly_name") or r.get("license_plate") or r.get("vehicle_id") or "Unknown"
        if r.get("license_plate") and r.get("friendly_name"):
            name = f"{r['friendly_name']} ({r['license_plate']})"
        elif r.get("license_plate"):
            name = r["license_plate"]
        labels.append(name)
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
