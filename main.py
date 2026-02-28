import pandas as pd
from fastapi import File, UploadFile
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fraud_engine import detect_fraud

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/analyze", response_class=HTMLResponse)
def analyze(
    request: Request,
    invoice_no: str = Form(...),
    amount: float = Form(...),
    supplier: str = Form(...),
    buyer: str = Form(...),
    lender: str = Form(...)
):
    data = {
        "invoice_no": invoice_no,
        "amount": amount,
        "supplier": supplier,
        "buyer": buyer,
        "lender": lender
    }

    result = detect_fraud(data)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "result": result
    })
@app.post("/upload", response_class=HTMLResponse)
async def upload_csv(request: Request, file: UploadFile = File(...)):

    df = pd.read_csv(file.file)

    results = []

    for index, row in df.iterrows():

        data = {
            "invoice_no": str(row["invoice_no"]),
            "amount": float(row["amount"]),
            "supplier": str(row["supplier"]),
            "buyer": str(row["buyer"]),
            "lender": str(row["lender"])
        }

        result = detect_fraud(data)

        results.append(result)

    return templates.TemplateResponse("results.html", {
        "request": request,
        "results": results
    })