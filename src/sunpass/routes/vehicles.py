from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from sunpass.db.queries import get_transponders, get_vehicles
from sunpass.routes import templates

router = APIRouter()


@router.get("/vehicles", response_class=HTMLResponse)
async def vehicles_page(request: Request):
    vehicles = await get_vehicles()
    transponders = await get_transponders()
    return templates.TemplateResponse(
        request,
        "vehicles.html",
        {
            "vehicles": vehicles,
            "transponders": transponders,
            "active_page": "vehicles",
        },
    )
