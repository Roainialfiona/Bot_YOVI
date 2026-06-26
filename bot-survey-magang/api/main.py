from fastapi import FastAPI, Depends, Query
from math import ceil
from api.auth import validate_token
from api.data import get_surveys

app = FastAPI(title="Mock Internal API")

DATA = get_surveys()

@app.get("/validate")
def validate(_: bool = Depends(validate_token)):
    return {"status": "ok"}

@app.get("/sales-agent-surveys")
def surveys(
    witel_id: int,
    page: int = Query(1),
    per_page: int = Query(50),
    _: bool = Depends(validate_token)
):
    total = len(DATA)
    total_pages = ceil(total / per_page)

    start = (page - 1) * per_page
    end = start + per_page

    return {
        "data": DATA[start:end],
        "links": {
            "last": f"http://localhost:8000/sales-agent-surveys?page={total_pages}"
        }
    }
