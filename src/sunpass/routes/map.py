from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from sunpass.db.queries import get_spending_by_plaza
from sunpass.plaza_coords import get_plaza_coords
from sunpass.routes import templates

router = APIRouter()


@router.get("/map", response_class=HTMLResponse)
async def map_page(request: Request):
    return templates.TemplateResponse(
        request,
        "map.html",
        {"active_page": "map"},
    )


@router.get("/api/map/heatmap")
async def api_heatmap(start_date: str | None = None, end_date: str | None = None):
    data = await get_spending_by_plaza(start_date, end_date)
    points = []
    unmatched = []
    for r in data:
        coords = get_plaza_coords(r["plaza_name"])
        if coords:
            points.append(
                {
                    "lat": coords[0],
                    "lng": coords[1],
                    "count": r["count"],
                    "total": r["total"],
                    "name": r["plaza_name"],
                }
            )
        else:
            unmatched.append(r["plaza_name"])

    if unmatched:
        import logging

        logging.getLogger(__name__).warning("Unmatched plazas: %s", unmatched)

    return JSONResponse({"points": points, "unmatched": unmatched})
