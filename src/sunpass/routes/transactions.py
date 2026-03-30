import csv
import io

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from sunpass.db.queries import get_filter_options, get_transaction_count, get_transactions

router = APIRouter()
templates = Jinja2Templates(directory="src/sunpass/templates")


@router.get("/transactions", response_class=HTMLResponse)
async def transactions_page(
    request: Request,
    start_date: str | None = None,
    end_date: str | None = None,
    vehicle_id: str | None = None,
    transponder_id: str | None = None,
    plaza_name: str | None = None,
):
    filters = await get_filter_options()
    txns = await get_transactions(
        start_date=start_date,
        end_date=end_date,
        vehicle_id=vehicle_id,
        transponder_id=transponder_id,
        plaza_name=plaza_name,
    )
    total_count = await get_transaction_count(
        start_date=start_date,
        end_date=end_date,
        vehicle_id=vehicle_id,
        transponder_id=transponder_id,
        plaza_name=plaza_name,
    )
    return templates.TemplateResponse(
        "transactions.html",
        {
            "request": request,
            "transactions": txns,
            "total_count": total_count,
            "filters": filters,
            "start_date": start_date,
            "end_date": end_date,
            "vehicle_id": vehicle_id,
            "transponder_id": transponder_id,
            "plaza_name": plaza_name,
            "active_page": "transactions",
        },
    )


@router.get("/fragments/transaction-table", response_class=HTMLResponse)
async def transaction_table_fragment(
    request: Request,
    start_date: str | None = None,
    end_date: str | None = None,
    vehicle_id: str | None = None,
    transponder_id: str | None = None,
    plaza_name: str | None = None,
):
    txns = await get_transactions(
        start_date=start_date,
        end_date=end_date,
        vehicle_id=vehicle_id,
        transponder_id=transponder_id,
        plaza_name=plaza_name,
    )
    total_count = await get_transaction_count(
        start_date=start_date,
        end_date=end_date,
        vehicle_id=vehicle_id,
        transponder_id=transponder_id,
        plaza_name=plaza_name,
    )
    return templates.TemplateResponse(
        "fragments/transaction_table.html",
        {"request": request, "transactions": txns, "total_count": total_count},
    )


@router.get("/transactions/export")
async def export_transactions(
    start_date: str | None = None,
    end_date: str | None = None,
    vehicle_id: str | None = None,
    transponder_id: str | None = None,
    plaza_name: str | None = None,
):
    txns = await get_transactions(
        start_date=start_date,
        end_date=end_date,
        vehicle_id=vehicle_id,
        transponder_id=transponder_id,
        plaza_name=plaza_name,
        limit=10000,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Posted Date", "Plaza/Road", "Agency", "Transponder", "Vehicle", "Type", "Amount"])
    for txn in txns:
        writer.writerow([
            txn.get("transaction_date", ""),
            txn.get("posted_date", ""),
            txn.get("plaza_name", ""),
            txn.get("agency", ""),
            txn.get("transponder_id", ""),
            txn.get("vehicle_id", ""),
            txn.get("transaction_type", ""),
            txn.get("amount", ""),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sunpass_transactions.csv"},
    )
