from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from sunpass.db.queries import get_transponders, get_vehicles

router = APIRouter()
templates = Jinja2Templates(directory="src/sunpass/templates")


@router.get("/vehicles", response_class=HTMLResponse)
async def vehicles_page(request: Request):
    vehicles = await get_vehicles()
    transponders = await get_transponders()
    return templates.TemplateResponse(
        "vehicles.html",
        {
            "request": request,
            "vehicles": vehicles,
            "transponders": transponders,
            "active_page": "vehicles",
        },
    )
