from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from sunpass.db.queries import get_dashboard_summary
from sunpass.routes import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    summary = await get_dashboard_summary()
    return templates.TemplateResponse(
        request, "dashboard.html",
        {"summary": summary, "active_page": "dashboard"},
    )
