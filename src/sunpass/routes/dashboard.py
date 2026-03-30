from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from sunpass.db.queries import get_dashboard_summary

router = APIRouter()
templates = Jinja2Templates(directory="src/sunpass/templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    summary = await get_dashboard_summary()
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "summary": summary, "active_page": "dashboard"},
    )
